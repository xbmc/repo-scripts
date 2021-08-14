import os
import sys
from datetime import timedelta

import simplecache
import xbmc
import xbmcplugin
from xbmcgui import ListItem

from .language import get_string as _
from resources.lib import logger, ADDON, ADDONPATH


try:
    # Python 3
    from urllib.parse import urlparse, parse_qs
except ImportError:
    # Python 2
    from urlparse import urlparse, parse_qs

cache = simplecache.SimpleCache()


def menu():
    route = sys.argv[0]
    addon_handle = int(sys.argv[1])
    base_url = sys.argv[0]
    command = sys.argv[2][1:]
    parsed = parse_qs(command)


    logger.debug("Menu started.  route: {}, handle: {}, command: {}, parsed: {}, Arguments: {}".format(route, addon_handle, command, parsed, sys.argv))

    if route == "plugin://script.service.hue/":
        if not command:

            build_menu(base_url, addon_handle)

        elif command == "settings":
            logger.debug("Opening settings")
            ADDON.openSettings()

        elif command == "toggle":
            if cache.get("script.service.hue.service_enabled") and get_status() != "Disabled by daylight":
                logger.debug("Disable service")
                cache.set("script.service.hue.service_enabled", False)

            elif get_status() != "Disabled by daylight":
                logger.debug("Enable service")
                cache.set("script.service.hue.service_enabled", True)
            else:
                logger.debug("Disabled by daylight, ignoring")

            xbmc.executebuiltin('Container.Refresh')

    elif route == "plugin://script.service.hue/actions":
        action = parsed['action'][0]
        kgroupid = parsed['kgroupid'][0]
        logger.debug("Actions: {}, kgroupid: {}".format(action, kgroupid))
        if action == "menu":
            items = [

                (base_url + "?action=play&kgroupid=" + kgroupid, ListItem(_("Play"))),
                (base_url + "?action=pause&kgroupid=" + kgroupid, ListItem(_("Pause"))),
                (base_url + "?action=stop&kgroupid=" + kgroupid, ListItem(_("Stop"))),
            ]

            xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)

        else:
            cache.set("script.service.hue.action", (action, kgroupid), expiration=(timedelta(seconds=5)))

    else:
        logger.debug("Unknown command. Handle: {}, route: {}, Arguments: {}".format(addon_handle, route, sys.argv))


def build_menu(base_url, addon_handle):
    items = [

        (base_url + "/actions?kgroupid=1&action=menu", ListItem(_("Video Actions")), True),
        (base_url + "/actions?kgroupid=2&action=menu", ListItem(_("Audio Actions")), True),
        (base_url + "?toggle",
         ListItem(_("Hue Status: ") + get_status())),
        (base_url + "?settings", ListItem(_("Settings")))
    ]

    xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)


def get_status():
    enabled = cache.get("script.service.hue.service_enabled")
    daylight = cache.get("script.service.hue.daylight")
    daylight_disable = cache.get("script.service.hue.daylightDisable")
    #logger.debug("Current status: {}".format(daylight_disable))
    if daylight and daylight_disable:
        return _("Disabled by daylight")
    elif enabled:
        return _("Enabled")
    else:
        return _("Disabled")



def get_icon_path(icon_name):
    return os.path.join(ADDONPATH, 'resources', 'icons', icon_name+".png")
