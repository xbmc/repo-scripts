# -*- coding: utf-8 -*-
# Copyright (c) 2015 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

import multiprocessing

import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()

def display_error_message(
        message_id,
        append="",
        title=__addon__.getLocalizedString(32100).encode('utf-8'),
        type_=xbmcgui.NOTIFICATION_ERROR,
        time=1000,
        sound=True):
    """Display an error message in the Kodi interface"""
    display_message(
            message_id,
            append,
            title, 
            type_, 
            time, 
            sound)

def display_message(
        message_id, 
        append="",
        title=__addon__.getLocalizedString(32101).encode('utf-8'), 
        type_=xbmcgui.NOTIFICATION_INFO,
        time=5000,
        sound=False):
    """Display an informational message in the Kodi interface"""

    dialog = xbmcgui.Dialog()
    dialog.notification(
            title, 
            "{}{}".format(__addon__.getLocalizedString(message_id).encode('utf-8'), append),
            type_,
            time,
            sound)

def log(message):
    xbmc.log("projcontrol: {}".format(message), level=xbmc.LOGDEBUG)

