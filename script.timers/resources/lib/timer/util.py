import json
import time
from datetime import datetime, timedelta
from urllib import parse

# prevent Error: Failed to import _strptime because the import lockis held by another thread.
# see https://www.raspberrypi.org/forums/viewtopic.php?t=166912
import _strptime
import xbmc

_ON_SETTING_CHANGE_EVENTS = "onSettingChangeEvents"
_SETTING_CHANGE_EVENTS_MAX_SECS = 5
_SETTING_CHANGE_EVENTS_ACTIVE = 0

_WINDOW_TV_GUIDE = 10702
_WINDOW_RADIO_GUIDE = 10707
_PLAY_PVR_URL_PATTERN = "pvr://channels/%s/%s/%s_%i.pvr"

PVR_TV = "tv"
PVR_RADIO = "radio"

DEFAULT_TIME = "00:00"


def deactivateOnSettingsChangedEvents(addon):

    addon.setSetting(_ON_SETTING_CHANGE_EVENTS, "%i" % int(time.time()))


def activateOnSettingsChangedEvents(addon):

    addon.setSetting(_ON_SETTING_CHANGE_EVENTS, "%i" %
                     _SETTING_CHANGE_EVENTS_ACTIVE)


def isSettingsChangedEvents(addon):

    current = int("0%s" % addon.getSetting(_ON_SETTING_CHANGE_EVENTS))
    now = int(time.time())
    return now - current > _SETTING_CHANGE_EVENTS_MAX_SECS


def parse_xbmc_shortdate(date):

    format = xbmc.getRegion("dateshort")
    return datetime.strptime(date, format)


def parse_time(s_time, i_day=0):

    if s_time == "":
        s_time = DEFAULT_TIME

    if s_time.lower().endswith(" am") or s_time.lower().endswith(" pm"):
        t_time = time.strptime(s_time, "%I:%M %p")

    else:
        t_time = time.strptime(s_time, "%H:%M")

    return timedelta(
        days=i_day,
        hours=t_time.tm_hour,
        minutes=t_time.tm_min)


def abs_time_diff(td1, td2):

    return abs(time_diff(td1, td2))


def time_diff(td1, td2):

    s1 = td1.days * 86400 + td1.seconds
    s2 = td2.days * 86400 + td2.seconds

    return s2 - s1


def time_duration_str(s_start, s_end):
    _dt_start = parse_time(s_start)
    _dt_end = parse_time(s_end, i_day=1)
    _secs = time_diff(_dt_start, _dt_end) % 86400
    return format_from_seconds(_secs)


def format_from_seconds(secs):
    return "%02i:%02i" % (secs // 3600, (secs % 3600) // 60)


def get_current_epg_view():

    if xbmc.getCondVisibility("Window.IsActive(%s)" % _WINDOW_TV_GUIDE):
        return PVR_TV

    elif xbmc.getCondVisibility("Window.IsActive(%s)" % _WINDOW_RADIO_GUIDE):
        return PVR_RADIO

    else:
        return None


def get_pvr_channel_path(type, channelno):

    try:
        _result = json_rpc("PVR.GetChannelGroups", {
            "channeltype": type})
        channelGroupAll = _result["channelgroups"][0]["label"]

        _result = json_rpc("PVR.GetClients")
        pvrClients = _result["clients"]

        _result = json_rpc("PVR.GetChannels", {
            "channelgroupid": "all%s" % type, "properties": ["uniqueid", "clientid"]})
        channel = _result["channels"][int(channelno) - 1]

        pvrClient = list(filter(
            lambda _c: _c["supportsepg"] == True and _c["clientid"] == channel["clientid"], pvrClients))[0]

        if channelGroupAll and pvrClient and channel:
            return _PLAY_PVR_URL_PATTERN % (type, parse.quote(channelGroupAll), pvrClient["addonid"], channel["uniqueid"])

    except:
        pass

    return None


def json_rpc(jsonmethod, params=None):

    kodi_json = {}

    kodi_json["jsonrpc"] = "2.0"
    kodi_json["method"] = jsonmethod

    if not params:
        params = {}

    kodi_json["params"] = params
    kodi_json["id"] = 1

    json_response = xbmc.executeJSONRPC(json.dumps(kodi_json))
    json_object = json.loads(json_response)
    return json_object["result"] if "result" in json_object else None
