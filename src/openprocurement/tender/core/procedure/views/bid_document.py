from cornice.resource import resource
from pyramid.security import Allow, Everyone, ALL_PERMISSIONS
from openprocurement.api.utils import json_view
from openprocurement.tender.core.procedure.views.bid import resolve_bid
from openprocurement.tender.core.procedure.views.document import BaseDocumentResource, resolve_document
from openprocurement.tender.core.procedure.serializers.document import ConfidentialDocumentSerializer
from openprocurement.tender.core.procedure.models.bid_document import (
    PostDocument,
    PatchDocument,
    Document,
)
from openprocurement.tender.core.procedure.validation import (
    validate_input_data,
    validate_patch_data,
    validate_item_owner,
    validate_bid_document_operation_period,
    unless_allowed_by_qualification_milestone,
    validate_upload_document,
    update_doc_fields_on_put_document,
    validate_data_model,
    validate_bid_document_operation_in_award_status,
    validate_bid_document_in_tender_status,
    validate_download_bid_document,
    validate_update_bid_document_confidentiality,
    validate_bid_financial_document_in_tender_status,
    validate_view_bid_document,
    validate_bid_document_operation_in_bid_status,
    validate_view_bid_documents_allowed_in_bid_status,
    validate_view_financial_bid_documents_allowed_in_tender_status,
    validate_view_financial_bid_documents_allowed_in_bid_status,
)


def validate_post_create_model(**kwargs):
    def validator(request, **_):
        validate_input_data(request.root.create_model_class, **kwargs)(request)

    return validator


def validate_patch_update_model(**kwargs):
    def validator(request, **_):
        validate_input_data(request.root.update_model_class, **kwargs)(request)

    return validator


def validate_patch_model(**kwargs):
    def validator(request, **_):
        validate_patch_data(request.root.model_class, **kwargs)(request)

    return validator


def validate_put_update_model(**kwargs):
    def validator(request, **_):
        validate_input_data(request.root.create_model_class, **kwargs)(request)

    return validator


def validate_put_model(**kwargs):
    def validator(request, **_):
        validate_data_model(request.root.model_class)(request)

    return validator


class BaseTenderBidDocumentResource(BaseDocumentResource):
    item_name = "bid"
    model_class = Document
    create_model_class = PostDocument
    update_model_class = PatchDocument
    serializer_class = ConfidentialDocumentSerializer

    def __acl__(self):
        acl = [
            (Allow, Everyone, "view_tender"),
            (Allow, "g:brokers", "create_bid"),
            (Allow, "g:brokers", "edit_bid"),
            (Allow, "g:Administrator", "edit_bid"),  # wtf ???
            (Allow, "g:admins", ALL_PERMISSIONS),  # some tests use this, idk why
        ]
        return acl

    def get_modified(self):
        return self.request.validated["tender"]["status"] != "active.tendering"

    def __init__(self, request, context=None):
        super().__init__(request, context)
        if context and request.matchdict:
            resolve_bid(request)
            resolve_document(request, self.item_name, self.container)

    @json_view(
        validators=(
            validate_view_bid_document,
            validate_view_bid_documents_allowed_in_bid_status,
            validate_download_bid_document,
        ),
        permission="view_tender",
    )
    def get(self):
        return super().get()

    @json_view(
        validators=(
            validate_view_bid_document,
            validate_view_bid_documents_allowed_in_bid_status,
        ),
        permission="view_tender",
    )
    def collection_get(self):
        return super().collection_get()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_post_create_model(allow_bulk=True),
            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
        ),
        permission="edit_bid",
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_put_update_model(),
            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
            validate_update_bid_document_confidentiality,
            update_doc_fields_on_put_document,
            validate_upload_document,
            validate_put_model(),
        ),
        permission="edit_bid",
    )
    def put(self):
        return super().put()

    @json_view(
        content_type="application/json",
        validators=(
            validate_item_owner("bid"),
            validate_patch_update_model(none_means_remove=True),
            validate_patch_model(item_name="document"),
            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
            validate_update_bid_document_confidentiality,
        ),
        permission="edit_bid",
    )
    def patch(self):
        return super().patch()


