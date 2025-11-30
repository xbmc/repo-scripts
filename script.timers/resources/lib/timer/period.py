from datetime import datetime, timedelta

from resources.lib.utils import datetime_utils


class Period:

    def __init__(self, start: 'timedelta | datetime', end: 'timedelta | datetime') -> None:

        if type(start) != type(end):
            raise Exception(
                "types of <start> and <end> must be identically!!!")

        self.start: 'timedelta | datetime' = start
        self.end: 'timedelta | datetime' = end

    def _compareByWeekdays(self, period_start: timedelta, period_end: timedelta) -> 'tuple[timedelta,timedelta,timedelta]':

        self_start = self.start
        self_end = self.end
        week = timedelta(days=7)

        if self_start > self_end and period_start <= period_end:
            self_end += week
            if period_end < self_start:
                period_start += week
                period_end += week

        elif self_start <= self_end and period_start > period_end:
            period_end += week
            if self_end < period_start:
                self_start += week
                self_end += week

        max_start = max(self_start, period_start)
        min_end = min(self_end, period_end)

        return self_start - period_start, self_end - period_end, min_end - max_start if max_start <= min_end else None

    def _compareByDates(self, period_start: datetime, period_end: datetime) -> 'tuple[timedelta,timedelta,timedelta]':

        max_start = max(self.start, period_start)
        min_end = min(self.end, period_end)

        return self.start - period_start, self.end - period_end, min_end - max_start if max_start <= min_end else None

    def compare(self, period: 'Period') -> 'tuple[timedelta,timedelta,timedelta]':

        if type(self.start) != type(period.start):
            raise Exception(
                f"can't compare {str(self)} with {str(period)} caused by different types")

        if type(self.start) == timedelta:
            return self._compareByWeekdays(period.start, period.end)
        else:
            return self._compareByDates(period.start, period.end)

    def hit(self, timestamp: 'timedelta | datetime', base: datetime = None) -> 'tuple[timedelta,timedelta,bool]':

        if type(self.start) == timedelta and type(timestamp) == timedelta:
            s, e, l = self._compareByWeekdays(timestamp, timestamp)
            return s, e, l is not None
        elif type(self.start) == datetime and type(timestamp) == datetime:
            s, e, l = self._compareByDates(timestamp, timestamp)
            return s, e, l is not None

        if type(timestamp) == datetime:
            period = Period.to_datetime_period(
                period=self, base=base or timestamp)
            s, e, l = period._compareByDates(timestamp, timestamp)
            return s, e, l is not None

        elif type(self.start) == datetime:
            if not base:
                raise ("This type of comparision requires a base-datetime")

            timestamp = datetime_utils.apply_for_datetime(
                base, timestamp, force_future=True)
            s, e, l = self._compareByDates(timestamp, timestamp)
            return s, e, l is not None

    def __str__(self) -> str:

        start = self.start if type(
            self.start) == timedelta else self.start.strftime("%Y-%m-%d %H:%M:%S")
        end = self.end if type(self.end) == timedelta else self.end.strftime(
            "%Y-%m-%d %H:%M:%S")
        return f"Period[start={start}, end={end}]"

    @staticmethod
    def to_datetime_period(period: 'Period', base: datetime) -> 'Period':

        if type(period.start) == datetime:
            return period

        start = datetime_utils.apply_for_datetime(base, period.start)
        end = datetime_utils.apply_for_datetime(base, period.end)
        if start < end < base:
            start += timedelta(days=7)
            end += timedelta(days=7)

        return Period(start, end)
