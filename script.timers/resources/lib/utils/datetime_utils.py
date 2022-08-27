import datetime
import time

import xbmc
import xbmcaddon

DEFAULT_TIME = "00:00"

WEEKLY = 7


def _parse_datetime_from_str(s: str, format: str) -> datetime:

    return datetime.datetime.fromtimestamp(time.mktime(time.strptime(s, format)))


def parse_datetime_str(s: str) -> datetime:

    return _parse_datetime_from_str(s, "%Y-%m-%d %H:%M")


def parse_xbmc_shortdate(s: str) -> datetime.datetime:

    return _parse_datetime_from_str(s, format=xbmc.getRegion("dateshort"))


def periods_to_human_readable(days: 'list[int]', start: str, end="") -> str:

    addon = xbmcaddon.Addon()

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
                                   start, addon.getLocalizedString(32024), end)
    else:
        human += " %s %s" % (addon.getLocalizedString(32041), start)

    return human


def parse_time(s_time: str, i_day=0) -> datetime.timedelta:

    if s_time == "":
        s_time = DEFAULT_TIME

    if s_time.lower().endswith(" am") or s_time.lower().endswith(" pm"):
        t_time = time.strptime(s_time, "%I:%M %p")

    else:
        t_time = time.strptime(s_time, "%H:%M")

    return datetime.timedelta(
        days=i_day,
        hours=t_time.tm_hour,
        minutes=t_time.tm_min)


def abs_time_diff(td1: datetime.timedelta, td2: datetime.timedelta) -> datetime.timedelta:

    return abs(time_diff(td1, td2))


def time_diff(td1: datetime.timedelta, td2: datetime.timedelta) -> datetime.timedelta:

    s1 = td1.days * 86400 + td1.seconds
    s2 = td2.days * 86400 + td2.seconds

    return s2 - s1


def time_duration_str(start: str, end: str) -> str:
    _dt_start = parse_time(start)
    _dt_end = parse_time(end, i_day=1)
    _secs = time_diff(_dt_start, _dt_end) % 86400
    return format_from_seconds(_secs)


def format_from_seconds(secs: int) -> str:
    return "%02i:%02i" % (secs // 3600, (secs % 3600) // 60)


def get_now(offset=0) -> 'tuple[datetime.datetime, datetime.timedelta]':
    dt_now = datetime.datetime.today()
    td_now = datetime.timedelta(hours=dt_now.hour, minutes=dt_now.minute,
                                seconds=dt_now.second, days=dt_now.weekday())
    if offset:
        if offset > 0:
            td_now += datetime.timedelta(seconds=offset)
        else:
            td_now -= datetime.timedelta(seconds=abs(offset))

    return dt_now, td_now
