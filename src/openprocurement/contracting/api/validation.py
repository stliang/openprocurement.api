# -*- coding: utf-8 -*-
from openprocurement.api.utils import (
    update_logging_context,
    raise_operation_error, requested_fields_changes,
)
from openprocurement.api.validation import (
    validate_json_data,
    validate_data,
    _validate_accreditation_level,
    OPERATIONS,
)
from openprocurement.contracting.api.models import Contract, Change
from openprocurement.tender.core.validation import (
    validate_update_contract_value,
    validate_update_contract_value_amount,
    validate_update_contract_value_net_required,
    validate_contract_items_unit_value_amount,
)
from openprocurement.api.models import Model, IsoDateTimeType, Guarantee, ContractValue
from openprocurement.contracting.api.models import OrganizationReference
from schematics.types import StringType
from schematics.types.compound import ModelType
from openprocurement.api.models import schematics_default_role
from openprocurement.contracting.core.utils import get_transaction_by_id


def validate_contract_data(request, **kwargs):
    update_logging_context(request, {"contract_id": "__new__"})
    data = validate_json_data(request)
    model = request.contract_from_data(data, create=False)
    _validate_contract_accreditation_level(request, model)
    return validate_data(request, model, data=data)


def _validate_contract_accreditation_level(request, model):
    _validate_accreditation_level(request, model.create_accreditations, "contract", "creation")


def validate_patch_contract_data(request, **kwargs):
    return validate_data(request, Contract, True)


def validate_put_transaction_to_contract(request, **kwargs):
    class InitialTransaction(Model):
        date = IsoDateTimeType(required=True)
        value = ModelType(Guarantee, required=True)
        payer = ModelType(OrganizationReference, required=True)
        payee = ModelType(OrganizationReference, required=True)
        status = StringType(required=True)

        class Options:
            roles = {
                "create": schematics_default_role
            }

    return validate_data(request, model=InitialTransaction)


def validate_change_data(request, **kwargs):
    update_logging_context(request, {"change_id": "__new__"})
    data = validate_json_data(request)
    return validate_data(request, Change, data=data)


def validate_patch_change_data(request, **kwargs):
    return validate_data(request, Change, True)


# changes
def validate_contract_change_add_not_in_allowed_contract_status(request, **kwargs):
    contract = request.validated["contract"]
    if contract.status != "active":
        raise_operation_error(
            request, "Can't add contract change in current ({}) contract status".format(contract.status)
        )


def validate_create_contract_change(request, **kwargs):
    contract = request.validated["contract"]
    if contract.changes and contract.changes[-1].status == "pending":
        raise_operation_error(request, "Can't create new contract change while any (pending) change exists")


def validate_contract_change_update_not_in_allowed_change_status(request, **kwargs):
    change = request.validated["change"]
    if change.status == "active":
        raise_operation_error(request, "Can't update contract change in current ({}) status".format(change.status))


def validate_update_contract_change_status(request, **kwargs):
    data = request.validated["data"]
    if not data.get("dateSigned", ""):
        raise_operation_error(request, "Can't update contract change status. 'dateSigned' is required.")


# contract
def validate_contract_update_not_in_allowed_status(request, **kwargs):
    contract = request.validated["contract"]
    if request.authenticated_role != "Administrator" and contract.status != "active":
        raise_operation_error(request, "Can't update contract in current ({}) status".format(contract.status))


def validate_terminate_contract_without_amountPaid(request, **kwargs):
    contract = request.validated["contract"]
    if contract.status == "terminated" and not contract.amountPaid:
        raise_operation_error(request, "Can't terminate contract while 'amountPaid' is not set")


def validate_credentials_generate(request, **kwargs):
    contract = request.validated["contract"]
    if contract.status != "active":
        raise_operation_error(
            request, "Can't generate credentials in current ({}) contract status".format(contract.status)
        )


# contract document
def validate_contract_document_operation_not_in_allowed_contract_status(request, **kwargs):
    if request.validated["contract"].status != "active":
        raise_operation_error(
            request,
            "Can't {} document in current ({}) contract status".format(
                OPERATIONS.get(request.method), request.validated["contract"].status
            ),
        )


def validate_transaction_existence(request, **kwargs):
    transaction = get_transaction_by_id(request)
    if not transaction:
        raise_operation_error(request, "Transaction does not exist", status=404)


def validate_file_transaction_upload(request, **kwargs):
    transaction = get_transaction_by_id(request)
    if not transaction:
        raise_operation_error(request, "Can't add document contract to nonexistent transaction", status=404)

    update_logging_context(request, {"document_id": "__new__"})
    if request.registry.docservice_url and request.content_type == "application/json":
        model = type(transaction).documents.model_class
        return validate_data(request, model)


def validate_update_contracting_items_unit_value_amount(request, **kwargs):
    contract = request.validated["contract"]
    if contract.items:
        validate_contract_items_unit_value_amount(request, contract)


def validate_add_document_to_active_change(request, **kwargs):
    data = request.validated["data"]
    if "relatedItem" in data and data.get("documentOf") == "change":
        changes = request.validated["contract"].changes
        if not any(c.id == data["relatedItem"] and c.status == "pending" for c in changes):
            raise_operation_error(request, "Can't add document to 'active' change")


# contract value and paid
def validate_update_contracting_value_amount(request, name="value", **kwargs):
    validate_update_contract_value_amount(request, name=name)


def validate_update_contracting_paid_amount(request, **kwargs):
    data = request.validated["data"]
    value = data.get("value")
    paid = data.get("amountPaid")
    if not paid:
        return
    validate_update_contracting_value_amount(request, name="amountPaid")
    if not value:
        return
    attr = "amountNet"
    paid_amount = paid.get(attr)
    value_amount = value.get(attr)
    if value_amount and paid_amount > value_amount:
        raise_operation_error(
            request,
            "AmountPaid {} can`t be greater than value {}".format(attr, attr),
            name="amountPaid",
        )


def validate_contract_patch_items_amount_unchanged(request, **kwargs):
    if 'items' not in request.validated["data"]:
        return
    old_contract_items = request.contract.items or []
    new_contract_items = request.validated["data"].get('items') or []
    if len(old_contract_items) != len(new_contract_items):
        raise_operation_error(
            request, f"Can't add or remove items."
        )


def validate_update_contracting_value_readonly(request, **kwargs):
    validate_update_contract_value(request, name="value", attrs=("currency",))


def validate_update_contracting_value_identical(request, **kwargs):
    if requested_fields_changes(request, ("amountPaid",)):
        value = request.validated["data"].get("value")
        paid_data = request.validated["json_data"].get("amountPaid")
        for attr in ("currency",):
            if value and paid_data and paid_data.get(attr) is not None:
                paid = ContractValue(paid_data)
                if value.get(attr) != paid.get(attr):
                    raise_operation_error(
                        request,
                        "{} of {} should be identical to {} of value of contract".format(attr, "amountPaid", attr),
                        name="amountPaid",
                    )


def validate_update_contract_paid_net_required(request, **kwargs):
    validate_update_contract_value_net_required(request, name="amountPaid")
