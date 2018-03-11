# -*- coding: utf-8 -*-

"""
    screensaver.atv4
    Copyright (C) 2015-2018 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import xbmc
import xbmcgui
import offline as off
import playlist
import threading
from commonatv import translate, addon, addon_path
from trans import ScreensaverTrans

monitor = xbmc.Monitor()


class Screensaver(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        self.DPMStime = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"powermanagement.displaysoff"},"id":2}'))['result']['value'] * 60
        self.isDPMSactive = bool(self.DPMStime > 0)
        self.active = True
        self.videoplaylist = playlist.AtvPlaylist().getPlaylist()
        xbmc.log(msg="kodi dpms time:" + str(self.DPMStime), level=xbmc.LOGDEBUG)
        xbmc.log(msg="kodi dpms active:" + str(self.isDPMSactive), level=xbmc.LOGDEBUG)

    def onInit(self):
        self.getControl(32502).setLabel(translate(32008))
        self.setProperty("screensaver-atv4-loading", "true")

        if self.videoplaylist:
            self.setProperty("screensaver-atv4-loading", "false")
            self.atv4player = xbmc.Player()

            # Start player thread
            threading.Thread(target=self.start_playback).start()

            # DPMS logic
            self.max_allowed_time = None

            if self.isDPMSactive and addon.getSetting("check-dpms") == "1":
                self.max_allowed_time = self.DPMStime

            elif addon.getSetting("check-dpms") == "2":
                self.max_allowed_time = int(addon.getSetting("manual-dpms")) * 60

            xbmc.log(msg="check dpms:" + str(addon.getSetting("check-dpms")),
                     level=xbmc.LOGDEBUG)
            xbmc.log(msg="before supervision:" + str(self.max_allowed_time),
                     level=xbmc.LOGDEBUG)

            if self.max_allowed_time:
                delta = 0
                while self.active:
                    if delta >= self.max_allowed_time:
                        self.activateDPMS()
                        break
                    xbmc.sleep(1000)
                    delta += 1
        else:
            self.novideos()

    def activateDPMS(self):
        xbmc.log(msg="[Aerial Screensaver] Manually activating DPMS!", level=xbmc.LOGDEBUG)
        self.active = False

        # Take action on the video
        enable_window_placeholder = False
        if addon.getSetting("dpms-action") == "0":
            self.atv4player.pause()
        else:
            self.clearAll()
            enable_window_placeholder = True

        if addon.getSetting("toggle-displayoff") == "true" or addon.getSetting("toggle-cecoff") == "true":
            monitor.waitForAbort(1)

        if addon.getSetting("toggle-displayoff") == "true":
            try:
                xbmc.executebuiltin('ToggleDPMS')
            except Exception as e:
                xbmc.log(msg="[Aerial Screensaver] Failed to toggle DPMS: %s" %
                         (str(e)), level=xbmc.LOGDEBUG)

        if addon.getSetting("toggle-cecoff") == "true":
            try:
                xbmc.executebuiltin('CECStandby')
            except Exception as e:
                xbmc.log(msg="[Aerial Screensaver] Failed to toggle device off via CEC: %s" % (str(e)), level=xbmc.LOGDEBUG)

        # Enable placeholder window
        if enable_window_placeholder:
            self.toTransparent()

    def novideos(self):
        self.setProperty("screensaver-atv4-loading", "false")
        self.getControl(32503).setVisible(True)
        self.getControl(32503).setLabel(translate(32007))

    @classmethod
    def toTransparent(self):
        trans = ScreensaverTrans(
            'screensaver-atv4-trans.xml',
            addon_path,
            'default',
            '',
        )
        trans.doModal()
        xbmc.sleep(100)
        del trans

    def clearAll(self, close=True):
        self.active = False
        self.atv4player.stop()
        self.close()

    def onAction(self, action):
        addon.setSetting("is_locked", "false")
        self.clearAll()

    def start_playback(self):
        self.playindex = 0
        self.atv4player.play(self.videoplaylist[self.playindex], windowed=True)
        while self.active and not monitor.abortRequested():
            monitor.waitForAbort(1)
            if not self.atv4player.isPlaying() and self.active:
                if self.playindex < len(self.videoplaylist) - 1:
                    self.playindex += 1
                else:
                    self.playindex = 0
                self.atv4player.play(self.videoplaylist[self.playindex], windowed=True)


def run(params=False):
    if not params:
        addon.setSetting("is_locked", "true")
        screensaver = Screensaver(
            'screensaver-atv4.xml',
            addon_path,
            'default',
            '',
        )
        screensaver.doModal()
        xbmc.sleep(100)
        del screensaver

    else:
        off.offline()
