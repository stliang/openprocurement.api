from openprocurement.tender.core.procedure.views.award_complaint_document import AwardComplaintDocumentResource
from openprocurement.tender.open.procedure.state.award_complaint_document import OpenAwardComplaintDocumentState
from openprocurement.tender.open.constants import ABOVE_THRESHOLD
from cornice.resource import resource


@resource(
    name=f"{ABOVE_THRESHOLD}:Tender Award Complaint Documents",
    collection_path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/documents",
    path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/documents/{document_id}",
    procurementMethodType=ABOVE_THRESHOLD,
    description="Tender award complaint documents",
)
class OpenAwardComplaintDocumentResource(AwardComplaintDocumentResource):
    state_class = OpenAwardComplaintDocumentState
