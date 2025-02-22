import standards
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from isodate import ISO8601Error, parse_duration, duration_isoformat
from isodate.duration import Duration
import re
from uuid import uuid4
from urllib.parse import urlparse, parse_qs
from string import hexdigits
from hashlib import algorithms_guaranteed, new as hash_new
from schematics.exceptions import ConversionError, ValidationError, StopValidation
from schematics.models import Model as SchematicsModel
from schematics.transforms import whitelist, blacklist, export_loop, convert
from schematics.types import (
    StringType,
    IntType,
    FloatType,
    BooleanType,
    BaseType,
    EmailType,
    MD5Type,
    DecimalType as BaseDecimalType,
)
from schematics.types.compound import ModelType, DictType, ListType as BaseListType
from schematics.types.serializable import serializable
from openprocurement.api.utils import (
    get_now,
    set_parent,
    get_schematics_document,
    get_first_revision_date,
    get_root,
    parse_date,
)
from openprocurement.api.constants import (
    CPV_CODES,
    ORA_CODES,
    DK_CODES,
    CPV_BLOCK_FROM,
    SCALE_CODES,
    ORGANIZATION_SCALE_FROM,
    UA_ROAD_SCHEME,
    UA_ROAD,
    GMDN_2019_SCHEME,
    GMDN_2023_SCHEME,
    GMDN_2019,
    GMDN_2023,
    COUNTRIES,
    UA_REGIONS,
    VALIDATE_ADDRESS_FROM, TZ,
    VALIDATE_TELEPHONE_FROM,
    CURRENCIES,
    VALIDATE_CURRENCY_FROM,
    UNIT_CODE_REQUIRED_FROM,
)

schematics_default_role = blacklist("doc_id", "__parent__")
schematics_embedded_role = blacklist("_id", "_rev", "doc_type", "__parent__")
unit_codes = standards.load("unit_codes/recommended.json")
UNIT_CODES = unit_codes.keys()

plain_role = blacklist("_attachments", "revisions", "dateModified") + schematics_embedded_role
listing_role = whitelist("dateModified", "doc_id")
draft_role = whitelist("status")


class DecimalType(BaseDecimalType):
    def __init__(self, precision=-3, min_value=None, max_value=None, **kwargs):
        super(DecimalType, self).__init__(**kwargs)
        self.min_value, self.max_value = min_value, max_value
        self.precision = Decimal("1E{:d}".format(precision))

    def _apply_precision(self, value):
        try:
            value = Decimal(value).quantize(self.precision, rounding=ROUND_HALF_UP).normalize()
        except (TypeError, InvalidOperation):
            raise ConversionError(self.messages["number_coerce"].format(value))
        return value

    def to_primitive(self, value, context=None):
        return self._apply_precision(value)

    def to_native(self, value, context=None):
        return self._apply_precision(value)


# TODO: remove custom URLType after newer version of schematics will be used. The latest version has universal regex.
class URLType(StringType):
    MESSAGES = {
        'invalid_url': u"Not a well formed URL.",
        'not_found': u"URL does not exist.",
    }

    URL_REGEX = re.compile(r'^https?://\S+$', re.IGNORECASE)

    def __init__(self, verify_exists=False, **kwargs):
        self.verify_exists = verify_exists
        super(URLType, self).__init__(**kwargs)

    def validate_url(self, value):
        if not URLType.URL_REGEX.match(value):
            raise StopValidation(self.messages['invalid_url'])
        if self.verify_exists:
            from six.moves import urllib
            try:
                request = urllib.Request(value)
                urllib.urlopen(request)
            except Exception:
                raise StopValidation(self.messages['not_found'])


class StrictStringType(StringType):
    allow_casts = (str,)


class StrictIntType(IntType): # There are can be problem with old tenders where int values stores in string
    def to_native(self, value, context=None):
        if not isinstance(value, int):
            raise ConversionError(self.messages['number_coerce']
                                  .format(value, self.number_type.lower()))
        return super().to_native(value, context=context)


class StrictDecimalType(DecimalType):
    def to_native(self, value, context=None):
        if not isinstance(value, (int, float)):
            raise ConversionError(self.messages['number_coerce'].format(value))
        return super().to_native(value, context=context)


class StrictBooleanType(BooleanType):
    def to_native(self, value, context=None):
        if not isinstance(value, bool):
            raise ConversionError(f"Value '{value}' is not boolean.")
        return super().to_native(value, context=context)


