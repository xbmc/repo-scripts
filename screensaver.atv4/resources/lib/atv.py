"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import json
import threading

import xbmc
import xbmcgui

from .commonatv import translate, addon, addon_path
from .offline import offline
from .playlist import AtvPlaylist
from .trans import ScreensaverTrans

monitor = xbmc.Monitor()


class Screensaver(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        self.DPMStime = json.loads(xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"powermanagement.displaysoff"},"id":2}'))[
                            'result']['value'] * 60
        self.isDPMSactive = bool(self.DPMStime > 0)
        self.active = True
        self.atv4player = None
        self.video_playlist = AtvPlaylist().compute_playlist_array()
        xbmc.log(msg=f"kodi dpms time: {self.DPMStime}", level=xbmc.LOGDEBUG)
        xbmc.log(msg=f"kodi dpms active: {self.isDPMSactive}", level=xbmc.LOGDEBUG)

    def onInit(self):
        self.getControl(32502).setLabel(translate(32008))
        self.setProperty("screensaver-atv4-loading", "true")

        if self.video_playlist:
            self.setProperty("screensaver-atv4-loading", "false")
            self.atv4player = xbmc.Player()

            # Start player thread
            threading.Thread(target=self.start_playback).start()

            # DPMS logic
            self.max_allowed_time = None

            if self.isDPMSactive and addon.getSettingInt("check-dpms") == 1:
                self.max_allowed_time = self.DPMStime

            elif addon.getSettingInt("check-dpms") == 2:
                self.max_allowed_time = addon.getSettingInt("manual-dpms") * 60

            xbmc.log(msg=f"check dpms: {addon.getSetting('check-dpms')}",
                     level=xbmc.LOGDEBUG)
            xbmc.log(msg=f"before supervision: {self.max_allowed_time}",
                     level=xbmc.LOGDEBUG)

            if self.max_allowed_time:
                delta = 0
                while self.active:
                    if delta >= self.max_allowed_time:
                        self.activateDPMS()
                        break
                    monitor.waitForAbort(1)
                    delta += 1
        else:
            self.novideos()

    def activateDPMS(self):
        xbmc.log(msg="[Aerial Screensaver] Manually activating DPMS!", level=xbmc.LOGDEBUG)
        self.active = False

        # Take action on the video
        enable_window_placeholder = False
        if addon.getSettingInt("dpms-action") == 0:
            self.atv4player.pause()
        else:
            self.clearAll()
            enable_window_placeholder = True

        if addon.getSettingBool("toggle-displayoff") or addon.getSettingBool("toggle-cecoff"):
            monitor.waitForAbort(1)

        if addon.getSettingBool("toggle-displayoff"):
            try:
                xbmc.executebuiltin('ToggleDPMS')
            except Exception as e:
                xbmc.log(msg=f"[Aerial Screensaver] Failed to toggle DPMS: {e}",
                         level=xbmc.LOGDEBUG)

        if addon.getSetting("toggle-cecoff") == "true":
            try:
                xbmc.executebuiltin('CECStandby')
            except Exception as e:
                xbmc.log(msg=f"[Aerial Screensaver] Failed to toggle device off via CEC: {e}",
                         level=xbmc.LOGDEBUG)

        # Enable placeholder window
        if enable_window_placeholder:
            self.toTransparent()

    def novideos(self):
        self.setProperty("screensaver-atv4-loading", "false")
        self.getControl(32503).setLabel(translate(32048))
        self.getControl(32503).setVisible(True)

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
        if self.atv4player:
            self.atv4player.stop()
        self.close()

    def onAction(self, action):
        addon.setSettingBool("is_locked", False)
        self.clearAll()

    def start_playback(self):
        self.playindex = 0
        self.atv4player.play(self.video_playlist[self.playindex], windowed=True)
        while self.active and not monitor.abortRequested():
            monitor.waitForAbort(1)
            # If we finish playing the video
            if not self.atv4player.isPlaying() and self.active:
                # Increment the iterator used to access the array or reset to 0
                if self.playindex < len(self.video_playlist) - 1:
                    self.playindex += 1
                else:
                    self.playindex = 0
                # Using the updated iterator, start playing the next video
                self.atv4player.play(self.video_playlist[self.playindex], windowed=True)


def run(params=False):
    if not params:
        addon.setSettingBool("is_locked", True)
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
        # Params existed or was true when calling run(), so download files locally
        offline()
