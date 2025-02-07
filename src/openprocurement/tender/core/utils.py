import re
from functools import wraps
from dateorro import (
    calc_datetime,
    calc_working_datetime,
    calc_normalized_datetime,
)
from datetime import timedelta
from logging import getLogger

from openprocurement.api.constants import (
    WORKING_DAYS,
    WORKING_DATE_ALLOW_MIDNIGHT_FROM,
    NORMALIZED_CLARIFICATIONS_PERIOD_FROM,
    NORMALIZED_TENDER_PERIOD_FROM,
)
from openprocurement.api.utils import (
    get_now,
    get_first_revision_date,
)
from openprocurement.api.validation import validate_json_data
from openprocurement.tender.core.constants import (
    NORMALIZED_COMPLAINT_PERIOD_FROM,
)
from openprocurement.tender.open.constants import (
    ABOVE_THRESHOLD_GROUP_NAME,
    ABOVE_THRESHOLD_GROUP,
)

LOGGER = getLogger("openprocurement.tender.core")

ACCELERATOR_RE = re.compile(".accelerator=(?P<accelerator>\d+)")


QUICK = "quick"
QUICK_NO_AUCTION = "quick(mode:no-auction)"
QUICK_FAST_FORWARD = "quick(mode:fast-forward)"
QUICK_FAST_AUCTION = "quick(mode:fast-auction)"


class ProcurementMethodTypePredicate(object):
    """ Route predicate factory for procurementMethodType route predicate. """

    def __init__(self, val, config):
        self.val = val

    def text(self):
        return "procurementMethodType = %s" % (self.val,)

    phash = text

    def __call__(self, context, request):
        procurement_method_type = self.procurement_method_type(request)
        if isinstance(self.val, list):
            return procurement_method_type in self.val
        return procurement_method_type == self.val

    @staticmethod
    def tender_data(request):
        if request.tender_doc is not None:
            return request.tender_doc
        elif request.method == "POST" and request.path.endswith("/tenders"):
            # that's how we can have a "POST /tender" view for every tender type
            return validate_json_data(request)
        else:
            return None

    @classmethod
    def procurement_method_type(cls, request):
        data = cls.tender_data(request)
        if data is None:
            return None
        return data.get("procurementMethodType", "belowThreshold")

    @classmethod
    def route_prefix(cls, request):
        procurement_method_type = cls.procurement_method_type(request)
        if procurement_method_type in ABOVE_THRESHOLD_GROUP:
            return ABOVE_THRESHOLD_GROUP_NAME
        return procurement_method_type


class ComplaintTypePredicate(object):
    """ Route predicate factory for complaintType route predicate. """

    def __init__(self, val, config):
        self.val = val

    def text(self):
        return "complaintType = %s" % (self.val,)

    phash = text

    def __call__(self, context, request):
        return request.complaint_type == self.val



def get_tender_accelerator(context):
    if context and "procurementMethodDetails" in context and context["procurementMethodDetails"]:
        re_obj = ACCELERATOR_RE.search(context["procurementMethodDetails"])
        if re_obj and "accelerator" in re_obj.groupdict():
            return int(re_obj.groupdict()["accelerator"])
    return None


def acceleratable(wrapped):
    @wraps(wrapped)
    def wrapper(date_obj, timedelta_obj, tender=None, working_days=False, calendar=WORKING_DAYS):
        accelerator = get_tender_accelerator(tender)
        if accelerator:
            return calc_datetime(date_obj, timedelta_obj, accelerator=accelerator)
        return wrapped(date_obj, timedelta_obj, tender=tender, working_days=working_days, calendar=calendar)
    return wrapper


@acceleratable
def calculate_tender_date(date_obj, timedelta_obj, tender=None, working_days=False, calendar=WORKING_DAYS):
    if working_days:
        tender_date = get_first_revision_date(tender, default=get_now())
        midnight = tender_date > WORKING_DATE_ALLOW_MIDNIGHT_FROM
        return calc_working_datetime(date_obj, timedelta_obj, midnight, calendar)
    else:
        return calc_datetime(date_obj, timedelta_obj)


def calculate_period_start_date(date_obj, timedelta_obj, normalized_from_date_obj, tender=None):
    tender_date = get_first_revision_date(tender, default=get_now())
    if tender_date > normalized_from_date_obj:
        return calc_normalized_datetime(date_obj, ceil=timedelta_obj > timedelta())
    else:
        return date_obj


@acceleratable
def calculate_tender_business_date(date_obj, timedelta_obj, tender=None, working_days=False, calendar=WORKING_DAYS):
    start_obj = calculate_period_start_date(date_obj, timedelta_obj, NORMALIZED_TENDER_PERIOD_FROM, tender)
    return calculate_tender_date(start_obj, timedelta_obj, tender, working_days, calendar)


@acceleratable
def calculate_complaint_business_date(date_obj, timedelta_obj, tender=None, working_days=False, calendar=WORKING_DAYS):
    start_obj = calculate_period_start_date(date_obj, timedelta_obj, NORMALIZED_COMPLAINT_PERIOD_FROM, tender)
    return calculate_tender_date(start_obj, timedelta_obj, tender, working_days, calendar)


@acceleratable
def calculate_clarif_business_date(date_obj, timedelta_obj, tender=None, working_days=False, calendar=WORKING_DAYS):
    start_obj = calculate_period_start_date(date_obj, timedelta_obj, NORMALIZED_CLARIFICATIONS_PERIOD_FROM, tender)
    return calculate_tender_date(start_obj, timedelta_obj, tender, working_days, calendar)