class IsoDateTimeType(BaseType):
    MESSAGES = {"parse": "Could not parse {0}. Should be ISO8601."}

    def to_native(self, value, context=None):
        if isinstance(value, datetime):
            return value
        try:
            return parse_date(value, default_timezone=TZ)
        except ValueError:
            raise ConversionError(self.messages["parse"].format(value))
        except OverflowError as e:
            raise ConversionError(str(e))

    def to_primitive(self, value, context=None):
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class IsoDurationType(BaseType):
    """ Iso Duration format
           P is the duration designator (referred to as "period"), and is always placed at the beginning of the duration.
           Y is the year designator that follows the value for the number of years.
           M is the month designator that follows the value for the number of months.
           W is the week designator that follows the value for the number of weeks.
           D is the day designator that follows the value for the number of days.
           T is the time designator that precedes the time components.
           H is the hour designator that follows the value for the number of hours.
           M is the minute designator that follows the value for the number of minutes.
           S is the second designator that follows the value for the number of seconds.
           examples:  'P5000Y72M8W10DT55H3000M5S'
    """

    MESSAGES = {"parse": "Could not parse {0}. Should be ISO8601 Durations."}

    def to_native(self, value, context=None):
        if isinstance(value, Duration) or isinstance(value, timedelta):
            return value
        try:
            return parse_duration(value)
        except TypeError:
            raise ConversionError(self.messages["parse"].format(value))
        except ISO8601Error as e:
            raise ConversionError(str(e))

    def to_primitive(self, value, context=None):
        return duration_isoformat(value)


class ListType(BaseListType):
    def export_loop(self, list_instance, field_converter, role=None, print_none=False):
        """Loops over each item in the model and applies either the field
        transform or the multitype transform.  Essentially functions the same
        as `transforms.export_loop`.
        """
        data = []
        for value in list_instance:
            if hasattr(self.field, "export_loop"):
                shaped = self.field.export_loop(value, field_converter, role=role, print_none=print_none)
                feels_empty = shaped and len(shaped) == 0
            else:
                shaped = field_converter(self.field, value)
                feels_empty = shaped is None

            # Print if we want empty or found a value
            if feels_empty and self.field.allow_none():
                data.append(shaped)
            elif shaped is not None:
                data.append(shaped)
            elif print_none:
                data.append(shaped)

        # Return data if the list contains anything
        if len(data) > 0:
            return data
        elif len(data) == 0 and self.allow_none():
            return data
        elif print_none:
            return data


class SifterListType(ListType):
    def __init__(self, field, min_size=None, max_size=None, filter_by=None, filter_in_values=[], **kwargs):
        self.filter_by = filter_by
        self.filter_in_values = filter_in_values
        super(SifterListType, self).__init__(field, min_size=min_size, max_size=max_size, **kwargs)

    def export_loop(self, list_instance, field_converter, role=None, print_none=False):
        """ Use the same functionality as original method but apply
        additional filters.
        """
        data = []
        for value in list_instance:
            if hasattr(self.field, "export_loop"):
                item_role = role
                # apply filters
                if role not in ["plain", None] and self.filter_by and hasattr(value, self.filter_by):
                    val = getattr(value, self.filter_by)
                    if val in self.filter_in_values:
                        item_role = val

                shaped = self.field.export_loop(value, field_converter, role=item_role, print_none=print_none)
                feels_empty = shaped and len(shaped) == 0
            else:
                shaped = field_converter(self.field, value)
                feels_empty = shaped is None

            # Print if we want empty or found a value
            if feels_empty and self.field.allow_none():
                data.append(shaped)
            elif shaped is not None:
                data.append(shaped)
            elif print_none:
                data.append(shaped)

        # Return data if the list contains anything
        if len(data) > 0:
            return data
        elif len(data) == 0 and self.allow_none():
            return data
        elif print_none:
            return data


class Model(SchematicsModel):

    class Options:
        """Export options for Document."""

        serialize_when_none = False
        roles = {"default": blacklist("__parent__"), "embedded": blacklist("__parent__")}

    __parent__ = BaseType()

    # def __getattribute__(self, name):
    #     serializables = super(Model, self).__getattribute__("_serializables")
    #     if name in serializables.adaptive_items:
    #         return serializables[name](self)
    #     return super(Model, self).__getattribute__(name)

    def __getitem__(self, name):
        try:
            return getattr(self, name)
        except AttributeError as e:
            raise KeyError(e)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for k in self._fields:
                if k != "__parent__" and self.get(k) != other.get(k):
                    return False
            return True
        return NotImplemented

    def convert(self, raw_data, **kw):
        """
        Converts the raw data into richer Python constructs according to the
        fields on the model
        """
        value = convert(self.__class__, raw_data, **kw)
        for i, j in value.items():
            if isinstance(j, list):
                for x in j:
                    set_parent(x, self)
            else:
                set_parent(j, self)
        return value

    def to_patch(self, role=None):
        """
        Return data as it would be validated. No filtering of output unless
        role is defined.
        """
        field_converter = lambda field, value: field.to_primitive(value)
        data = export_loop(self.__class__, self, field_converter, role=role, raise_error_on_role=True, print_none=True)
        return data

    def get_role(self):
        root = self.get_root()
        request = root.request
        return "Administrator" if request.authenticated_role == "Administrator" else "edit"

    def get_root(self):
        root = self.__parent__
        while root.__parent__ is not None:
            root = root.__parent__
        return root


