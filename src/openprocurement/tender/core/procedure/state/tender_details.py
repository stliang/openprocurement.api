from datetime import timedelta
from typing import TYPE_CHECKING

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from openprocurement.framework.dps.constants import DPS_TYPE
from openprocurement.tender.core.constants import (
    PROCUREMENT_METHOD_SELECTIVE,
    LIMITED_PROCUREMENT_METHOD_TYPES,
    PROCUREMENT_METHOD_LIMITED,
    PROCUREMENT_METHOD_OPEN,
    SELECTIVE_PROCUREMENT_METHOD_TYPES,
    AGREEMENT_NOT_FOUND_MESSAGE,
)
from openprocurement.tender.core.procedure.context import (
    get_request,
    get_tender_config,
)
from openprocurement.api.context import get_now
from openprocurement.tender.core.procedure.utils import (
    dt_from_iso,
    set_mode_test_titles,
    tender_created_before,
    validate_field,
    tender_created_after,
)
from openprocurement.api.utils import (
    raise_operation_error,
)
from openprocurement.api.constants import (
    RELEASE_ECRITERIA_ARTICLE_17,
    TENDER_PERIOD_START_DATE_STALE_MINUTES,
    TENDER_CONFIG_OPTIONALITY,
    TENDER_CONFIG_JSONSCHEMAS,
    RELATED_LOT_REQUIRED_FROM,
)
from openprocurement.tender.core.procedure.state.tender import TenderState
from openprocurement.tender.core.utils import (
    calculate_tender_business_date,
    calculate_complaint_business_date,
)
from openprocurement.tender.open.constants import COMPETITIVE_ORDERING, ABOVE_THRESHOLD
from openprocurement.tender.core.constants import (
    AGREEMENT_STATUS_MESSAGE,
    AGREEMENT_CONTRACTS_MESSAGE,
    AGREEMENT_IDENTIFIER_MESSAGE,
)

if TYPE_CHECKING:
    baseclass = TenderState
else:
    baseclass = object


class TenderConfigMixin(baseclass):
    configurations = (
        "hasAuction",
        "hasAwardingOrder",
        "hasValueRestriction",
        "valueCurrencyEquality",
        "hasPrequalification",
        "minBidsNumber",
        "hasPreSelectionAgreement",
    )

    def validate_config(self, data):
        config = get_tender_config()
        for config_name in self.configurations:
            value = config.get(config_name)

            if value is None and TENDER_CONFIG_OPTIONALITY.get(config_name, True) is False:
                raise_operation_error(
                    self.request,
                    "This field is required.",
                    status=422,
                    location="body",
                    name=config_name,
                )

            procurement_method_type = data.get("procurementMethodType")
            config_schema = TENDER_CONFIG_JSONSCHEMAS.get(procurement_method_type)
            if not config_schema:
                raise NotImplementedError
            schema = config_schema["properties"][config_name]
            try:
                validate(value, schema)
            except ValidationError as e:
                raise_operation_error(
                    self.request,
                    e.message,
                    status=422,
                    location="body",
                    name=config_name,
                )


