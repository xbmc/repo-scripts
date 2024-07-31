# Copyright (C) 2019 Kodi Hue Service (script.service.hue)
# This file is part of script.service.hue
# SPDX-License-Identifier: MIT
# See LICENSE.TXT for more information.

import sys
from urllib.parse import parse_qs

import xbmc
import xbmcplugin
import xbmcvfs
from xbmcgui import ListItem

from . import ADDON, ADDONID, ADDONPATH
from .kodiutils import cache_set, cache_get, log
from .language import get_string as _


def menu():
    route = sys.argv[0]
    addon_handle = int(sys.argv[1])
    base_url = sys.argv[0]
    command = sys.argv[2][1:]
    parsed = parse_qs(command)
    log(f"[SCRIPT.SERVICE.HUE] menu: {route}, {addon_handle}, {base_url}, {command}, {parsed}")

    if route == f"plugin://{ADDONID}/":
        handle_route(base_url, addon_handle, command)
    elif route == f"plugin://{ADDONID}/actions":
        handle_actions_route(parsed, base_url, addon_handle)
    else:
        log(f"[SCRIPT.SERVICE.HUE] Unknown command. Handle: {addon_handle}, route: {route}, Arguments: {sys.argv}")


def handle_route(base_url, addon_handle, command):
    if not command:
        build_menu(base_url, addon_handle)
    elif command == "settings":
        ADDON.openSettings()
        xbmc.executebuiltin('Container.Refresh')
    elif command == "toggle":
        handle_toggle_command()


def handle_toggle_command():
    if cache_get("service_enabled") and _get_status() != "Disabled by daytime":
        log("[SCRIPT.SERVICE.HUE] Disable service")
        cache_set("service_enabled", False)
    elif _get_status() != "Disabled by daytime":
        log("[SCRIPT.SERVICE.HUE] Enable service")
        cache_set("service_enabled", True)
    else:
        log("[SCRIPT.SERVICE.HUE] Disabled by daytime, ignoring")
    xbmc.executebuiltin('Container.Refresh')


def handle_actions_route(parsed, base_url, addon_handle):
    action = parsed['action'][0]
    light_group_id = parsed['light_group_id'][0]
    log(f"[SCRIPT.SERVICE.HUE] Actions: {action}, light_group_id: {light_group_id}")
    if action == "menu":
        xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=play&light_group_id=" + light_group_id, ListItem(_("Play")))
        xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=pause&light_group_id=" + light_group_id, ListItem(_("Pause")))
        xbmcplugin.addDirectoryItem(addon_handle, base_url + "?action=stop&light_group_id=" + light_group_id, ListItem(_("Stop")))
        xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)
    else:
        cache_set("action", (action, light_group_id))


def build_menu(base_url, addon_handle):
    log(f"[SCRIPT.SERVICE.HUE] build_menu: status: {_get_status()}")
    status_item = ListItem(_("Hue Status: ") + _get_status())
    status_icon = _get_status_icon()
    if status_icon:
        status_item.setArt({"icon": status_icon})
        log(f"[SCRIPT.SERVICE.HUE] status_icon: {status_icon}")
    settings_item = ListItem(_("Settings"))
    settings_item.setArt({"icon": xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/settings.png")})
    add_directory_items(base_url, addon_handle, status_item, settings_item)
    xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)


def add_directory_items(base_url, addon_handle, status_item, settings_item):
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "/actions?light_group_id=1&action=menu", ListItem(_("Video Scenes")), True)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "/actions?light_group_id=2&action=menu", ListItem(_("Audio Scenes")), True)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "?toggle", status_item)
    xbmcplugin.addDirectoryItem(addon_handle, base_url + "?settings", settings_item)


def _get_status():
    enabled = cache_get("service_enabled")
    daytime = cache_get("daytime")
    daytime_disable = ADDON.getSettingBool("daylightDisable")  # Legacy setting name, it's daytime everywhere now
    log(f"[SCRIPT.SERVICE.HUE] _get_status enabled: {enabled}   -  {type(enabled)}, daytime: {daytime}, daytime_disable: {daytime_disable}")
    if daytime and daytime_disable:
        return "Disabled by daytime"
    elif enabled:
        return "Enabled"
    else:
        return "Disabled"


def _get_status_icon():
    enabled = cache_get("service_enabled")
    daytime = cache_get("daytime")
    daytime_disable = ADDON.getSettingBool("daylightDisable")
    # log("[SCRIPT.SERVICE.HUE] Current status: {}".format(daytime_disable))
    if daytime and daytime_disable:
        return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/daylight.png")  # Disabled by daytime, legacy icon name
    elif enabled:
        return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/enabled.png")  # Enabled
    return xbmcvfs.makeLegalFilename(ADDONPATH + "resources/icons/disabled.png")  # Disabled
