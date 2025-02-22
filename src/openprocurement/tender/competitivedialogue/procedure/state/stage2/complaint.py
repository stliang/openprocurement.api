from openprocurement.tender.competitivedialogue.procedure.state.stage2.tender import (
    CDUAStage2TenderState,
    CDEUStage2TenderState,
)
from openprocurement.tender.core.procedure.state.complaint import ComplaintStateMixin


class CDUAStage2TenderComplaintState(ComplaintStateMixin, CDUAStage2TenderState):
    pass


class CDEUStage2TenderComplaintState(ComplaintStateMixin, CDEUStage2TenderState):
    pass
