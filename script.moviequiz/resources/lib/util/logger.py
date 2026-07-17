import xbmc


LOG_PREFACE = "script.moviequiz >> "


def debug(message):
    xbmc.log(LOG_PREFACE + message, xbmc.LOGDEBUG)


def info(message):
    xbmc.log(LOG_PREFACE + message, xbmc.LOGINFO)


def warning(message):
    xbmc.log(LOG_PREFACE + message, xbmc.LOGWARNING)


def error(message):
    xbmc.log(LOG_PREFACE + message, xbmc.LOGERROR)


def fatal(message):
    xbmc.log(LOG_PREFACE + message, xbmc.LOGFATAL)
