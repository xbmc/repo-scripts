from urllib import parse

import xbmc
from resources.lib.utils.jsonrpc_utils import json_rpc
from resources.lib.utils.system_utils import get_kodi_version

PVR_TV = "tv"
PVR_RADIO = "radio"

_WINDOW_TV_GUIDE = 10702
_WINDOW_RADIO_GUIDE = 10707

_PLAY_PVR_URL_PATTERN = "pvr://channels/%s/%s/%s_%i.pvr"
_PLAY_PVR_URL_PATTERN_V21 = "pvr://channels/%s/%s@%i/%i@%s_%i.pvr"

_CHANNEL_GROUP_ALL_ID = -1


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
        channels = [c for c in _result["channels"]
                    if c["channelnumber"] == channelno]

        if not channels:
            return None

        pvrClient = [_c for _c in pvrClients if _c["supportsepg"]
                     == True and _c["clientid"] == channels[0]["clientid"]][0]

        if channelGroupAll and pvrClient and channels[0]:
            if get_kodi_version() < 21.0:
                return _PLAY_PVR_URL_PATTERN % (type, parse.quote(channelGroupAll), pvrClient["addonid"], channels[0]["uniqueid"])
            else:
                return _PLAY_PVR_URL_PATTERN_V21 % (type, parse.quote(channelGroupAll), _CHANNEL_GROUP_ALL_ID, pvrClient["instanceid"], pvrClient["addonid"], channels[0]["uniqueid"])

    except:
        pass

    return None