class RootModel(Model):
    _id = StringType(deserialize_from=['id', 'doc_id'])
    _rev = StringType()
    doc_type = StringType()
    public_modified = BaseType()

    @serializable(serialized_name="id")
    def doc_id(self):
        """A property that is serialized by schematics exports."""
        return self._id

    def _get_id(self):
        """id property getter."""
        return self._id

    def _set_id(self, value):
        """id property setter."""
        if self.id is not None:
            raise AttributeError('id can only be set on new documents')
        self._id = value

    id = property(_get_id, _set_id, doc='The document ID')

    @property
    def rev(self):
        """A property for self._rev"""
        return self._rev


class Guarantee(Model):
    amount = FloatType(required=True, min_value=0)  # Amount as a number.
    currency = StringType(required=True, default="UAH", max_length=3, min_length=3)  # 3-letter ISO 4217 format.

    def validate_currency(self, data, value):
        try:
            root = get_root(data.get("__parent__", {}))
        except AttributeError:
            root = None
        is_valid_date = get_first_revision_date(root, default=get_now()) >= VALIDATE_CURRENCY_FROM
        if is_valid_date and value not in CURRENCIES:
            raise ValidationError(f"Currency must be only {', '.join(CURRENCIES)}.")


class Value(Guarantee):
    valueAddedTaxIncluded = BooleanType(required=True, default=True)
    denominator = DecimalType()
    addition = DecimalType()


class Period(Model):
    startDate = IsoDateTimeType()  # The state date for the period.
    endDate = IsoDateTimeType()  # The end date for the period.

    def validate_startDate(self, data, value):
        if value and data.get("endDate") and data.get("endDate") < value:
            raise ValidationError("period should begin before its end")


class PeriodEndRequired(Period):
    endDate = IsoDateTimeType(required=True)  # The end date for the period.


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
            raise ValidationError(BaseType.MESSAGES["choices"].format(CPV_CODES))
        elif data.get("scheme") == "ДК021" and code not in DK_CODES:
            raise ValidationError(BaseType.MESSAGES["choices"].format(DK_CODES))

    def validate_scheme(self, data, scheme):
        schematics_document = get_schematics_document(data["__parent__"])
        date = get_first_revision_date(schematics_document, default=get_now())
        if date > CPV_BLOCK_FROM and scheme != "ДК021":
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


class Unit(Model):
    """Description of the unit which the good comes in e.g. hours, kilograms. Made up of a unit name, and the value of a single unit."""

    name = StringType()
    name_en = StringType()
    name_ru = StringType()
    value = ModelType(Value)
    code = StringType(required=True)

    def validate_code(self, data, value):
        root = get_root(data['__parent__'])
        validation_date = get_first_revision_date(root, default=get_now())
        if validation_date >= UNIT_CODE_REQUIRED_FROM:
            validate_unit_code(value)


class BaseAddress(Model):
    streetAddress = StringType()
    locality = StringType()
    region = StringType()
    postalCode = StringType()
    countryName = StringType(required=True)
    countryName_en = StringType()
    countryName_ru = StringType()


class Address(BaseAddress):
    def validate_countryName(self, data, value):
        root = get_root(data['__parent__'])
        if get_first_revision_date(root, default=get_now()) >= VALIDATE_ADDRESS_FROM:
            if value not in COUNTRIES:
                raise ValidationError("field address:countryName not exist in countries catalog")

    def validate_region(self, data, value):
        root = get_root(data['__parent__'])
        if get_first_revision_date(root, default=get_now()) >= VALIDATE_ADDRESS_FROM:
            if data["countryName"] == "Україна":
                if value and value not in UA_REGIONS:
                    raise ValidationError("field address:region not exist in ua_regions catalog")


