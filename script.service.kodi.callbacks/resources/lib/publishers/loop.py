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


import threading
import time
from json import loads as jloads

import xbmc
import xbmcgui
from resources.lib.events import Events
from resources.lib.pubsub import Publisher, Message, Topic
from resources.lib.utils.poutil import KodiPo

kodipo = KodiPo()
_ = kodipo.getLocalizedString


def getStereoscopicMode():
    """
    Retrieves stereoscopic mode from json-rpc
    @return: "off", "split_vertical", "split_horizontal", "row_interleaved", "hardware_based", "anaglyph_cyan_red",
             "anaglyph_green_magenta", "monoscopic"
    @rtype: str
    """
    query = '{"jsonrpc": "2.0", "method": "GUI.GetProperties", "params": {"properties": ["stereoscopicmode"]}, "id": 1}'
    result = xbmc.executeJSONRPC(query)
    jsonr = jloads(result)
    ret = ''
    if 'result' in jsonr:
        if 'stereoscopicmode' in jsonr['result']:
            if 'mode' in jsonr['result']['stereoscopicmode']:
                ret = jsonr['result']['stereoscopicmode']['mode'].encode('utf-8')
    return ret


def getProfileString():
    """
    Retrieves the current profile as a path
    @rtype: str
    """
    ps = xbmc.translatePath('special://profile')
    return ps


class LoopPublisher(threading.Thread, Publisher):
    publishes = Events().CustomLoop.keys()

    def __init__(self, dispatcher, settings):
        Publisher.__init__(self, dispatcher)
        threading.Thread.__init__(self, name='LoopPublisher')
        self.interval = settings.general['LoopFreq']
        self.abort_evt = threading.Event()
        self.abort_evt.clear()
        self.openwindowids = settings.getOpenwindowids()
        self.closewindowsids = settings.getClosewindowids()
        idleT = settings.getIdleTimes()
        afterIdle = settings.getAfterIdleTimes()
        self.player = xbmc.Player()
        if idleT is not None:
            if len(idleT) > 0:
                self.idleTs = []
                self._startidle = 0
                self._playeridle = False
                for key in idleT.keys():
                    # time, key, executed
                    self.idleTs.append([idleT[key], key, False])
            else:
                self.idleTs = []
        else:
            self.idleTs = []
        if afterIdle is not None:
            if len(afterIdle) > 0:
                self.afterIdles = []
                self._startidle = 0
                self._playeridle = False
                for key in afterIdle.keys():
                    # time, key, triggered
                    self.afterIdles.append([afterIdle[key], key, False])
            else:
                self.afterIdles = []
        else:
            self.afterIdles = []
        if len(self.idleTs) > 0 or len(self.afterIdles) > 0:
            self.doidle = True
        else:
            self.doidle = False

    def run(self):
        lastwindowid = xbmcgui.getCurrentWindowId()
        lastprofile = getProfileString()
        laststereomode = getStereoscopicMode()
        interval = self.interval
        firstloop = True
        starttime = time.time()
        while not self.abort_evt.is_set():

            self._checkIdle()

            newprofile = getProfileString()
            if newprofile != lastprofile:
                self.publish(Message(Topic('onProfileChange'), profilePath=newprofile))
                lastprofile = newprofile

            newstereomode = getStereoscopicMode()
            if newstereomode != laststereomode:
                self.publish(Message(Topic('onStereoModeChange'), stereoMode=newstereomode))
                laststereomode = newstereomode

            newwindowid = xbmcgui.getCurrentWindowId()
            if newwindowid != lastwindowid:
                if lastwindowid in self.closewindowsids.keys():
                    self.publish(Message(Topic('onWindowClose', self.closewindowsids[lastwindowid])))
                if newwindowid in self.openwindowids:
                    self.publish(Message(Topic('onWindowOpen', self.openwindowids[newwindowid])))
                lastwindowid = newwindowid

            if firstloop:
                endtime = time.time()
                interval = int(interval - (endtime - starttime) * 1000)
                interval = max(5, interval)
                firstloop = False
            xbmc.sleep(interval)
        del self.player

    def _checkIdle(self):
        if self.doidle is False:
            return
        XBMCit = xbmc.getGlobalIdleTime()
        if self.player.isPlaying():
            self._playeridle = False
            self._startidle = XBMCit
        else:  # player is not playing
            if self._playeridle is False:  # if the first pass with player idle, start timing here
                self._playeridle = True
                self._startidle = XBMCit
        myit = XBMCit - self._startidle  # amount of time idle and not playing
        for it in self.idleTs:
            if myit > it[0]:  # if time exceeded idle timer
                if it[2] is False:  # idle task has NOT been executed
                    msg = Message(Topic('onIdle', it[1]))
                    self.publish(msg)
                    it[2] = True
            else:  # if time has not exceeded timer
                it[2] = False  # reset task executed flag
        for it in self.afterIdles:
            if myit > it[0]:  # time has exceeded timer
                it[2] = True  # set flag that task needs to be executed when exiting idle
            else:  # time has not exceeded idle timer
                if it[2] is True:  # if flag to execute has been set
                    msg = Message(Topic('afterIdle', it[1]))
                    self.publish(msg)
                it[2] = False  # reset flag to execute

    def abort(self, timeout=0):
        self.abort_evt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop LoopPublisher T:%i') % self.ident)
