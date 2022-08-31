# -*- coding: utf-8 -*-
from openprocurement.tender.core.views.award_rr_evidence import BaseAwardRequirementResponseEvidenceResource
from openprocurement.tender.core.utils import optendersresource
from openprocurement.tender.open.constants import ABOVE_THRESHOLD


@optendersresource(
    name=f"{ABOVE_THRESHOLD}:Award Requirement Response Evidence",
    collection_path="/tenders/{tender_id}/awards/{award_id}/requirement_responses/{requirement_response_id}/evidences",
    path="/tenders/{tender_id}/awards/{award_id}/requirement_responses/{requirement_response_id}/evidences/{evidence_id}",
    procurementMethodType=ABOVE_THRESHOLD,
    description="Tender award evidences",
)
class AwardRequirementResponseEvidenceResource(
    BaseAwardRequirementResponseEvidenceResource
):
    pass
