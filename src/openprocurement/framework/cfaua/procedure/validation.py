from decimal import Decimal
from schematics.exceptions import ValidationError

from openprocurement.api.context import get_request
from openprocurement.api.utils import raise_operation_error


def validate_update_agreement_status(request, **kwargs):
    if changes := request.validated["agreement"].get("changes"):
        data = request.validated["data"]
        pending_changes = [change for change in changes if change["status"] == "pending"]
        if data.get("status") == "terminated" and pending_changes:
            raise_operation_error(request, "Can't update agreement status with pending change.")


def validate_agreement_change_add_not_in_allowed_agreement_status(request, **kwargs):
    agreement = request.validated["agreement"]
    if agreement["status"] != "active":
        raise_operation_error(
            request, f"Can't add agreement change in current ({agreement['status']}) agreement status"
        )


def validate_agreement_change_update_not_in_allowed_change_status(request, **kwargs):
    change = request.validated["change"]
    if change["status"] in {"active", "cancelled"}:
        raise_operation_error(request, f"Can't update agreement change in current ({change['status']}) status")


def validate_create_agreement_change(request, **kwargs):
    agreement = request.validated["agreement"]
    if agreement.get("changes") and agreement["changes"][-1]["status"] == "pending":
        raise_operation_error(request, "Can't create new agreement change while any (pending) change exists")


def validate_values_uniq(values):
    codes = [i.get("value") for i in values]
    if any([codes.count(i) > 1 for i in set(codes)]):
        raise ValidationError("Feature value should be uniq for feature")


def validate_features_uniq(features):
    if features:
        codes = [feature.get("code") for feature in features]
        if any([codes.count(i) > 1 for i in set(codes)]):
            raise ValidationError("Feature code should be uniq for all features")


def validate_parameters_uniq(parameters):
    if parameters:
        codes = [param.get("code") for param in parameters]
        if [i for i in set(codes) if codes.count(i) > 1]:
            raise ValidationError("Parameter code should be uniq for all parameters")

# changes modifications validators


def validate_item_price_variation_modifications(modifications):
    for modification in modifications:
        if modification.get("addend"):
            raise ValidationError("Only factor is allowed for itemPriceVariation type of change")
        if not Decimal("0.9") <= modification.get("factor") <= Decimal("1.1"):
            raise ValidationError("Modification factor should be in range 0.9 - 1.1")


def validate_third_party_modifications(modifications):
    for modification in modifications:
        if modification.get("addend"):
            raise ValidationError("Only factor is allowed for thirdParty type of change")


def validate_modifications_items_uniq(modifications):
    agreement = get_request().validated["agreement"]
    if modifications:
        agreement_items_id = {item["id"] for item in agreement.get("items", [])}
        item_ids = {m.itemId for m in modifications if m.itemId in agreement_items_id}
        if len(item_ids) != len(modifications):
            raise ValidationError("Item id should be uniq for all modifications and one of agreement:items")


def validate_modifications_contracts_uniq(modifications):
    agreement = get_request().validated["agreement"]
    if modifications:
        agreement_contracts_id = {contract["id"] for contract in agreement.get("contracts")}
        contracts_ids = {mod["contractId"] for mod in modifications if mod["contractId"] in agreement_contracts_id}
        if len(contracts_ids) != len(modifications):
            raise ValidationError("Contract id should be uniq for all modifications and one of agreement:contracts")


def validate_only_addend_or_only_factor(modifications):
    if modifications:
        changes_with_addend_and_factor = [
            mod for mod in modifications if mod.get("addend") and mod.get("factor")
        ]
        if changes_with_addend_and_factor:
            raise ValidationError("Change with taxRate rationaleType, can have only factor or only addend")


def validate_credentials_generate(request, **kwargs):
    agreement = request.validated["agreement"]
    if agreement["status"] != "active":
        raise_operation_error(
            request, f"Can't generate credentials in current ({agreement['status']}) agreement status"
        )
