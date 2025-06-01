import xbmc, xbmcaddon
from prefsettings import settings

LOG_NONE = 0
LOG_ERROR = 1
LOG_INFO = 2
LOG_DEBUG = 3

settings = settings()

def log(level, msg):
    log_level = settings.logLevel

    if level <= log_level:
        if level == LOG_ERROR:
            kodi_log_level = xbmc.LOGERROR
        elif level == LOG_INFO:
            kodi_log_level = xbmc.LOGINFO
        elif level == LOG_DEBUG:
            kodi_log_level = xbmc.LOGDEBUG
        else:
            log(LOG_ERROR, "Unknown log level " + str(level))
            log(LOG_INFO, msg)
            return

        xbmc.log("[Language Preference Manager]: " + str(msg), kodi_log_level)