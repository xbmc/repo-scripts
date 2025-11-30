import locale
import re
import time
from datetime import datetime, timedelta

import xbmc
import xbmcaddon

DEFAULT_TIME = "00:00"

WEEKLY = 7
TIMER_BY_DATE = 8


class DateTimeDelta():

    def __init__(self, dt: datetime) -> None:

        self.dt = dt
        self.td = timedelta(hours=dt.hour, minutes=dt.minute,
                            seconds=dt.second, days=dt.weekday())

    @staticmethod
    def now(offset=0) -> 'DateTimeDelta':

        dt_now = datetime.today()

        if offset:
            if offset > 0:
                dt_now += timedelta(seconds=offset)
            else:
                dt_now -= timedelta(seconds=abs(offset))

        return DateTimeDelta(dt_now)


def _parse_datetime_from_str(s: str, format: str) -> datetime:

    try:
        return datetime.strptime(s, format)
    except:
        # Workaround for some Kodi versions
        return datetime.fromtimestamp(time.mktime(time.strptime(s, format)))


def parse_date_str(s: str) -> datetime:

    return _parse_datetime_from_str(s, "%Y-%m-%d")


def to_date_str(dt: datetime) -> datetime:

    return dt.strftime("%Y-%m-%d")


def parse_datetime_str(s: str) -> datetime:

    return _parse_datetime_from_str(s, "%Y-%m-%d %H:%M")


def parse_xbmc_shortdate(s: str) -> datetime:

    return _parse_datetime_from_str(s, format=xbmc.getRegion("dateshort").replace("%-", "%"))


def parse_date_from_xbmcdialog(s: str) -> datetime:

    return _parse_datetime_from_str(s.replace(" ", ""), format="%d/%m/%Y")


def convert_for_xbmcdialog(s: str) -> str:

    _dt = parse_date_str(s)
    return f"{_dt.day:2}/{_dt.month:2}/{_dt.year}"


def periods_to_human_readable(days: 'list[int]', start: str, end="", date="") -> str:

    addon = xbmcaddon.Addon()

    try:
        locale.setlocale(
            locale.LC_ALL, xbmc.getLanguage(format=xbmc.ISO_639_1))
    except:
        pass

    def _day_str(d: int, plural=False) -> str:

        return addon.getLocalizedString(d + (32210 if plural else 32200))

    def _sumarize(days: 'list[int]') -> 'list[list[int]]':

        if not days:
            return list()

        other_days = list()
        start = days[0]
        end = start
        for i in range(1, len(days)):
            day = days[i]
            if day == WEEKLY:
                continue

            elif day == end + 1:
                end = day

            else:
                other_days.append(day)

        period = [start]
        if start != end:
            period.append(end)

        periods = _sumarize(days=other_days)
        periods.append(period)
        return periods

    def _period_str(period: 'list[int]', plural=False) -> str:

        if len(period) == 1:
            return _day_str(period[0], plural=plural)

        else:
            _join = ", " if period[0] + \
                1 == period[1] else " %s " % addon.getLocalizedString(32024)
            return "%s%s%s" % (_day_str(period[0], plural=plural), _join, _day_str(period[1], plural=plural))

    days.sort()

    if not days or days == [WEEKLY]:
        return addon.getLocalizedString(32034)

    if days == [i for i in range(8)]:
        human = addon.getLocalizedString(32035)

    elif days == [TIMER_BY_DATE] and date:
        date = parse_date_str(date)
        human = date.strftime(xbmc.getRegion("datelong"))

    else:
        periods = _sumarize(days=days)
        periods.reverse()

        plural = WEEKLY in days
        human = ", ".join([_period_str(p, plural) for p in periods])
        lead, sep, trail = human.rpartition(", ")
        if lead:
            human = "%s %s %s" % (lead, addon.getLocalizedString(32040), trail)

    if end:
        human += " %s %s %s %s" % (addon.getLocalizedString(32042),
                                   start, addon.getLocalizedString(32021), end)
    else:
        human += " %s %s" % (addon.getLocalizedString(32041), start)

    return human


def parse_time(s_time: str, i_day=0) -> timedelta:

    if s_time == "":
        s_time = DEFAULT_TIME

    m = re.match(r"^(\d{1,2}):(\d{1,2})( am)?( pm)?$", s_time.lower())
    if not m:
        return None

    tm_hour = int(m.groups()[0])
    if m.groups()[2] and tm_hour >= 12:  # am:
        tm_hour -= 12
    elif m.groups()[3] and tm_hour < 12:  # pm
        tm_hour += 12

    tm_min = int(m.groups()[1])
    tm_day = i_day + tm_hour // 24

    return timedelta(
        days=tm_day,
        hours=tm_hour % 24,
        minutes=tm_min)


def datetime_diff(t1: datetime, t2: datetime) -> int:

    return int((t2 - t1).total_seconds())


def time_diff(t1: 'timedelta | datetime', t2: 'timedelta | datetime', base: datetime = None) -> int:

    def _datetimedelta_diff(dt1: datetime, td2: timedelta, base: datetime) -> int:

        dt2 = apply_for_datetime(base or dt1, td2)
        return int((dt2 - dt1).total_seconds())

    if type(t1) == type(t2):
        return int((t2 - t1).total_seconds())

    elif type(t1) == datetime and type(t2) == timedelta:
        return _datetimedelta_diff(t1, t2, base)

    elif type(t1) == timedelta and type(t2) == datetime:
        return _datetimedelta_diff(t2, t1, base)

    raise ("Invalid datatype recognized. Only datetime and timedelta are supported")


def time_duration_str(start: str, end: str) -> str:
    _dt_start = parse_time(start)
    _dt_end = parse_time(end, i_day=1)
    _secs = int((_dt_end - _dt_start).total_seconds()) % 86400
    return format_from_seconds(_secs)


def format_from_seconds(secs: int) -> str:
    return "%02i:%02i" % (secs // 3600, (secs % 3600) // 60)


def format_from_timedelta(td: timedelta) -> 'tuple[str, int]':
    seconds = int(td.total_seconds())
    return format_from_seconds(seconds), seconds % 60


def apply_for_datetime(dt_now: datetime, timestamp: timedelta, force_future=False) -> datetime:

    dt_last_monday_same_time = dt_now - \
        timedelta(days=dt_now.weekday())
    dt_last_monday_midnight = datetime(year=dt_last_monday_same_time.year,
                                       month=dt_last_monday_same_time.month,
                                       day=dt_last_monday_same_time.day)

    applied_for_now = dt_last_monday_midnight + timestamp
    if force_future and applied_for_now < dt_now:
        applied_for_now += timedelta(days=7)
    return applied_for_now