@resource(
    name="belowThreshold:Tender Bid Eligibility Documents",
    collection_path="/tenders/{tender_id}/bids/{bid_id}/eligibility_documents",
    path="/tenders/{tender_id}/bids/{bid_id}/eligibility_documents/{document_id}",
    procurementMethodType="belowThreshold",
    description="Tender bidder eligibility documents",
)
class BaseTenderBidEligibilityDocumentResource(BaseTenderBidDocumentResource):
    """ Tender Bid Eligibility Documents """

    container = "eligibilityDocuments"


@resource(
    name="belowThreshold:Tender Bid Financial Documents",
    collection_path="/tenders/{tender_id}/bids/{bid_id}/financial_documents",
    path="/tenders/{tender_id}/bids/{bid_id}/financial_documents/{document_id}",
    procurementMethodType="belowThreshold",
    description="Tender bidder financial documents",
)
class BaseTenderBidFinancialDocumentResource(BaseTenderBidDocumentResource):
    """ Tender Bid Financial Documents """

    container = "financialDocuments"

    @json_view(
        validators=(
            validate_view_financial_bid_documents_allowed_in_tender_status,
            validate_view_financial_bid_documents_allowed_in_bid_status,
        ),
        permission="view_tender",
    )
    def collection_get(self):
        return super(BaseTenderBidFinancialDocumentResource, self).collection_get()

    @json_view(
        validators=(
            validate_view_financial_bid_documents_allowed_in_tender_status,
            validate_view_financial_bid_documents_allowed_in_bid_status,
            validate_download_bid_document,
        ),
        permission="view_tender",
    )
    def get(self):
        return super(BaseTenderBidFinancialDocumentResource, self).get()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_input_data(PostDocument, allow_bulk=True),

            unless_allowed_by_qualification_milestone(
                validate_bid_financial_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
        ),
        permission="edit_bid",
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_input_data(PostDocument),

            unless_allowed_by_qualification_milestone(
                validate_bid_financial_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
            validate_update_bid_document_confidentiality,

            update_doc_fields_on_put_document,
            validate_upload_document,

            validate_data_model(Document),
        ),
        permission="edit_bid",
    )
    def put(self):
        return super().put()

    @json_view(
        content_type="application/json",
        validators=(
            validate_item_owner("bid"),
            validate_input_data(PatchDocument, none_means_remove=True),
            validate_patch_data(Document, item_name="document"),
            unless_allowed_by_qualification_milestone(
                validate_bid_financial_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_bid_document_operation_in_bid_status,
            validate_update_bid_document_confidentiality,
        ),
        permission="edit_bid",
    )
    def patch(self):
        return super().patch()


@resource(
    name="belowThreshold:Tender Bid Qualification Documents",
    collection_path="/tenders/{tender_id}/bids/{bid_id}/qualification_documents",
    path="/tenders/{tender_id}/bids/{bid_id}/qualification_documents/{document_id}",
    procurementMethodType="belowThreshold",
    description="Tender bidder qualification documents",
)
class BaseTenderBidQualificationDocumentResource(BaseTenderBidDocumentResource):
    """ Tender Bid Qualification Documents """

    container = "qualificationDocuments"

    @json_view(
        validators=(
            validate_view_financial_bid_documents_allowed_in_tender_status,
            validate_view_financial_bid_documents_allowed_in_bid_status,
        ),
        permission="view_tender",
    )
    def collection_get(self):
        return super(BaseTenderBidQualificationDocumentResource, self).collection_get()

    @json_view(
        validators=(
            validate_view_financial_bid_documents_allowed_in_tender_status,
            validate_view_financial_bid_documents_allowed_in_bid_status,
            validate_download_bid_document,
        ),
        permission="view_tender",
    )
    def get(self):
        return super(BaseTenderBidQualificationDocumentResource, self).get()
