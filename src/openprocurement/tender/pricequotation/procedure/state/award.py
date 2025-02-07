from openprocurement.tender.core.procedure.state.award import AwardStateMixing
from openprocurement.tender.core.procedure.context import get_request
from openprocurement.api.context import get_now
from openprocurement.tender.core.procedure.contracting import (
    add_contracts,
    save_contracts_to_contracting,
    update_econtracts_statuses,
)
from openprocurement.tender.pricequotation.procedure.state.tender import PriceQuotationTenderState
from openprocurement.api.utils import raise_operation_error, get_contract_by_id


class AwardState(AwardStateMixing, PriceQuotationTenderState):

    def award_on_patch(self, before, award):
        if before["status"] != award["status"]:
            self.award_status_up(before["status"], award["status"], award)
        elif award["status"] == "pending":
            pass  # allowing to update award in pending status
        else:
            raise_operation_error(
                get_request(),
                f"Can't update award in current ({before['status']}) status"
            )

    def award_status_up(self, before, after, award):
        assert before != after, "Statuses must be different"

        if before == "pending" and after == "active":
            contracts = add_contracts(get_request(), award)
            self.add_next_award()
            save_contracts_to_contracting(contracts, award)

        elif before == "pending" and after == "unsuccessful":
            self.add_next_award()

        elif before == "active" and after == "cancelled":
            cancelled_contracts_ids = self.set_award_contracts_cancelled(award)
            update_econtracts_statuses(cancelled_contracts_ids, after)
            self.add_next_award()
        else:  # any other state transitions are forbidden
            raise_operation_error(
                get_request(),
                f"Can't update award in current ({before}) status"
            )
        # date updated when status updated
        award["date"] = get_now().isoformat()