class Location(Model):
    latitude = BaseType(required=True)
    longitude = BaseType(required=True)
    elevation = BaseType()


class HashType(StringType):

    MESSAGES = {
        "hash_invalid": "Hash type is not supported.",
        "hash_length": "Hash value is wrong length.",
        "hash_hex": "Hash value is not hexadecimal.",
    }

    def to_native(self, value, context=None):
        value = super(HashType, self).to_native(value, context)

        if ":" not in value:
            raise ValidationError(self.messages["hash_invalid"])

        hash_type, hash_value = value.split(":", 1)

        if hash_type not in algorithms_guaranteed:
            raise ValidationError(self.messages["hash_invalid"])

        if len(hash_value) != hash_new(hash_type).digest_size * 2:
            raise ValidationError(self.messages["hash_length"])
        try:
            int(hash_value, 16)
        except ValueError:
            raise ConversionError(self.messages["hash_hex"])
        return value


class Document(Model):
    class Options:
        namespace = "Document"
        roles = {
            "create": blacklist("id", "datePublished", "dateModified", "author", "download_url"),
            "edit": blacklist("id", "url", "datePublished", "dateModified", "author", "hash", "download_url"),
            "embedded": (blacklist("url", "download_url") + schematics_embedded_role),
            "default": blacklist("__parent__"),
            "view": schematics_default_role,
            "revisions": whitelist("url", "dateModified"),
        }

    id = MD5Type(required=True, default=lambda: uuid4().hex)
    hash = HashType()
    documentType = StringType(
        choices=[
            "tenderNotice",
            "awardNotice",
            "contractNotice",
            "notice",
            "biddingDocuments",
            "technicalSpecifications",
            "evaluationCriteria",
            "clarifications",
            "shortlistedFirms",
            "riskProvisions",
            "billOfQuantity",
            "bidders",
            "conflictOfInterest",
            "debarments",
            "evaluationReports",
            "winningBid",
            "complaints",
            "contractSigned",
            "contractArrangements",
            "contractSchedule",
            "contractAnnexe",
            "contractGuarantees",
            "subContract",
            "eligibilityCriteria",
            "contractProforma",
            "commercialProposal",
            "qualificationDocuments",
            "eligibilityDocuments",
            "registerExtract",
            "registerFiscal",
            "winningBid",
            "evidence",
            "register",
        ]
    )
    title = StringType(required=True)  # A title of the document.
    title_en = StringType()
    title_ru = StringType()
    description = StringType()  # A description of the document.
    description_en = StringType()
    description_ru = StringType()
    format = StringType(required=True, regex="^[-\w]+/[-\.\w\+]+$")
    url = StringType(required=True)  # Link to the document or attachment.
    datePublished = IsoDateTimeType(default=get_now)
    dateModified = IsoDateTimeType(default=get_now)  # Date that the document was last dateModified
    language = StringType()
    relatedItem = MD5Type()
    author = StringType()

    @serializable(serialized_name="url")
    def download_url(self):
        url = self.url
        if not url or "?download=" not in url:
            return url
        doc_id = parse_qs(urlparse(url).query)["download"][-1]
        root = self.__parent__
        parents = []
        while root.__parent__ is not None:
            parents[0:0] = [root]
            root = root.__parent__
        request = root.request
        if not request.registry.docservice_url:
            return url
        if "status" in parents[0] and parents[0].status in type(parents[0])._options.roles:
            role = parents[0].status
            for index, obj in enumerate(parents):
                if obj.id != url.split("/")[(index - len(parents)) * 2 - 1]:
                    break
                field = url.split("/")[(index - len(parents)) * 2]
                if "_" in field:
                    field = field[0] + field.title().replace("_", "")[1:]
                roles = type(obj)._options.roles
                if roles[role if role in roles else "default"](field, []):
                    return url
        from openprocurement.api.utils import generate_docservice_url

        if not self.hash:
            path = [i for i in urlparse(url).path.split("/") if len(i) == 32 and not set(i).difference(hexdigits)]
            return generate_docservice_url(request, doc_id, False, "{}/{}".format(path[0], path[-1]))
        return generate_docservice_url(request, doc_id, False)

    def import_data(self, raw_data, **kw):
        """
        Converts and imports the raw data into the instance of the model
        according to the fields in the model.
        :param raw_data:
            The data to be imported.
        """
        data = self.convert(raw_data, **kw)
        del_keys = [k for k in data.keys() if data[k] == getattr(self, k)]
        for k in del_keys:
            del data[k]

        self._data.update(data)
        return self


