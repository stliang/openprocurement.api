# -*- coding: utf-8 -*-
from schematics.exceptions import ValidationError

from openprocurement.api.utils import get_now, raise_operation_error, update_logging_context
from openprocurement.api.validation import validate_data, OPERATIONS
from openprocurement.frameworkagreement.cfaua.constants import MIN_BIDS_NUMBER


def validate_patch_qualification_data(request):
    qualification_class = type(request.context)
    return validate_data(request, qualification_class, True)

# bids
def validate_view_bids_in_active_tendering(request):
    if request.validated['tender_status'] == 'active.tendering':
        raise_operation_error(request, 'Can\'t view {} in current ({}) tender status'.format('bid' if request.matchdict.get('bid_id') else 'bids', request.validated['tender_status']))

# bid document
def validate_add_bid_document_not_in_allowed_status(request):
    if request.context.status in ['invalid', 'unsuccessful', 'deleted']:
        raise_operation_error(request, 'Can\'t add document to \'{}\' bid'.format(request.context.status))


def validate_update_bid_document_confidentiality(request):
    if request.validated['tender_status'] != 'active.tendering' and 'confidentiality' in request.validated.get('data', {}):
        if request.context.confidentiality != request.validated['data']['confidentiality']:
            raise_operation_error(request, 'Can\'t update document confidentiality in current ({}) tender status'.format(request.validated['tender_status']))


def validate_update_bid_document_not_in_allowed_status(request):
    bid = getattr(request.context, "__parent__")
    if bid and bid.status in ['invalid', 'unsuccessful', 'deleted']:
        raise_operation_error(request, 'Can\'t update {} \'{}\' bid'.format('document in' if request.method == 'PUT' else 'document data for',bid.status))


# qualification
def validate_qualification_document_operation_not_in_allowed_status(request):
    if request.validated['tender_status'] != 'active.pre-qualification':
        raise_operation_error(request, 'Can\'t {} document in current ({}) tender status'.format(OPERATIONS.get(request.method), request.validated['tender_status']))


def validate_qualification_document_operation_not_in_pending(request):
    qualification = request.validated['qualification']
    if qualification.status != 'pending':
        raise_operation_error(request, 'Can\'t {} document in current qualification status'.format(OPERATIONS.get(request.method)))

# qualification complaint
def validate_qualification_update_not_in_pre_qualification(request):
    tender = request.validated['tender']
    if tender.status not in ['active.pre-qualification']:
        raise_operation_error(request, 'Can\'t update qualification in current ({}) tender status'.format(tender.status))


def validate_cancelled_qualification_update(request):
    if request.context.status == 'cancelled':
        raise_operation_error(request, 'Can\'t update qualification in current cancelled qualification status')


def validate_add_complaint_not_in_pre_qualification(request):
    tender = request.validated['tender']
    if tender.status not in ['active.pre-qualification.stand-still']:
        raise_operation_error(request, 'Can\'t add complaint in current ({}) tender status'.format(tender.status))


def validate_update_complaint_not_in_pre_qualification(request):
    tender = request.validated['tender']
    if tender.status not in ['active.pre-qualification', 'active.pre-qualification.stand-still']:
        raise_operation_error(request, 'Can\'t update complaint in current ({}) tender status'.format(tender.status))


def validate_update_qualification_complaint_only_for_active_lots(request):
    tender = request.validated['tender']
    if any([i.status != 'active' for i in tender.lots if i.id == request.validated['qualification'].lotID]):
        raise_operation_error(request, 'Can update complaint only in active lot status')


def validate_add_complaint_not_in_qualification_period(request):
    tender = request.validated['tender']
    if tender.qualificationPeriod and \
       (tender.qualificationPeriod.startDate and tender.qualificationPeriod.startDate > get_now() or
            tender.qualificationPeriod.endDate and tender.qualificationPeriod.endDate < get_now()):
        raise_operation_error(request, 'Can add complaint only in qualificationPeriod')


def validate_tender_status_update(request):
    tender = request.context
    data = request.validated['data']
    if request.authenticated_role == 'tender_owner' and 'status' in data and data['status'] not in ['active.pre-qualification.stand-still', 'active.qualification.stand-still', tender.status]:
        raise_operation_error(request, 'Can\'t update tender status')

