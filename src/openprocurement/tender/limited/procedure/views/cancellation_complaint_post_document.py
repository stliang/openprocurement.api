from openprocurement.tender.core.procedure.views.cancellation_complaint_post_document import (
    BaseCancellationComplaintPostDocumentResource,
)
from cornice.resource import resource


@resource(
    name="negotiation:Tender Cancellation Complaint Post Documents",
    collection_path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType="negotiation",
    description="Tender cancellation complaint post documents",
)
class NegotiationCancellationComplaintPostDocumentResource(BaseCancellationComplaintPostDocumentResource):
    pass


@resource(
    name="negotiation.quick:Tender Cancellation Complaint Post Documents",
    collection_path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType="negotiation.quick",
    description="Tender cancellation complaint post documents",
)
class NegotiationQuickCancellationComplaintPostDocumentResource(BaseCancellationComplaintPostDocumentResource):
    pass