class Identifier(Model):
    scheme = StringType(
        required=True, choices=ORA_CODES
    )  # The scheme that holds the unique identifiers used to identify the item being identified.
    id = BaseType(required=True)  # The identifier of the organization in the selected scheme.
    legalName = StringType()  # The legally registered name of the organization.
    legalName_en = StringType()
    legalName_ru = StringType()
    uri = URLType()  # A URI to identify the organization.


class Item(Model):
    """A good, service, or work to be contracted."""

    id = StringType(required=True, min_length=1, default=lambda: uuid4().hex)
    description = StringType(required=True)  # A description of the goods, services to be provided.
    description_en = StringType()
    description_ru = StringType()
    classification = ModelType(CPVClassification)
    additionalClassifications = ListType(ModelType(AdditionalClassification), default=list())
    unit = ModelType(Unit)  # Description of the unit which the good comes in e.g. hours, kilograms
    quantity = FloatType(min_value=0)  # The number of units required
    deliveryDate = ModelType(Period)
    deliveryAddress = ModelType(Address)
    deliveryLocation = ModelType(Location)
    relatedLot = MD5Type()
    relatedBuyer = MD5Type()


class ContactPoint(Model):
    name = StringType(required=True)
    name_en = StringType()
    name_ru = StringType()
    email = EmailType()
    telephone = StringType()
    faxNumber = StringType()
    url = URLType()

    def validate_email(self, data, value):
        if not value and not data.get("telephone"):
            raise ValidationError("telephone or email should be present")

    def validate_telephone(self, data, value):
        try:
            root = get_schematics_document(data["__parent__"])
        except AttributeError:
            pass
        else:
            apply_validation = get_first_revision_date(root, default=get_now()) >= VALIDATE_TELEPHONE_FROM
            if apply_validation:
                validate_telephone(value)


class Organization(Model):
    """An organization."""

    class Options:
        roles = {"embedded": schematics_embedded_role, "view": schematics_default_role}

    name = StringType(required=True)
    name_en = StringType()
    name_ru = StringType()
    identifier = ModelType(Identifier, required=True)
    additionalIdentifiers = ListType(ModelType(Identifier))
    address = ModelType(Address, required=True)
    contactPoint = ModelType(ContactPoint, required=True)


class BusinessOrganization(Organization):
    scale = StringType(choices=SCALE_CODES)

    def validate_scale(self, data, value):
        try:
            schematics_document = get_schematics_document(data["__parent__"])
        except AttributeError:
            pass
        else:
            validation_date = get_first_revision_date(schematics_document, default=get_now())
            if validation_date >= ORGANIZATION_SCALE_FROM and value is None:
                raise ValidationError(BaseType.MESSAGES["required"])


class ContactLessBusinessOrganization(BusinessOrganization):
    contactPoint = ModelType(ContactPoint)


class Revision(Model):
    author = StringType()
    date = IsoDateTimeType(default=get_now)
    changes = ListType(DictType(BaseType), default=list())
    rev = StringType()


class BaseContract(Model):
    buyerID = StringType()
    awardID = StringType()
    contractID = StringType()
    contractNumber = StringType()
    title = StringType()  # Contract title
    title_en = StringType()
    title_ru = StringType()
    description = StringType()  # Contract description
    description_en = StringType()
    description_ru = StringType()
    status = StringType(choices=["pending", "pending.winner-signing", "terminated", "active", "cancelled"], default="pending")
    period = ModelType(Period)
    value = ModelType(Value)
    dateSigned = IsoDateTimeType()
    documents = ListType(ModelType(Document), default=list())
    items = ListType(ModelType(Item))
    suppliers = ListType(ModelType(BusinessOrganization), min_size=1, max_size=1)
    date = IsoDateTimeType()


class Contract(BaseContract):
    id = MD5Type(required=True, default=lambda: uuid4().hex)


class BankAccount(Model):
    id = StringType(required=True)
    scheme = StringType(choices=["IBAN", ], required=True)


class Reference(Model):
    id = StringType(required=True)
    title = StringType()


class ContractValue(Value):
    amountNet = FloatType(min_value=0)


PROCURING_ENTITY_KINDS = ("authority", "central", "defense", "general", "other", "social", "special")


# Validations
def validate_telephone(value):
    if value and re.match("^(\+)?[0-9]{2,}(,( )?(\+)?[0-9]{2,})*$", value) is None:
        raise ValidationError(u"wrong telephone format (could be missed +)")


def validate_unit_code(value):
    if value not in UNIT_CODES:
        raise ValidationError(u"Code should be one of valid unit codes.")