#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Various helper methods'''

import xbmcgui
import xbmc
import sys
import urllib
from traceback import format_exc

ADDON_ID = "script.skin.helper.backgrounds"


def log_msg(msg, loglevel=xbmc.LOGDEBUG):
    '''log to kodi logfile'''
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("Skin Helper Backgrounds --> %s" % msg, level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log exception details'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGDEBUG)
    log_msg("ERROR in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)


def urlencode(text):
    '''helper to urlencode a (unicode) string'''
    if isinstance(text, unicode):
        text = text.encode("utf-8")
    blah = urllib.urlencode({'blahblahblah': text})
    blah = blah[13:]
    return blah


def get_content_path(lib_path):
    '''helper to get the real browsable path'''
    if "$INFO" in lib_path and "reload=" not in lib_path:
        lib_path = lib_path.replace("$INFO[Window(Home).Property(", "")
        lib_path = lib_path.replace(")]", "")
        win = xbmcgui.Window(10000)
        lib_path = win.getProperty(lib_path)
        del win
    if "activate" in lib_path.lower():
        if "activatewindow(musiclibrary," in lib_path.lower():
            lib_path = lib_path.lower().replace("activatewindow(musiclibrary,", "musicdb://")
            lib_path = lib_path.replace(",return", "/")
            lib_path = lib_path.replace(", return", "/")
        else:
            lib_path = lib_path.lower().replace(",return", "")
            lib_path = lib_path.lower().replace(", return", "")
            if ", " in lib_path:
                lib_path = lib_path.split(", ", 1)[1]
            elif " , " in lib_path:
                lib_path = lib_path.split(" , ", 1)[1]
            elif " ," in lib_path:
                lib_path = lib_path.split(", ", 1)[1]
            elif "," in lib_path:
                lib_path = lib_path.split(",", 1)[1]
        lib_path = lib_path.replace(")", "")
        lib_path = lib_path.replace("\"", "")
        lib_path = lib_path.replace("musicdb://special://", "special://")
        lib_path = lib_path.replace("videodb://special://", "special://")
    if "&reload=" in lib_path:
        lib_path = lib_path.split("&reload=")[0]
    return lib_path
