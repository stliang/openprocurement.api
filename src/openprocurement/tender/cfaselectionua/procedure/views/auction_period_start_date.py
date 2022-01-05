from openprocurement.tender.core.procedure.views.auction_period_start_date import TenderAuctionPeriodResource
from cornice.resource import resource


@resource(
    name="closeFrameworkAgreementSelectionUA:Tender Auction Period Start Date",
    collection_path="/tenders/{tender_id}/auctionPeriod",
    path="/tenders/{tender_id}/lots/{lot_id}/auctionPeriod",
    procurementMethodType="closeFrameworkAgreementSelectionUA",
    description="Tender auctionPeriod start date",
)
class TenderAuctionPeriodResource(TenderAuctionPeriodResource):
    pass
