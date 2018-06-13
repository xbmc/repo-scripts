'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi
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

# base imports
import time

# Kodi imports
import xbmc
import xbmcgui

from resources.lib.common import *
from resources.lib.settings import *
from resources.lib.lcdproc import *
from resources.lib.infolabels import *

global g_failedConnectionNotified
global g_initialConnectAttempt
global g_lcdproc

global g_xbmcMonitor

def initGlobals():
  global g_failedConnectionNotified
  global g_initialConnectAttempt
  global g_lcdproc
  global g_xbmcMonitor

  g_failedConnectionNotified = False
  g_initialConnectAttempt = True

  g_xbmcMonitor = xbmc.Monitor()

  settings_initGlobals()
  g_lcdproc = LCDProc()

  InfoLabel_Initialize()

# handle dispay of connection notificaiton popups
def HandleConnectionNotification(bConnectSuccess):
  global g_failedConnectionNotified
  global g_initialConnectAttempt

  if not bConnectSuccess:
    if not g_failedConnectionNotified:
      g_failedConnectionNotified = True
      g_initialConnectAttempt = False
      text = KODI_ADDON_SETTINGS.getLocalizedString(32500)
      xbmcgui.Dialog().notification(KODI_ADDON_NAME, text, KODI_ADDON_ICON)
  else:
    text = KODI_ADDON_SETTINGS.getLocalizedString(32501)
    if not g_initialConnectAttempt:
      xbmcgui.Dialog().notification(KODI_ADDON_NAME, text, KODI_ADDON_ICON)
      g_failedConnectionNotified = True

# returns mode identifier based on currently playing media/active navigation
def getLcdMode():
  ret = LCD_MODE.LCD_MODE_GENERAL

  navActive = InfoLabel_IsNavigationActive()
  screenSaver = InfoLabel_IsScreenSaverActive()
  playingVideo = InfoLabel_PlayingVideo()
  playingTVShow = InfoLabel_PlayingTVShow()
  playingMusic = InfoLabel_PlayingAudio()
  playingPVRTV = InfoLabel_PlayingLiveTV()
  playingPVRRadio = InfoLabel_PlayingLiveRadio()

  if navActive:
    ret = LCD_MODE.LCD_MODE_NAVIGATION
  elif screenSaver:
    ret = LCD_MODE.LCD_MODE_SCREENSAVER
  elif playingPVRTV:
    ret = LCD_MODE.LCD_MODE_PVRTV
  elif playingPVRRadio:
    ret = LCD_MODE.LCD_MODE_PVRRADIO
  elif playingTVShow:
    ret = LCD_MODE.LCD_MODE_TVSHOW
  elif playingVideo:
    ret = LCD_MODE.LCD_MODE_VIDEO
  elif playingMusic:
    ret = LCD_MODE.LCD_MODE_MUSIC

  return ret

def process_lcd():
  global g_xbmcMonitor

  while not g_xbmcMonitor.abortRequested():
    if handleConnectLCD():
      settingsChanged = settings_didSettingsChange()

      if settingsChanged:
        g_lcdproc.UpdateGUISettings()

      g_lcdproc.Render(getLcdMode(), settingsChanged)

    time.sleep(1.0 / float(settings_getRefreshRate())) # refresh after configured rate

  g_lcdproc.Shutdown()

def handleConnectLCD():
  global g_xbmcMonitor

  ret = True

  # make sure not to block things when shutdown is requested
  if not g_xbmcMonitor.abortRequested():
    #check for new settings
    if settings_checkForNewSettings() or not g_lcdproc.IsConnected():    #networksettings changed?
      g_failedConnectionNotified = False  #reset notification flag

      ret = g_lcdproc.Initialize()
      if not settings_getHideConnPopups():
        HandleConnectionNotification(ret)

  return ret

######
# main()
def main():
  # init vars and classes
  initGlobals()

  # initialise and load GUI settings
  settings_setup()

  # do LCD processing loop (needs to catch xbmc.Monitor().abortRequested() !)
  process_lcd()

######
# script entry point
if __name__ == "__main__":
  main()