class TenderDetailsMixing(TenderConfigMixin, baseclass):
    """
    describes business logic rules for tender owners
    when they prepare tender for tendering stage
    """

    config: dict

    tender_create_accreditations = None
    tender_central_accreditations = None
    tender_edit_accreditations = None

    required_exclusion_criteria = {
        "CRITERION.EXCLUSION.CONVICTIONS.PARTICIPATION_IN_CRIMINAL_ORGANISATION",
        "CRITERION.EXCLUSION.CONVICTIONS.FRAUD",
        "CRITERION.EXCLUSION.CONVICTIONS.CORRUPTION",
        "CRITERION.EXCLUSION.CONVICTIONS.CHILD_LABOUR-HUMAN_TRAFFICKING",
        "CRITERION.EXCLUSION.CONTRIBUTIONS.PAYMENT_OF_TAXES",
        "CRITERION.EXCLUSION.BUSINESS.BANKRUPTCY",
        "CRITERION.EXCLUSION.MISCONDUCT.MARKET_DISTORTION",
        "CRITERION.EXCLUSION.CONFLICT_OF_INTEREST.MISINTERPRETATION",
        "CRITERION.EXCLUSION.NATIONAL.OTHER",
    }

    enquiry_period_timedelta: timedelta
    enquiry_stand_still_timedelta: timedelta
    allow_tender_period_start_date_change = False
    pre_qualification_complaint_stand_still = timedelta(days=0)
    tendering_period_extra_working_days = False
    agreement_min_active_contracts = 3
    items_classification_prefix_length_default = 4
    should_validate_pre_selection_agreement = True

    def validate_tender_patch(self, before, after):
        request = get_request()
        if before["status"] != after["status"]:
            self.validate_cancellation_blocks(request, before)

    def on_post(self, tender):
        self.validate_config(tender)
        self.validate_procurement_method(tender)
        self.validate_lots_count(tender)
        self.validate_minimal_step(tender)
        self.validate_submission_method(tender)
        self.validate_items_classification_prefix(tender)
        self.watch_value_meta_changes(tender)
        self.update_date(tender)
        super().on_post(tender)

        # set author for documents passed with tender data
        for doc in tender.get("documents", ""):
            doc["author"] = "tender_owner"

    def on_patch(self, before, after):
        self.validate_procurement_method(after, before=before)
        self.validate_lots_count(after)
        self.validate_pre_qualification_status_change(before, after)
        self.validate_tender_period_start_date_change(before, after)
        self.validate_minimal_step(after, before=before)
        self.validate_submission_method(after, before=before)
        self.validate_kind_change(after, before)
        self.validate_award_criteria_change(after, before)
        self.validate_items_classification_prefix(after)
        self.watch_value_meta_changes(after)
        super().on_patch(before, after)

    def always(self, data):
        self.set_mode_test(data)
        super().always(data)

    def status_up(self, before, after, data):
        if after == "draft" and before != "draft":
            raise_operation_error(
                get_request(),
                "Can't change status to draft",
                status=422,
                location="body",
                name="status"
            )
        if after != "draft" and before == "draft":
            self.validate_pre_selection_agreement(data)
        elif after == "active.tendering" and before != "active.tendering":
            tendering_start = data["tenderPeriod"]["startDate"]
            if dt_from_iso(tendering_start) <= get_now() - timedelta(minutes=TENDER_PERIOD_START_DATE_STALE_MINUTES):
                raise_operation_error(
                    get_request(),
                    "tenderPeriod.startDate should be in greater than current date",
                    status=422,
                    location="body",
                    name="tenderPeriod.startDate"
                )
        super().status_up(before, after, data)


    _agreement = None

    def get_agreement(self, tender):
        agreements = tender.get("agreements")
        if not agreements:
            return None
        if not self._agreement:
            self._agreement = self.request.registry.mongodb.agreements.get(agreements[0]["id"])
        return self._agreement


    def validate_pre_selection_agreement(self, tender):
        if self.should_validate_pre_selection_agreement is False:
            return

        def raise_agreements_error(message):
            raise_operation_error(
                self.request,
                message,
                status=422,
                location="body",
                name="agreements",
            )

        config = get_tender_config()
        if config["hasPreSelectionAgreement"] is True:
            agreements = tender.get("agreements")
            if not agreements:
                raise_agreements_error("This field is required.")

            if len(agreements) != 1:
                raise_agreements_error("Exactly one agreement is expected.")

            agreement = self.get_agreement(tender)

            tender_agreement_type_mapping = {
                COMPETITIVE_ORDERING: DPS_TYPE
            }

            if tender_agreement_type_mapping.get(tender["procurementMethodType"]) != agreement["agreementType"]:
                raise_agreements_error("Agreement type mismatch.")

            if not agreement:
                raise_agreements_error(AGREEMENT_NOT_FOUND_MESSAGE)

            if self.is_agreement_not_active(agreement):
                raise_agreements_error(AGREEMENT_STATUS_MESSAGE)

            if self.has_insufficient_active_contracts(agreement):
                raise_agreements_error(AGREEMENT_CONTRACTS_MESSAGE.format(self.agreement_min_active_contracts))

            if self.has_mismatched_procuring_entities(tender, agreement):
                raise_agreements_error(AGREEMENT_IDENTIFIER_MESSAGE)

    def set_mode_test(self, tender):
        config = get_tender_config()
        if config.get("test"):
            tender["mode"] = "test"
        if tender.get("mode") == "test":
            set_mode_test_titles(tender)

    def validate_lots_count(self, tender):
        if tender.get("procurementMethodType") == COMPETITIVE_ORDERING:
            # TODO: consider using config
            max_lots_count = 1
            if len(tender.get("lots", "")) > max_lots_count:
                raise_operation_error(
                    get_request(),
                    "Can't create more than {} lots".format(max_lots_count),
                    status=422,
                    location="body",
                    name="lots"
                )

    def validate_pre_qualification_status_change(self, before, after):
        # TODO: find a better place for this check, may be a distinct endpoint: PUT /tender/uid/status
        if before["status"] == "active.pre-qualification":
            passed_data = get_request().validated["json_data"]
            if passed_data != {"status": "active.pre-qualification.stand-still"}:
                raise_operation_error(
                    get_request(),
                    "Can't update tender at 'active.pre-qualification' status",
                )
            else:  # switching to active.pre-qualification.stand-still
                lots = after.get("lots")
                if lots:
                    active_lots = {lot["id"] for lot in lots if lot.get("status", "active") == "active"}
                else:
                    active_lots = {None}

                if any(
                    i["status"] in self.block_complaint_status
                    for q in after["qualifications"]
                    for i in q.get("complaints", "")
                    if q.get("lotID") in active_lots
                ):
                    raise_operation_error(
                        get_request(),
                        "Can't switch to 'active.pre-qualification.stand-still' before resolve all complaints"
                    )

                if self.all_bids_are_reviewed(after):
                    after["qualificationPeriod"]["endDate"] = calculate_complaint_business_date(
                        get_now(), self.pre_qualification_complaint_stand_still, after
                    ).isoformat()
                    after["qualificationPeriod"]["reportingDatePublication"] = get_now().isoformat()
                else:
                    raise_operation_error(
                        get_request(),
                        "Can't switch to 'active.pre-qualification.stand-still' while not all bids are qualified",
                    )

        # before status != active.pre-qualification
        elif after["status"] == "active.pre-qualification.stand-still":
            raise_operation_error(
                get_request(),
                f"Can't switch to 'active.pre-qualification.stand-still' from {before['status']}",
            )

    @staticmethod
    def all_bids_are_reviewed(tender):
        bids = tender.get("bids", "")
        lots = tender.get("lots")
        if lots:
            active_lots = {lot["id"] for lot in lots if lot.get("status", "active") == "active"}
            return all(
                lotValue.get("status") != "pending"
                for bid in bids
                if bid.get("status") not in ("invalid", "deleted")
                for lotValue in bid.get("lotValues", "")
                if lotValue["relatedLot"] in active_lots

            )
        else:
            return all(bid.get("status") != "pending" for bid in bids)

    @staticmethod
    def all_awards_are_reviewed(tender):
        """
        checks if all tender awards are reviewed
        """
        return all(award["status"] != "pending" for award in tender["awards"])

    @staticmethod
    def update_date(tender):
        now = get_now().isoformat()
        tender["date"] = now

        for lot in tender.get("lots", ""):
            lot["date"] = now

    @staticmethod
    def watch_value_meta_changes(tender):
        # tender currency and valueAddedTaxIncluded must be specified only ONCE
        # instead it's specified in many places but we need keep them the same
        value = tender.get("value")
        if not value:
            return
        currency = value.get("currency")
        tax_inc = value.get("valueAddedTaxIncluded")

        # items
        for item in tender["items"]:
            if "unit" in item and "value" in item["unit"]:
                item["unit"]["value"]["currency"] = currency
                item["unit"]["value"]["valueAddedTaxIncluded"] = tax_inc

        # lots
        for lot in tender.get("lots", ""):
            value = lot.get("value")
            if value:
                value["currency"] = currency
                value["valueAddedTaxIncluded"] = tax_inc

            minimal_step = lot.get("minimalStep")
            if minimal_step:
                minimal_step["currency"] = currency
                minimal_step["valueAddedTaxIncluded"] = tax_inc

    def validate_tender_period_start_date_change(self, before, after):
        if self.allow_tender_period_start_date_change:
            return

        if "draft" in before["status"]:
            # draft, draft.stage2
            # still can change tenderPeriod.startDate
            return

        tender_period_start_before = before.get("tenderPeriod", {}).get("startDate")
        tender_period_start_after = after.get("tenderPeriod", {}).get("startDate")
        if tender_period_start_before != tender_period_start_after:
            raise_operation_error(
                get_request(),
                "Can't change tenderPeriod.startDate",
                status=422,
                location="body",
                name="tenderPeriod.startDate"
            )

    def validate_award_criteria_change(self, after, before):
        if before.get("awardCriteria") != after.get("awardCriteria"):
            raise_operation_error(
                get_request(),
                "Can't change awardCriteria",
                name="awardCriteria"
            )

    def validate_kind_change(self, after, before):
        if before["status"] not in ("draft", "draft.stage2"):
            if before["procuringEntity"].get("kind") != after["procuringEntity"].get("kind"):
                raise_operation_error(
                    get_request(),
                    "Can't change procuringEntity.kind in a public tender",
                    status=422,
                    location="body",
                    name="procuringEntity"
                )

    @classmethod
    def validate_tender_exclusion_criteria(cls, before, after):
        if tender_created_before(RELEASE_ECRITERIA_ARTICLE_17):
            return

        if after.get("status") not in ("active", "active.tendering"):
            return

        tender_criteria = {
            criterion["classification"]["id"]
            for criterion in after.get("criteria", "")
            if criterion.get("classification")
        }

        # exclusion criteria
        if cls.required_exclusion_criteria - tender_criteria:
            raise_operation_error(
                get_request(),
                f"Tender must contain all required `EXCLUSION` criteria: "
                f"{', '.join(sorted(cls.required_exclusion_criteria))}",
            )

    @staticmethod
    def validate_tender_language_criteria(before, after):
        if tender_created_before(RELEASE_ECRITERIA_ARTICLE_17):
            return

        if after.get("status") not in ("active", "active.tendering"):
            return

        tender_criteria = {
            criterion["classification"]["id"]
            for criterion in after.get("criteria", "")
            if criterion.get("classification")
        }
        language_criterion = "CRITERION.OTHER.BID.LANGUAGE"
        if language_criterion not in tender_criteria:
            raise_operation_error(get_request(), f"Tender must contain {language_criterion} criterion")

    def validate_minimal_step(self, data, before=None):
        config = get_tender_config()
        kwargs = {
            "before": before,
            "enabled": config.get("hasAuction") is True,
        }
        validate_field(data, "minimalStep", **kwargs)

    def validate_submission_method(self, data, before=None):
        config = get_tender_config()
        kwargs = {
            "before": before,
            "enabled": config.get("hasAuction") is True,
        }
        validate_field(data, "submissionMethod", default="electronicAuction", **kwargs)
        validate_field(data, "submissionMethodDetails", required=False, **kwargs)
        validate_field(data, "submissionMethodDetails_en", required=False, **kwargs)
        validate_field(data, "submissionMethodDetails_ru", required=False, **kwargs)

    @staticmethod
    def default_procurement_method(data):
        config = get_tender_config()
        if config["hasPreSelectionAgreement"] is True:
            return PROCUREMENT_METHOD_SELECTIVE
        if data["procurementMethodType"] in SELECTIVE_PROCUREMENT_METHOD_TYPES:
            return PROCUREMENT_METHOD_SELECTIVE
        if data["procurementMethodType"] in LIMITED_PROCUREMENT_METHOD_TYPES:
            return PROCUREMENT_METHOD_LIMITED
        return PROCUREMENT_METHOD_OPEN

    def validate_procurement_method(self, data, before=None):
        default_procurement_method = self.default_procurement_method(data)
        if before is None and data.get("procurementMethod") is None:
            # default on post only
            data["procurementMethod"] = default_procurement_method
        if data.get("procurementMethod") != default_procurement_method:
            raise_operation_error(
                self.request,
                "procurementMethod should be {}".format(default_procurement_method),
                status=422,
                location="body",
                name="procurementMethod",
            )

    @classmethod
    def get_items_classification_prefix_length(cls, tender):
        if any(i.get("classification")['id'][:3] == "336" for i in tender.get("items", "")):
            # medicine
            return 3
        else:
            return cls.items_classification_prefix_length_default

    @staticmethod
    def get_items_classification_prefix_name(length):
        LENGTH_TO_NAME = {
            3: "group",
            4: "class",
            5: "category",
            6: "subcategory",
        }
        return LENGTH_TO_NAME[length]

    def validate_items_classification_prefix(self, tender):
        if not self.items_classification_prefix_length_default:
            return

        classification_prefix_list = set()
        classification_prefix_length = self.get_items_classification_prefix_length(tender)
        classification_prefix_name = self.get_items_classification_prefix_name(classification_prefix_length)
        error_message = f"CPV {classification_prefix_name} of items should be identical"

        for item in tender.get("items", ""):
            classification_prefix_list.add(item["classification"]["id"][:classification_prefix_length])

        if self.should_validate_pre_selection_agreement:
            agreement = self.get_agreement(tender)
            if agreement:
                classification_prefix_list.add(agreement["classification"]["id"][:classification_prefix_length])
                error_message = f"CPV {classification_prefix_name} of items should be identical to agreement"

        if len(classification_prefix_list) != 1:
            raise_operation_error(
                get_request(),
                [error_message],
                status=422,
                name="items"
            )

    @classmethod
    def validate_items_classification_prefix_unchanged(cls, before, after):
        classification_prefix_list = set()
        classification_prefix_length = 3  # group
        for item in before.get("items", ""):
            classification_prefix_list.add(item["classification"]["id"][:classification_prefix_length])
        for item in after.get("items", ""):
            classification_prefix_list.add(item["classification"]["id"][:classification_prefix_length])
        if len(classification_prefix_list) != 1:
            name = cls.get_items_classification_prefix_name(classification_prefix_length)
            raise_operation_error(
                get_request(),
                [f"Can't change classification {name} of items"],
                status=422,
                name="items"
            )

    def validate_tender_period_extension(self, tender):
        if "tenderPeriod" in tender and "endDate" in tender["tenderPeriod"]:
            tendering_end = dt_from_iso(tender["tenderPeriod"]["endDate"])
            if calculate_tender_business_date(
                get_now(),
                self.tendering_period_extra,
                tender=tender,
                working_days=self.tendering_period_extra_working_days,
            ) > tendering_end:
                raise_operation_error(
                    get_request(),
                    "tenderPeriod should be extended by {0.days} {1}".format(
                        self.tendering_period_extra,
                        "working days" if self.tendering_period_extra_working_days else "days",
                    )
                )

    @staticmethod
    def calculate_item_identification_tuple(item):
        result = (
            item["id"],
            item["classification"]["id"],
            item["classification"]["scheme"],
            item["unit"]["code"] if item.get("unit") else None,
            tuple((c["id"], c["scheme"]) for c in item.get("additionalClassifications", ""))
        )
        return result

    @classmethod
    def is_agreement_not_active(cls, agreement):
        return agreement.get("status") != "active"

    @classmethod
    def has_insufficient_active_contracts(cls, agreement):
        active_contracts_count = sum(
            c["status"] == "active"
            for c in agreement.get("contracts", "")
        )
        return active_contracts_count < cls.agreement_min_active_contracts

    @classmethod
    def has_mismatched_procuring_entities(cls, tender, agreement):
        agreement_identifier = agreement["procuringEntity"]["identifier"]
        tender_identifier = tender["procuringEntity"]["identifier"]
        return (
            tender_identifier["id"] != agreement_identifier["id"]
            or tender_identifier["scheme"] != agreement_identifier["scheme"]
        )

    def validate_related_lot_in_items(self, after):
        if (tender_created_after(RELATED_LOT_REQUIRED_FROM) or after.get("procurementMethodType") == ABOVE_THRESHOLD)\
                and after["status"] != "draft":
            for item in after["items"]:
                if not item.get("relatedLot"):
                    raise_operation_error(
                        get_request(),
                        "This field is required",
                        status=422,
                        location="body",
                        name="item.relatedLot"
                    )


class TenderDetailsState(TenderDetailsMixing, TenderState):
    pass
