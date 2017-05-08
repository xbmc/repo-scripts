import os
import xbmc


def is_websocket_debug_mode():
    return os.path.exists(os.path.expanduser('~/.MIRACLE_WEBSOCKET_DEBUG'))


def debug(msg):
    xbmc.log('Miracle addon: %s' % msg, level=xbmc.LOGDEBUG)


def error(msg):
    xbmc.log('Miracle addon: %s' % msg, level=xbmc.LOGERROR)


def notify(msg):
    xbmc.executebuiltin('XBMC.Notification(Miracle,' + msg + ',10)')

