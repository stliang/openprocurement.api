# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from datetime import timedelta

from openprocurement.api.tests.base import snitch
from openprocurement.api.utils import get_now

from openprocurement.tender.belowthreshold.tests.base import test_tender_below_organization
from openprocurement.tender.belowthreshold.tests.contract import (
    TenderContractResourceTestMixin,
    TenderContractDocumentResourceTestMixin,
)

from openprocurement.tender.openua.tests.contract_blanks import (
    create_tender_contract,
    patch_tender_contract,
)

from openprocurement.tender.openuadefense.tests.base import (
    BaseTenderUAContentWebTest,
    test_tender_openuadefense_bids,
)

from openprocurement.tender.belowthreshold.tests.contract_blanks import (
    patch_tender_contract_value_vat_not_included,
    patch_tender_contract_value,
    patch_tender_contract_status_by_owner,
    patch_tender_contract_status_by_others,
    patch_tender_contract_status_by_supplier,
    create_tender_contract_document_by_supplier,
    create_tender_contract_document_by_others,
    put_tender_contract_document_by_supplier,
    put_tender_contract_document_by_others,
    patch_tender_contract_document_by_supplier,
    patch_contract_single_item_unit_value,
    patch_contract_single_item_unit_value_with_status,
    patch_contract_multi_items_unit_value,
)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractResourceTest(BaseTenderUAContentWebTest, TenderContractResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_openuadefense_bids

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        # Create award
        authorization = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "value": self.initial_bids[0]["value"],
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]
        self.award_value = award["value"]
        self.award_suppliers = award["suppliers"]
        self.app.authorization = authorization
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active", "qualified": True, "eligible": True}},
        )

    test_create_tender_contract = snitch(create_tender_contract)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_patch_tender_contract_value = snitch(patch_tender_contract_value)
    test_patch_tender_contract_status_by_owner = snitch(patch_tender_contract_status_by_owner)
    test_patch_tender_contract_status_by_others = snitch(patch_tender_contract_status_by_others)
    test_patch_tender_contract_status_by_supplier = snitch(patch_tender_contract_status_by_supplier)
    test_patch_contract_single_item_unit_value = snitch(patch_contract_single_item_unit_value)
    test_patch_contract_single_item_unit_value_with_status = snitch(
        patch_contract_single_item_unit_value_with_status
    )
    test_patch_contract_multi_items_unit_value = snitch(patch_contract_multi_items_unit_value)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractVATNotIncludedResourceTest(BaseTenderUAContentWebTest, TenderContractResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_openuadefense_bids

    def create_award(self):
        authorization = self.app.authorization
        self.app.authorization = ("Basic", ("token", ""))
        response = self.app.post_json(
            "/tenders/{}/awards".format(self.tender_id),
            {
                "data": {
                    "suppliers": [test_tender_below_organization],
                    "status": "pending",
                    "bid_id": self.initial_bids[0]["id"],
                    "value": {
                        "amount": self.initial_bids[0]["value"]["amount"],
                        "currency": self.initial_bids[0]["value"]["currency"],
                        "valueAddedTaxIncluded": False,
                    },
                }
            },
        )
        award = response.json["data"]
        self.award_id = award["id"]
        self.award_value = award["value"]
        self.app.authorization = authorization
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active", "qualified": True, "eligible": True}},
        )

    @patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
    def setUp(self):
        super(TenderContractVATNotIncludedResourceTest, self).setUp()
        self.create_award()

    test_patch_tender_contract_value_vat_not_included = snitch(patch_tender_contract_value_vat_not_included)
    test_patch_tender_contract_status_by_owner = snitch(patch_tender_contract_status_by_owner)
    test_patch_tender_contract_status_by_others = snitch(patch_tender_contract_status_by_others)
    test_patch_tender_contract_status_by_supplier = snitch(patch_tender_contract_status_by_supplier)


@patch("openprocurement.tender.core.procedure.utils.NEW_CONTRACTING_FROM", get_now() + timedelta(days=1))
class TenderContractDocumentResourceTest(BaseTenderUAContentWebTest, TenderContractDocumentResourceTestMixin):
    initial_status = "active.qualification"
    initial_bids = test_tender_openuadefense_bids
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
        response = self.app.patch_json(
            "/tenders/{}/awards/{}".format(self.tender_id, self.award_id),
            {"data": {"status": "active", "qualified": True, "eligible": True}},
        )
        # Create contract for award
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


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractVATNotIncludedResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
