from openprocurement.api.context import get_request
from openprocurement.framework.core.procedure.models.framework import FrameworkChronographData
from openprocurement.framework.core.procedure.state.framework import FrameworkState
from openprocurement.framework.dps.procedure.state.qualification import DPSQualificationState
from openprocurement.framework.dps.procedure.state.submission import DPSSubmissionState
from openprocurement.framework.dps.procedure.models.framework import (
    PatchActiveFramework,
    PatchFramework,
)


class DPSFrameworkState(FrameworkState):
    qualification_class = DPSQualificationState
    submission_class = DPSSubmissionState

    def get_patch_data_model(self):
        request = get_request()
        validated_framework = request.validated["framework"]
        status = validated_framework["status"]
        request_data = request.json["data"]
        new_status = request_data.get("status") or status

        if request.authenticated_role == "chronograph":
            return FrameworkChronographData
        elif new_status == "active":
            return PatchActiveFramework
        return PatchFramework
