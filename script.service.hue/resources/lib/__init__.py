import functools
import time
from collections import deque
from logging import getLogger
from threading import Event

import xbmc
import xbmcaddon
import simplecache

NUM_GROUPS = 2  # group0= video, group1=audio
STRDEBUG = False  # Show string ID in UI
DEBUG = False  # Enable python remote debug
REMOTE_DBG_SUSPEND = False  # Auto suspend thread when debugger attached
QHUE_TIMEOUT = 1  # passed to requests, in seconds.
MINIMUM_COLOR_DISTANCE = 0.005
SETTINGS_CHANGED = Event()
PROCESS_TIMES = deque(maxlen=100)
ROLLBAR_API_KEY = "b871c6292a454fb490344f77da186e10"

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile'))  # .decode('utf-8'))
ADDONPATH = xbmc.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')


from resources.lib import kodilogging
logger = getLogger(ADDONID)
kodilogging.config()

cache = simplecache.SimpleCache()


def timer(func):
    """Logs the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        startTime = time.time()  # 1
        value = func(*args, **kwargs)
        endTime = time.time()  # 2
        runTime = endTime - startTime  # 3
        PROCESS_TIMES.append(runTime)

        return value

    return wrapper_timer
