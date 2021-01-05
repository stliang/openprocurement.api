# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import snitch

from openprocurement.tender.belowthreshold.tests.base import test_lots, test_draft_claim, test_author
from openprocurement.tender.belowthreshold.tests.complaint import TenderComplaintResourceTestMixin
from openprocurement.tender.belowthreshold.tests.complaint_blanks import (
    # TenderComplaintDocumentResourceTest
    not_found,
    create_tender_complaint_document,
)

from openprocurement.tender.openua.tests.complaint import TenderUAComplaintResourceTestMixin
from openprocurement.tender.openua.tests.complaint_blanks import (
    # TenderLotAwardComplaintResourceTest
    create_tender_lot_complaint,
    # TenderComplaintDocumentResourceTest
    put_tender_complaint_document,
    patch_tender_complaint_document,
    mistaken_status_tender_complaint,
)

from openprocurement.tender.simpledefense.tests.base import BaseSimpleDefContentWebTest


class TenderComplaintResourceTest(
    BaseSimpleDefContentWebTest, TenderComplaintResourceTestMixin, TenderUAComplaintResourceTestMixin
):
    test_author = test_author
    test_mistaken_status_tender_complaint = snitch(mistaken_status_tender_complaint)



class TenderLotAwardComplaintResourceTest(BaseSimpleDefContentWebTest):
    initial_lots = test_lots
    test_author = test_author

    test_create_tender_complaint = snitch(create_tender_lot_complaint)


class TenderComplaintDocumentResourceTest(BaseSimpleDefContentWebTest):
    def setUp(self):
        super(TenderComplaintDocumentResourceTest, self).setUp()
        # Create complaint
        response = self.app.post_json(
            "/tenders/{}/complaints".format(self.tender_id),
            {"data": test_draft_claim},
        )
        complaint = response.json["data"]
        self.complaint_id = complaint["id"]
        self.complaint_owner_token = response.json["access"]["token"]

    test_author = test_author

    test_not_found = snitch(not_found)
    test_create_tender_complaint_document = snitch(create_tender_complaint_document)
    test_put_tender_complaint_document = snitch(put_tender_complaint_document)
    test_patch_tender_complaint_document = snitch(patch_tender_complaint_document)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderComplaintDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderComplaintResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
