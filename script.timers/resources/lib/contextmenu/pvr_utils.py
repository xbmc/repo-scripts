from urllib import parse

import xbmc
from resources.lib.utils.jsonrpc_utils import json_rpc

PVR_TV = "tv"
PVR_RADIO = "radio"

_WINDOW_TV_GUIDE = 10702
_WINDOW_RADIO_GUIDE = 10707

_PLAY_PVR_URL_PATTERN = "pvr://channels/%s/%s/%s_%i.pvr"


def get_current_epg_view() -> str:

    if xbmc.getCondVisibility("Window.IsActive(%s)" % _WINDOW_TV_GUIDE):
        return PVR_TV

    elif xbmc.getCondVisibility("Window.IsActive(%s)" % _WINDOW_RADIO_GUIDE):
        return PVR_RADIO

    else:
        return None


def get_pvr_channel_path(type: str, channelno: str) -> str:

    try:
        channelno = int(channelno)
        _result = json_rpc("PVR.GetChannelGroups", {
            "channeltype": type})
        channelGroupAll = _result["channelgroups"][0]["label"]

        _result = json_rpc("PVR.GetClients")
        pvrClients = _result["clients"]

        _result = json_rpc("PVR.GetChannels", {
            "channelgroupid": "all%s" % type, "properties": ["uniqueid", "clientid", "channelnumber"]})
        channel = next(
            filter(lambda c: c["channelnumber"] == channelno, _result["channels"]), None)

        if not channel:
            return None

        pvrClient = list(filter(
            lambda _c: _c["supportsepg"] == True and _c["clientid"] == channel["clientid"], pvrClients))[0]

        if channelGroupAll and pvrClient and channel:
            return _PLAY_PVR_URL_PATTERN % (type, parse.quote(channelGroupAll), pvrClient["addonid"], channel["uniqueid"])

    except:
        pass

    return None
