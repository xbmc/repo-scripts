"""Thin helpers around the Kodi modules: strings, settings, logging, JSON-RPC."""
import json

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon("service.refract")
ADDON_NAME = ADDON.getAddonInfo("name")
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
ICON = xbmcvfs.translatePath(ADDON.getAddonInfo("icon"))


def string(string_id, *args):
    text = ADDON.getLocalizedString(string_id)
    return text.format(*args) if args else text


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[service.refract] {0}".format(message), level)


def setting_bool(key):
    return ADDON.getSettingBool(key)


def setting_int(key):
    return ADDON.getSettingInt(key)


def set_setting(key, value):
    ADDON.setSettingString(key, value)


def notify(message, time_ms=4000):
    xbmcgui.Dialog().notification(ADDON_NAME, message, ICON, time_ms)


def jsonrpc(method, params=None):
    """Kodi's own API: the add-on rules forbid reading Kodi's database directly."""
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if "error" in response:
        log("JSON-RPC {0} failed: {1}".format(method, response["error"]), xbmc.LOGWARNING)
        return None
    return response.get("result")
