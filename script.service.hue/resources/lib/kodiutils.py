#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import datetime
import json
from json import JSONDecodeError

import xbmcgui
import xbmc

from . import ADDON, ADDONID, FORCEDEBUGLOG

cache_window = xbmcgui.Window(10000)


def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=False):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def convert_time(time_string: str) -> datetime.time:
    parts = list(map(int, time_string.split(':')))
    if len(parts) == 2:
        return datetime.time(parts[0], parts[1])
    elif len(parts) == 3:
        return datetime.time(parts[0], parts[1], parts[2])


def cache_get(key: str):
    data_str = cache_window.getProperty(f"{ADDONID}.{key}]")
    try:
        data = json.loads(data_str)
        return data
    except JSONDecodeError:
        return None


def cache_set(key: str, data):
    data_str = json.dumps(data)
    cache_window.setProperty(f"{ADDONID}.{key}]", data_str)
    return


def log(message, level=xbmc.LOGDEBUG):
    if FORCEDEBUGLOG:
        xbmc.log(message, xbmc.LOGWARNING)
    else:
        xbmc.log(message, level)