# agreement
def validate_agreement_data(request):
    update_logging_context(request, {'agreement_id': '__new__'})
    model = type(request.tender).agreements.model_class
    return validate_data(request, model)


def validate_patch_agreement_data(request):
    model = type(request.tender).agreements.model_class
    return validate_data(request, model, True)


def validate_agreement_operation_not_in_allowed_status(request):
    if request.validated['tender_status'] not in ['active.qualification', 'active.awarded']:
        raise_operation_error(request,
                              'Can\'t {} agreement in current ({}) tender status'.format(
                                  OPERATIONS.get(request.method), request.validated['tender_status']))


def validate_update_agreement_only_for_active_lots(request):
    tender = request.validated['tender']
    if any([
        i.status != 'active'
            for i in tender.lots if i.id in [a.lotID for a in tender.awards if a.id == request.context.awardID]]):
        raise_operation_error(request, 'Can update agreement only in active lot status')


def validate_update_agreement_value(request):
    tender = request.validated['tender']
    data = request.validated['data']
    if data.get('value'):
        for ro_attr in ('valueAddedTaxIncluded', 'currency'):
            if data['value'][ro_attr] != getattr(request.context.value, ro_attr):
                raise_operation_error(request, 'Can\'t update {} for agreement value'.format(ro_attr))
        award = [a for a in tender.awards if a.id == request.context.awardID][0]
        if request.content_configurator.reverse_awarding_criteria:
            if data['value']['amount'] != award.value.amount:
                raise_operation_error(
                    request, 'Value amount should be equal to awarded amount ({})'.format(award.value.amount)
                )
        else:
            if data['value']['amount'] > award.value.amount:
                raise_operation_error(
                    request, 'Value amount should be less or equal to awarded amount ({})'.format(award.value.amount)
                )


def validate_agreement_signing(request):
    tender = request.validated['tender']
    data = request.validated['data']
    if request.context.status != 'active' and 'status' in data and data['status'] == 'active':
        award = [a for a in tender.awards if a.id == request.context.awardID][0]
        stand_still_end = award.complaintPeriod.endDate
        if stand_still_end > get_now():
            raise_operation_error(
                request, 'Can\'t sign agreement before stand-still period end ({})'.format(stand_still_end.isoformat())
            )
        pending_complaints = [
            i
            for i in tender.complaints
            if i.status in tender.block_complaint_status and i.relatedLot in [None, award.lotID]
        ]
        pending_awards_complaints = [
            i
            for a in tender.awards
            for i in a.complaints
            if i.status in tender.block_complaint_status and a.lotID == award.lotID
        ]
        if pending_complaints or pending_awards_complaints:
            raise_operation_error(request, 'Can\'t sign agreement before reviewing all complaints')


def validate_agreement_update_with_accepted_complaint(request):
    tender = request.validated['tender']
    if any([
        any([c.status == 'accepted' for c in i.complaints])
            for i in tender.awards if i.lotID in [a.lotID for a in tender.awards if a.id == request.context.awardID]]):
        raise_operation_error(request, 'Can\'t update agreement with accepted complaint')


# award complaint
def validate_award_complaint_operation_not_in_allowed_status(request):
    tender = request.validated['tender']
    if tender.status not in ['active.qualification.stand-still']:
        raise_operation_error(
            request,
            'Can\'t {} complaint in current ({}) tender status'.format(OPERATIONS.get(request.method), tender.status)
        )


def validate_add_complaint_not_in_complaint_period(request):
    if not request.context.complaintPeriod or (request.context.complaintPeriod and
       (request.context.complaintPeriod.startDate and request.context.complaintPeriod.startDate > get_now() or
            request.context.complaintPeriod.endDate and request.context.complaintPeriod.endDate < get_now())):
        raise_operation_error(request, 'Can add complaint only in complaintPeriod')


def validate_max_awards_number(number, *args):
    if number < MIN_BIDS_NUMBER:
        raise ValidationError('Maximal awards number can\'t be less then minimal')
