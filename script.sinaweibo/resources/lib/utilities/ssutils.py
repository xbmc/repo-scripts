
import datetime
from common_addon import *

def get_timedelta_string(td):
    if td.days > 0:
        return "(" + str(td.days) + " " + get_days_string(td.days) + " " + translate(32054) + ")"
    else:
        hours = td.seconds / 3600
        if hours > 0:
            minutes = (td.seconds - hours * 3600) / 60
            if minutes > 0:
                return "(" + str(hours) + " " + get_hour_string(hours) + " " + translate(32055) + " " + str(
                    minutes) + " " + get_minutes_string(minutes) + " " + translate(32054) + ")"
            else:
                return "(" + str(hours) + " " + get_hour_string(hours) + " " + translate(32054) + ")"
        else:
            minutes = td.seconds / 60
            if minutes > 0:
                seconds = td.seconds - minutes * 60
                return "(" + str(minutes) + " " + get_minutes_string(minutes) + " " + translate(32055) + " " + str(
                    seconds) + " " + get_seconds_string(seconds) + " " + translate(32054) + ")"
            else:
                return "(" + str(td.seconds) + " " + get_seconds_string(td.seconds) + " " + translate(32054) + ")"


def get_days_string(days):
    if days == 1:
        return translate(32056)
    else:
        return translate(32057)


def get_hour_string(hours):
    if hours == 1:
        return translate(32058)
    else:
        return translate(32059)


def get_minutes_string(minutes):
    if minutes == 1:
        return translate(32060)
    else:
        return translate(32061)


def get_seconds_string(seconds):
    if seconds == 1:
        return translate(32062)
    else:
        return translate(32063)
