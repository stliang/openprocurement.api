# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import snitch
from openprocurement.tender.belowthreshold.tests.base import test_tender_below_lots

from openprocurement.tender.belowthreshold.tests.tender import TenderResourceTestMixin
from openprocurement.tender.belowthreshold.tests.tender_blanks import (
    invalid_tender_conditions,
    create_tender_with_inn,
    create_tender_with_inn_before,
    tender_milestones_required,
    patch_tender_lots_none,
    tender_minimalstep_validation,
    tender_lot_minimalstep_validation,
    patch_tender_minimalstep_validation,
    patch_not_author,
)

from openprocurement.tender.open.tests.tender_blanks import create_tender_invalid_config
from openprocurement.tender.openua.tests.tender import TenderUaProcessTestMixin
from openprocurement.tender.openua.tests.tender_blanks import (
    empty_listing,
    create_tender_generated,
    tender_with_main_procurement_category,
    tender_finance_milestones,
    create_tender_with_criteria_lcc,
)

from openprocurement.tender.simpledefense.tests.base import (
    BaseSimpleDefWebTest,
    test_tender_simpledefense_data,
    test_tender_simpledefense_bids,
)
from openprocurement.tender.simpledefense.tests.tender_blanks import create_tender_invalid
from openprocurement.tender.openuadefense.tests.tender_blanks import (
    patch_tender,
    patch_tender_ua,
    one_valid_bid_tender_ua,
    patch_item_with_zero_quantity,
    one_invalid_bid_tender_new,
    one_invalid_bid_tender_after_new,
    one_invalid_bid_tender_before_new,
)


class TenderUAResourceTest(BaseSimpleDefWebTest, TenderResourceTestMixin):
    docservice = True
    initial_data = test_tender_simpledefense_data
    initial_lots = test_lots_data = test_tender_below_lots

    test_empty_listing = snitch(empty_listing)
    test_create_tender_invalid = snitch(create_tender_invalid)
    test_create_tender_invalid_config = snitch(create_tender_invalid_config)
    test_create_tender_generated = snitch(create_tender_generated)
    test_patch_tender = snitch(patch_tender)
    test_patch_tender_ua = snitch(patch_tender_ua)
    test_tender_with_main_procurement_category = snitch(tender_with_main_procurement_category)
    test_tender_finance_milestones = snitch(tender_finance_milestones)
    test_create_tender_with_inn = snitch(create_tender_with_inn)
    test_create_tender_with_inn_before = snitch(create_tender_with_inn_before)
    test_tender_milestones_required = snitch(tender_milestones_required)
    test_patch_tender_lots_none = snitch(patch_tender_lots_none)
    test_tender_minimalstep_validation = snitch(tender_minimalstep_validation)
    test_tender_lot_minimalstep_validation = snitch(tender_lot_minimalstep_validation)
    test_patch_tender_minimalstep_validation = snitch(patch_tender_minimalstep_validation)
    test_patch_item_with_zero_quantity = snitch(patch_item_with_zero_quantity)
    test_create_tender_with_criteria_lcc = snitch(create_tender_with_criteria_lcc)


class TenderUAProcessTest(BaseSimpleDefWebTest, TenderUaProcessTestMixin):
    docservice = True
    initial_data = test_tender_simpledefense_data
    initial_bids = test_bids_data = test_tender_simpledefense_bids
    initial_lots = test_tender_below_lots

    test_invalid_tender_conditions = snitch(invalid_tender_conditions)
    test_one_valid_bid_tender_ua = snitch(one_valid_bid_tender_ua)
    test_one_invalid_bid_tender_new = snitch(one_invalid_bid_tender_new)
    test_one_invalid_bid_tender_after_new = snitch(one_invalid_bid_tender_after_new)
    test_one_invalid_bid_tender_before_new = snitch(one_invalid_bid_tender_before_new)
    test_patch_not_author = snitch(patch_not_author)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderUAProcessTest))
    suite.addTest(unittest.makeSuite(TenderUAResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
