from schematics.exceptions import ValidationError

from openprocurement.api.utils import error_handler
from openprocurement.tender.core.procedure.context import get_tender_config


def has_unanswered_questions(tender, filter_cancelled_lots=True):
    if filter_cancelled_lots and tender.get("lots"):
        active_lots = [l["id"] for l in tender["lots"] if l["status"] == "active"]
        active_items = [i["id"] for i in tender.get("items")
                        if not i.get("relatedLot") or i["relatedLot"] in active_lots]
        return any(
            not i["answer"]
            for i in tender.get("questions", "")
            if i["questionOf"] == "tender"
            or i["questionOf"] == "lot" and i["relatedItem"] in active_lots
            or i["questionOf"] == "item" and i["relatedItem"] in active_items
        )
    return any(not i["answer"] for i in tender.get("questions", ""))


def has_unanswered_complaints(tender, filter_cancelled_lots=True, block_tender_complaint_status=("pending",)):
    if filter_cancelled_lots and tender.get("lots"):
        active_lots = [l["id"] for l in tender.get("lots") if l["status"] == "active"]
        return any(
            [
                i["status"] in block_tender_complaint_status
                for i in tender.get("complaints", "")
                if not i["relatedLot"] or (i["relatedLot"] in active_lots)
            ])


def validation_error_handler(func):
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except ValidationError as e:
            if isinstance(e.messages, dict):
                error_name = list(e.messages[0].keys())[0]
                error_msg = e.messages[0][error_name]
            else:
                error_name = "data"
                error_msg = e.messages[0]

            self.request.errors.status = 422
            self.request.errors.add("body", error_name, error_msg)
            raise error_handler(self.request)
    return wrapper


def awarding_is_unsuccessful(awards):
    """
    Check whether awarding is unsuccessful for tender/lot.
    If hasAwardingOrder is True, than only the last award's status is being checked.
    If hasAwardingOrder is False, all awards are being checked. If there are no awards with statuses
    active or pending for tender/lot, than awarding is unsuccessful.
    """
    config = get_tender_config()
    awarding_order_enabled = config.get("hasAwardingOrder")
    awards_statuses = {award["status"] for award in awards}
    return (awarding_order_enabled and awards and awards[-1]["status"] == "unsuccessful") or \
           (awarding_order_enabled is False and not awards_statuses.intersection({"active", "pending"}))
