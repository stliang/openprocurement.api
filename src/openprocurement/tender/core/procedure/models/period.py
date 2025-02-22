from openprocurement.api.context import get_now
from openprocurement.api.models import IsoDateTimeType, Model
from schematics.validate import ValidationError


class Period(Model):
    startDate = IsoDateTimeType()  # The state date for the period.
    endDate = IsoDateTimeType()  # The end date for the period.

    def validate_startDate(self, data, value):
        if value and data.get("endDate") and data.get("endDate") < value:
            raise ValidationError("period should begin before its end")


class QualificationPeriod(Period):
    reportingDatePublication = IsoDateTimeType()


class PeriodEndRequired(Period):
    endDate = IsoDateTimeType(required=True)


class PostPeriodStartEndRequired(Period):
    startDate = IsoDateTimeType(required=True, default=get_now)  # The state date for the period.
    endDate = IsoDateTimeType(required=True, default=get_now)  # The end date for the period.


class PeriodStartEndRequired(Period):
    startDate = IsoDateTimeType(required=True)  # The state date for the period.
    endDate = IsoDateTimeType(required=True)  # The end date for the period.


class StartedPeriodEndRequired(PeriodEndRequired):
    startDate = IsoDateTimeType(default=lambda: get_now().isoformat())


class EnquiryPeriod(Period):
    clarificationsUntil = IsoDateTimeType()
    invalidationDate = IsoDateTimeType()


class EnquiryPeriodEndRequired(EnquiryPeriod):
    endDate = IsoDateTimeType(required=True)


class StartedEnquiryPeriodEndRequired(EnquiryPeriodEndRequired):
    startDate = IsoDateTimeType(default=lambda: get_now().isoformat())


class LotAuctionPeriod(Period):
    shouldStartAfter = IsoDateTimeType()


class TenderAuctionPeriod(Period):
    shouldStartAfter = IsoDateTimeType()
