'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi

    InfoLabel handling
    Copyright (C) 2012-2018 Daniel 'herrnst' Scheller

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import time

import xbmc
import xbmcgui

from .common import WINDOW_IDS
from .settings import *

class InfoLabels():

    ########
    # ctor
    def __init__(self, settings):
        # take note of Settings instance
        self._settings = settings

        # init members
        self._nav_oldmenu = ""
        self._nav_oldsubmenu = ""
        self._navtimer = time.time()

        # pre-py3 compat
        self._py2compat = False
        if sys.version_info.major < 3:
            self._py2compat = True

    def GetInfoLabel(self, strLabel):
        ret = xbmc.getInfoLabel(strLabel)
        # pre-py3 compat
        if self._py2compat:
            return ret.decode("utf-8")
        return ret

    def GetBool(self, strBool):
        return xbmc.getCondVisibility(strBool)

    def GetActiveWindowID(self):
        return int(xbmcgui.getCurrentWindowId())

    def timeToSecs(self, timeAr):
    # initialise return
        currentSecs = 0

        arLen = len(timeAr)
        if arLen == 1:
            currentSecs = int(timeAr[0])
        elif arLen == 2:
            currentSecs = int(timeAr[0]) * 60 + int(timeAr[1])
        elif arLen == 3:
            currentSecs = int(timeAr[0]) * 60 * 60 + int(timeAr[1]) * 60 + int(timeAr[2])

        return currentSecs

    def WindowIsActive(self, WindowID):
        return self.GetBool("Window.IsActive(" + str(WindowID) + ")")

    def PlayingVideo(self):
        return self.GetBool("Player.HasVideo")

    def PlayingTVShow(self):
        if self.PlayingVideo() and len(self.GetInfoLabel("VideoPlayer.TVShowTitle")):
            return True

        return False

    def PlayingAudio(self):
        return self.GetBool("Player.HasAudio")

    def PlayingLiveTV(self):
        return self.GetBool("PVR.IsPlayingTV")

    def PlayingLiveRadio(self):
        return self.GetBool("PVR.IsPlayingRadio")

    def GetSystemTime(self):
        # apply some split magic for 12h format here, as "hh:mm:ss"
        # makes up for format guessing inside XBMC - fix for post-frodo at
        # https://github.com/xbmc/xbmc/pull/2321
        ret = "0" + self.GetInfoLabel("System.Time(hh:mm:ss)").split(" ")[0]
        return ret[-8:]

    def GetPlayerTime(self):
        if self.PlayingLiveTV() or self.PlayingLiveRadio():
            return self.GetInfoLabel("PVR.EpgEventElapsedTime")

        return self.GetInfoLabel("Player.Time")

    def GetPlayerDuration(self):
        if self.PlayingLiveTV() or self.PlayingLiveRadio():
            return self.GetInfoLabel("PVR.EpgEventDuration")

        return self.GetInfoLabel("Player.Duration")

    def IsPlayerPlaying(self):
        return self.GetBool("Player.HasMedia")

    def IsPlayerPaused(self):
        return self.GetBool("Player.Paused")

    def IsPlayerForwarding(self):
        return self.GetBool("Player.Forwarding")

    def IsPlayerRewinding(self):
        return self.GetBool("Player.Rewinding")

    def IsInternetStream(self):
        return self.GetBool("Player.IsInternetStream")

    def IsPassthroughAudio(self):
        return self.GetBool("Player.Passthrough")

    def IsPVRRecording(self):
        return self.GetBool("PVR.IsRecording")

    def IsPlaylistRandom(self):
        return self.GetBool("Playlist.IsRandom")

    def IsPlaylistRepeatAll(self):
        return self.GetBool("Playlist.IsRepeat")

    def IsPlaylistRepeatOne(self):
        return self.GetBool("Playlist.IsRepeatOne")

    def IsPlaylistRepeatAny(self):
        return (self.IsPlaylistRepeatAll() | self.IsPlaylistRepeatOne())

    def IsDiscInDrive(self):
        return self.GetBool("System.HasMediaDVD")

    def IsScreenSaverActive(self):
        return self.GetBool("System.ScreenSaverActive")

    def IsMuted(self):
        return self.GetBool("Player.Muted")

    def GetVolumePercent(self):
        volumedb = float(self.GetInfoLabel("Player.Volume").replace(",", ".").replace(" dB", ""))
        return (100 * (60.0 + volumedb) / 60)

    def GetPlayerTimeSecs(self):
        currentTimeAr = self.GetPlayerTime().split(":")
        if currentTimeAr[0] == "":
            return 0

        return self.timeToSecs(currentTimeAr)

    def GetPlayerDurationSecs(self):
        currentDurationAr = self.GetPlayerDuration().split(":")
        if currentDurationAr[0] == "":
            return 0

        return self.timeToSecs(currentDurationAr)

    def GetProgressPercent(self):
        tCurrent = self.GetPlayerTimeSecs()
        tTotal = self.GetPlayerDurationSecs()

        if float(tTotal) == 0.0:
            return 0

        return float(tCurrent)/float(tTotal)

    def IsNavigationActive(self):
        ret = False

        navtimeout = self._settings.getNavTimeout()
        menu = self.GetInfoLabel("$INFO[System.CurrentWindow]")
        subMenu = self.GetInfoLabel("$INFO[System.CurrentControl]")

        if menu != self._nav_oldmenu or subMenu != self._nav_oldsubmenu or (self._navtimer + navtimeout) > time.time():
            ret = True
            if menu != self._nav_oldmenu or subMenu != self._nav_oldsubmenu:
                self._navtimer = time.time()
            self._nav_oldmenu = menu
            self._nav_oldsubmenu = subMenu

        return ret

    def IsWindowIDPVR(self, iWindowID):
        if iWindowID >= WINDOW_IDS.WINDOW_PVR and iWindowID <= WINDOW_IDS.WINDOW_PVR_MAX:
            return True

        return False

    def IsWindowIDVideo(self, iWindowID):
        if iWindowID in [WINDOW_IDS.WINDOW_VIDEO_NAV, WINDOW_IDS.WINDOW_VIDEO_PLAYLIST]:
            return True

        return False

    def IsWindowIDMusic(self, iWindowID):
        if iWindowID in [WINDOW_IDS.WINDOW_MUSIC_PLAYLIST, WINDOW_IDS.WINDOW_MUSIC_NAV,
                         WINDOW_IDS.WINDOW_MUSIC_PLAYLIST_EDITOR]:
            return True

        return False

    def IsWindowIDPictures(self, iWindowID):
        if iWindowID == WINDOW_IDS.WINDOW_PICTURES:
            return True

        return False

    def IsWindowIDWeather(self, iWindowID):
        if iWindowID == WINDOW_IDS.WINDOW_WEATHER:
            return True

        return False
