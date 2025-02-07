from typing import TYPE_CHECKING, TypeVar

from openprocurement.api.auth import ACCR_3, ACCR_5, ACCR_4
from openprocurement.tender.core.procedure.context import get_request
from openprocurement.api.context import get_now
from openprocurement.tender.core.utils import calculate_complaint_business_date
from openprocurement.tender.cfaua.procedure.state.tender import CFAUATenderState
from openprocurement.tender.cfaua.constants import (
    TENDERING_EXTRA_PERIOD,
    ENQUIRY_PERIOD_TIME,
    ENQUIRY_STAND_STILL_TIME,
    QUALIFICATION_COMPLAINT_STAND_STILL,
    PREQUALIFICATION_COMPLAINT_STAND_STILL,
)
from openprocurement.api.utils import raise_operation_error
from openprocurement.tender.openua.procedure.state.tender_details import OpenUATenderDetailsMixing


if TYPE_CHECKING:
    baseclass = CFAUATenderState
else:
    baseclass = object


class CFAUATenderDetailsMixing(OpenUATenderDetailsMixing, baseclass):
    tender_create_accreditations = (ACCR_3, ACCR_5)
    tender_central_accreditations = (ACCR_5,)
    tender_edit_accreditations = (ACCR_4,)

    tendering_period_extra = TENDERING_EXTRA_PERIOD
    enquiry_period_timedelta = - ENQUIRY_PERIOD_TIME
    enquiry_stand_still_timedelta = ENQUIRY_STAND_STILL_TIME
    pre_qualification_complaint_stand_still = PREQUALIFICATION_COMPLAINT_STAND_STILL
    qualification_complaint_stand_still = QUALIFICATION_COMPLAINT_STAND_STILL
    tendering_period_extra_working_days = False

    def on_post(self, tender):
        super().on_post(tender)
        self.initialize_enquiry_period(tender)

    def on_patch(self, before, after):
        self.validate_items_classification_prefix_unchanged(before, after)
        self.validate_qualification_status_change(before, after)

        # bid invalidation rules
        if before["status"] == "active.tendering":
            self.validate_tender_period_extension(after)
            self.invalidate_bids_data(after)
        elif after["status"] == "active.tendering":
            after["enquiryPeriod"]["invalidationDate"] = get_now().isoformat()

        if after["status"] in ("draft", "active.tendering"):
            self.initialize_enquiry_period(after)

        self.validate_tender_exclusion_criteria(before, after)
        self.validate_tender_language_criteria(before, after)
        super().on_patch(before, after)  # TenderDetailsMixing.on_patch

    def status_up(self, before, after, data):
        if (
            before == "draft" and after == "active.tendering"
            or before == "active.pre-qualification" and after == "active.pre-qualification.stand-still"
            or before == "active.qualification" and after == "active.qualification.stand-still"
        ):
            pass  # allowed scenario
        else:
            raise_operation_error(
                get_request(),
                f"Can't update tender to {after} status",
                status=403,
                location="body",
                name="status"
            )
        super().status_up(before, after, data)


    def validate_qualification_status_change(self, before, after):
        if before["status"] == "active.qualification":
            passed_data = get_request().validated["json_data"]
            if passed_data != {"status": "active.qualification.stand-still"}:
                raise_operation_error(
                    get_request(),
                    "Can't update tender at 'active.qualification' status",
                )
            else:  # switching to active.qualification.stand-still
                lots = after.get("lots")
                if lots:
                    active_lots = {lot["id"] for lot in lots if lot.get("status", "active") == "active"}
                else:
                    active_lots = {None}

                if any(
                    i["status"] in self.block_complaint_status
                    for q in after["awards"]
                    for i in q.get("complaints", "")
                    if q.get("lotID") in active_lots
                ):
                    raise_operation_error(
                        get_request(),
                        "Can't switch to 'active.qualification.stand-still' before resolve all complaints"
                    )

                if self.all_awards_are_reviewed(after):
                    after["awardPeriod"]["endDate"] = calculate_complaint_business_date(
                        get_now(), self.qualification_complaint_stand_still, after
                    ).isoformat()
                    for award in after["awards"]:
                        if award["status"] != "cancelled":
                            award["complaintPeriod"] = {
                                "startDate": get_now().isoformat(),
                                "endDate": after["awardPeriod"]["endDate"],
                            }
                else:
                    raise_operation_error(
                        get_request(),
                        "Can't switch to 'active.qualification.stand-still' while not all awards are qualified",
                    )

        # before status != active.qualification
        elif after["status"] == "active.qualification.stand-still":
            raise_operation_error(
                get_request(),
                f"Can't switch to 'active.qualification.stand-still' from {before['status']}",
            )


    @staticmethod
    def watch_value_meta_changes(tender):
        pass  # TODO: shouldn't it work here


class CFAUATenderDetailsState(CFAUATenderDetailsMixing, CFAUATenderState):
    pass
