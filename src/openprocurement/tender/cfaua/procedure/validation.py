from openprocurement.api.utils import raise_operation_error
from openprocurement.api.validation import OPERATIONS


# bid
def validate_bid_posted_status(request, **_):
    allowed = ("draft", "pending")
    if request.validated["data"]["status"] not in allowed:
        raise_operation_error(
            request,
            f"Bid can be added only with status: {allowed}."
        )


def validate_view_bids_in_active_tendering(request, **_):
    tender_status = request.validated["tender"]["status"]
    if tender_status == "active.tendering":
        raise_operation_error(
            request,
            "Can't view {} in current ({}) tender status".format(
                "bid" if request.matchdict.get("bid_id") else "bids", tender_status
            ),
        )


# bid document
def validate_bid_document_in_tender_status(request, **_):
    tender_status = request.validated["tender"]["status"]
    if tender_status not in ("active.tendering", "active.qualification", "active.qualification.stand-still"):
        raise_operation_error(request, "Can't upload document in current ({}) tender status".format(tender_status))


def validate_bid_financial_document_in_tender_status(request, **_):
    tender_status = request.validated["tender"]["status"]
    if tender_status not in ("active.tendering", "active.qualification",
                             "active.awarded", "active.qualification.stand-still"):
        raise_operation_error(request, f"Can't upload document in current ({tender_status}) tender status")


def validate_bid_document_operation_in_award_status(request, **_):
    tender_status = request.validated["tender"]["status"]
    bid_id = request.validated["bid"]["id"]
    if tender_status in ("active.qualification", "active.awarded") and not any(
        award["bid_id"] == bid_id
        and award["status"] in ("pending", "active")
        for award in request.validated["tender"].get("awards", "")
    ):
        raise_operation_error(
            request,
            f"Can't {OPERATIONS.get(request.method)} document because award of bid is not in pending or active state"
        )
