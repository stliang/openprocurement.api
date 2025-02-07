# -*- coding: utf-8 -*-
import os
import re

import pytz

from configparser import ConfigParser, DEFAULTSECT
from ciso8601 import parse_datetime
from pytz import timezone
from datetime import datetime
from logging import getLogger
from requests import Session

import standards

LOGGER = getLogger("openprocurement.api")
VERSION = "2.5"
ROUTE_PREFIX = "/api/{}".format(VERSION)
SESSION = Session()
SCHEMA_VERSION = 24
SCHEMA_DOC = "openprocurement_schema"
OCID_PREFIX = os.environ.get("OCID_PREFIX", "ocds-be6bcu")

TZ = timezone(os.environ["TZ"] if "TZ" in os.environ else "Europe/Kiev")
SANDBOX_MODE = os.environ.get("SANDBOX_MODE", False)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DOCUMENT_BLACKLISTED_FIELDS = ("title", "format", "url", "dateModified", "hash")
DOCUMENT_WHITELISTED_FIELDS = ("id", "datePublished", "author", "__parent__")

# Tenders in which could be used criteria connected with guarantee
GUARANTEE_ALLOWED_TENDER_TYPES = (
    "belowThreshold",
    "aboveThreshold",
    "competitiveOrdering",
    "aboveThresholdUA",
    "aboveThresholdEU",
    "esco",
)

WORKING_DAYS = {}
HOLIDAYS = standards.load("calendars/workdays_off.json")
for date_str in HOLIDAYS:
    WORKING_DAYS[date_str] = True


def parse_str_list(value):
    return [x.strip() for x in value.split(',') if x.strip()]


DEPRECATED_FEED_USER_AGENTS = parse_str_list(os.environ.get("DEPRECATED_FEED_USER_AGENTS", ""))

TENDER_PERIOD_START_DATE_STALE_MINUTES = int(os.environ.get("TENDER_PERIOD_START_DATE_STALE_MINUTES", 10))

CPV_CODES = list(standards.load("classifiers/cpv_en.json"))
CPV_CODES.append("99999999-9")
DK_CODES = list(standards.load("classifiers/dk021_uk.json"))
FUNDERS = [
    (i["identifier"]["scheme"], i["identifier"]["id"])
    for i in standards.load("codelists/tender/tender_funder.json")
]
ORA_CODES = [i["code"] for i in standards.load("organizations/identifier_scheme.json")["data"]]
# extended keys gmdn contains actual and obsolete codes, since deleted codes can block un-refactored endpoints
GMDN_2019 = set(standards.load("classifiers/gmdn.json"))
GMDN_2023 = set(standards.load("classifiers/gmdn_2023.json"))
GMDN_CPV_PREFIXES = standards.load("classifiers/gmdn_cpv_prefixes.json")
UA_ROAD = standards.load("classifiers/ua_road.json")
UA_ROAD_CPV_PREFIXES = standards.load("classifiers/ua_road_cpv_prefixes.json")

# complaint objections classifications
ARTICLE_16 = set(criterion["classification"]["id"] for criterion in standards.load("criteria/article_16.json"))
ARTICLE_17 = set(criterion["classification"]["id"] for criterion in standards.load("criteria/article_17.json"))
OTHER_CRITERIA = set(criterion["classification"]["id"] for criterion in standards.load("criteria/other.json"))
VIOLATION_AMCU = set(standards.load("AMCU/violation_amcu.json"))
REQUESTED_REMEDIES_TYPES = set(standards.load("AMCU/requested_remedies_type.json"))

ADDITIONAL_CLASSIFICATIONS_SCHEMES = ["ДКПП", "NONE", "ДК003", "ДК015", "ДК018"]
ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017 = ["ДК003", "ДК015", "ДК018", "specialNorms"]

INN_SCHEME = "INN"
ATC_SCHEME = "ATC"
GMDN_2019_SCHEME = "GMDN"
GMDN_2023_SCHEME = "GMDN-2023"
UA_ROAD_SCHEME = "UA-ROAD"

CPV_PHARM_PRODUCTS = "33600000-6"

COORDINATES_REG_EXP = re.compile(r"-?\d{1,3}\.\d+|-?\d{1,3}")

SCALE_CODES = ["micro", "sme", "mid", "large", "not specified"]

CPV_ITEMS_CLASS_FROM = datetime(2017, 1, 1, tzinfo=TZ)
CPV_BLOCK_FROM = datetime(2017, 6, 2, tzinfo=TZ)

