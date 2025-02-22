from schematics.types.compound import ModelType
from schematics.types import MD5Type, StringType
from openprocurement.api.models import Model, Value
from openprocurement.tender.core.procedure.models.guarantee import WeightedValue
from openprocurement.tender.core.procedure.validation import (
    validate_lotvalue_value,
    validate_related_lot,
)
from openprocurement.tender.core.procedure.context import get_tender


class PostLotValue(Model):
    status = StringType(choices=["pending"], default="pending", required=True)
    value = ModelType(Value, required=True)
    relatedLot = MD5Type(required=True)

    def validate_value(self, data, value):
        validate_lotvalue_value(get_tender(), data["relatedLot"], value)

    def validate_relatedLot(self, data, related_lot):
        validate_related_lot(get_tender(), related_lot)


class PatchLotValue(PostLotValue):
    status = StringType(choices=["pending"], default="pending")
    value = ModelType(Value)
    relatedLot = MD5Type()

    def validate_value(self, data, value):
        if value is not None:
            validate_lotvalue_value(get_tender(), data["relatedLot"], value)

    def validate_relatedLot(self, data, related_lot):
        if related_lot is not None:
            validate_related_lot(get_tender(), related_lot)


class LotValue(PostLotValue):
    weightedValue = ModelType(WeightedValue)
    status = StringType(choices=["pending", "active", "unsuccessful"], required=True)
    date = StringType()
