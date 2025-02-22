from openprocurement.api.models import ValidationError, Period, URLType
from openprocurement.tender.core.procedure.models.address import Address
from openprocurement.tender.core.procedure.models.base import ModelType, ListType, Model
from openprocurement.tender.core.procedure.models.unit import Unit
from openprocurement.tender.core.procedure.context import get_tender
from openprocurement.tender.core.procedure.utils import (
    tender_created_after,
    tender_created_before,
)
from openprocurement.tender.core.procedure.validation import validate_gmdn, validate_ua_road
from schematics.types import (
    StringType,
    MD5Type,
    FloatType,
    BaseType,
)
from openprocurement.api.constants import (
    CPV_CODES,
    DK_CODES,
    CPV_BLOCK_FROM,
    UA_ROAD_SCHEME,
    UA_ROAD,
    GMDN_2019_SCHEME,
    GMDN_2023_SCHEME,
    GMDN_2019,
    GMDN_2023,
    UNIT_CODE_REQUIRED_FROM,
    UNIT_PRICE_REQUIRED_FROM,
    MULTI_CONTRACTS_REQUIRED_FROM,
    CPV_336_INN_FROM,
    INN_SCHEME,
    CPV_PHARM_PRODUCTS,
    CPV_ITEMS_CLASS_FROM,
    NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES,
)
from uuid import uuid4


class Location(Model):
    latitude = BaseType(required=True)
    longitude = BaseType(required=True)
    elevation = BaseType()


class Classification(Model):
    scheme = StringType(required=True)  # The classification scheme for the goods
    id = StringType(required=True)  # The classification ID from the Scheme used
    description = StringType(required=True)  # A description of the goods, services to be provided.
    description_en = StringType()
    description_ru = StringType()
    uri = URLType()


class CPVClassification(Classification):
    scheme = StringType(required=True, default="CPV", choices=["CPV", "ДК021"])
    id = StringType(required=True)

    def validate_id(self, data, code):
        if data.get("scheme") == "CPV" and code not in CPV_CODES:
            raise ValidationError("Value must be one of CPV codes")
        elif data.get("scheme") == "ДК021" and code not in DK_CODES:
            raise ValidationError("Value must be one of ДК021 codes")

    def validate_scheme(self, data, scheme):
        if tender_created_after(CPV_BLOCK_FROM) and scheme != "ДК021":
            raise ValidationError(BaseType.MESSAGES["choices"].format(["ДК021"]))


class AdditionalClassification(Classification):
    def validate_id(self, data, value):
        if data["scheme"] == UA_ROAD_SCHEME and value not in UA_ROAD:
            raise ValidationError(f"{UA_ROAD_SCHEME} id not found in standards")
        if data["scheme"] == GMDN_2019_SCHEME and value not in GMDN_2019:
            raise ValidationError(f"{GMDN_2019_SCHEME} id not found in standards")
        if data["scheme"] == GMDN_2023_SCHEME and value not in GMDN_2023:
            raise ValidationError(f"{GMDN_2023_SCHEME} id not found in standards")

    def validate_description(self, data, value):
        if data["scheme"] == UA_ROAD_SCHEME and UA_ROAD.get(data["id"]) != value:
            raise ValidationError("{} description invalid".format(UA_ROAD_SCHEME))


class BaseItem(Model):
    id = StringType(required=True, min_length=1, default=lambda: uuid4().hex)
    description = StringType(required=True)  # A description of the goods, services to be provided.
    description_en = StringType()
    description_ru = StringType()
    unit = ModelType(Unit)  # Description of the unit which the good comes in e.g. hours, kilograms
    quantity = FloatType(min_value=0)  # The number of units required
    relatedLot = MD5Type()


