from cornice.resource import resource

from openprocurement.api.utils import json_view
from openprocurement.framework.core.procedure.models.document import PostDocument, PatchDocument, Document
from openprocurement.framework.core.procedure.validation import (
    validate_framework_document_operation_not_in_allowed_status,
)
from openprocurement.framework.core.procedure.views.document import CoreFrameworkDocumentResource
from openprocurement.framework.dps.constants import DPS_TYPE
from openprocurement.tender.core.procedure.validation import (
    validate_item_owner,
    validate_input_data,
    validate_patch_data_simple,
    validate_data_model,
    validate_upload_document,
    update_doc_fields_on_put_document,
)


@resource(
    name=f"{DPS_TYPE}:Framework Documents",
    collection_path="/frameworks/{framework_id}/documents",
    path="/frameworks/{framework_id}/documents/{document_id}",
    frameworkType=DPS_TYPE,
    description="Framework related binary files (PDFs, etc.)",
)
class FrameworkDocumentResource(CoreFrameworkDocumentResource):
    @json_view(permission="view_framework")
    def collection_get(self):
        return super().collection_get()

    @json_view(permission="view_framework")
    def get(self):
        return super().get()

    @json_view(
        validators=(
                validate_item_owner("framework"),
                validate_input_data(PostDocument, allow_bulk=True),
                validate_framework_document_operation_not_in_allowed_status,
        ),
        permission="edit_framework",
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        validators=(
                validate_item_owner("framework"),
                validate_input_data(PostDocument),
                update_doc_fields_on_put_document,
                validate_upload_document,
                validate_data_model(Document),
                validate_framework_document_operation_not_in_allowed_status,
        ),
        permission="edit_framework",
    )
    def put(self):
        return super().put()

    @json_view(
        content_type="application/json",
        validators=(
                validate_item_owner("framework"),
                validate_input_data(PatchDocument, none_means_remove=True),
                validate_patch_data_simple(Document, item_name="document"),
                validate_framework_document_operation_not_in_allowed_status,
        ),
        permission="edit_framework",
    )
    def patch(self):
        return super().patch()
