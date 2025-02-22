from openprocurement.tender.core.procedure.views.award_complaint_post_document import (
    BaseAwardComplaintPostDocumentResource,
)
from cornice.resource import resource


@resource(
    name="aboveThresholdUA:Tender Award Complaint Post Documents",
    collection_path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts/{post_id}/documents",
    path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts/{post_id}/documents/{document_id}",
    procurementMethodType="aboveThresholdUA",
    description="Tender award complaint post documents",
)
class OpenUAAwardComplaintPostDocumentResource(BaseAwardComplaintPostDocumentResource):
    pass
