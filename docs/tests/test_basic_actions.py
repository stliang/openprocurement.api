# -*- coding: utf-8 -*-
import os

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from openprocurement.api.models import get_now
from openprocurement.tender.belowthreshold.tests.utils import set_bid_lotvalues
from openprocurement.tender.open.tests.base import test_tender_open_complaint_objection
from openprocurement.tender.openeu.tests.tender import BaseTenderWebTest
from openprocurement.tender.belowthreshold.tests.base import (
    BaseTenderWebTest as BelowThresholdBaseTenderWebTest,
    test_tender_below_bids,
    test_tender_below_config,
)
from openprocurement.tender.core.tests.base import (
    test_exclusion_criteria,
)
from openprocurement.tender.core.tests.utils import change_auth
from openprocurement.api.constants import RELEASE_2020_04_19

from tests.base.constants import (
    DOCS_URL,
    AUCTIONS_URL,
)
from tests.base.test import (
    DumpsWebTestApp,
    MockWebTestMixin,
)
from tests.base.data import (
    test_docs_complaint,
    test_docs_claim,
    test_docs_lots,
    test_docs_subcontracting,
    test_docs_bid_draft,
    test_docs_bid2,
    test_docs_bid3_with_docs,
    test_docs_qualified,
    test_docs_tender_openeu,
    test_docs_eligible_evidence_data,
    test_docs_requirement_data,
    test_docs_requirement_group_data,
    test_docs_criterion_data,
    test_docs_tender_below,
)
from tests.base.helpers import complaint_create_pending

test_tender_below_data = deepcopy(test_docs_tender_below)

test_tender_data = deepcopy(test_docs_tender_openeu)
test_lots = deepcopy(test_docs_lots)
bid = deepcopy(test_docs_bid_draft)
bid2 = deepcopy(test_docs_bid2)
bid3 = deepcopy(test_docs_bid3_with_docs)

bid.update(test_docs_subcontracting)
bid.update(test_docs_qualified)
bid2.update(test_docs_qualified)
bid3.update(test_docs_qualified)

test_lots[0]['value'] = test_tender_data['value']
test_lots[0]['minimalStep'] = test_tender_data['minimalStep']
test_lots[1]['value'] = test_tender_data['value']
test_lots[1]['minimalStep'] = test_tender_data['minimalStep']

complaint = deepcopy(test_docs_complaint)
claim = deepcopy(test_docs_claim)
test_eligible_evidence_data = deepcopy(test_docs_eligible_evidence_data)
test_requirement_data = deepcopy(test_docs_requirement_data)
test_requirement_group_data = deepcopy(test_docs_requirement_group_data)
test_criterion_data = deepcopy(test_docs_criterion_data)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, 'source/tendering/basic-actions/http/')
OUTDATED_DIR = os.path.join(BASE_DIR, 'source/tendering/basic-actions/http-outdated/')