class Item(BaseItem):
    classification = ModelType(CPVClassification, required=True)
    additionalClassifications = ListType(ModelType(AdditionalClassification))
    deliveryDate = ModelType(Period)
    deliveryAddress = ModelType(Address)
    deliveryLocation = ModelType(Location)
    relatedLot = MD5Type()
    relatedBuyer = MD5Type()

    def validate_unit(self, data, value):
        if not value:
            if tender_created_after(UNIT_CODE_REQUIRED_FROM):
                raise ValidationError(BaseType.MESSAGES["required"])

    def validate_quantity(self, data, value):
        if value is None:
            if tender_created_after(UNIT_PRICE_REQUIRED_FROM):
                raise ValidationError(BaseType.MESSAGES["required"])

    def validate_additionalClassifications(self, data, items):
        tender_from_2017 = tender_created_after(CPV_ITEMS_CLASS_FROM)
        classification_id = data["classification"]["id"]
        not_cpv = classification_id == "99999999-9"
        required = tender_created_before(NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM) and not_cpv
        if not items and (not tender_from_2017 or tender_from_2017 and not_cpv and required):
            raise ValidationError("This field is required.")
        elif (
            tender_from_2017
            and not_cpv
            and items
            and not any(i["scheme"] in ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017 for i in items)
        ):
            raise ValidationError(
                "One of additional classifications should be one of [{0}].".format(
                    ", ".join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017)
                )
            )
        elif (
            not tender_from_2017
            and items
            and not any(i["scheme"] in ADDITIONAL_CLASSIFICATIONS_SCHEMES for i in items)
        ):
            raise ValidationError(
                "One of additional classifications should be one of [{0}].".format(
                    ", ".join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)
                )
            )
        if items is not None:
            validate_ua_road(classification_id, items)
            validate_gmdn(classification_id, items)


class RelatedBuyerMixing:
    """
    Add this mixing to tender or contract
    """

    def validate_items(self, data, items):
        if tender_created_after(MULTI_CONTRACTS_REQUIRED_FROM):
            tender_data = get_tender() or data
            if (
                data.get("status", tender_data.get("status")) != "draft"
                and data.get("buyers", tender_data.get("buyers"))
            ):
                for i in items or []:
                    if not i.relatedBuyer:
                        raise ValidationError(BaseType.MESSAGES["required"])


def validate_related_buyer_in_items(data, items):
    if tender_created_after(MULTI_CONTRACTS_REQUIRED_FROM):
        if data["status"] != "draft" and data.get("buyers"):
            for i in items or []:
                if not i.relatedBuyer:
                    raise ValidationError([{'relatedBuyer': ['This field is required.']}])


def validate_classification_id(items, *args):
    for item in items:
        if tender_created_after(CPV_336_INN_FROM):
            schemes = [x.scheme for x in item.additionalClassifications or []]
            schemes_inn_count = schemes.count(INN_SCHEME)
            if item.classification.id == CPV_PHARM_PRODUCTS and schemes_inn_count != 1:
                raise ValidationError(
                    "Item with classification.id={} have to contain exactly one additionalClassifications "
                    "with scheme={}".format(CPV_PHARM_PRODUCTS, INN_SCHEME)
                )
            if item.classification.id.startswith(CPV_PHARM_PRODUCTS[:3]) and schemes_inn_count > 1:
                raise ValidationError(
                    "Item with classification.id that starts with {} and contains additionalClassification "
                    "objects have to contain no more than one additionalClassifications "
                    "with scheme={}".format(CPV_PHARM_PRODUCTS[:3], INN_SCHEME))


def validate_items_uniq(items, *args):
    if items:
        ids = [i.id for i in items]
        if len(ids) > len(set(ids)):
            raise ValidationError("Item id should be uniq for all items")


def validate_quantity_required(data, value):
    if value is None:
        if tender_created_after(UNIT_PRICE_REQUIRED_FROM):
            raise ValidationError(BaseType.MESSAGES["required"])


def validate_unit_required(data, value):
    if not value:
        if tender_created_after(UNIT_CODE_REQUIRED_FROM):
            raise ValidationError(BaseType.MESSAGES["required"])
