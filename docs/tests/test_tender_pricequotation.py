import os
from copy import deepcopy
from datetime import timedelta

from openprocurement.api.models import get_now
from openprocurement.tender.pricequotation.tests.base import (
    BaseTenderWebTest,
    test_tender_pq_criteria_1,
    test_tender_pq_response_1,
    test_tender_pq_data,
    test_tender_pq_bids,
    test_tender_pq_bids_with_docs,
    test_tender_pq_short_profile,
    test_tender_pq_shortlisted_firms,
)
from openprocurement.tender.pricequotation.tests.utils import (
    criteria_drop_uuids,
    copy_criteria_req_id,
    copy_tender_items,
)
from openprocurement.tender.pricequotation.tests.data import PQ_MULTI_PROFILE_RELEASED

from openprocurement.tender.core.tests.utils import change_auth

from tests.base.test import (
    DumpsWebTestApp,
    MockWebTestMixin,
)
from tests.base.constants import (
    DOCS_URL,
    AUCTIONS_URL,
)
from tests.test_tender_config import TenderConfigCSVMixin

test_tender_data = deepcopy(test_tender_pq_data)
bid_draft = deepcopy(test_tender_pq_bids[0])
bid_draft["status"] = "draft"

TARGET_DIR = 'docs/source/tendering/pricequotation/http/'
TARGET_CSV_DIR = 'docs/source/tendering/pricequotation/csv/'


