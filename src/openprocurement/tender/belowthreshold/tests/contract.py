# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from datetime import timedelta

from openprocurement.api.tests.base import snitch
from openprocurement.api.utils import get_now

from openprocurement.tender.belowthreshold.tests.base import (
    TenderContentWebTest,
    test_tender_below_bids,
    test_tender_below_lots,
    test_tender_below_organization,
    test_tender_below_multi_buyers_data,
)
from openprocurement.tender.belowthreshold.tests.contract_blanks import (
    # TenderContractResourceTest
    create_tender_contract_invalid,
    create_tender_contract,
    create_tender_contract_in_complete_status,
    patch_tender_contract,
    patch_tender_contract_rationale_simple,
    get_tender_contract,
    get_tender_contracts,
    # Tender2LotContractResourceTest
    lot2_patch_tender_contract,
    lot2_patch_tender_contract_rationale_simple,
    # TenderContractDocumentResourceTest
    not_found,
    create_tender_contract_document,
    put_tender_contract_document,
    patch_tender_contract_document,
    # Tender2LotContractDocumentResourceTest
    lot2_create_tender_contract_document,
    lot2_put_tender_contract_document,
    lot2_patch_tender_contract_document,
    patch_tender_contract_value_vat_not_included,
    patch_tender_contract_value,
    patch_tender_contract_status_by_owner,
    patch_tender_contract_status_by_supplier,
    patch_tender_contract_status_by_others,
    create_tender_contract_document_by_supplier,
    create_tender_contract_document_by_others,
    put_tender_contract_document_by_supplier,
    put_tender_contract_document_by_others,
    patch_tender_contract_document_by_supplier,
    lot2_create_tender_contract_document_by_supplier,
    lot2_create_tender_contract_document_by_others,
    lot2_put_tender_contract_document_by_supplier,
    lot2_patch_tender_contract_document_by_supplier,
    patch_contract_single_item_unit_value,
    patch_contract_single_item_unit_value_with_status,
    patch_contract_single_item_unit_value_round,
    patch_contract_multi_items_unit_value,
    patch_tender_multi_contracts,
    patch_tender_multi_contracts_cancelled,
    patch_tender_multi_contracts_cancelled_with_one_activated,
    patch_tender_multi_contracts_cancelled_validate_amount,
    # Econtract
    create_econtract,
    cancelling_award_contract_sync,
    patch_multiple_contracts_in_contracting,
)


class TenderContractResourceTestMixin(object):
    test_create_tender_contract_invalid = snitch(create_tender_contract_invalid)
    test_get_tender_contract = snitch(get_tender_contract)
    test_get_tender_contracts = snitch(get_tender_contracts)


class TenderContractDocumentResourceTestMixin(object):
    test_not_found = snitch(not_found)
    test_create_tender_contract_document = snitch(create_tender_contract_document)
    test_put_tender_contract_document = snitch(put_tender_contract_document)
    test_patch_tender_contract_document = snitch(patch_tender_contract_document)


class TenderEcontractResourceTestMixin:
    test_create_econtract = snitch(create_econtract)
    test_cancelling_award_contract_sync = snitch(cancelling_award_contract_sync)


class TenderEContractMultiBuyersResourceTestMixin:
    test_patch_multiple_contracts_in_contracting = snitch(patch_multiple_contracts_in_contracting)


