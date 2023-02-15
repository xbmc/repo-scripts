from datetime import timedelta


class Period:

    def __init__(self, start: timedelta, end: timedelta) -> None:

        self.start: timedelta = start
        self.end: timedelta = end

    def _compare(self, period_start: timedelta, period_end: timedelta) -> 'tuple[timedelta,timedelta,timedelta]':

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

    def compare(self, period: 'Period') -> 'tuple[timedelta,timedelta,timedelta]':

        return self._compare(period.start, period.end)

    def hit(self, timestamp: timedelta) -> 'tuple[timedelta,timedelta, bool]':

        s, e, l = self._compare(timestamp, timestamp)
        return s, e, l is not None

    def __str__(self) -> str:
        return "Period[start=%s, end=%s]" % (self.start, self.end)
