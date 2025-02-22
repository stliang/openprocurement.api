from openprocurement.tender.core.procedure.views.complaint_post_document import BaseTenderComplaintPostDocumentResource
from cornice.resource import resource

from openprocurement.tender.open.constants import ABOVE_THRESHOLD_GROUP_NAME, ABOVE_THRESHOLD_GROUP


@resource(
    name=f"{ABOVE_THRESHOLD_GROUP_NAME}:Tender Complaint Post Documents",
    collection_path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType=ABOVE_THRESHOLD_GROUP,
    description="Tender complaint post documents",
)
class OpenComplaintPostDocumentResource(BaseTenderComplaintPostDocumentResource):
    pass
