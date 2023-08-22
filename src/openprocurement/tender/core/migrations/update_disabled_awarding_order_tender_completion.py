from datetime import datetime

from gevent import monkey

from openprocurement.api.utils import get_now
from openprocurement.tender.core.procedure.utils import contracts_allow_to_complete

if __name__ == "__main__":
    monkey.patch_all(thread=False, select=False)

import os
import argparse
import logging

from pyramid.paster import bootstrap

from openprocurement.api.constants import BASE_DIR

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# date of 2.6.202 release
DATE = datetime(year=2023, month=6, day=6)
BLOCK_COMPLAINT_STATUS = ("answered", "pending")


def tender_switch_status(tender):
    statuses = set([lot.get("status") for lot in tender.get("lots", [])])
    if statuses == {"cancelled"}:
        tender["status"] = "cancelled"
    elif not statuses - {"unsuccessful", "cancelled"}:
        tender["status"] = "unsuccessful"
    if not statuses - {"complete", "unsuccessful", "cancelled"}:
        tender["status"] = "complete"


def tender_has_complaints(tender):
    for complaint in tender.get("complaints", []):
        if (
            complaint.get("status", "") in BLOCK_COMPLAINT_STATUS and
            complaint.get("relatedLot") is None
        ):
            return True
    return False


def check_award_lot_complaints(tender: dict, lot_id: str, lot_awards: list) -> bool:
    pending_complaints = False
    for complaint in tender.get("complaints", []):
        if complaint["status"] in BLOCK_COMPLAINT_STATUS and complaint.get("relatedLot") == lot_id:
            pending_complaints = True
            break

    pending_awards_complaints = False
    for award in lot_awards:
        for complaint in award.get("complaints", []):
            if complaint.get("status") in BLOCK_COMPLAINT_STATUS:
                pending_awards_complaints = True
                break
    if pending_complaints or pending_awards_complaints:
        return False
    return True


def run(env, args):
    migration_name = os.path.basename(__file__).split(".")[0]

    logger.info("Starting migration: %s", migration_name)

    collection = env["registry"].mongodb.tenders.collection

    logger.info("Updating completed tenders with disabled hasAwardingOrder")

    log_every = 100000
    count = 0

    cursor = collection.find(
        {
            "public_modified": {"$gte": DATE.timestamp()},
            "is_public": True,
            "config.hasAwardingOrder": False,
            "status": "active.awarded",
            "lots": {"$exists": True},
            "contracts.status": "active",
        },
        {"lots": 1, "contracts": 1, "awards": 1, "status": 1, "agreements": 1, "complaints": 1},
        no_cursor_timeout=True,
    )
    cursor.batch_size(args.b)
    try:
        for tender in cursor:
            if tender_has_complaints(tender):
                continue
            lots = tender.get("lots", [])
            updated = False
            for lot in lots:
                if lot.get("status") == "active":
                    lot_awards = []
                    for a in tender.get("awards", []):
                        if a.get("lotID") == lot.get("id"):
                            lot_awards.append(a)
                    if not lot_awards:
                        continue
                    awards_statuses = {award["status"] for award in lot_awards}
                    if not check_award_lot_complaints(tender, lot["id"], lot_awards):
                        continue
                    elif not awards_statuses.intersection({"active", "pending"}):
                        continue
                    if awards_statuses.intersection({"active"}):
                        if "agreements" in tender:
                            allow_complete_lot = any([a["status"] == "active" for a in tender.get("agreements", [])])
                        else:
                            active_award_ids = {award["id"] for award in lot_awards if award["status"] == "active"}
                            contracts = [
                                contract for contract in tender.get("contracts", [])
                                if contract.get("awardID") in active_award_ids
                            ]
                            allow_complete_lot = contracts_allow_to_complete(contracts)
                        if allow_complete_lot:
                            lot["status"] = "complete"
                            tender_switch_status(tender)
                            updated = True
            if updated:
                collection.find_one_and_update(
                    {"_id": tender["_id"]},
                    [
                        {
                            "$set": {
                                "lots": lots,
                                "status": tender["status"],
                                "date": get_now().isoformat(),
                                "public_modified": {"$divide": [{"$toLong": "$$NOW"}, 1000]},
                            }
                        }
                    ]
                )
                count += 1
                if count % log_every == 0:
                    logger.info(f"Updating completed tenders with disabled hasAwardingOrder: updated {count} tenders")
    finally:
        cursor.close()

    logger.info(f"Updating completed tenders with disabled hasAwardingOrder finished: updated {count} tenders")

    logger.info(f"Successful migration: {migration_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        default=os.path.join(BASE_DIR, "etc/service.ini"),
        help="Path to service.ini file",
    )
    parser.add_argument(
        "-b",
        type=int,
        default=1000,
        help=(
            "Limits the number of documents returned in one batch. Each batch "
            "requires a round trip to the server."
        )
    )
    args = parser.parse_args()
    with bootstrap(args.p) as env:
        run(env, args)