class TenderResourceTest(BaseTenderWebTest, MockWebTestMixin, TenderConfigCSVMixin):
    AppClass = DumpsWebTestApp

    relative_to = os.path.dirname(__file__)
    initial_data = test_tender_data
    initial_bids = test_tender_pq_bids
    freezing_datetime = '2023-09-20T00:00:00+02:00'
    docservice = True
    docservice_url = DOCS_URL
    auctions_url = AUCTIONS_URL

    def setUp(self):
        super(TenderResourceTest, self).setUp()
        self.setUpMock()

    def tearDown(self):
        self.tearDownMock()
        super(TenderResourceTest, self).tearDown()

    def test_docs_config_csv(self):
        self.write_config_pmt_csv(
            pmt="priceQuotation",
            file_path=TARGET_CSV_DIR + "config.csv",
        )

    def test_docs_publish_tenders(self):
        tender_data = deepcopy(test_tender_data)
        tender_data.update(
            {
                "tenderPeriod": {"endDate": (get_now() + timedelta(days=14)).isoformat()}
            }
        )
        for item in tender_data['items']:
            item['deliveryDate'] = {
                "startDate": (get_now() + timedelta(days=2)).isoformat(),
                "endDate": (get_now() + timedelta(days=5)).isoformat()
            }
        criteria = criteria_drop_uuids(deepcopy(test_tender_pq_criteria_1))
        if PQ_MULTI_PROFILE_RELEASED:
            agreement = {"id": self.agreement_id}
            tender_data["agreement"] = agreement
            tender_data["criteria"] = criteria

        tender_data_1 = deepcopy(tender_data)
        response = self.app.post_json("/tenders", {"data": tender_data_1, "config": self.initial_config})
        self.assertEqual(response.status, "201 Created")
        tender_id_1 = response.json["data"]["id"]
        owner_token = response.json["access"]["token"]
        tender = response.json["data"]

        self.assertEqual(tender["status"], "draft")
        self.assertEqual(len(tender["items"]), 1)
        self.assertNotIn("shortlistedFirms", tender)
        self.assertIn("unit", tender["items"][0])

        if PQ_MULTI_PROFILE_RELEASED:
            self.assertIn("classification", tender["items"][0])
            self.assertIn("additionalClassifications", tender["items"][0])
            self.assertEqual(tender["agreement"], agreement)
        else:
            self.assertNotIn("classification", tender["items"][0])
            self.assertNotIn("additionalClassifications", tender["items"][0])
            self.assertNotEqual("agreement", tender)

        with open(TARGET_DIR + 'publish-tender.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                "/tenders/{}?acc_token={}".format(tender_id_1, owner_token),
                {"data": {"status": "draft.publishing"}}
            )
            self.assertEqual(response.status, "200 OK")
        tender = response.json["data"]
        self.assertEqual(tender["status"], "draft.publishing")

        if PQ_MULTI_PROFILE_RELEASED:
            data = {
                "data": {
                    "status": "active.tendering",
                    "shortlistedFirms": test_tender_pq_shortlisted_firms,
                }
            }
        else:
            items = deepcopy(tender["items"])
            items[0]["classification"] = test_tender_pq_short_profile["classification"]
            data = {
                "data": {
                    "status": "active.tendering",
                    "items": items,
                    "shortlistedFirms": test_tender_pq_shortlisted_firms,
                    "criteria": criteria
                }
            }

        test_tender_data2 = deepcopy(tender_data_1)
        if PQ_MULTI_PROFILE_RELEASED:
            test_tender_data2["items"][0]["profile"] = test_tender_pq_short_profile["id"] + "bad_profile"
        else:
            test_tender_data2["profiles"].append(test_tender_pq_short_profile["id"] + "bad_profile")

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': test_tender_data2, 'config': self.initial_config}
        )
        self.assertEqual(response.status, '201 Created')

        tender_id_2 = response.json['data']['id']

        with change_auth(self.app, ("Basic", ("pricequotation", ""))) as app:
            resp = app.patch_json("/tenders/{}".format(tender_id_1), data)
            self.assertEqual(resp.status, "200 OK")
            resp = app.patch_json('/tenders/{}'.format(tender_id_2), {"data": {"status": "draft.unsuccessful"}})
            self.assertEqual(resp.status, "200 OK")

        with open(TARGET_DIR + 'tender-after-bot-active.http', 'w') as self.app.file_obj:
            response = self.app.get("/tenders/{}".format(tender_id_1))
            tender = response.json["data"]
            self.assertEqual(response.status, "200 OK")
            self.assertIn("shortlistedFirms", tender)
            self.assertIn("classification", tender["items"][0])
            self.assertIn("unit", tender["items"][0])

        with open(TARGET_DIR + 'tender-after-bot-unsuccessful.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}'.format(tender_id_2))
            self.assertEqual(response.status, '200 OK')

    def test_docs_tutorial(self):

        request_path = '/tenders?opt_pretty=1'

        self.app.authorization = ('Basic', ('broker', ''))

        # Creating tender

        for item in test_tender_data['items']:
            item['deliveryDate'] = {
                "startDate": (get_now() + timedelta(days=2)).isoformat(),
                "endDate": (get_now() + timedelta(days=5)).isoformat()
            }

        test_tender_data.update(
            {
                "tenderPeriod": {"endDate": (get_now() + timedelta(days=14)).isoformat()},
                "criteria": criteria_drop_uuids(deepcopy(test_tender_pq_criteria_1))
            }
        )

        with open(TARGET_DIR + 'tender-post-attempt-json-data.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders?opt_pretty=1',
                {'data': test_tender_data, 'config': self.initial_config}
            )
            self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        with open(TARGET_DIR + 'blank-tender-view.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}'.format(tender['id']))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'initial-tender-listing.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders')
            self.assertEqual(response.status, '200 OK')

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': test_tender_data, 'config': self.initial_config}
        )
        self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'tender-listing-after-creation.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders')
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))

        # Modifying tender

        self.tick()

        response = self.app.get(f"/tenders/{self.tender_id}")
        tender = response.json["data"]

        tenderPeriod_endDate = get_now() + timedelta(days=15, seconds=10)
        with open(TARGET_DIR + 'patch-tender-data.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}?acc_token={}'.format(tender['id'], owner_token),
                {
                    'data': {
                        "tenderPeriod": {
                            "startDate": tender["tenderPeriod"]["startDate"],
                            "endDate": tenderPeriod_endDate.isoformat()
                        }
                    }
                }
            )

        self.app.authorization = ('Basic', ('broker', ''))

        self.set_status('active.tendering')

        with open(TARGET_DIR + 'tender-listing-after-patch.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')

        # Registering bid

        self.app.authorization = ('Basic', ('broker', ''))
        bids_access = {}
        bid_data = deepcopy(bid_draft)
        bid_data["requirementResponses"] = copy_criteria_req_id(tender["criteria"], test_tender_pq_response_1)
        bid_data["items"] = copy_tender_items(tender["items"])
        with open(TARGET_DIR + 'register-bidder.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/bids'.format(self.tender_id),
                {'data': bid_data}
            )
            bid1_id = response.json['data']['id']
            bids_access[bid1_id] = response.json['access']['token']
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'patch-bidder.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid1_id, bids_access[bid1_id]
                ),
                {'data': {"value": {"amount": 459}}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'activate-bidder.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid1_id, bids_access[bid1_id]
                ),
                {'data': {"status": "pending"}}
            )
            self.assertEqual(response.status, '200 OK')

        # Proposal Uploading

        with open(TARGET_DIR + 'upload-bid-proposal.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/bids/{}/documents?acc_token={}'.format(
                    self.tender_id, bid1_id, bids_access[bid1_id]
                ),
                {
                    'data': {
                        'title': 'Proposal.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf',
                    }
                }
            )
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'bidder-documents.http', 'w') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/bids/{}/documents?acc_token={}'.format(
                    self.tender_id, bid1_id, bids_access[bid1_id]
                )
            )
            self.assertEqual(response.status, '200 OK')

        # Second bid registration with documents
        bid_with_docs_data = deepcopy(test_tender_pq_bids_with_docs)
        bid_with_docs_data["requirementResponses"] = copy_criteria_req_id(tender["criteria"], test_tender_pq_response_1)
        bid_with_docs_data["items"] = copy_tender_items(tender["items"])
        with open(TARGET_DIR + 'register-2nd-bidder.http', 'w') as self.app.file_obj:
            for document in bid_with_docs_data['documents']:
                document['url'] = self.generate_docservice_url()
            response = self.app.post_json(
                '/tenders/{}/bids'.format(self.tender_id),
                {'data': bid_with_docs_data}
            )
            bid2_id = response.json['data']['id']
            bids_access[bid2_id] = response.json['access']['token']
            self.assertEqual(response.status, '201 Created')

        self.set_status('active.qualification')

        with open(TARGET_DIR + 'awards-listing.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        # get pending award
        award = [i for i in response.json['data'] if i['status'] == 'pending'][0]
        award_id = award['id']

        # activate award
        with open(TARGET_DIR + 'award-active.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
                {"data": {"status": "active"}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'awards-listing-after-activation.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        # cancel first winner
        with open(TARGET_DIR + 'award-cancelled.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
                {"data": {"status": "cancelled"}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'awards-listing-after-cancellation.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        # get new pending award and decline it
        award = [i for i in response.json['data'] if i['status'] == 'pending'][0]
        award_id = award['id']

        with open(TARGET_DIR + 'award-unsuccesful.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
                {"data": {"status": "unsuccessful"}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'awards-listing-after-unsuccesful.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        # get second bidder pending award
        award = [i for i in response.json['data'] if i['status'] == 'pending'][0]
        award_id = award['id']

        # activate second bidder award
        with open(TARGET_DIR + 'award-active-2.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
                {"data": {"status": "active"}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'awards-listing-after-activation-2.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'contract-listing.http', 'w') as self.app.file_obj:
            response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        self.contract_id = [contract for contract in response.json['data'] if contract['status'] == 'pending'][0]['id']

        ####  Set contract value

        # Preparing the cancellation request

        self.set_status('active.awarded')
        with open(TARGET_DIR + 'prepare-cancellation.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/cancellations?acc_token={}'.format(
                    self.tender_id, owner_token
                ),
                {'data': {'reason': 'cancellation reason', 'reasonType': 'noDemand'}}
            )
            self.assertEqual(response.status, '201 Created')

        cancellation_id = response.json['data']['id']

        # Changing cancellation reasonType

        with open(TARGET_DIR + 'update-cancellation-reasonType.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}?acc_token={}'.format(
                    self.tender_id, cancellation_id, owner_token
                ),
                {'data': {'reasonType': 'expensesCut'}}
            )
            self.assertEqual(response.status, '200 OK')

        # Filling cancellation with protocol and supplementary documentation

        with open(TARGET_DIR + 'upload-cancellation-doc.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
                    self.tender_id, cancellation_id, owner_token
                ),
                {
                    'data': {
                        'title': 'Notice.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf',
                    }
                }
            )
            cancellation_doc_id = response.json['data']['id']
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'patch-cancellation.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(
                    self.tender_id, cancellation_id, cancellation_doc_id, owner_token
                ),
                {'data': {"description": 'Changed description'}}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'update-cancellation-doc.http', 'w') as self.app.file_obj:
            response = self.app.put_json(
                '/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(
                    self.tender_id, cancellation_id, cancellation_doc_id, owner_token
                ),
                {
                    'data': {
                        'title': 'Notice-2.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf',
                    }
                }
            )
            self.assertEqual(response.status, '200 OK')

        # Activating the request and cancelling tender

        with open(TARGET_DIR + 'active-cancellation.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}?acc_token={}'.format(
                    self.tender_id, cancellation_id, owner_token
                ),
                {'data': {"status": "active"}}
            )
            self.assertEqual(response.status, '200 OK')

