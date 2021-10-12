# -*- coding: utf-8 -*-
from openprocurement.api.roles import RolesFromCsv
from schematics.types import StringType, BaseType
from schematics.types.compound import ModelType
from openprocurement.api.models import Address

from openprocurement.tender.cfaua.models.submodels.periods import PeriodEndRequired
from openprocurement.tender.cfaua.models.submodels.unit import Unit
from openprocurement.tender.core.models import Item as BaseItem, get_tender
from openprocurement.api.utils import get_now, get_first_revision_date
from openprocurement.api.constants import UNIT_PRICE_REQUIRED_FROM, MULTI_CONTRACTS_REQUIRED_FROM, \
    UNIT_CODE_REQUIRED_FROM
from schematics.exceptions import ValidationError


# openprocurement.tender.openua.models.Item
class Item(BaseItem):
    """A good, service, or work to be contracted."""

    class Options:
        roles = RolesFromCsv("Item.csv", relative_to=__file__)

    description_en = StringType(required=True, min_length=1)
    deliveryDate = ModelType(PeriodEndRequired, required=True)
    deliveryAddress = ModelType(Address, required=True)
    unit = ModelType(Unit)

    def validate_relatedBuyer(self, data, related_buyer):
        tender = get_tender(data["__parent__"])
        validation_date = get_first_revision_date(tender, default=get_now())
        validation_enabled = all([
            tender.buyers,
            tender.status != "draft",
            validation_date >= MULTI_CONTRACTS_REQUIRED_FROM
        ])
        if validation_enabled and not related_buyer:
            raise ValidationError(BaseType.MESSAGES["required"])

    def validate_unit(self, data, value):
        tender = get_tender(data["__parent__"])
        validation_date = get_first_revision_date(tender, default=get_now())
        if validation_date >= UNIT_CODE_REQUIRED_FROM and not value:
            raise ValidationError(BaseType.MESSAGES["required"])

    def validate_quantity(self, data, value):
        tender = get_tender(data["__parent__"])
        validation_date = get_first_revision_date(tender, default=get_now())
        if validation_date >= UNIT_PRICE_REQUIRED_FROM and value is None:
            raise ValidationError(BaseType.MESSAGES["required"])
