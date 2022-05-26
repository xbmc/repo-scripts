import datetime
import time

import xbmc

DEFAULT_TIME = "00:00"


def parse_xbmc_shortdate(date: str) -> datetime.datetime:

    format = xbmc.getRegion("dateshort")
    return datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, format)))


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


def time_duration_str(s_start: str, s_end: str) -> str:
    _dt_start = parse_time(s_start)
    _dt_end = parse_time(s_end, i_day=1)
    _secs = time_diff(_dt_start, _dt_end) % 86400
    return format_from_seconds(_secs)


def format_from_seconds(secs: int) -> str:
    return "%02i:%02i" % (secs // 3600, (secs % 3600) // 60)


def get_now() -> 'tuple[time.struct_time, datetime.timedelta]':
    t_now = time.localtime()
    td_now = datetime.timedelta(hours=t_now.tm_hour,
                                minutes=t_now.tm_min,
                                seconds=t_now.tm_sec,
                                days=t_now.tm_wday)
    return t_now, td_now
