# -*- coding: utf-8 -*-
from cornice.resource import resource

from openprocurement.api.utils import json_view
from openprocurement.framework.core.procedure.models.milestone import PatchMilestone, PostMilestone, Milestone
from openprocurement.framework.core.procedure.validation import (
    validate_agreement_operation_not_in_allowed_status,
    validate_contract_operation_not_in_allowed_status,
    validate_contract_suspended,
    validate_milestone_type,
    validate_patch_not_activation_milestone,
    validate_action_in_milestone_status,
    validate_patch_milestone_status,
)
from openprocurement.framework.core.procedure.views.milestone import AgreementContractMilestonesResource
from openprocurement.framework.electroniccatalogue.constants import ELECTRONIC_CATALOGUE_TYPE
from openprocurement.tender.core.procedure.validation import (
    validate_input_data,
    validate_patch_data,
    validate_data_documents,
    validate_item_owner,
)


@resource(
    name=f"{ELECTRONIC_CATALOGUE_TYPE}:Agreements Contracts Milestones",
    collection_path="/agreements/{agreement_id}/contracts/{contract_id}/milestones",
    path="/agreements/{agreement_id}/contracts/{contract_id}/milestones/{milestone_id}",
    description="Agreements Contracts Milestones",
    agreementType=ELECTRONIC_CATALOGUE_TYPE,
    accept="application/json",
)
class ElectronicCatalogueAgreementContractMilestoneResource(AgreementContractMilestonesResource):
    @json_view(
        content_type="application/json",
        permission="edit_agreement",
        validators=(
            validate_item_owner("framework"),
            validate_input_data(PostMilestone),
            validate_agreement_operation_not_in_allowed_status,
            validate_contract_operation_not_in_allowed_status,
            validate_contract_suspended,
            validate_milestone_type,
            validate_data_documents(route_key="milestone_id", uid_key="id"),
        ),
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        content_type="application/json",
        validators=(
            validate_item_owner("framework"),
            validate_input_data(PatchMilestone),
            validate_patch_data(Milestone, item_name="milestone"),
            validate_agreement_operation_not_in_allowed_status,
            validate_contract_operation_not_in_allowed_status,
            validate_contract_suspended,
            validate_patch_not_activation_milestone,
            validate_action_in_milestone_status,
            validate_patch_milestone_status,
        ),
        permission="edit_agreement",
    )
    def patch(self):
        return super().patch()
