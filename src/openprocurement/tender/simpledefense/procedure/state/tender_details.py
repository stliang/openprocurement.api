from openprocurement.api.auth import ACCR_3, ACCR_4, ACCR_5
from openprocurement.tender.openuadefense.procedure.state.tender_details import DefenseTenderDetailsState
from openprocurement.tender.simpledefense.constants import (
    TENDERING_EXTRA_PERIOD,
    ENQUIRY_PERIOD_TIME,
    ENQUIRY_STAND_STILL_TIME,
)


class SimpleDefenseTenderDetailsState(DefenseTenderDetailsState):
    tender_create_accreditations = (ACCR_3, ACCR_5)
    tender_central_accreditations = (ACCR_5,)
    tender_edit_accreditations = (ACCR_4,)

    tendering_period_extra = TENDERING_EXTRA_PERIOD

    enquiry_period_timedelta = - ENQUIRY_PERIOD_TIME
    enquiry_stand_still_timedelta = ENQUIRY_STAND_STILL_TIME
