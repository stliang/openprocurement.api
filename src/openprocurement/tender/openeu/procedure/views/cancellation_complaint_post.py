from openprocurement.tender.core.procedure.views.cancellation_complaint_post import (
    BaseCancellationComplaintPostResource,
)
from cornice.resource import resource


@resource(
    name="aboveThresholdEU:Tender Cancellation Complaint Posts",
    collection_path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts",
    path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}",
    procurementMethodType="aboveThresholdEU",
    description="Tender cancellation complaint posts",
)
class OpenEUCancellationComplaintPostResource(BaseCancellationComplaintPostResource):
    pass
