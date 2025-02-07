from schematics.types import StringType, BooleanType
from schematics.types.compound import ModelType
from openprocurement.tender.core.procedure.models.guarantee import WeightedValue
from openprocurement.tender.core.procedure.models.req_response import PostBidResponsesMixin, PatchObjResponsesMixin
from openprocurement.tender.core.procedure.models.bid import (
    Bid as BaseBid,
    PostBid as BasePostBid,
    PatchBid as BasePatchBid,
)
from openprocurement.tender.core.procedure.models.base import ListType
from openprocurement.tender.cfaua.procedure.models.lot_value import LotValue, PostLotValue, PatchLotValue


class PatchBid(PatchObjResponsesMixin, BasePatchBid):
    subcontractingDetails = StringType()
    lotValues = ListType(ModelType(PatchLotValue, required=True))
    selfQualified = BooleanType(choices=[True])  # selfQualified, selfEligible are the same as in the parent but
    selfEligible = BooleanType(choices=[True])   # tests fail because they in different order


class PostBid(PostBidResponsesMixin, BasePostBid):
    subcontractingDetails = StringType()
    lotValues = ListType(ModelType(PostLotValue, required=True))
    selfQualified = BooleanType(required=True, choices=[True])
    selfEligible = BooleanType(choices=[True])


class Bid(PostBidResponsesMixin, BaseBid):
    subcontractingDetails = StringType()
    lotValues = ListType(ModelType(LotValue, required=True))
    weightedValue = ModelType(WeightedValue)
    selfQualified = BooleanType(required=True, choices=[True])
