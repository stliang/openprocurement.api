from schematics.types import StringType
from schematics.types.serializable import serializable
from uuid import uuid4

from openprocurement.api.models import get_now, IsoDateTimeType, Model


class PostTransfer(Model):
    @serializable(serialized_name="_id")
    def id(self):
        return uuid4().hex

    @serializable
    def date(self):
        return get_now().isoformat()


class PatchTransfer(Model):
    pass


class Transfer(Model):
    owner = StringType(min_length=1)
    access_token = StringType(min_length=1, required=True)
    transfer_token = StringType(min_length=1, required=True)
    date = IsoDateTimeType(required=True)
    usedFor = StringType(min_length=32)  # object path (e.g. /tenders/{id})
