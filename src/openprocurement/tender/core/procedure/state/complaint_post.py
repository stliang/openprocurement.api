from openprocurement.tender.core.procedure.state.tender import TenderState
from openprocurement.tender.core.procedure.context import get_tender, get_complaint
from openprocurement.tender.core.procedure.utils import tender_created_after_2020_rules, dt_from_iso
from openprocurement.tender.core.utils import calculate_tender_business_date
from openprocurement.tender.core.constants import POST_SUBMIT_TIME
from logging import getLogger
from openprocurement.api.utils import raise_operation_error
from openprocurement.api.context import get_now
from openprocurement.api.constants import WORKING_DAYS
from datetime import timedelta


LOGGER = getLogger(__name__)


class ComplaintPostValidationsMixin:
    request: object
    post_submit_time: timedelta

    def validate_complaint_status(self, complaint):
        complaint_status = complaint.get("status")
        if complaint_status not in ["pending", "accepted"]:
            raise_operation_error(
                self.request,
                f"Can't submit or edit post in current ({complaint_status}) complaint status"
            )

    def validate_complaint_post_review_date(self, complaint):
        complaint_status = complaint.get("status")
        if complaint_status == "accepted":
            tender = get_tender()
            post_end_date = calculate_tender_business_date(
                dt_from_iso(complaint["reviewDate"]),
                - self.post_submit_time,
                tender=tender,
                working_days=True,
                calendar=WORKING_DAYS
            )
            if get_now() > post_end_date:
                raise_operation_error(
                    self.request,
                    f"Can submit or edit post not later than {self.post_submit_time.days} "
                    "full business days before reviewDate"
                )


class ComplaintPostState(ComplaintPostValidationsMixin, TenderState):
    post_submit_time = POST_SUBMIT_TIME

    def complaint_post_on_post(self, post):
        # set author for documents passed with tender data
        for doc in post.get("documents", ""):
            doc["author"] = self.request.authenticated_role
            assert doc["author"] in ("complaint_owner", "tender_owner", "aboveThresholdReviewers")

    def validate_complaint_post_on_post(self, post):
        complaint = get_complaint()
        if not tender_created_after_2020_rules():
            raise_operation_error(
                self.request,
                "Forbidden"
            )

        if complaint.get("type") != "complaint":
            raise_operation_error(
                self.request,
                f"Can't submit or edit post in current ({complaint.get('type')}) complaint type"
            )

        self.validate_complaint_status(complaint)
        self.validate_complaint_post_review_date(complaint)