TENDER_CONFIG_JSONSCHEMAS = {
    "aboveThreshold": standards.load(f"data_model/schema/TenderConfig/aboveThreshold.json"),
    "competitiveOrdering": standards.load(f"data_model/schema/TenderConfig/competitiveOrdering.json"),
    "aboveThresholdEU": standards.load(f"data_model/schema/TenderConfig/aboveThresholdEU.json"),
    "aboveThresholdUA.defense": standards.load(f"data_model/schema/TenderConfig/aboveThresholdUA.defense.json"),
    "aboveThresholdUA": standards.load(f"data_model/schema/TenderConfig/aboveThresholdUA.json"),
    "belowThreshold": standards.load(f"data_model/schema/TenderConfig/belowThreshold.json"),
    "closeFrameworkAgreementSelectionUA": standards.load(f"data_model/schema/TenderConfig/closeFrameworkAgreementSelectionUA.json"),
    "closeFrameworkAgreementUA": standards.load(f"data_model/schema/TenderConfig/closeFrameworkAgreementUA.json"),
    "competitiveDialogueEU": standards.load(f"data_model/schema/TenderConfig/competitiveDialogueEU.json"),
    "competitiveDialogueEU.stage2": standards.load(f"data_model/schema/TenderConfig/competitiveDialogueEU.stage2.json"),
    "competitiveDialogueUA": standards.load(f"data_model/schema/TenderConfig/competitiveDialogueUA.json"),
    "competitiveDialogueUA.stage2": standards.load(f"data_model/schema/TenderConfig/competitiveDialogueUA.stage2.json"),
    "esco": standards.load(f"data_model/schema/TenderConfig/esco.json"),
    "negotiation": standards.load(f"data_model/schema/TenderConfig/negotiation.json"),
    "negotiation.quick": standards.load(f"data_model/schema/TenderConfig/negotiation.quick.json"),
    "priceQuotation": standards.load(f"data_model/schema/TenderConfig/priceQuotation.json"),
    "reporting": standards.load(f"data_model/schema/TenderConfig/reporting.json"),
    "simple.defense": standards.load(f"data_model/schema/TenderConfig/simple.defense.json"),
}

def get_default_constants_file_path():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "constants.ini")


def load_constants(file_path):
    config = ConfigParser()
    try:
        with open(file_path) as fp:
            config.readfp(fp)
    except Exception as e:
        raise type(e)(
            "Can't read file '{0}': use current path or override using "
            "CONSTANTS_FILE_PATH env variable".format(file_path)
        )
    return config


def parse_date(value):
    date = parse_datetime(value)
    if not date.tzinfo:
        date = TZ.localize(date)
    return date

def parse_bool(value):
    if str(value).lower() in ("yes", "y", "true",  "t", "1"): return True
    if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): return False
    raise ValueError('Invalid value for boolean conversion: ' + str(value))


def get_constant(config, constant, section=DEFAULTSECT, parse_func=parse_date):
    return parse_func(os.environ.get("{}_{}".format(section, constant)) or config.get(section, constant))


CONSTANTS_FILE_PATH = os.environ.get("CONSTANTS_FILE_PATH", get_default_constants_file_path())
CONSTANTS_CONFIG = load_constants(CONSTANTS_FILE_PATH)

BUDGET_PERIOD_FROM = get_constant(CONSTANTS_CONFIG, "BUDGET_PERIOD_FROM")

# Set non required additionalClassification for classification_id 999999-9
NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM = get_constant(
    CONSTANTS_CONFIG, "NOT_REQUIRED_ADDITIONAL_CLASSIFICATION_FROM"
)

# Set INN additionalClassification validation required
CPV_336_INN_FROM = get_constant(CONSTANTS_CONFIG, "CPV_336_INN_FROM")

JOURNAL_PREFIX = os.environ.get("JOURNAL_PREFIX", "JOURNAL_")

# Add scale field to organization
ORGANIZATION_SCALE_FROM = get_constant(CONSTANTS_CONFIG, "ORGANIZATION_SCALE_FROM")

# Set mainProcurementCategory required
MPC_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "MPC_REQUIRED_FROM")

MILESTONES_VALIDATION_FROM = get_constant(CONSTANTS_CONFIG, "MILESTONES_VALIDATION_FROM")

# Plan.buyers required
PLAN_BUYERS_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "PLAN_BUYERS_REQUIRED_FROM")

# negotiation.quick cause required
QUICK_CAUSE_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "QUICK_CAUSE_REQUIRED_FROM")

