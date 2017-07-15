#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Utils module. Some basic functions that maybe I'll need more than once
"""
import sys
import xbmc, xbmcaddon, xbmcgui
from threading import Timer

__addon__ = xbmcaddon.Addon("script.simkl")


def log(s):
    xbmc.log("-- Simkl: {0}".format(s), level=xbmc.LOGDEBUG)


def get_str(strid):
    """ Given an id, returns the localized string """
    return __addon__.getLocalizedString(strid)


def get_setting(settingid):
    """ Given an id, return the setting """
    ret = __addon__.getSetting(settingid)
    log("get setting {0} = {1}".format(settingid, ret))
    return ret


def set_setting(settingid, val):
    """ Given an id, return the setting """
    log("set setting, {0} = {1}".format(settingid, val))
    __addon__.setSetting(settingid, val)


def system_lock(name, sec=0):
    w = xbmcgui.Window(10000)
    if w.getProperty(name) == "True":
        log('already started, ' + name)
        sys.exit(0)
    w.setProperty(name, "True")
    if sec != 0:
        def stop_singleton():
            w.clearProperty(name)

        t = Timer(sec, stop_singleton)
        t.start()
