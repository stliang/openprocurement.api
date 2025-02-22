from openprocurement.tender.core.procedure.state.award import AwardStateMixing
from openprocurement.tender.core.procedure.context import get_request, get_tender, get_tender_config
from openprocurement.api.context import get_now
from openprocurement.tender.openua.constants import STAND_STILL_TIME
from openprocurement.tender.openua.procedure.state.tender import OpenUATenderState
from openprocurement.tender.core.procedure.contracting import update_econtracts_statuses
from openprocurement.api.utils import raise_operation_error



class AwardState(AwardStateMixing, OpenUATenderState):
    award_stand_still_time = STAND_STILL_TIME  # move to tender state class?

    def award_status_up(self, before, after, award):
        assert before != after, "Statuses must be different"
        tender = get_tender()
        config = get_tender_config()
        awarding_order_enabled = config.get("hasAwardingOrder")
        now = get_now().isoformat()

        if before == "pending" and after == "active":
            self.award_status_up_from_pending_to_active(award, tender, awarding_order_enabled)

        elif before == "pending" and after == "unsuccessful":
            self.award_status_up_from_pending_to_unsuccessful(award, tender)

        elif before == "active" and after == "cancelled":
            if any(i.get("status") == "satisfied" for i in award.get("complaints", "")):
                for i in tender.get("awards", ""):
                    if i.get("lotID") == award.get("lotID"):
                        period = i.get("complaintPeriod")
                        if period:
                            if not period.get("endDate") or period["endDate"] > now:
                                period["endDate"] = now
                        self.set_object_status(i, "cancelled")
                        contracts_ids = self.set_award_contracts_cancelled(i)
                        update_econtracts_statuses(contracts_ids, after)
                self.add_next_award()

            else:
                if award["complaintPeriod"]["endDate"] > now:
                    award["complaintPeriod"]["endDate"] = now
                contracts_ids = self.set_award_contracts_cancelled(award)
                self.add_next_award()
                update_econtracts_statuses(contracts_ids, after)

        elif (
            before == "unsuccessful" and after == "cancelled"
            and any(i["status"] == "satisfied"
                    for i in award.get("complaints", ""))
        ):
            if tender["status"] == "active.awarded":
                self.set_object_status(tender, "active.qualification")
                if "endDate" in tender["awardPeriod"]:
                    del tender["awardPeriod"]["endDate"]

            if award["complaintPeriod"]["endDate"] > now:
                award["complaintPeriod"]["endDate"] = now

            for i in tender.get("awards"):
                if i.get("lotID") == award.get("lotID"):
                    period = i.get("complaintPeriod")
                    if period:
                        if not period.get("endDate") or period["endDate"] > now:
                            period["endDate"] = now
                    self.set_object_status(i, "cancelled")
                    self.set_award_contracts_cancelled(i)
            self.add_next_award()

        else:  # any other state transitions are forbidden
            raise_operation_error(get_request(),
                                  f"Can't update award in current ({before}) status")
        # date updated when status updated
        award["date"] = get_now().isoformat()

