from openprocurement.tender.core.procedure.views.complaint_post_document import BaseTenderComplaintPostDocumentResource
from cornice.resource import resource


@resource(
    name="esco:Tender Complaint Post Documents",
    collection_path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType="esco",
    description="Tender complaint post documents",
)
class OpenEUComplaintPostDocumentResource(BaseTenderComplaintPostDocumentResource):
    pass