# Budget breakdown required from
BUDGET_BREAKDOWN_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "BUDGET_BREAKDOWN_REQUIRED_FROM")

# Business date calculation first non working day midnight allowed from
WORKING_DATE_ALLOW_MIDNIGHT_FROM = get_constant(CONSTANTS_CONFIG, "WORKING_DATE_ALLOW_MIDNIGHT_FROM")

NORMALIZED_CLARIFICATIONS_PERIOD_FROM = get_constant(CONSTANTS_CONFIG, "NORMALIZED_CLARIFICATIONS_PERIOD_FROM")

RELEASE_2020_04_19 = get_constant(CONSTANTS_CONFIG, "RELEASE_2020_04_19")

# CS-6687 make required complaint identifier fields for tenders created from
COMPLAINT_IDENTIFIER_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "COMPLAINT_IDENTIFIER_REQUIRED_FROM")

# CS-7231 new negotiation causes released (old partly disabled)
NEW_NEGOTIATION_CAUSES_FROM = get_constant(CONSTANTS_CONFIG, "NEW_NEGOTIATION_CAUSES_FROM")

# CS-8167 tender/lot minimalStep validation
MINIMAL_STEP_VALIDATION_FROM = get_constant(CONSTANTS_CONFIG, "MINIMAL_STEP_VALIDATION_FROM")

# CS-11442 contract/items/additionalClassifications scheme: COO
COUNTRIES_MAP = standards.load("classifiers/countries.json")

# Address validation
COUNTRIES = {c["name_uk"] for c in COUNTRIES_MAP.values()}
UA_REGIONS = standards.load("classifiers/ua_regions.json")
VALIDATE_ADDRESS_FROM = get_constant(CONSTANTS_CONFIG, "VALIDATE_ADDRESS_FROM")

# address and kind fields required for procuringEntity and buyers objects in plan
PLAN_ADDRESS_KIND_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "PLAN_ADDRESS_KIND_REQUIRED_FROM")

NORMALIZED_TENDER_PERIOD_FROM = get_constant(CONSTANTS_CONFIG, "NORMALIZED_TENDER_PERIOD_FROM")
RELEASE_ECRITERIA_ARTICLE_17 = get_constant(CONSTANTS_CONFIG, "RELEASE_ECRITERIA_ARTICLE_17")

# CS-8383 add requirement status and versioning
CRITERION_REQUIREMENT_STATUSES_FROM = get_constant(CONSTANTS_CONFIG, "CRITERION_REQUIREMENT_STATUSES_FROM")

RELEASE_SIMPLE_DEFENSE_FROM = get_constant(CONSTANTS_CONFIG, "RELEASE_SIMPLE_DEFENSE_FROM")

# CS-8981 new complaints in openuadefense
NEW_DEFENSE_COMPLAINTS_FROM = get_constant(CONSTANTS_CONFIG, "NEW_DEFENSE_COMPLAINTS_FROM")
NEW_DEFENSE_COMPLAINTS_TO = get_constant(CONSTANTS_CONFIG, "NEW_DEFENSE_COMPLAINTS_TO")

# CS-8981 award claims restricted in openuadefense
NO_DEFENSE_AWARD_CLAIMS_FROM = get_constant(CONSTANTS_CONFIG, "NO_DEFENSE_AWARD_CLAIMS_FROM")

# CS-8595 two phase commit
TWO_PHASE_COMMIT_FROM = get_constant(CONSTANTS_CONFIG, "TWO_PHASE_COMMIT_FROM")

# CS-9327 guarantee support
RELEASE_GUARANTEE_CRITERION_FROM = get_constant(CONSTANTS_CONFIG, "RELEASE_GUARANTEE_CRITERION_FROM")

# CS-9158 metrics support
RELEASE_METRICS_FROM = get_constant(CONSTANTS_CONFIG, "RELEASE_METRICS_FROM")

# CS-8330 validation for ContactPoint.telephone
VALIDATE_TELEPHONE_FROM = get_constant(CONSTANTS_CONFIG, "VALIDATE_TELEPHONE_FROM")

# CS-10305 validation required fields by submission
REQUIRED_FIELDS_BY_SUBMISSION_FROM = get_constant(CONSTANTS_CONFIG, "REQUIRED_FIELDS_BY_SUBMISSION_FROM")
# CS-9333 unit object required for item
UNIT_PRICE_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "UNIT_PRICE_REQUIRED_FROM")

