#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import functools
import time
from collections import deque
from threading import Event

import simplecache
import xbmc
import xbmcaddon
import xbmcvfs

STRDEBUG = False  # Show string ID in UI
QHUE_TIMEOUT = 1  # passed to requests, in seconds.
MINIMUM_COLOR_DISTANCE = 0.005
SETTINGS_CHANGED = Event()
AMBI_RUNNING = Event()
CONNECTED = Event()
PROCESS_TIMES = deque(maxlen=100)
ROLLBAR_API_KEY = "b871c6292a454fb490344f77da186e10"

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
# ADDONDIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ADDONPATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')

CACHE = simplecache.SimpleCache()


def timer(func):
    # Logs the runtime of the decorated function

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.time()  # 1
        value = func(*args, **kwargs)
        end_time = time.time()  # 2
        run_time = end_time - start_time  # 3
        PROCESS_TIMES.append(run_time)
        return value
    return wrapper_timer
