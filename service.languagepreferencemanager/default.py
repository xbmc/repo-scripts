import os, sys, re
import xbmc, xbmcaddon, xbmcvfs

import json as simplejson

__addon__ = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonPath__ = __addon__.getAddonInfo('path')
__addonResourcePath__ = xbmcvfs.translatePath(os.path.join(__addonPath__, 'resources', 'lib'))
__addonIconFile__ = xbmcvfs.translatePath(os.path.join(__addonPath__, 'icon.png'))
__user_data_path__ = xbmcvfs.translatePath("special://profile/addon_data/service.languagepreferencemanager/")
sys.path.append(__addonResourcePath__)

from langcodes import *
from prefsettings import settings
from prefutils import LangPref_Monitor
from prefutils import LangPrefMan_Player

settings = settings()

LOG_NONE = 0
LOG_ERROR = 1
LOG_INFO = 2
LOG_DEBUG = 3


def log(level, msg):
    if level <= settings.logLevel:
        if level == LOG_ERROR:
            l = xbmc.LOGERROR
        elif level == LOG_INFO:
            l = xbmc.LOGINFO
        elif level == LOG_DEBUG:
            l = xbmc.LOGDEBUG
        xbmc.log("[Language Preference Manager]: " + str(msg), l)


class Main:
    def __init__(self):
        self._init_vars()
        if not settings.service_enabled:
            log(LOG_INFO, "Service not enabled")

        settings.readSettings()
        self._daemon()

    def _init_vars(self):
        self.Monitor = LangPref_Monitor()
        self.Player = LangPrefMan_Player()

    def _daemon(self):
        while not self.Monitor.abortRequested():
            self.Monitor.waitForAbort(1)


# Allow this to be called as a script with parameters
if len(sys.argv) > 1 and sys.argv[1] == 'show_overrides':
    from resources.lib.override_preference_dialog import *
elif __name__ == "__main__":
    log(LOG_INFO, 'service {0} version {1} started'.format(__addonname__, __addonversion__))
    main = Main()
    log(LOG_INFO, 'service {0} version {1} stopped'.format(__addonname__, __addonversion__))
