from openprocurement.tender.core.procedure.models.document import PostDocument, PatchDocument, Document
from openprocurement.tender.core.procedure.validation import (
    validate_input_data,
    validate_patch_data,
    validate_item_owner,
    unless_bots_or_auction,
    update_doc_fields_on_put_document,
    validate_upload_document,
    validate_data_model,
    validate_tender_document_update_not_by_author_or_tender_owner,
)
from openprocurement.tender.pricequotation.procedure.validation import validate_document_operation_in_not_allowed_period
from openprocurement.tender.pricequotation.constants import PQ
from openprocurement.tender.core.procedure.views.tender_document import TenderDocumentResource
from cornice.resource import resource
from openprocurement.api.utils import json_view


@resource(
    name="{}:Tender Documents".format(PQ),
    collection_path="/tenders/{tender_id}/documents",
    path="/tenders/{tender_id}/documents/{document_id}",
    procurementMethodType=PQ,
    description="Tender related binary files (PDFs, etc.)",
)
class PQTenderDocumentResource(TenderDocumentResource):

    @json_view(
        validators=(
            unless_bots_or_auction(validate_item_owner("tender")),
            validate_input_data(PostDocument, allow_bulk=True),
            validate_document_operation_in_not_allowed_period,
        ),
        permission="upload_tender_documents",
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        validators=(
            unless_bots_or_auction(validate_item_owner("tender")),
            validate_input_data(PostDocument),

            validate_document_operation_in_not_allowed_period,
            validate_tender_document_update_not_by_author_or_tender_owner,

            update_doc_fields_on_put_document,
            validate_upload_document,
            validate_data_model(Document),
        ),
        permission="upload_tender_documents",
    )
    def put(self):
        return super().put()

    @json_view(
        content_type="application/json",
        validators=(
            unless_bots_or_auction(validate_item_owner("tender")),
            validate_input_data(PatchDocument, none_means_remove=True),
            validate_patch_data(Document, item_name="document"),

            validate_document_operation_in_not_allowed_period,
            validate_tender_document_update_not_by_author_or_tender_owner,
        ),
        permission="upload_tender_documents",
    )
    def patch(self):
        return super().patch()