class TenderOpenEUResourceTest(BaseTenderWebTest, MockWebTestMixin):
    AppClass = DumpsWebTestApp

    relative_to = os.path.dirname(__file__)
    initial_data = test_tender_data
    docservice = True
    docservice_url = DOCS_URL
    auctions_url = AUCTIONS_URL

    def setUp(self):
        super(TenderOpenEUResourceTest, self).setUp()
        self.setUpMock()

    def tearDown(self):
        self.tearDownMock()
        super(TenderOpenEUResourceTest, self).tearDown()

    def test_complaints(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        with open(TARGET_DIR + 'complaints/claim-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': claim})
            self.assertEqual(response.status, '201 Created')

        complaint_token = response.json['access']['token']
        complaint_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/complaint-submission-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/documents?acc_token={}'.format(self.tender_id, complaint_id,
                                                                          complaint_token),
                {"data": {
                    "title": "Complaint_Attachment.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }},
            )
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/complaint-claim.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint_id, complaint_token),
                {"data": {"status": "claim"}})
            self.assertEqual(response.status, '200 OK')

        claim_data = {'data': claim.copy()}
        claim_data['data']['status'] = 'claim'
        with open(TARGET_DIR + 'complaints/complaint-submission-claim.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id), claim_data)
            self.assertEqual(response.status, '201 Created')

        complaint2_token = response.json['access']['token']
        complaint2_id = response.json['data']['id']

        complaint_data = {'data': complaint.copy()}

        complaint_url = "/tenders/{}/complaints".format(self.tender_id)
        complaint3_id, complaint3_token = complaint_create_pending(self, complaint_url, complaint_data)

        response = self.app.post_json(
            '/tenders/{}/complaints'.format(self.tender_id), claim_data)
        self.assertEqual(response.status, '201 Created')
        complaint4_id = response.json['data']['id']
        complaint4_token = response.json['access']['token']

        with open(TARGET_DIR + 'complaints/complaint-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')

        complaint1_token = response.json['access']['token']
        complaint1_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/complaint-complaint.http', 'w') as self.app.file_obj:
            if get_now() < RELEASE_2020_04_19:
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint1_id, complaint1_token),
                    {"data": {"status": "pending"}})
            else:
                with change_auth(self.app, ("Basic", ("bot", ""))):
                    response = self.app.patch_json(
                        '/tenders/{}/complaints/{}'.format(self.tender_id, complaint1_id),
                        {"data": {"status": "pending"}})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-answer.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint2_id, owner_token),
                {'data': {
                    "status": "answered",
                    "resolutionType": "resolved",
                    "resolution": "Виправлено неконкурентні умови"
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint4_id, owner_token),
            {'data': {
                "status": "answered",
                "resolutionType": "invalid",
                "resolution": "Вимога не відповідає предмету закупівлі"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-satisfy.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint2_id, complaint2_token),
                {"data": {
                    "satisfied": True,
                    "status": "resolved"
                }})
            self.assertEqual(response.status, '200 OK')

        if get_now() < RELEASE_2020_04_19:
            with open(TARGET_DIR + 'complaints/complaint-escalate.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint4_id, complaint4_token),
                    {"data": {
                        "satisfied": False,
                        "status": "pending"
                    }})
                self.assertEqual(response.status, '200 OK')

        complaint5_id, complaint5_token = complaint_create_pending(self, complaint_url, complaint_data)
        complaint6_id, complaint6_token = complaint_create_pending(self, complaint_url, complaint_data)
        complaint9_id, complaint9_token = complaint_create_pending(self, complaint_url, complaint_data)

        self.app.authorization = ('Basic', ('reviewer', ''))
        with open(TARGET_DIR + 'complaints/complaint-reject.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}'.format(self.tender_id, complaint9_id),
                {'data': {
                    "status": "invalid",
                    "rejectReason": "alreadyExists"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-accept.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}'.format(self.tender_id, complaint1_id),
                {'data': {
                    "status": "accepted",
                    "reviewDate": get_now().isoformat(),
                    "reviewPlace": "Place of review"
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/complaints/{}'.format(self.tender_id, complaint3_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/complaints/{}'.format(self.tender_id, complaint5_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/complaints/{}'.format(self.tender_id, complaint6_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-resolution-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json('/tenders/{}/complaints/{}/documents'.format(self.tender_id, complaint1_id),
                                          {"data": {
                                              "title": "ComplaintResolution.pdf",
                                              "url": self.generate_docservice_url(),
                                              "hash": "md5:" + "0" * 32,
                                              "format": "application/pdf",
                                          }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/complaint-resolve.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}'.format(self.tender_id, complaint1_id),
                {'data': {
                    "status": "satisfied"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-decline.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}'.format(self.tender_id, complaint3_id),
                {'data': {
                    "status": "declined"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint-accepted-stopped.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}'.format(self.tender_id, complaint5_id),
                {'data': {
                    "decision": "Тендер скасовується замовником",
                    "status": "stopped",
                    "rejectReason": "tenderCancelled"
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        with open(TARGET_DIR + 'complaints/complaint-resolved.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint1_id, owner_token),
                {'data': {
                    "tendererAction": "Умови виправлено",
                    "status": "resolved"
                }})
            self.assertEqual(response.status, '200 OK')

        if RELEASE_2020_04_19 > get_now():
            with open(OUTDATED_DIR + 'complaints/complaint-accepted-stopping.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint6_id, complaint6_token),
                    {"data": {
                        "cancellationReason": "Тендер скасовується замовником",
                        "status": "stopping"
                    }},
                    status=200,
                )
            self.assertEqual(response.status, '200 OK')

            self.app.authorization = ('Basic', ('reviewer', ''))
            with open(OUTDATED_DIR + 'complaints/complaint-stopping-stopped.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}'.format(self.tender_id, complaint6_id),
                    {'data': {
                        "decision": "Тендер скасовується замовником",
                        "status": "stopped",
                        "rejectReason": "tenderCancelled"
                    }})
                self.assertEqual(response.status, '200 OK')

        if get_now() < RELEASE_2020_04_19:
            # before RELEASE_2020_04_19 from pending to mistaken transition was available by reviewer
            self.app.authorization = ('Basic', ('broker', ''))
            complaint7_id, complaint7_token = complaint_create_pending(self, complaint_url, complaint_data)

            with open(OUTDATED_DIR + 'complaints/complaint-mistaken.http', 'w') as self.app.file_obj:
                self.app.authorization = ('Basic', ('reviewer', ''))
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint7_id, complaint7_token),
                    {"data": {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')
        else:
            # since RELEASE_2020_04_19 from draft to mistaken transition was available by complainant
            self.app.authorization = ('Basic', ('broker', ''))
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')
            complaint7_id = response.json['data']['id']
            complaint7_token = response.json['access']['token']

            with open(TARGET_DIR + 'complaints/complaint-mistaken.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint7_id, complaint7_token),
                    {"data": {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        complaint_url = "/tenders/{}/complaints".format(self.tender_id)
        complaint8_id, complaint8_token = complaint_create_pending(self, complaint_url, complaint_data)

        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/complaint-post-reviewer-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/posts'.format(
                    self.tender_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "complaint_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post1_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))

        with open(TARGET_DIR + 'complaints/complaint-post-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, complaint8_id, complaint8_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post1_id,
                    "documents": [{
                        'title': 'post_document_complaint.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')

        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/complaint-post-reviewer-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/posts'.format(
                    self.tender_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "tender_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post2_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))

        with open(TARGET_DIR + 'complaints/complaint-post-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, complaint8_id, owner_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post2_id,
                    "documents": [{
                        'title': 'post_document_tender.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/complaints-list.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/tenders/{}/complaints'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/complaint.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/tenders/{}/complaints/{}'.format(self.tender_id, complaint1_id))
            self.assertEqual(response.status, '200 OK')

    def test_complaints_objections(self):
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        self.tender_id = tender['id']
        owner_token = response.json['access']['token']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        test_tender_open_complaint_objection["relatesTo"] = "tender"
        test_tender_open_complaint_objection["relatedItem"] = self.tender_id
        objection = deepcopy(test_tender_open_complaint_objection)
        complaint_data = deepcopy(complaint)
        complaint_data["objections"] = [objection]
        with open(TARGET_DIR + 'complaints/complaint-objections-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint_data})
            self.assertEqual(response.status, '201 Created')

        objection["arguments"] = []
        complaint_data["objections"] = [objection]
        with open(TARGET_DIR + 'complaints/complaint-objections-invalid-arguments.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint_data},
                status=422,
            )
            self.assertEqual(response.status, '422 Unprocessable Entity')

        objection = deepcopy(test_tender_open_complaint_objection)
        objection["arguments"][0]["evidences"] = []
        complaint_data["objections"] = [objection]
        with open(TARGET_DIR + 'complaints/complaint-objections-empty-evidences.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint_data},
            )
            self.assertEqual(response.status, '201 Created')
            complaint_token = response.json['access']['token']
            complaint_id = response.json['data']['id']
            objection_id = response.json['data']['objections'][0]['id']

        with open(TARGET_DIR + 'complaints/complaint-document-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints/{}/documents?acc_token={}'.format(
                    self.tender_id, complaint_id, complaint_token),
                {"data": {
                    "title": "Evidence_Attachment.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')
            doc_id = response.json['data']['id']

        objection["id"] = objection_id
        objection["arguments"][0]["evidences"] = [{
            "title": "Evidence",
            "description": "Test evidence",
            "relatedDocument": doc_id
        }]
        with open(TARGET_DIR + 'complaints/complaint-objections-evidences-with-document.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint_id, complaint_token),
                {'data': {"objections": [objection]}},
            )
            self.assertEqual(response.status, '200 OK')

        objection = deepcopy(test_tender_open_complaint_objection)
        objection["requestedRemedies"] = []
        complaint_data["objections"] = [objection]
        with open(TARGET_DIR + 'complaints/complaint-objections-invalid-requested-remedies.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint_data},
                status=422,
            )
            self.assertEqual(response.status, '422 Unprocessable Entity')

        # add document to complaint via POST and set relatedDocument in objections in one action
        doc_id = uuid4().hex
        complaint_data["documents"] = [{
            "id": doc_id,
            "title": "Evidence_Attachment.pdf",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/pdf",
        }]
        objection = deepcopy(test_tender_open_complaint_objection)
        objection["arguments"][0]["evidences"] = [{
            "title": "Evidence",
            "description": "Test evidence",
            "relatedDocument": doc_id,
        }]
        complaint_data["objections"] = [objection]
        with open(TARGET_DIR + 'complaints/complaint-objections-with-document-one-action.http',
                  'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/complaints'.format(self.tender_id),
                {'data': complaint_data},
            )
            self.assertEqual(response.status, '201 Created')

    def test_qualification_complaints(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        bid_data = deepcopy(bid)
        set_bid_lotvalues(bid_data, [lot])
        response = self.app.post_json(
            '/tenders/{}/bids'.format(self.tender_id),
            {'data': bid_data})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']

        response = self.app.patch_json(
            '/tenders/{}/bids/{}?acc_token={}'.format(
                self.tender_id, bid_id, bid_token),
            {'data': {"status": "pending"}})

        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        bid_data_2 = deepcopy(bid2)
        set_bid_lotvalues(bid_data_2, [lot])
        self.create_bid(self.tender_id, bid_data_2)

        # Pre-qualification
        self.set_status('active.pre-qualification', {"id": self.tender_id, 'status': 'active.tendering'})

        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.assertEqual(response.status, "200 OK")
        qualifications = response.json['data']

        for qualification in qualifications:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                {"data": {
                    "status": "active",
                    "qualified": True,
                    "eligible": True
                }})
            self.assertEqual(response.status, "200 OK")

        self.tick()

        # active.pre-qualification.stand-still
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, owner_token),
            {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification.stand-still")

        qualification_id = qualifications[0]['id']

        with open(TARGET_DIR + 'complaints/qualification-complaint-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(
                    self.tender_id, qualification_id, bid_token),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')

        complaint1_token = response.json['access']['token']
        complaint1_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/qualification-complaint-submission-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/documents?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint1_id, complaint1_token),
                {"data": {
                    "title": "Complaint_Attachment.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/qualification-complaint-complaint.http', 'w') as self.app.file_obj:
            if get_now() < RELEASE_2020_04_19:
                response = self.app.patch_json(
                    '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id, qualification_id, complaint1_id, complaint1_token),
                    {"data": {"status": "pending"}})
            else:
                with change_auth(self.app, ("Basic", ("bot", ""))):
                    response = self.app.patch_json(
                        '/tenders/{}/qualifications/{}/complaints/{}'.format(
                            self.tender_id, qualification_id, complaint1_id),
                        {"data": {"status": "pending"}})
        self.assertEqual(response.status, '200 OK')

        complaint_data = {'data': complaint.copy()}

        complaint_url = "/tenders/{}/qualifications/{}/complaints".format(self.tender_id, qualification_id)
        complaint2_id, complaint2_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint3_id, complaint3_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint4_id, complaint4_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint5_id, complaint5_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        claim_data = {'data': claim.copy()}
        claim_data['data']['status'] = 'claim'
        with open(TARGET_DIR + 'complaints/qualification-complaint-submission-claim.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(
                    self.tender_id, qualification_id, bid_token), claim_data)
            self.assertEqual(response.status, '201 Created')

        complaint6_token = response.json['access']['token']
        complaint6_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/qualification-complaint-answer.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint6_id, owner_token),
                {"data": {
                    "status": "answered",
                    "resolutionType": "resolved",
                    "resolution": "Умови виправлено, вибір переможня буде розгянуто повторно"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-satisfy.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint6_id, complaint6_token),
                {"data": {
                    "satisfied": True,
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.post_json(
            '/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(
                self.tender_id, qualification_id, bid_token), claim_data)
        self.assertEqual(response.status, '201 Created')
        complaint7_token = response.json['access']['token']
        complaint7_id = response.json['data']['id']

        response = self.app.patch_json(
            '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                self.tender_id, qualification_id, complaint7_id, owner_token),
            {'data': {
                "status": "answered",
                "resolutionType": "invalid",
                "resolution": "Вимога не відповідає предмету закупівлі"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-unsatisfy.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint7_id, complaint7_token),
                {"data": {
                    "satisfied": False,
                }})
            self.assertEqual(response.status, '200 OK')

        complaint_url = "/tenders/{}/qualifications/{}/complaints".format(self.tender_id, qualification_id)
        complaint8_id, complaint8_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/qualification-complaint-post-reviewer-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/posts'.format(
                    self.tender_id, qualification_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "complaint_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post1_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))

        with open(TARGET_DIR + 'complaints/qualification-complaint-post-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint8_id, complaint8_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post1_id,
                    "documents": [{
                        'title': 'post_document_complaint.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')

        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/qualification-complaint-post-reviewer-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/posts'.format(
                    self.tender_id, qualification_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "tender_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post2_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))

        with open(TARGET_DIR + 'complaints/qualification-complaint-post-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint8_id, owner_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post2_id,
                    "documents": [{
                        'title': 'post_document_tender.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')

        response = self.app.post_json(
            '/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(
                self.tender_id, qualification_id, bid_token),
            {'data': claim})
        self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/qualification-complaint-claim.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, qualification_id,
                    response.json['data']['id'], response.json['access']['token']),
                {"data": {
                    "status": "claim"
                }})
            self.assertEqual(response.status, '200 OK')

        if get_now() < RELEASE_2020_04_19:
            # before RELEASE_2020_04_19 from pending to mistaken transition was available by reviewer
            self.app.authorization = ('Basic', ('broker', ''))
            complaint9_id, complaint9_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

            with open(OUTDATED_DIR + 'complaints/qualification-complaint-mistaken.http', 'w') as self.app.file_obj:
                self.app.authorization = ('Basic', ('reviewer', ''))
                response = self.app.patch_json(
                    '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id,
                        qualification_id,
                        complaint9_id,
                        complaint9_token
                    ),
                    {"data": {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')
        else:
            # since RELEASE_2020_04_19 from draft to mistaken transition was available by complainant
            self.app.authorization = ('Basic', ('broker', ''))
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(
                    self.tender_id,
                    qualification_id,
                    bid_token,
                ),
                {'data': complaint}
            )
            self.assertEqual(response.status, '201 Created')
            complaint9_id = response.json['data']['id']
            complaint9_token = response.json['access']['token']

            with open(TARGET_DIR + 'complaints/qualification-complaint-mistaken.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id,
                        qualification_id,
                        complaint9_id,
                        complaint9_token
                    ),
                    {"data": {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('reviewer', ''))
        with open(TARGET_DIR + 'complaints/qualification-complaint-reject.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint2_id),
                {"data": {
                    "status": "invalid",
                    "rejectReason": "alreadyExists"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-accept.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint1_id),
                {"data": {
                    "status": "accepted",
                    "reviewDate": get_now().isoformat(),
                    "reviewPlace": "Place of review"
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/qualifications/{}/complaints/{}'.format(
                self.tender_id, qualification_id, complaint3_id),
            {"data": {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/qualifications/{}/complaints/{}'.format(
                self.tender_id, qualification_id, complaint4_id),
            {"data": {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/qualifications/{}/complaints/{}'.format(
                self.tender_id, qualification_id, complaint5_id),
            {"data": {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-resolution-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/complaints/{}/documents'.format(
                    self.tender_id, qualification_id, complaint1_id),
                {"data": {
                    "title": "ComplaintResolution.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/qualification-complaint-resolve.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint1_id),
                {"data": {
                    "status": "satisfied"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-decline.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint3_id),
                {"data": {
                    "status": "declined"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint-accepted-stopped.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint5_id),
                {"data": {
                    "decision": "Тендер скасовується замовником",
                    "status": "stopped",
                    "rejectReason": "tenderCancelled"
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        with open(TARGET_DIR + 'complaints/qualification-complaint-resolved.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, complaint1_id, owner_token),
                {"data": {
                    "tendererAction": "Умови виправлено",
                    "status": "resolved"
                }})
            self.assertEqual(response.status, '200 OK')

        if RELEASE_2020_04_19 > get_now():
            with open(OUTDATED_DIR + 'complaints/qualification-complaint-accepted-stopping.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/qualifications/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id, qualification_id, complaint4_id, complaint4_token),
                    {"data": {
                        "cancellationReason": "Тендер скасовується замовником",
                        "status": "stopping"
                    }},
                    status=200,
                )
                self.assertEqual(response.status, '200 OK')

                self.app.authorization = ('Basic', ('reviewer', ''))
                with open(OUTDATED_DIR + 'complaints/qualification-complaint-stopping-stopped.http', 'w') as self.app.file_obj:
                    response = self.app.patch_json(
                        '/tenders/{}/qualifications/{}/complaints/{}'.format(
                            self.tender_id, qualification_id, complaint4_id),
                        {"data": {
                            "decision": "Тендер скасовується замовником",
                            "status": "stopped",
                            "rejectReason": "tenderCancelled"
                        }})
                    self.assertEqual(response.status, '200 OK')

        self.app.authorization = None
        with open(TARGET_DIR + 'complaints/qualification-complaints-list.http', 'w') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/complaints'.format(
                    self.tender_id, qualification_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/qualification-complaint.http', 'w') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/complaints/{}'.format(
                    self.tender_id, qualification_id, complaint1_id))
            self.assertEqual(response.status, '200 OK')

    def test_award_complaints(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        bid_data = deepcopy(bid)
        set_bid_lotvalues(bid_data, [lot])
        response = self.app.post_json(
            '/tenders/{}/bids'.format(self.tender_id),
            {'data': bid_data})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']

        response = self.app.patch_json(
            '/tenders/{}/bids/{}?acc_token={}'.format(
                self.tender_id, bid_id, bid_token),
            {'data': {"status": "pending"}})

        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        bid_data_2 = deepcopy(bid2)
        set_bid_lotvalues(bid_data_2, [lot])
        self.create_bid(self.tender_id, bid_data_2)
        # response = self.app.post_json(
        #     '/tenders/{}/bids'.format(self.tender_id),
        #     {'data': bid2})

        # Pre-qualification
        self.set_status(
            'active.pre-qualification',
            {"id": self.tender_id, 'status': 'active.tendering'})
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.assertEqual(response.status, "200 OK")
        qualifications = response.json['data']

        for qualification in qualifications:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(
                    self.tender_id, qualification['id'], owner_token),
                {"data": {
                    "status": "active",
                    "qualified": True,
                    "eligible": True
                }})
            self.assertEqual(response.status, "200 OK")

        # active.pre-qualification.stand-still
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, owner_token),
            {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification.stand-still")

        # switch to active.auction
        self.set_status('active.auction')
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(self.tender_id))
        auction_bids_data = response.json['data']['bids']
        self.app.post_json(
            '/tenders/{}/auction/{}'.format(self.tender_id, lot_id),
            {
                'data': {
                    'bids': [
                        {
                            "id": b["id"],
                            "lotValues": [
                                {"value": lot["value"], "relatedLot": lot["relatedLot"]}
                                for lot in b["lotValues"]
                            ]
                        }
                        for b in auction_bids_data
                    ]
                }
            }
        )

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
            {"data": {
                "status": "active",
                "qualified": True,
                "eligible": True
            }})
        self.assertEqual(response.status, '200 OK')

        self.tick()

        with open(TARGET_DIR + 'complaints/award-complaint-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                    self.tender_id, award_id, bid_token),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')

        self.tick()

        complaint1_token = response.json['access']['token']
        complaint1_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/award-complaint-submission-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/documents?acc_token={}'.format(
                    self.tender_id, award_id, complaint1_id, complaint1_token),
                {"data": {
                    "title": "Complaint_Attachment.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/award-complaint-complaint.http', 'w') as self.app.file_obj:
            if get_now() < RELEASE_2020_04_19:
                response = self.app.patch_json(
                    '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id, award_id, complaint1_id, complaint1_token),
                    {"data": {"status": "pending"}})
            else:
                with change_auth(self.app, ("Basic", ("bot", ""))):
                    response = self.app.patch_json(
                        '/tenders/{}/awards/{}/complaints/{}'.format(
                            self.tender_id, award_id, complaint1_id),
                        {"data": {"status": "pending"}})

            self.assertEqual(response.status, '200 OK')

        complaint_data = {'data': complaint.copy()}
        # with open(OUTDATED_DIR + 'complaints/award-complaint-submission-complaint.http', 'w') as self.app.file_obj:
        #     response = self.app.post_json(
        #         '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
        #             self.tender_id, award_id, bid_token),
        #         complaint_data)
        #     self.assertEqual(response.status, '201 Created')
        #
        # complaint2_id = response.json['data']['id']

        complaint_url = "/tenders/{}/awards/{}/complaints".format(self.tender_id, award_id)

        complaint2_id, complaint2_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint3_id, complaint3_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint4_id, complaint4_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        complaint5_id, complaint5_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        claim_data = {'data': claim.copy()}
        claim_data['data']['status'] = 'claim'
        with open(TARGET_DIR + 'complaints/award-complaint-submission-claim.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                    self.tender_id, award_id, bid_token), claim_data)
            self.assertEqual(response.status, '201 Created')

        complaint6_token = response.json['access']['token']
        complaint6_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/award-complaint-answer.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, award_id, complaint6_id, owner_token),
                {'data': {
                    "status": "answered",
                    "resolutionType": "resolved",
                    "resolution": "Умови виправлено, вибір переможня буде розгянуто повторно"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-satisfy.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, award_id, complaint6_id, complaint6_token),
                {'data': {
                    "satisfied": True,
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                self.tender_id, award_id, bid_token), claim_data)
        self.assertEqual(response.status, '201 Created')
        complaint7_token = response.json['access']['token']
        complaint7_id = response.json['data']['id']

        response = self.app.patch_json(
            '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                self.tender_id, award_id, complaint7_id, owner_token),
            {'data': {
                "status": "answered",
                "resolutionType": "invalid",
                "resolution": "Вимога не відповідає предмету закупівлі"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-unsatisfy.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, award_id, complaint7_id, complaint7_token),
                {'data': {
                    "satisfied": False,
                }})
            self.assertEqual(response.status, '200 OK')

        complaint_url = "/tenders/{}/awards/{}/complaints".format(self.tender_id, award_id)
        complaint8_id, complaint8_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/award-complaint-post-reviewer-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/posts'.format(
                    self.tender_id, award_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "complaint_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post1_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))
        print("start")
        with open(TARGET_DIR + 'complaints/award-complaint-post-complaint-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, award_id, complaint8_id, complaint8_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post1_id,
                    "documents": [{
                        'title': 'post_document_complaint.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')
        return
        self.app.authorization = ('Basic', ('reviewer', ''))

        with open(TARGET_DIR + 'complaints/award-complaint-post-reviewer-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/posts'.format(
                    self.tender_id, award_id, complaint8_id),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Відсутній документ",
                    "recipient": "tender_owner",
                }})
            self.assertEqual(response.status, '201 Created')

        post2_id = response.json['data']['id']

        self.app.authorization = ('Basic', ('broker', ''))

        with open(TARGET_DIR + 'complaints/award-complaint-post-tender-owner.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/posts?acc_token={}'.format(
                    self.tender_id, award_id, complaint8_id, owner_token),
                {"data": {
                    "title": "Уточнення по вимозі",
                    "description": "Додано документ",
                    "recipient": "aboveThresholdReviewers",
                    "relatedPost": post2_id,
                    "documents": [{
                        'title': 'post_document_tender.pdf',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/pdf'
                    }]
                }})
            self.assertEqual(response.status, '201 Created')

        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                self.tender_id, award_id, bid_token),
            {'data': claim})
        self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/award-complaint-claim.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, award_id,
                    response.json['data']['id'], response.json['access']['token']),
                {'data': {
                    "status": "claim"
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('reviewer', ''))
        with open(TARGET_DIR + 'complaints/award-complaint-reject.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint2_id),
                {'data': {
                    "status": "invalid",
                    "rejectReason": "alreadyExists"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-accept.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint1_id),
                {'data': {
                    "status": "accepted",
                    "reviewDate": get_now().isoformat(),
                    "reviewPlace": "Place of review"
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint3_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint4_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint5_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "Place of review"
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-resolution-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints/{}/documents'.format(
                    self.tender_id, award_id, complaint1_id),
                {"data": {
                    "title": "ComplaintResolution.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/award-complaint-resolve.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint1_id),
                {'data': {
                    "status": "satisfied"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-decline.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint3_id),
                {'data': {
                    "status": "declined"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-accepted-stopped.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint5_id),
                {'data': {
                    "decision": "Тендер скасовується замовником",
                    "status": "stopped",
                    "rejectReason": "tenderCancelled"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaints-list.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/tenders/{}/awards/{}/complaints'.format(self.tender_id, award_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get(
                '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint1_id))
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        with open(TARGET_DIR + 'complaints/award-complaint-resolved.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, award_id, complaint1_id, owner_token),
                {'data': {
                    "tendererAction": "Умови виправлено, вибір переможня буде розгянуто повторно",
                    "status": "resolved"
                }})
            self.assertEqual(response.status, '200 OK')

        if RELEASE_2020_04_19 > get_now():
            with open(OUTDATED_DIR + 'complaints/award-complaint-accepted-stopping.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id, award_id, complaint4_id, complaint4_token),
                    {'data': {
                        "cancellationReason": "Тендер скасовується замовником",
                        "status": "stopping",
                    }},
                    status=200,
                )
                self.assertEqual(response.status, '200 OK')

            self.app.authorization = ('Basic', ('reviewer', ''))
            with open(OUTDATED_DIR + 'complaints/award-complaint-stopping-stopped.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/awards/{}/complaints/{}'.format(self.tender_id, award_id, complaint4_id),
                    {'data': {
                        "decision": "Тендер скасовується замовником",
                        "status": "stopped",
                        "rejectReason": "tenderCancelled"
                    }})
                self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('reviewer', ''))
        response = self.app.patch_json(
            '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                self.tender_id, award_id, complaint4_id, complaint4_token),
            {'data': {
                "status": "declined",
                "rejectReason": "tenderCancelled",
            }})
        self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        with open(TARGET_DIR + 'complaints/award-complaint-satisfied-resolving.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
                {'data': {
                    "status": "cancelled"
                }})
            self.assertEqual(response.status, '200 OK')
            new_award_id = response.headers['Location'][-32:]

        award_id = new_award_id
        complaint_url = "/tenders/{}/awards/{}/complaints".format(self.tender_id, award_id)
        self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
            {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/award-complaint-submit.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                    self.tender_id, award_id, bid_token),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')

        if get_now() < RELEASE_2020_04_19:
            # before RELEASE_2020_04_19 from pending to mistaken transition was available by reviewer
            self.app.authorization = ('Basic', ('broker', ''))
            complaint9_id, complaint9_token = complaint_create_pending(self, complaint_url, complaint_data, bid_token)

            with open(OUTDATED_DIR + 'complaints/award-complaint-mistaken.http', 'w') as self.app.file_obj:
                self.app.authorization = ('Basic', ('reviewer', ''))
                response = self.app.patch_json(
                    '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id,
                        award_id,
                        complaint9_id,
                        complaint9_token
                    ),
                    {'data': {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')
        else:
            # since RELEASE_2020_04_19 from draft to mistaken transition was available by complainant
            self.app.authorization = ('Basic', ('broker', ''))
            response = self.app.post_json(
                '/tenders/{}/awards/{}/complaints?acc_token={}'.format(
                    self.tender_id, award_id, bid_token),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')
            complaint9_id = response.json['data']['id']
            complaint9_token = response.json['access']['token']

            with open(TARGET_DIR + 'complaints/award-complaint-mistaken.http', 'w') as self.app.file_obj:
                response = self.app.patch_json(
                    '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id,
                        award_id,
                        complaint9_id,
                        complaint9_token),
                    {'data': {"status": "mistaken"}},
                )
                self.assertEqual(response.status, '200 OK')

    def test_cancellation_complaints(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        # Cancellation turn to complaint_period
        response = self.app.post_json(
            '/tenders/{}/cancellations?acc_token={}'.format(
                self.tender_id, owner_token),
            {'data': {'reason': 'cancellation reason', 'reasonType': 'noDemand'}})
        cancellation_id = response.json['data']['id']
        self.assertEqual(response.status, '201 Created')

        response = self.app.post_json(
            '/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
                self.tender_id, cancellation_id, owner_token),
            {"data": {
                "title": "Notice.pdf",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/pdf",
            }})
        self.assertEqual(response.status, '201 Created')

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}?acc_token={}'.format(
                self.tender_id, cancellation_id, owner_token),
            {'data': {"status": "pending"}})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-submission.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/cancellations/{}/complaints'.format(
                    self.tender_id, cancellation_id),
                {'data': complaint})
            self.assertEqual(response.status, '201 Created')

        complaint1_token = response.json['access']['token']
        complaint1_id = response.json['data']['id']

        with open(TARGET_DIR + 'complaints/cancellation-complaint-submission-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/cancellations/{}/complaints/{}/documents?acc_token={}'.format(
                    self.tender_id, cancellation_id, complaint1_id, complaint1_token),
                {"data": {
                    "title": "Complaint_Attachment.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        complaint_data = {'data': complaint.copy()}

        complaint_url = "/tenders/{}/cancellations/{}/complaints".format(self.tender_id, cancellation_id)
        complaint3_id, complaint3_token = complaint_create_pending(self, complaint_url, complaint_data)

        complaint4_id, complaint4_token = complaint_create_pending(self, complaint_url, complaint_data)

        with open(TARGET_DIR + 'complaints/cancellation-complaint-complaint.http', 'w') as self.app.file_obj:
            if get_now() < RELEASE_2020_04_19:
                response = self.app.patch_json(
                    '/tenders/{}/cancellations/{}/complaints/{}?acc_token={}'.format(
                        self.tender_id, cancellation_id, complaint1_id, complaint1_token),
                    {"data": {"status": "pending"}})
            else:
                with change_auth(self.app, ("Basic", ("bot", ""))):
                    response = self.app.patch_json(
                        '/tenders/{}/cancellations/{}/complaints/{}'.format(
                            self.tender_id, cancellation_id, complaint1_id),
                        {"data": {"status": "pending"}})

            self.assertEqual(response.status, '200 OK')

        complaint5_id, complaint5_token = complaint_create_pending(self, complaint_url, complaint_data)
        complaint6_id, complaint6_token = complaint_create_pending(self, complaint_url, complaint_data)

        self.app.authorization = ('Basic', ('reviewer', ''))
        with open(TARGET_DIR + 'complaints/cancellation-complaint-reject.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint4_id),
                {'data': {
                    "status": "invalid",
                    "rejectReason": "tenderCancelled",
                    "rejectReasonDescription": "reject reason description",
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-accept.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint1_id),
                {'data': {
                    "status": "accepted",
                    "reviewDate": get_now().isoformat(),
                    "reviewPlace": "some",
                }})
            self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}/complaints/{}'.format(
                self.tender_id, cancellation_id, complaint3_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}/complaints/{}'.format(
                self.tender_id, cancellation_id, complaint5_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            }})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}/complaints/{}'.format(
                self.tender_id, cancellation_id, complaint6_id),
            {'data': {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            }})
        self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-resolution-upload.http', 'w') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/cancellations/{}/complaints/{}/documents'.format
                (self.tender_id, cancellation_id, complaint1_id),
                {"data": {
                    "title": "ComplaintResolution.pdf",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/pdf",
                }})
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-resolve.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint1_id),
                {'data': {
                    "status": "satisfied"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-decline.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint3_id),
                {'data': {
                    "status": "declined"
                }})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint-accepted-stopped.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint5_id),
                {'data': {
                    "decision": "Тендер скасовується замовником",
                    "status": "stopped",
                    "rejectReason": "tenderCancelled",
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}?acc_token={}'.format(
                self.tender_id, cancellation_id, owner_token),
            {'data': {'status': 'unsuccessful'}}
        )
        self.assertEqual(response.status_code, 200)

        with open(TARGET_DIR + 'complaints/cancellation-complaint-resolved.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}?acc_token={}'.format(
                    self.tender_id, cancellation_id, complaint1_id, owner_token),
                {'data': {
                    "tendererAction": "Умови виправлено",
                    "status": "resolved",
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('reviewer', ''))
        with open(TARGET_DIR + 'complaints/cancellation-complaint-accepted-stopped.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/cancellations/{}/complaints/{}'.format(
                    self.tender_id, cancellation_id, complaint6_id),
                {'data': {
                    "decision": "Тендер скасовується замовником",
                    "status": "stopped",
                    "rejectReason": "tenderCancelled",
                }})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        # Create new cancellations
        response = self.app.post_json(
            '/tenders/{}/cancellations?acc_token={}'.format(
                self.tender_id, owner_token),
            {'data': {'reason': 'cancellation reason', 'reasonType': 'unFixable'}})
        cancellation2_id = response.json['data']['id']
        self.assertEqual(response.status, '201 Created')

        response = self.app.post_json(
            '/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
                self.tender_id, cancellation2_id, owner_token),
            {"data": {
                "title": "Notice.pdf",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/pdf",
            }})
        self.assertEqual(response.status, '201 Created')

        response = self.app.patch_json(
            '/tenders/{}/cancellations/{}?acc_token={}'.format(
                self.tender_id, cancellation2_id, owner_token),
            {'data': {"status": "pending"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.post_json(
            '/tenders/{}/cancellations/{}/complaints'.format(self.tender_id, cancellation2_id),
            {'data': complaint})
        self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'complaints/cancellation-complaints-list.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/tenders/{}/cancellations/{}/complaints'.format(
                self.tender_id, cancellation_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'complaints/cancellation-complaint.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/tenders/{}/cancellations/{}/complaints/{}'.format(
                self.tender_id, cancellation_id, complaint1_id))
            self.assertEqual(response.status, '200 OK')

    def test_tender_criteria_article_17(self):
        self.app.authorization = ('Basic', ('broker', ''))
        tender_data = deepcopy(test_tender_data)
        tender_data.update({"status": "draft"})

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': tender_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        other_criteria = deepcopy(test_criterion_data)
        other_criteria["classification"]["id"] = "CRITERION.OTHER"

        exclusion_criteria = deepcopy(test_criterion_data)

        with open(TARGET_DIR + 'criteria/bulk-create-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria?acc_token={}'.format(self.tender_id, owner_token),
                {'data': [other_criteria]},
            )
            self.assertEqual(response.status, '201 Created')

        criteria_1 = response.json['data'][0]
        criteria_id_1 = criteria_1['id']

        # Try to update tender from `draft` to `active.tendering` without criteria
        with open(TARGET_DIR + 'criteria/update-tender-status-without-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}?acc_token={}'.format(self.tender_id, owner_token),
                {"data": {"status": "active.tendering"}},
                status=403,
            )
            self.assertEqual(response.status, '403 Forbidden')

        with open(TARGET_DIR + 'criteria/bulk-create-exclusion-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria?acc_token={}'.format(self.tender_id, owner_token),
                {'data': [exclusion_criteria]},
            )
            self.assertEqual(response.status, '201 Created')

        criteria_2 = response.json['data'][0]
        criteria_id_2 = criteria_2['id']

        with open(TARGET_DIR + 'criteria/patch-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, owner_token),
                {'data': {'title': 'Updated title'}},
            )
            self.assertEqual(response.status, '200 OK')

        # Try to patch exclusion criteria
        with open(TARGET_DIR + 'criteria/patch-exclusion-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, owner_token),
                {'data': {'title': 'Updated title'}},
                status=403,
            )
            self.assertEqual(response.status, '403 Forbidden')

        # Requirement groups operation
        rg_id_1 = criteria_1["requirementGroups"][0]["id"]
        rg_id_2 = criteria_2["requirementGroups"][0]["id"]

        test_rg_data = deepcopy(test_requirement_group_data)

        with open(TARGET_DIR + 'criteria/add-criteria-requirement-group.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria/{}/requirement_groups?acc_token={}'.format(
                    self.tender_id, criteria_id_1, owner_token),
                {'data': test_rg_data},
            )
            self.assertEqual(response.status, '201 Created')

        # Try to add requirement group to exclusion criteria
        with open(TARGET_DIR + 'criteria/add-exclusion-criteria-requirement-group.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria/{}/requirement_groups?acc_token={}'.format(
                    self.tender_id, criteria_id_2, owner_token),
                {'data': test_rg_data},
                status=403,
            )
            self.assertEqual(response.status, '403 Forbidden')

        with open(TARGET_DIR + 'criteria/patch-criteria-requirement-group.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, owner_token),
                {'data': {'description': 'Updated description'}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/patch-exclusion-criteria-requirement-group.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, owner_token),
                {'data': {'description': 'Updated description'}},
                status=403,
            )
            self.assertEqual(response.status, '403 Forbidden')

        with open(TARGET_DIR + 'criteria/criteria-requirement-group-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups'.format(self.tender_id, criteria_id_1),
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria-requirement-group.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups/{}'.format(self.tender_id, criteria_id_1, rg_id_1),
            )
            self.assertEqual(response.status, '200 OK')

        # Requirements operation

        requirement_id_1 = criteria_1["requirementGroups"][0]["requirements"][0]["id"]
        requirement_id_2 = criteria_2["requirementGroups"][0]["requirements"][0]["id"]

        with open(TARGET_DIR + 'criteria/add-criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, owner_token),
                {'data': test_requirement_data},
            )
            self.assertEqual(response.status, '201 Created')

        with open(TARGET_DIR + 'criteria/add-exclusion-criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, owner_token),
                {'data': test_requirement_data},
                status=403
            )
            self.assertEqual(response.status, '403 Forbidden')

        test_evidence_data = deepcopy(test_eligible_evidence_data)

        with open(TARGET_DIR + 'criteria/patch-criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, owner_token),
                {'data': {
                    'title': 'Updated title',
                    'eligibleEvidences': [test_evidence_data]
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/patch-exclusion-criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'eligibleEvidences': [
                        test_evidence_data,
                    ]
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria-requirement-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements'.format(
                    self.tender_id, criteria_id_1, rg_id_1),
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1),
            )
            self.assertEqual(response.status, '200 OK')

        # Eligible evidence operation

        test_evidence_data_1 = deepcopy(test_evidence_data)
        test_evidence_data_2 = deepcopy(test_evidence_data)
        test_evidence_data_2["type"] = "statement"
        with open(TARGET_DIR + 'criteria/bulk-update-requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, owner_token),
                {"data": {"eligibleEvidences": [test_evidence_data_1, test_evidence_data_2]}},
            )
            self.assertEqual(response.status, '200 OK')

        evidence = response.json["data"]["eligibleEvidences"][1]

        with open(TARGET_DIR + 'criteria/bulk-delete-requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, owner_token),
                {"data": {"eligibleEvidences": [evidence]}},
            )
            self.assertEqual(response.status, '200 OK')

        self.app.patch_json(
            '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, owner_token),
            {"data": {"eligibleEvidences": [test_evidence_data_1, test_evidence_data_2]}},
        )

        with open(TARGET_DIR + 'criteria/add-requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}/evidences?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, owner_token),
                {'data': test_evidence_data},
            )
            self.assertEqual(response.status, '201 Created')
        evidence_id = response.json['data']['id']

        with open(TARGET_DIR + 'criteria/patch-requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, evidence_id, owner_token),
                {'data': {'title_en': 'Documented approve'}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-evidences-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}/evidences'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1),
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}/evidences/{}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, evidence_id),
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/delete-requirement-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_1, rg_id_1, requirement_id_1, evidence_id, owner_token),
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria-list.http', 'wb') as self.app.file_obj:
            response = self.app.get('/tenders/{}/criteria'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria.http', 'wb') as self.app.file_obj:
            response = self.app.get('/tenders/{}/criteria/{}'.format(self.tender_id, criteria_id_1))
            self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")
        with open(TARGET_DIR + 'criteria/put-exclusion-criteria-requirement.http', 'wb') as self.app.file_obj:
            response = self.app.put_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'eligibleEvidences': [
                        test_evidence_data,
                    ]
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-put-add-evidence.http', 'wb') as self.app.file_obj:
            test_evidence_data_new = deepcopy(test_evidence_data)
            test_evidence_data_new["title"] = "new, added by requirement PUT"
            response = self.app.put_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'eligibleEvidences': [
                        test_evidence_data,
                        test_evidence_data_new
                    ]
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-put-update-evidence.http', 'wb') as self.app.file_obj:
            test_evidence_data_new["title"] = "changed_new, changed by requirement PUT"
            response = self.app.put_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'eligibleEvidences': [
                        test_evidence_data,
                        test_evidence_data_new
                    ]
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-put-delete-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.put_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'eligibleEvidences': []
                }},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/criteria-requirement-cancellation.http', 'wb') as self.app.file_obj:
            response = self.app.put_json(
                '/tenders/{}/criteria/{}/requirement_groups/{}/requirements/{}?acc_token={}'.format(
                    self.tender_id, criteria_id_2, rg_id_2, requirement_id_2, owner_token),
                {'data': {
                    'status': 'cancelled'
                }},
            )
            self.assertEqual(response.status, '200 OK')

    def test_bid_requirement_response(self):
        tender_data = deepcopy(self.initial_data)

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': tender_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        criteria_data = deepcopy(test_exclusion_criteria[:2])

        criteria_data[1]["requirementGroups"][0]["requirements"].append({
            "dataType": "boolean",
            "expectedValue": "true",
            "title": "Additional requirement"
        })

        response = self.app.post_json(
            '/tenders/{}/criteria?acc_token={}'.format(self.tender_id, owner_token),
            {'data': criteria_data},
        )
        self.assertEqual(response.status, '201 Created')

        criteria = response.json["data"]

        bid_data = deepcopy(bid)
        set_bid_lotvalues(bid_data, [lot])
        response = self.app.post_json(
            '/tenders/{}/bids'.format(self.tender_id),
            {'data': bid_data})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']
        self.assertEqual(response.status, '201 Created')

        response = self.app.post_json(
            "/tenders/{}/bids/{}/documents?acc_token={}".format(
                self.tender_id, bid_id, bid_token),
            {"data": {
                "title": "name.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }}
        )
        self.assertEqual(response.status, "201 Created")

        doc_id = response.json["data"]["id"]

        evidence_data = {
            "title": "Requirement response",
            "relatedDocument": {
                "id": doc_id,
                "title": "name.doc",
            },
            "type": "document",
        }

        requirement_1_1 = criteria[0]["requirementGroups"][0]["requirements"][0]
        requirement_1_2 = criteria[0]["requirementGroups"][1]["requirements"][0]
        requirement_2_1 = criteria[1]["requirementGroups"][0]["requirements"][0]
        requirement_2_2 = criteria[1]["requirementGroups"][0]["requirements"][1]

        rr_mock = {
            "title": "Requirement response",
            "description": "some description",
            "requirement": {
                "id": requirement_1_1["id"],
                "title": requirement_1_1["title"],
            },
            "evidences": [
                evidence_data,
            ],
            "value": "True",
        }
        rr_1_1 = deepcopy(rr_mock)
        rr_1_2 = deepcopy(rr_mock)
        rr_1_2["requirement"] = {
            "id": requirement_1_2["id"],
            "title": requirement_1_2["title"],
        }
        rr_2_1 = deepcopy(rr_mock)
        rr_2_1["title"] = "Requirement response 2"
        rr_2_1["requirement"] = {
            "id": requirement_2_1["id"],
            "title": requirement_2_1["title"],
        }

        with open(TARGET_DIR + 'criteria/requirement-response-basic-data-1.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': [rr_1_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/bid-activation-not-all-criteria.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'status': 'pending'}},
                status=422
            )
            self.assertEqual(response.status, '422 Unprocessable Entity')

        with open(TARGET_DIR + 'criteria/requirement-response-basic-data-2.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': [rr_1_1, rr_1_2, rr_2_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/bid-activation-answered-on-two-groups.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'status': 'pending'}},
                status=422
            )
            self.assertEqual(response.status, '422 Unprocessable Entity')

        with open(TARGET_DIR + 'criteria/requirement-response-basic-data-3.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': [rr_1_1, rr_2_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/bid-activation-not-all-requirements.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'status': 'pending'}},
                status=422
            )
            self.assertEqual(response.status, '422 Unprocessable Entity')

        with open(TARGET_DIR + 'criteria/add-requirement-response-from-bid.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': [rr_1_1, rr_2_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        rr_1_1["title"] = "Requirement response 1"
        with open(TARGET_DIR + 'criteria/patch-requirement-response-from-bid.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': [rr_1_1, rr_2_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/delete-requirement-response-from-bid.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': {'requirementResponses': []}},
            )
            self.assertEqual(response.status, '200 OK')

        test_rr_data = [deepcopy(rr_mock), ]

        with open(TARGET_DIR + 'criteria/create-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/bids/{}/requirement_responses?acc_token={}'.format(
                    self.tender_id, bid_id, bid_token),
                {'data': test_rr_data},
            )
            self.assertEqual(response.status, '201 Created')

        rr_id = response.json["data"][0]["id"]

        with open(TARGET_DIR + 'criteria/update-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, bid_id, rr_id, bid_token),
                {'data': {'title': 'Updated title'}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/create-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/bids/{}/requirement_responses/{}/evidences?acc_token={}'.format(
                    self.tender_id, bid_id, rr_id, bid_token),
                {'data': evidence_data},
            )
            self.assertEqual(response.status, '201 Created')

        evidence_id = response.json["data"]["id"]

        with open(TARGET_DIR + 'criteria/update-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/bids/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, bid_id, rr_id, evidence_id, bid_token),
                {'data': {'title': 'Update evidence title'}},
            )
            self.assertEqual(response.status, '200 OK')

        self.set_status("active.auction")
        with open(TARGET_DIR + 'criteria/requirement-response-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/bids/{}/requirement_responses'.format(self.tender_id, bid_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/bids/{}/requirement_responses/{}'.format(self.tender_id, bid_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-response-evidence-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/bids/{}/requirement_responses/{}/evidences'.format(self.tender_id, bid_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/bids/{}/requirement_responses/{}/evidences/{}'.format(
                    self.tender_id, bid_id, rr_id, evidence_id))
            self.assertEqual(response.status, '200 OK')

        self.set_status("draft")

        with open(TARGET_DIR + 'criteria/delete-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/bids/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, bid_id, rr_id, evidence_id, bid_token))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/delete-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/bids/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, bid_id, rr_id, bid_token))
            self.assertEqual(response.status, '200 OK')

    def test_award_requirement_response(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        criteria_data = deepcopy(test_exclusion_criteria[6:8])

        response = self.app.post_json(
            '/tenders/{}/criteria?acc_token={}'.format(self.tender_id, owner_token),
            {'data': criteria_data},
        )
        self.assertEqual(response.status, '201 Created')

        criteria = response.json["data"]

        bid_data = deepcopy(bid)
        bid_data["status"] = "draft"
        set_bid_lotvalues(bid_data, [lot])

        response = self.app.post_json(
            '/tenders/{}/bids'.format(self.tender_id),
            {'data': bid_data})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']

        response = self.app.patch_json(
            '/tenders/{}/bids/{}?acc_token={}'.format(
                self.tender_id, bid_id, bid_token),
            {'data': {"status": "pending"}})

        # create second bid
        bid_data_2 = deepcopy(bid2)
        set_bid_lotvalues(bid_data_2, [lot])
        self.create_bid(self.tender_id, bid_data_2)

        # Pre-qualification
        self.set_status(
            'active.pre-qualification',
            {"id": self.tender_id, 'status': 'active.tendering'})
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.assertEqual(response.status, "200 OK")
        qualifications = response.json['data']

        for qualification in qualifications:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(
                    self.tender_id, qualification['id'], owner_token),
                {"data": {
                    "status": "active",
                    "qualified": True,
                    "eligible": True
                }})
            self.assertEqual(response.status, "200 OK")

        # active.pre-qualification.stand-still
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, owner_token),
            {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification.stand-still")

        # switch to active.auction
        self.set_status('active.auction')
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(self.tender_id))
        auction_bids_data = response.json['data']['bids']
        self.app.post_json(
            '/tenders/{}/auction/{}'.format(self.tender_id, lot_id),
            {
                'data': {
                    'bids': [
                        {
                            "id": b["id"],
                            "lotValues": [
                                {"value": lot["value"], "relatedLot": lot["relatedLot"]}
                                for lot in b["lotValues"]
                            ]
                        }
                        for b in auction_bids_data
                    ]
                }
            }
        )

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]

        self.set_status("active.qualification")

        response = self.app.post_json(
            "/tenders/{}/awards/{}/documents?acc_token={}".format(
                self.tender_id, award_id, owner_token),
            {"data": {
                "title": "name.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }}
        )
        self.assertEqual(response.status, "201 Created")

        doc_id = response.json["data"]["id"]

        # response = self.app.patch_json(
        #     '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, owner_token),
        #     {"data": {
        #         "status": "active",
        #         "qualified": True,
        #         "eligible": True
        #     }})
        # self.assertEqual(response.status, '200 OK')

        evidence_data = {
            "title": "Requirement response",
            "relatedDocument": {
                "id": doc_id,
                "title": "name.doc",
            },
            "type": "document",
        }

        requirement_1 = criteria[0]["requirementGroups"][0]["requirements"][0]
        requirement_2 = criteria[1]["requirementGroups"][0]["requirements"][0]

        rr_mock = {
            "title": "Requirement response",
            "description": "some description",
            "requirement": {
                "id": requirement_1["id"],
                "title": requirement_1["title"],
            },
            "evidences": [
                evidence_data,
            ],
            "value": "True",
        }
        rr_1 = deepcopy(rr_mock)
        rr_2 = deepcopy(rr_mock)
        rr_2["title"] = "Requirement response 2"
        rr_2["requirement"] = {
            "id": requirement_2["id"],
            "title": requirement_2["title"],
        }

        self.tick()

        with open(TARGET_DIR + 'criteria/add-requirement-response-from-award.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(
                    self.tender_id, award_id, owner_token),
                {'data': {'requirementResponses': [rr_1, rr_2]}},
            )
            self.assertEqual(response.status, '200 OK')

        rr_1["title"] = "Requirement response 1"
        with open(TARGET_DIR + 'criteria/patch-requirement-response-from-award.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(
                    self.tender_id, award_id, owner_token),
                {'data': {'requirementResponses': [rr_1, rr_2]}},
            )
            self.assertEqual(response.status, '200 OK')

        tender = self.mongodb.tenders.get(self.tender_id)
        for a in tender["awards"]:
            if a["id"] == award_id:
                del a["requirementResponses"]
        self.mongodb.tenders.save(tender)

        test_rr_data = [deepcopy(rr_mock), ]

        with open(TARGET_DIR + 'criteria/award-create-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/requirement_responses?acc_token={}'.format(
                    self.tender_id, award_id, owner_token),
                {'data': test_rr_data},
            )
            self.assertEqual(response.status, '201 Created')

        rr_id = response.json["data"][0]["id"]

        with open(TARGET_DIR + 'criteria/award-update-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, award_id, rr_id, owner_token),
                {'data': {"title": "Updated title"}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-create-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/awards/{}/requirement_responses/{}/evidences?acc_token={}'.format(
                    self.tender_id, award_id, rr_id, owner_token),
                {'data': evidence_data},
            )
            self.assertEqual(response.status, '201 Created')

        evidence_id = response.json["data"]["id"]

        with open(TARGET_DIR + 'criteria/award-update-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/awards/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, award_id, rr_id, evidence_id, owner_token),
                {'data': {'title': 'Update evidence title'}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-requirement-response-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/awards/{}/requirement_responses'.format(self.tender_id, award_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/awards/{}/requirement_responses/{}'.format(self.tender_id, award_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-requirement-response-evidence-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/awards/{}/requirement_responses/{}/evidences'.format(self.tender_id, award_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/awards/{}/requirement_responses/{}/evidences/{}'.format(
                    self.tender_id, award_id, rr_id, evidence_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-delete-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/awards/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, award_id, rr_id, evidence_id, owner_token))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/award-delete-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/awards/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, award_id, rr_id, owner_token))
            self.assertEqual(response.status, '200 OK')


    def test_qualification_requirement_response(self):
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/tenders?opt_pretty=1',
            {'data': self.initial_data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.tender_id = tender['id']

        # add lot
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]}
        )
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]
        lot_id = lot["id"]

        # add relatedLot for item
        items = deepcopy(tender["items"])
        for item in items:
            item["relatedLot"] = lot_id
        response = self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
            {"data": {"items": items}}
        )
        self.assertEqual(response.status, '200 OK')

        self.set_status("active.tendering")

        criteria_data = deepcopy(test_exclusion_criteria[6:8])

        response = self.app.post_json(
            '/tenders/{}/criteria?acc_token={}'.format(self.tender_id, owner_token),
            {'data': criteria_data},
        )
        self.assertEqual(response.status, '201 Created')

        criteria = response.json["data"]

        bid_data = deepcopy(bid)
        bid_data["status"] = "draft"
        set_bid_lotvalues(bid_data, [lot])

        response = self.app.post_json(
            '/tenders/{}/bids'.format(self.tender_id),
            {'data': bid_data})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']

        response = self.app.patch_json(
            '/tenders/{}/bids/{}?acc_token={}'.format(
                self.tender_id, bid_id, bid_token),
            {'data': {"status": "pending"}})

        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        bid_data_2 = deepcopy(bid2)
        set_bid_lotvalues(bid_data_2, [lot])
        self.create_bid(self.tender_id, bid_data_2)

        # Pre-qualification
        self.set_status(
            'active.pre-qualification',
            {"id": self.tender_id, 'status': 'active.tendering'})
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.assertEqual(response.status, "200 OK")
        qualifications = response.json['data']

        qualification_id = qualifications[0]["id"]
        response = self.app.post_json(
            "/tenders/{}/qualifications/{}/documents?acc_token={}".format(
                self.tender_id, qualification_id, owner_token),
            {"data": {
                "title": "name.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }}
        )
        self.assertEqual(response.status, "201 Created")

        doc_id = response.json["data"]["id"]

        evidence_data = {
            "title": "Requirement response",
            "relatedDocument": {
                "id": doc_id,
                "title": "name.doc",
            },
            "type": "document",
        }

        requirement_1 = criteria[0]["requirementGroups"][0]["requirements"][0]
        requirement_2 = criteria[1]["requirementGroups"][0]["requirements"][0]

        rr_mock = {
            "title": "Requirement response",
            "description": "some description",
            "requirement": {
                "id": requirement_1["id"],
                "title": requirement_1["title"],
            },
            "evidences": [
                evidence_data,
            ],
            "value": "True",
        }
        rr_1 = deepcopy(rr_mock)
        rr_2 = deepcopy(rr_mock)
        rr_2["title"] = "Requirement response 2"
        rr_2["requirement"] = {
            "id": requirement_2["id"],
            "title": requirement_2["title"],
        }

        self.tick()

        with open(TARGET_DIR + 'criteria/add-requirement-response-from-qualification.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, owner_token),
                {'data': {'requirementResponses': [rr_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        rr_1["title"] = "Requirement response 1"
        with open(TARGET_DIR + 'criteria/patch-requirement-response-from-qualification.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, owner_token),
                {'data': {'requirementResponses': [rr_1]}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/delete-requirement-response-from-qualification.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, owner_token),
                {'data': {'requirementResponses': []}},
            )
            self.assertEqual(response.status, '200 OK')

        test_rr_data = [rr_2, ]

        with open(TARGET_DIR + 'criteria/qualification-create-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/requirement_responses?acc_token={}'.format(
                    self.tender_id, qualification_id, owner_token),
                {'data': test_rr_data},
            )
            self.assertEqual(response.status, '201 Created')

        rr_id = response.json["data"][0]["id"]

        with open(TARGET_DIR + 'criteria/qualification-update-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, rr_id, owner_token),
                {'data': {"title": "Updated title"}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-create-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/tenders/{}/qualifications/{}/requirement_responses/{}/evidences?acc_token={}'.format(
                    self.tender_id, qualification_id, rr_id, owner_token),
                {'data': evidence_data},
            )
            self.assertEqual(response.status, '201 Created')

        evidence_id = response.json["data"]["id"]

        with open(TARGET_DIR + 'criteria/qualification-update-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}/qualifications/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, rr_id, evidence_id, owner_token),
                {'data': {'title': 'Update evidence title'}},
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-requirement-response-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/requirement_responses'.format(self.tender_id, qualification_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/requirement_responses/{}'.format(
                    self.tender_id, qualification_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-requirement-response-evidence-list.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/requirement_responses/{}/evidences'.format(
                    self.tender_id, qualification_id, rr_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.get(
                '/tenders/{}/qualifications/{}/requirement_responses/{}/evidences/{}'.format(
                    self.tender_id, qualification_id, rr_id, evidence_id))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-delete-requirement-response-evidence.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/qualifications/{}/requirement_responses/{}/evidences/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, rr_id, evidence_id, owner_token))
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'criteria/qualification-delete-requirement-response.http', 'wb') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/qualifications/{}/requirement_responses/{}?acc_token={}'.format(
                    self.tender_id, qualification_id, rr_id, owner_token))
            self.assertEqual(response.status, '200 OK')

    def test_docs_constants(self):
        with open(TARGET_DIR + 'constants/constants.http', 'w') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get('/constants'.format(self.tender_id))
            self.assertEqual(response.status, '200 OK')



class TenderBelowThresholdResourceTest(BelowThresholdBaseTenderWebTest, MockWebTestMixin):
    AppClass = DumpsWebTestApp

    relative_to = os.path.dirname(__file__)
    initial_data = test_tender_below_data
    initial_config = test_tender_below_config
    initial_bids = test_tender_below_bids
    docservice = True
    docservice_url = DOCS_URL
    auctions_url = AUCTIONS_URL

    def setUp(self):
        super(TenderBelowThresholdResourceTest, self).setUp()
        self.setUpMock()

    def tearDown(self):
        self.tearDownMock()
        super(TenderBelowThresholdResourceTest, self).tearDown()

    def test_docs_milestones(self):
        self.app.authorization = ('Basic', ('broker', ''))
        data = deepcopy(test_tender_below_data)

        for item in data['items']:
            item['deliveryDate'] = {
                "startDate": (get_now() + timedelta(days=2)).isoformat(),
                "endDate": (get_now() + timedelta(days=5)).isoformat()
            }

        data.update({
            "enquiryPeriod": {"endDate": (get_now() + timedelta(days=7)).isoformat()},
            "tenderPeriod": {"endDate": (get_now() + timedelta(days=14)).isoformat()}
        })

        data["milestones"] = [
            {
                'title': "signingTheContract",
                'code': 'prepayment',
                'type': 'financing',
                'duration': {'days': 5, 'type': 'banking'},
                'sequenceNumber': 0,
                'percentage': 45.55,
            },
            {
                'title': "deliveryOfGoods",
                'code': 'postpayment',
                'type': 'financing',
                'duration': {'days': 7, 'type': 'calendar'},
                'sequenceNumber': 1,
                'percentage': 54.45,
            },
        ]
        with open(TARGET_DIR + 'milestones/tender-post-milestones.http', 'w') as self.app.file_obj:
            response = self.app.post_json('/tenders', {'data': data, 'config': self.initial_config})
        self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        owner_token = response.json['access']['token']

        milestones = deepcopy(tender["milestones"])
        milestones[1].update({
            "title": "anotherEvent",
            "description": "Підозрілий опис",
        })
        with open(TARGET_DIR + 'milestones/tender-patch-milestones.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
                {"data": {
                    "milestones": milestones
                }}
            )
            self.assertEqual(response.status, '200 OK')

        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(tender["id"], owner_token),
            {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot = response.json["data"]

        milestones[0]["relatedLot"] = lot["id"]
        milestones[1]["relatedLot"] = lot["id"]
        with open(TARGET_DIR + 'milestones/tender-patch-lot-milestones.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/tenders/{}?acc_token={}'.format(tender["id"], owner_token),
                {"data": {
                    "milestones": milestones
                }}
            )
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'milestones/tender-delete-lot-milestones-error.http', 'w') as self.app.file_obj:
            response = self.app.delete(
                '/tenders/{}/lots/{}?acc_token={}'.format(tender["id"], lot['id'], owner_token),
                status=422
            )
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(
            response.json['errors'],
            [{
                "location": "body",
                "name": "data",
                "description": "Cannot delete lot with related milestones"
            }]
        )
