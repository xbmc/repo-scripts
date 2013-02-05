'''
    XBMC LCDproc addon
    Copyright (C) 2012 Team XBMC
    
    InfoLabel handling
    Copyright (C) 2012 Daniel 'herrnst' Scheller
    
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

import os
import string
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

# wonder why "from settings import *" does not work...
__settingshandler__ = sys.modules[ "settings" ]

# enum snippet from http://stackoverflow.com/a/1695250 - thanks!
def enum(*sequential, **named):
  enums = dict(zip(sequential, range(len(sequential))), **named)
  return type('Enum', (), enums)

# interesting XBMC GUI Window IDs (no defines seem to exist for this)
class WINDOW_IDS:
  WINDOW_WEATHER               = 12600
  WINDOW_PVR                   = 10601
  WINDOW_PVR_MAX               = 10699
  WINDOW_VIDEOS                = 10006
  WINDOW_VIDEO_FILES           = 10024
  WINDOW_VIDEO_NAV             = 10025
  WINDOW_VIDEO_PLAYLIST        = 10028
  WINDOW_MUSIC                 = 10005
  WINDOW_MUSIC_PLAYLIST        = 10500
  WINDOW_MUSIC_FILES           = 10501
  WINDOW_MUSIC_NAV             = 10502
  WINDOW_MUSIC_PLAYLIST_EDITOR = 10503
  WINDOW_PICTURES              = 10002
  WINDOW_DIALOG_VOLUME_BAR     = 10104
  WINDOW_DIALOG_KAI_TOAST      = 10107
  
global g_InfoLabel_oldMenu
global g_InfoLabel_oldSubMenu
global g_InfoLabel_navTimer

def InfoLabel_Initialize():
  global g_InfoLabel_oldMenu
  global g_InfoLabel_oldSubMenu
  global g_InfoLabel_navTimer

  g_InfoLabel_oldMenu = ""
  g_InfoLabel_oldSubMenu = ""
  g_InfoLabel_navTimer = time.time()

def InfoLabel_timeToSecs(timeAr):
  arLen = len(timeAr)
  if arLen == 1:
    currentSecs = int(timeAr[0])
  elif arLen == 2:
    currentSecs = int(timeAr[0]) * 60 + int(timeAr[1])
  elif arLen == 3:
    currentSecs = int(timeAr[0]) * 60 * 60 + int(timeAr[1]) * 60 + int(timeAr[2])
  return currentSecs

def InfoLabel_WindowIsActive(WindowID):
  return xbmc.getCondVisibility("Window.IsActive(" + str(WindowID) + ")")

def InfoLabel_PlayingVideo():
  return xbmc.getCondVisibility("Player.HasVideo")

def InfoLabel_PlayingAudio():
  return xbmc.getCondVisibility("Player.HasAudio")

def InfoLabel_PlayingLiveTV():
  return xbmc.getCondVisibility("PVR.IsPlayingTV")

def InfoLabel_PlayingLiveRadio():
  return xbmc.getCondVisibility("PVR.IsPlayingRadio")

def InfoLabel_GetPlayerTime():
  return xbmc.getInfoLabel("Player.Time")

def InfoLabel_GetPlayerDuration():
  return xbmc.getInfoLabel("Player.Duration")

def InfoLabel_GetActiveWindowID():
  return int(xbmcgui.getCurrentWindowId())

def InfoLabel_IsPlayerPlaying():
  return xbmc.getCondVisibility("Player.Playing")

def InfoLabel_IsPlayerPaused():
  return xbmc.getCondVisibility("Player.Paused")

def InfoLabel_IsPlayerForwarding():
  return xbmc.getCondVisibility("Player.Forwarding")

def InfoLabel_IsPlayerRewinding():
  return xbmc.getCondVisibility("Player.Rewinding")

def InfoLabel_IsPlayingAny():
  return (InfoLabel_IsPlayerPlaying() |
          InfoLabel_IsPlayerPaused() |
          InfoLabel_IsPlayerForwarding() |
          InfoLabel_IsPlayerRewinding())

def InfoLabel_IsPassthroughAudio():
  return xbmc.getCondVisibility("Player.Passthrough")

def InfoLabel_IsPVRRecording():
  return xbmc.getCondVisibility("PVR.IsRecording")

def InfoLabel_IsPlaylistRandom():
  return xbmc.getCondVisibility("Playlist.IsRandom")

def InfoLabel_IsPlaylistRepeatAll():
  return xbmc.getCondVisibility("Playlist.IsRepeat")

def InfoLabel_IsPlaylistRepeatOne():
  return xbmc.getCondVisibility("Playlist.IsRepeatOne")

def InfoLabel_IsPlaylistRepeatAny():
  return (InfoLabel_IsPlaylistRepeatAll() | InfoLabel_IsPlaylistRepeatOne())

def InfoLabel_IsDiscInDrive():
  return xbmc.getCondVisibility("System.HasMediaDVD")

def InfoLabel_IsScreenSaverActive():
  return xbmc.getCondVisibility("System.ScreenSaverActive")

def InfoLabel_GetInfoLabel(strLabel):
  return xbmc.getInfoLabel(strLabel)

def InfoLabel_GetVolumePercent():
  volumedb = float(string.replace(string.replace(xbmc.getInfoLabel("Player.Volume"), ",", "."), " dB", ""))
  return (100 * (60.0 + volumedb) / 60)

def InfoLabel_GetPlayerTimeSecs():
  currentTimeAr = InfoLabel_GetPlayerTime().split(":")
  if currentTimeAr[0] == "":
    return 0

  return InfoLabel_timeToSecs(currentTimeAr)

def InfoLabel_GetPlayerDurationSecs():
  currentDurationAr = InfoLabel_GetPlayerDuration().split(":")
  if currentDurationAr[0] == "":
    return 0

  return InfoLabel_timeToSecs(currentDurationAr)

def InfoLabel_GetProgressPercent():
  tCurrent = InfoLabel_GetPlayerTimeSecs()
  tTotal = InfoLabel_GetPlayerDurationSecs()

  if float(tTotal) == 0.0:
    return 0

  return float(tCurrent)/float(tTotal)

def InfoLabel_IsNavigationActive():
  global g_InfoLabel_oldMenu
  global g_InfoLabel_oldSubMenu
  global g_InfoLabel_navTimer

  #from settings import settings_getNavTimeout

  ret = False

  navtimeout = __settingshandler__.settings_getNavTimeout()
  menu = InfoLabel_GetInfoLabel("$INFO[System.CurrentWindow]")
  subMenu = InfoLabel_GetInfoLabel("$INFO[System.CurrentControl]")

  if menu != g_InfoLabel_oldMenu or subMenu != g_InfoLabel_oldSubMenu or (g_InfoLabel_navTimer + navtimeout) > time.time():
    ret = True
    if menu != g_InfoLabel_oldMenu or subMenu != g_InfoLabel_oldSubMenu:
      g_InfoLabel_navTimer = time.time()      
    g_InfoLabel_oldMenu = menu
    g_InfoLabel_oldSubMenu = subMenu

  return ret

def InfoLabel_IsWindowIDPVR(iWindowID):
  if iWindowID >= WINDOW_IDS.WINDOW_PVR and iWindowID <= WINDOW_IDS.WINDOW_PVR_MAX:
    return True

  return False

def InfoLabel_IsWindowIDVideo(iWindowID):
  if iWindowID in [WINDOW_IDS.WINDOW_VIDEOS, WINDOW_IDS.WINDOW_VIDEO_FILES,
                   WINDOW_IDS.WINDOW_VIDEO_NAV, WINDOW_IDS.WINDOW_VIDEO_PLAYLIST]:
    return True

  return False

def InfoLabel_IsWindowIDMusic(iWindowID):
  if iWindowID in [WINDOW_IDS.WINDOW_MUSIC, WINDOW_IDS.WINDOW_MUSIC_PLAYLIST,
                   WINDOW_IDS.WINDOW_MUSIC_FILES, WINDOW_IDS.WINDOW_MUSIC_NAV,
                   WINDOW_IDS.WINDOW_MUSIC_PLAYLIST_EDITOR]:
    return True

  return False

def InfoLabel_IsWindowIDPictures(iWindowID):
  if iWindowID == WINDOW_IDS.WINDOW_PICTURES:
    return True

  return False

def InfoLabel_IsWindowIDWeather(iWindowID):
  if iWindowID == WINDOW_IDS.WINDOW_WEATHER:
    return True

  return False
