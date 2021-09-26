import sys
from datetime import timedelta
from urllib.parse import parse_qs

import xbmc
import xbmcplugin
import xbmcvfs
from xbmcgui import ListItem

from resources.lib import ADDON, CACHE, ADDONID, ADDONPATH
from .language import get_string as _


def menu():
    route = sys.argv[0]
    addon_handle = int(sys.argv[1])
    base_url = sys.argv[0]
    command = sys.argv[2][1:]
    parsed = parse_qs(command)

    if route == f"plugin://{ADDONID}/":
        if not command:
            build_menu(base_url, addon_handle)

        elif command == "settings":
            ADDON.openSettings()

        elif command == "toggle":
            if CACHE.get(f"{ADDONID}.service_enabled") and _get_status() != "Disabled by daylight":
                xbmc.log("[script.service.hue] Disable service")
                CACHE.set(f"{ADDONID}.service_enabled", False)

            elif _get_status() != "Disabled by daylight":
                xbmc.log("[script.service.hue] Enable service")
                CACHE.set(f"{ADDONID}.service_enabled", True)
            else:
                xbmc.log("[script.service.hue] Disabled by daylight, ignoring")

            xbmc.executebuiltin('Container.Refresh')

    elif route == f"plugin://{ADDONID}/actions":
        action = parsed['action'][0]
        light_group_id = parsed['light_group_id'][0]
        xbmc.log(f"[script.service.hue] Actions: {action}, light_group_id: {light_group_id}")
        if action == "menu":

            xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=play&light_group_id=" + light_group_id, ListItem(_("Play")))
            xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=pause&light_group_id=" + light_group_id, ListItem(_("Pause")))
            xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=stop&light_group_id=" + light_group_id, ListItem(_("Stop")))

            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)
        else:
            CACHE.set(f"{ADDONID}.action", (action, light_group_id), expiration=(timedelta(seconds=5)))
    else:
        xbmc.log(f"[script.service.hue] Unknown command. Handle: {addon_handle}, route: {route}, Arguments: {sys.argv}")


def build_menu(base_url, addon_handle):
    status_item = ListItem(_("Hue Status: ") + _get_status())
    status_icon = _get_status_icon()
    if status_icon:
        status_item.setArt({"icon": status_icon})
        xbmc.log(f"[script.service.hue] status_icon: {status_icon}")

    settings_item = ListItem(_("Settings"))
    settings_item.setArt({"icon": xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/settings.png")})

    xbmcplugin.addDirectoryItem(addon_handle, base_url + "/actions?light_group_id=1&action=menu", ListItem(_("Video Actions")), True)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "/actions?light_group_id=2&action=menu", ListItem(_("Audio Actions")), True)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "?toggle", status_item)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "?settings", settings_item)

    xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)


def _get_status():
    enabled = CACHE.get(f"{ADDONID}.service_enabled")
    daylight = CACHE.get(f"{ADDONID}.daylight")
    daylight_disable = ADDON.getSettingBool("daylightDisable")
    # xbmc.log("[script.service.hue] Current status: {}".format(daylight_disable))
    if daylight and daylight_disable:
        return _("Disabled by daylight")
    elif enabled:
        return _("Enabled")
    return _("Disabled")


def _get_status_icon():
    enabled = CACHE.get(f"{ADDONID}.service_enabled")
    daylight = CACHE.get(f"{ADDONID}.daylight")
    daylight_disable = ADDON.getSettingBool("daylightDisable")
    # xbmc.log("[script.service.hue] Current status: {}".format(daylight_disable))
    if daylight and daylight_disable:
        return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/daylight.png")  # Disabled by Daylight
    elif enabled:
        return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/enabled.png")  # Enabled
    return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/disabled.png")  # Disabled