class CreateActiveAwardMixin:
    def create_award(self):
        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "value": self.initial_data["value"],
                }
            },
        )
        self.app.authorization = auth
        award = response.json["data"]
        self.award_id = award["id"]
        self.award_value = award["value"]
        self.award_suppliers = award["suppliers"]

        response = self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

        response = self.app.get(f"/tenders/{self.tender_id}")
        self.contracts_ids = [i["id"] for i in response.json["data"].get("contracts", "")]
        self.bid_token = self.initial_bids_tokens[award["bid_id"]]


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractResourceTest(TenderContentWebTest, CreateActiveAwardMixin, TenderContractResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        self.create_award()

    test_create_tender_contract = snitch(create_tender_contract)
    test_create_tender_contract_in_complete_status = snitch(create_tender_contract_in_complete_status)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_patch_tender_contract_rationale_simple = snitch(patch_tender_contract_rationale_simple)
    test_patch_tender_contract_value = snitch(patch_tender_contract_value)
    test_patch_tender_contract_status_by_owner = snitch(patch_tender_contract_status_by_owner)
    test_patch_tender_contract_status_by_supplier = snitch(patch_tender_contract_status_by_supplier)
    test_patch_tender_contract_status_by_others = snitch(patch_tender_contract_status_by_others)
    test_patch_contract_single_item_unit_value = snitch(patch_contract_single_item_unit_value)
    test_patch_contract_single_item_unit_value_with_status = snitch(
        patch_contract_single_item_unit_value_with_status
    )
    test_patch_contract_single_item_unit_value_round = snitch(
        patch_contract_single_item_unit_value_round
    )
    test_patch_contract_multi_items_unit_value = snitch(patch_contract_multi_items_unit_value)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractVATNotIncludedResourceTest(TenderContentWebTest, TenderContractResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids

    def create_award(self):
        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "items": self.initial_data["items"],
                    "value": {
                        "amount": self.initial_data["value"]["amount"],
                        "currency": self.initial_data["value"]["currency"],
                        "valueAddedTaxIncluded": False,
                    },
                }
            },
        )
        self.app.authorization = auth
        self.award_id = response.json["data"]["id"]
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractVATNotIncludedResourceTest, self).setUp()
        self.create_award()

    test_patch_tender_contract_value_vat_not_included = snitch(patch_tender_contract_value_vat_not_included)
    test_patch_tender_contract_status_by_owner = snitch(patch_tender_contract_status_by_owner)
    test_patch_tender_contract_status_by_supplier = snitch(patch_tender_contract_status_by_supplier)
    test_patch_tender_contract_status_by_others = snitch(patch_tender_contract_status_by_others)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class Tender2LotContractResourceTest(TenderContentWebTest):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids
    initial_lots = 2 * test_tender_below_lots

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(Tender2LotContractResourceTest, self).setUp()
        # Create award

        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "lotID": self.initial_lots[0]["id"],
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]
        self.app.authorization = auth
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

    test_lot2_patch_tender_contract = snitch(lot2_patch_tender_contract)
    test_lot2_patch_tender_contract_rationale_simple = snitch(lot2_patch_tender_contract_rationale_simple)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractDocumentResourceTest(TenderContentWebTest, TenderContractDocumentResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids
    docservice = True

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()
        # Create award
        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))

        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {"data": {"suppliers": [test_tender_below_organization], "status": "pending", "bid_id": self.initial_bids[0]["id"]}},
        )
        award = response.json["data"]
        self.award_id = award["id"]

        self.app.authorization = auth
        response = self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

        # Create contract for award
        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))

        response = self.app.post_json(
            "/tenders/{}/contracts".format(self.tender_id),
            {"data": {"title": "contract title", "description": "contract description", "awardID": self.award_id}},
        )
        contract = response.json["data"]
        self.contract_id = contract["id"]
        self.app.authorization = auth

    test_create_tender_contract_document_by_supplier = snitch(create_tender_contract_document_by_supplier)
    test_create_tender_contract_document_by_others = snitch(create_tender_contract_document_by_others)
    test_put_tender_contract_document_by_supplier = snitch(put_tender_contract_document_by_supplier)
    test_put_tender_contract_document_by_others = snitch(put_tender_contract_document_by_others)
    test_patch_tender_contract_document_by_supplier = snitch(patch_tender_contract_document_by_supplier)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class Tender2LotContractDocumentResourceTest(TenderContentWebTest):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids
    initial_lots = 2 * test_tender_below_lots
    docservice = True

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(Tender2LotContractDocumentResourceTest, self).setUp()
        # Create award
        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))

        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "lotID": self.initial_lots[0]["id"],
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]

        self.app.authorization = auth
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )
        # Create contract for award

        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/contracts".format(self.tender_id),
            {"data": {"title": "contract title", "description": "contract description", "awardID": self.award_id}},
        )
        contract = response.json["data"]
        self.contract_id = contract["id"]
        self.app.authorization = auth

    test_lot2_create_tender_contract_document = snitch(lot2_create_tender_contract_document)
    test_lot2_put_tender_contract_document = snitch(lot2_put_tender_contract_document)
    test_lot2_patch_tender_contract_document = snitch(lot2_patch_tender_contract_document)
    test_lot2_create_tender_contract_document_by_supplier = snitch(lot2_create_tender_contract_document_by_supplier)
    test_lot2_create_tender_contract_document_by_others = snitch(lot2_create_tender_contract_document_by_others)
    test_lot2_put_tender_contract_document_by_supplier = snitch(lot2_put_tender_contract_document_by_supplier)
    test_lot2_patch_tender_contract_document_by_supplier = snitch(lot2_patch_tender_contract_document_by_supplier)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractMultiBuyersResourceTest(TenderContentWebTest):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids
    initial_data = test_tender_below_multi_buyers_data

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractMultiBuyersResourceTest, self).setUp()
        TenderContractResourceTest.create_award(self)

    test_patch_tender_multi_contracts = snitch(patch_tender_multi_contracts)
    test_patch_tender_multi_contracts_cancelled = snitch(patch_tender_multi_contracts_cancelled)
    test_patch_tender_multi_contracts_cancelled_with_one_activated = snitch(
        patch_tender_multi_contracts_cancelled_with_one_activated
    )
    test_patch_tender_multi_contracts_cancelled_validate_amount = snitch(
        patch_tender_multi_contracts_cancelled_validate_amount
    )


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderLotContractMultiBuyersResourceTest(TenderContentWebTest):
    initial_status = "active.qualification"
    initial_data = test_tender_below_multi_buyers_data
    initial_bids = test_tender_below_bids
    initial_lots = test_tender_below_lots

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderLotContractMultiBuyersResourceTest, self).setUp()
        # Create award

        auth = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "lotID": self.initial_lots[0]["id"],
                    "value": self.initial_data["value"],
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]
        self.app.authorization = auth
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active"}},
        )

    test_patch_lot_tender_multi_contracts = snitch(patch_tender_multi_contracts)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() - timedelta(days=1))
class TenderEContractResourceTest(
    TenderContentWebTest,
    CreateActiveAwardMixin,
    TenderEcontractResourceTestMixin,
):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() - timedelta(days=1))
    def setUp(self):
        super().setUp()
        self.create_award()


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() - timedelta(days=1))
class TenderEContractMultiBuyersResourceTest(
    TenderContentWebTest,
    CreateActiveAwardMixin,
    TenderEContractMultiBuyersResourceTestMixin,
):
    initial_status = "active.qualification"
    initial_bids = test_tender_below_bids
    initial_data = test_tender_below_multi_buyers_data

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() - timedelta(days=1))
    def setUp(self):
        super().setUp()
        self.create_award()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractVATNotIncludedResourceTest))
    suite.addTest(unittest.makeSuite(Tender2LotContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractMultiBuyersResourceTest))
    suite.addTest(unittest.makeSuite(TenderLotContractMultiBuyersResourceTest))
    suite.addTest(unittest.makeSuite(TenderEContractResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
