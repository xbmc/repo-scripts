#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import xbmc
import threading

def log(loglevel=xbmc.LOGNOTICE, msg=''):
    if isinstance(msg, str):
        msg = msg.decode("utf-8")
    message = u"$$$ [%s] - %s" % ('kodi.callbacks', msg)
    xbmc.log(msg=message.encode("utf-8"), level=loglevel)

class KodiLogger(object):
    LOGDEBUG = 0
    LOGERROR = 4
    LOGFATAL = 6
    LOGINFO = 1
    LOGNONE = 7
    LOGNOTICE = 2
    LOGSEVERE = 5
    LOGWARNING = 3
    _instance = None
    _lock = threading.Lock()
    selfloglevel = xbmc.LOGDEBUG
    kodirunning = True

    def __new__(cls):
        if xbmc.getFreeMem() == long():
            KodiLogger.kodirunning = False
        if KodiLogger._instance is None:
            with KodiLogger._lock:
                if KodiLogger._instance is None:
                    KodiLogger._instance = super(KodiLogger, cls).__new__(cls)
        return KodiLogger._instance

    def __init__(self):
        KodiLogger._instance = self

    @staticmethod
    def setLogLevel(arg):
        KodiLogger.selfloglevel = arg

    @staticmethod
    def log(loglevel=None, msg=''):
        if loglevel is None:
            loglevel = KodiLogger.selfloglevel
        if isinstance(msg, str):
            msg = msg.decode("utf-8")
        if KodiLogger.kodirunning:
            message = u"$$$ [%s] - %s" % (u'kodi.callbacks', msg)
            xbmc.log(msg=message.encode("utf-8", 'replace'), level=loglevel)
        else:
            print msg