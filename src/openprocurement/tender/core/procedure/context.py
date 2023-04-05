import threading
from typing import Union
from openprocurement.api.context import get_now, get_request
from openprocurement.api.constants import RELEASE_2020_04_19
from openprocurement.api.utils import get_first_revision_date

# monkey.patch_all() makes this gevent._gevent_clocal.local instance
thread_context = threading.local()


def get_tender() -> Union[dict, None]:
    tender = get_request().validated.get("tender")
    return tender


def get_tender_config() -> Union[dict, None]:
    tender = get_request().validated.get("tender_config")
    return tender


def get_award() -> Union[dict, None]:
    award = get_request().validated.get("award")
    return award


def get_contract() -> Union[dict, None]:
    tender = get_request().validated.get("contract")
    return tender


def get_cancellation() -> Union[dict, None]:
    cancellation = get_request().validated.get("cancellation")
    return cancellation


def get_bid() -> dict:
    bid = get_request().validated.get("bid")
    return bid


def get_document() -> dict:
    return get_request().validated.get("document")


def get_bids_before_auction_results_context():
    """
    get_bids_before_auction_results
    we need it for each lot, so we set it on first call
    and use it multiple times for one request
    """
    if "bids_before_auction" not in get_request().validated:
        tender = get_request().validated["tender"]
        from openprocurement.tender.core.procedure.awarding import get_bids_before_auction_results
        get_request().validated["bids_before_auction"] = get_bids_before_auction_results(tender)
    return get_request().validated["bids_before_auction"]


def since_2020_rules():  # TODO use it everywhere?
    return get_first_revision_date(get_tender(), default=get_now()) > RELEASE_2020_04_19
