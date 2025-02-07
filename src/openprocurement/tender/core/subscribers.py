# -*- coding: utf-8 -*-
from pyramid.events import subscriber
from pyramid.events import ContextFound
from openprocurement.api.events import ErrorDescriptorEvent
from openprocurement.api.utils import update_logging_context


@subscriber(ErrorDescriptorEvent)
def tender_error_handler(event):
    if "tender" in event.request.validated:
        event.params["TENDER_REV"] = event.request.validated["tender"]["_rev"]
        event.params["TENDERID"] = event.request.validated["tender"]["tenderID"]
        event.params["TENDER_STATUS"] = event.request.validated["tender"]["status"]


@subscriber(ContextFound)
def extend_tender_logging_context(event):
    request = event.request
    if "tender" in request.validated:
        params = {}
        params["TENDER_REV"] = request.validated["tender"]["_rev"]
        params["TENDERID"] = request.validated["tender"]["tenderID"]
        params["TENDER_STATUS"] = request.validated["tender"]["status"]
        params["TENDER_MODE"] = request.validated["tender"].get("mode")
        update_logging_context(request, params)