# CS-10431 validation currency
CURRENCIES = standards.load("codelists/tender/tender_currency.json")
VALIDATE_CURRENCY_FROM = get_constant(CONSTANTS_CONFIG, "VALIDATE_CURRENCY_FROM")

# CS-10207 multi contracts required for multi buyers
MULTI_CONTRACTS_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "MULTI_CONTRACTS_REQUIRED_FROM")

# CS-11202 add new constant for validate code
UNIT_CODE_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "UNIT_CODE_REQUIRED_FROM")

# CS-11411 multi profile available for pq tenders
PQ_MULTI_PROFILE_FROM = get_constant(CONSTANTS_CONFIG, "PQ_MULTI_PROFILE_FROM")

# CS-11856 hash criteria id
PQ_CRITERIA_ID_FROM = get_constant(CONSTANTS_CONFIG, "PQ_CRITERIA_ID_FROM")
PQ_CRITERIA_RESPONSES_ALL_FROM = get_constant(CONSTANTS_CONFIG, "PQ_CRITERIA_RESPONSES_ALL_FROM")

# Decided in CS-8167
MINIMAL_STEP_VALIDATION_PRESCISSION = 2
MINIMAL_STEP_VALIDATION_LOWER_LIMIT = 0.005
MINIMAL_STEP_VALIDATION_UPPER_LIMIT = 0.03


# Masking
MASK_OBJECT_DATA = get_constant(CONSTANTS_CONFIG, "MASK_OBJECT_DATA", parse_func=parse_bool)
MASK_IDENTIFIER_IDS = set(standards.load("organizations/mask_identifiers.json"))
MASK_OBJECT_DATA_SINGLE = get_constant(CONSTANTS_CONFIG, "MASK_OBJECT_DATA_SINGLE", parse_func=parse_bool)

# CS-12463
FRAMEWORK_ENQUIRY_PERIOD_OFF_FROM = get_constant(CONSTANTS_CONFIG, "FRAMEWORK_ENQUIRY_PERIOD_OFF_FROM")

# CS-12553
FAST_CATALOGUE_FLOW_FRAMEWORK_IDS = get_constant(
    CONSTANTS_CONFIG,
    "FAST_CATALOGUE_FLOW_FRAMEWORK_IDS",
    parse_func=parse_str_list,
)

# Tender config optionality
TENDER_CONFIG_OPTIONALITY = {
    "hasAuction": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_HAS_AUCTION_OPTIONAL",
        parse_func=parse_bool,
    ),
    "hasAwardingOrder": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_HAS_AWARDING_ORDER_OPTIONAL",
        parse_func=parse_bool,
    ),
    "hasValueRestriction": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_HAS_VALUE_RESTRICTION_OPTIONAL",
        parse_func=parse_bool,
    ),
    "valueCurrencyEquality": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_VALUE_CURRENCY_EQUALITY",
        parse_func=parse_bool,
    ),
    "hasPrequalification": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_HAS_PREQUALIFICATION_OPTIONAL",
        parse_func=parse_bool,
    ),
    "minBidsNumber": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_MIN_BIDS_NUMBER_OPTIONAL",
        parse_func=parse_bool,
    ),
    "hasPreSelectionAgreement": get_constant(
        CONSTANTS_CONFIG,
        "TENDER_CONFIG_HAS_PRE_SELECTION_AGREEMENT_OPTIONAL",
        parse_func=parse_bool,
    ),
}

# Tender weightedValue pre-calculation on switch to active.auction
TENDER_WEIGHTED_VALUE_PRE_CALCULATION = get_constant(
    CONSTANTS_CONFIG,
    "TENDER_WEIGHTED_VALUE_PRE_CALCULATION",
    parse_func=parse_bool,
)

PQ_NEW_CONTRACTING_FROM = get_constant(CONSTANTS_CONFIG, "PQ_NEW_CONTRACTING_FROM")
ECONTRACT_SIGNER_INFO_REQUIRED = get_constant(
    CONSTANTS_CONFIG,
    "ECONTRACT_SIGNER_INFO_REQUIRED",
    parse_func=parse_bool,
)

# Contract templates

CONTRACT_TEMPLATES_KEYS = set(standards.load("templates/contract_templates_keys.json"))

NEW_CONTRACTING_FROM = get_constant(CONSTANTS_CONFIG, "NEW_CONTRACTING_FROM")

# Related lot is required

RELATED_LOT_REQUIRED_FROM = get_constant(CONSTANTS_CONFIG, "RELATED_LOT_REQUIRED_FROM")
