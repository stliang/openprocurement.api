import unittest

from openprocurement.api.tests.base import snitch

from openprocurement.tender.openua.tests.tender_blanks import (
    # TenderStage2UAResourceTest
    empty_listing as empty_listing_ua,
)

from openprocurement.tender.competitivedialogue.tests.stage2.tender_blanks import (
    create_tender_invalid_config,
    # CompetitiveDialogStage2EUResourceTest
    create_tender_invalid_eu,
    patch_tender_eu,
    # TenderStage2UAResourceTest
    create_tender_invalid_ua,
    patch_tender_ua,
    # CompetitiveDialogStage2ResourceTest
    listing,
    listing_draft,
    tender_not_found,
    invalid_procurementMethod,
    listing_changes,
    create_tender,
    tender_features_invalid,
    get_tender,
    tender_features,
    patch_tender_1,
    dateModified_tender,
    guarantee,
    tender_Administrator_change,
    patch_not_author,
    tender_funders,
    # TenderStage2UAProcessTest
    invalid_tender_conditions,
    one_valid_bid_tender_ua,
    one_invalid_and_1draft_bids_tender,
    first_bid_tender,
    tender_milestones_not_required,
    create_tender_central,
)
from openprocurement.tender.competitivedialogue.tests.base import (
    BaseCompetitiveDialogEUStage2WebTest,
    BaseCompetitiveDialogUAStage2WebTest,
    test_tender_cdua_stage2_data,
    test_tender_cdeu_stage2_data,
    test_tender_cd_access_token,
    test_tender_cd_author,
    test_tender_cdua_stage2_config,
    test_tender_cdeu_stage2_config,
    test_tender_cd_lots,
)
from openprocurement.tender.core.tests.criteria_utils import add_criteria


class CompetitiveDialogStage2EUResourceTest(BaseCompetitiveDialogEUStage2WebTest):
    docservice = True
    initial_auth = ("Basic", ("competitive_dialogue", ""))
    author_data = test_tender_cd_author
    initial_data = test_tender_cdeu_stage2_data
    initial_config = test_tender_cdeu_stage2_config
    test_access_token_data = test_tender_cd_access_token  # TODO: change attribute identifier
    initial_lots = test_tender_cd_lots

    def set_tender_status(self, tender, token, status):
        auth = self.app.authorization
        if status == "draft.stage2":
            self.app.authorization = ("Basic", ("competitive_dialogue", ""))
            response = self.app.patch_json(
                "/tenders/{id}?acc_token={token}".format(id=tender["id"], token=token), {"data": {"status": status}}
            )
            self.app.authorization = auth
            return response
        if status == "active.tendering":
            add_criteria(self, tender["id"], token)
            self.app.authorization = ("Basic", ("broker", ""))
            response = self.app.patch_json(
                "/tenders/{id}?acc_token={token}".format(id=tender["id"], token=token), {"data": {"status": status}}
            )
            self.app.authorization = auth
            return response

    test_invalid_procurementMethod = snitch(invalid_procurementMethod)
    test_listing = snitch(listing)
    test_listing_changes = snitch(listing_changes)
    test_listing_draft = snitch(listing_draft)
    test_create_tender_invalid = snitch(create_tender_invalid_eu)
    test_create_tender_invalid_config = snitch(create_tender_invalid_config)
    test_create_tender = snitch(create_tender)
    test_create_tender_central = snitch(create_tender_central)
    test_get_tender = snitch(get_tender)
    test_tender_features_invalid = snitch(tender_features_invalid)
    test_tender_features = snitch(tender_features)
    test_patch_tender = snitch(patch_tender_1)
    test_patch_tender_eu = snitch(patch_tender_eu)
    test_dateModified_tender = snitch(dateModified_tender)
    test_tender_not_found = snitch(tender_not_found)
    test_guarantee = snitch(guarantee)
    test_tender_Administrator_change = snitch(tender_Administrator_change)
    test_patch_not_author = snitch(patch_not_author)
    test_tender_funders = snitch(tender_funders)
    test_tender_milestones_not_required = snitch(tender_milestones_not_required)


class TenderStage2UAResourceTest(BaseCompetitiveDialogUAStage2WebTest):
    docservice = True
    initial_data = test_tender_cdua_stage2_data
    initial_config = test_tender_cdua_stage2_config
    test_access_token_data = test_tender_cd_access_token  # TODO: change attribute identifier
    author_data = test_tender_cd_author
    initial_lots = test_tender_cd_lots

    def set_tender_status(self, tender, token, status):
        auth = self.app.authorization
        if status == "draft.stage2":
            self.app.authorization = ("Basic", ("competitive_dialogue", ""))
            response = self.app.patch_json(
                "/tenders/{id}?acc_token={token}".format(id=tender["id"], token=token), {"data": {"status": status}}
            )
            self.app.authorization = auth
            return response
        if status == "active.tendering":
            add_criteria(self, tender["id"], token)
            self.app.authorization = ("Basic", ("broker", ""))
            response = self.app.patch_json(
                "/tenders/{id}?acc_token={token}".format(id=tender["id"], token=token), {"data": {"status": status}}
            )
            self.app.authorization = auth
            return response

    test_invalid_procurementMethod = snitch(invalid_procurementMethod)
    test_empty_listing = snitch(empty_listing_ua)
    test_listing = snitch(listing)
    test_listing_changes = snitch(listing_changes)
    test_listing_draft = snitch(listing_draft)
    test_create_tender_invalid = snitch(create_tender_invalid_ua)
    test_create_tender_invalid_config = snitch(create_tender_invalid_config)
    test_create_tender = snitch(create_tender)
    test_create_tender_central = snitch(create_tender_central)
    test_get_tender = snitch(get_tender)
    test_tender_features_invalid = snitch(tender_features_invalid)
    test_tender_features = snitch(tender_features)
    test_patch_tender = snitch(patch_tender_1)
    test_patch_tender_ua = snitch(patch_tender_ua)
    test_dateModified_tender = snitch(dateModified_tender)
    test_tender_not_found = snitch(tender_not_found)
    test_guarantee = snitch(guarantee)
    test_tender_Administrator_change = snitch(tender_Administrator_change)
    test_patch_not_author = snitch(patch_not_author)
    test_tender_milestones_not_required = snitch(tender_milestones_not_required)


class TenderStage2UAProcessTest(BaseCompetitiveDialogUAStage2WebTest):
    docservice = True
    test_tender_data_ua = test_tender_cdua_stage2_data  # TODO: change attribute identifier
    author_data = test_tender_cd_author  # TODO: change attribute identifier

    test_invalid_tender_conditions = snitch(invalid_tender_conditions)
    test_one_valid_bid_tender_ua = snitch(one_valid_bid_tender_ua)
    test_1invalid_and_1draft_bids_tender = snitch(one_invalid_and_1draft_bids_tender)
    test_first_bid_tender = snitch(first_bid_tender)


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
