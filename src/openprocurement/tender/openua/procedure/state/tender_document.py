from openprocurement.tender.openua.procedure.state.tender_details import TenderDetailsState
from openprocurement.tender.core.procedure.state.tender_document import TenderDocumentState
from openprocurement.tender.core.procedure.context import get_tender, get_request
from openprocurement.tender.core.procedure.utils import is_item_owner


class UATenderDocumentState(TenderDocumentState):

    def on_post(self, data):
        super().on_post(data)
        self.invalidate_bids_data()

    def on_patch(self, before, after):
        super().on_patch(before, after)
        self.invalidate_bids_data()

    def invalidate_bids_data(self):
        tender = get_tender()
        if is_item_owner(get_request(), tender) and tender.get("status") == "active.tendering":
            tender_state = TenderDetailsState(self.request)
            tender_state.validate_tender_period_extension(tender)
            tender_state.invalidate_bids_data(tender)
