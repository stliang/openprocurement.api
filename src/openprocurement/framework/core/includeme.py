from openprocurement.api.database import COLLECTION_CLASSES
from openprocurement.framework.core.database import (
    FrameworkCollection,
    AgreementCollection,
    SubmissionCollection,
    QualificationCollection,
)
from logging import getLogger
from pkg_resources import iter_entry_points

from openprocurement.framework.core.procedure.utils import (
    extract_framework_doc,
    extract_submission_doc,
    extract_qualification_doc,
    extract_agreement_doc,
)
from openprocurement.framework.core.utils import (
    extract_doc,
    register_framework_frameworkType,
    register_submission_submissionType,
    register_qualification_qualificationType,
    FrameworkTypePredicate,
    SubmissionTypePredicate,
    QualificationTypePredicate,
    framework_from_data,
    submission_from_data,
    qualification_from_data,
    AgreementTypePredicate,
    agreement_from_data,
    register_agreement_agreementType,
)

LOGGER = getLogger("openprocurement.framework.core")


def includeme(config):
    LOGGER.info("Init framework.core plugin")

    COLLECTION_CLASSES["frameworks"] = FrameworkCollection
    COLLECTION_CLASSES["agreements"] = AgreementCollection
    COLLECTION_CLASSES["submissions"] = SubmissionCollection
    COLLECTION_CLASSES["qualifications"] = QualificationCollection

    config.add_request_method(extract_doc, "framework", reify=True)
    config.add_request_method(extract_doc, "submission", reify=True)
    config.add_request_method(extract_doc, "qualification", reify=True)
    config.add_request_method(extract_doc, "agreement", reify=True)
    config.add_request_method(extract_framework_doc, "framework_doc", reify=True)
    config.add_request_method(extract_submission_doc, "submission_doc", reify=True)
    config.add_request_method(extract_qualification_doc, "qualification_doc", reify=True)
    config.add_request_method(extract_agreement_doc, "agreement_doc", reify=True)

    # framework frameworkType plugins support
    config.registry.framework_frameworkTypes = {}
    config.registry.submission_submissionTypes = {}
    config.registry.qualification_qualificationTypes = {}
    config.registry.agreement_agreementTypes = {}
    config.add_route_predicate("frameworkType", FrameworkTypePredicate)
    config.add_route_predicate("submissionType", SubmissionTypePredicate)
    config.add_route_predicate("qualificationType", QualificationTypePredicate)
    config.add_route_predicate("agreementType", AgreementTypePredicate)
    config.add_request_method(framework_from_data)
    config.add_request_method(submission_from_data)
    config.add_request_method(qualification_from_data)
    config.add_request_method(agreement_from_data)
    config.add_directive("add_framework_frameworkTypes", register_framework_frameworkType)
    config.add_directive("add_submission_submissionTypes", register_submission_submissionType)
    config.add_directive("add_qualification_qualificationTypes", register_qualification_qualificationType)
    config.add_directive("add_agreement_agreementTypes", register_agreement_agreementType)
    # config.scan("openprocurement.framework.core.views")
    config.scan("openprocurement.framework.core.procedure.views")

    # search for plugins
    settings = config.get_settings()
    plugins = settings.get("plugins") and [plugin.strip() for plugin in settings["plugins"].split(",")]
    for entry_point in iter_entry_points("openprocurement.framework.core.plugins"):
        if not plugins or entry_point.name in plugins:
            plugin = entry_point.load()
            plugin(config)
