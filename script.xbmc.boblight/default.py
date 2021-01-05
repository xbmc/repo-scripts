# -*- coding: utf-8 -*- 
'''
    Boblight for Kodi
    Copyright (C) 2012, 2020 Team XBMC, bobo1on1, Memphiz, wrtlprnft

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
'''
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os

__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__icon__       = __addon__.getAddonInfo('icon')
__ID__         = __addon__.getAddonInfo('id')
__language__   = __addon__.getLocalizedString

__profile__    = xbmcvfs.translatePath( __addon__.getAddonInfo('profile') )

from resources.lib.settings import *
from resources.lib.tools import *

log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

capture_width  = 32
capture_height = 32
settings       = settings()
capture        = xbmc.RenderCapture()

class MyPlayer( xbmc.Player ):
  def __init__(self, monitor):
    xbmc.Player.__init__( self )
    self.monitor = monitor
    self.playing = False
    log('MyPlayer - init')
        
  def onPlayBackStopped( self ):
    self.playing = False
    myPlayerChanged('stop', self.monitor)

  def onPlayBackPaused( self ):
    myPlayerChanged('paused', self.monitor)

  
  def onPlayBackEnded( self ):
    self.playing = False
    myPlayerChanged('stop', self.monitor)
  
  def onAVStarted( self ):
    self.playing = True
    myPlayerChanged('start', self.monitor)
    capture.capture(capture_width, capture_height)
  
  def isPlaying( self ):
    return self.playing

class MyMonitor( xbmc.Monitor ):
  def __init__( self, *args, **kwargs ):
    xbmc.Monitor.__init__( self )
    log('MyMonitor - init')
        
  def onSettingsChanged( self ):
    settings.start()
    if not settings.reconnect:
      check_state(self)
      
  def onScreensaverDeactivated( self ):
    settings.setScreensaver(False)
      
  def onScreensaverActivated( self ):    
    settings.setScreensaver(True)

class Main():
  def __init__( self, *args, **kwargs ):
    self.warning   = 0
  
  def connectBoblight(self):
    bob.bob_set_priority(255)
    
    if settings.hostip == None:
      log("connecting to local boblightd")
    else:
      log("connecting to boblightd %s:%s" % (settings.hostip, str(settings.hostport)))
  
    ret = bob.bob_connect(settings.hostip, settings.hostport)
  
    if not ret:
      log("connection to boblightd failed: %s" % bob.bob_geterror())
      if self.warning < 3 and settings.other_misc_notifications:
        xbmcgui.Dialog().notification(__scriptname__, localize(32500), __icon__, 750)
        self.warning += 1
      settings.reconnect = True
      settings.run_init = True
      settings.force_update = True
      return False
    else:
      self.warning = 0
      if settings.other_misc_notifications:
        xbmcgui.Dialog().notification(__scriptname__, localize(32501), __icon__, 750)
      log("connected to boblightd")
      bob.bob_set_priority(128)  
      return True
  
  def startup(self):
    platform = get_platform()
    libpath  = get_libpath(platform)
    loaded   = bob.bob_loadLibBoblight(libpath,platform)
  
    if loaded == 1:                                #libboblight not found                                               
      if platform == 'linux':
        xbmcgui.Dialog().ok(__scriptname__, localize(32504) + " " + localize(32505) + " " + localize(32506))
      
      else:
        # ask user if we should fetch the lib for osx, ios, android and windows
        if xbmcgui.Dialog().yesno(__scriptname__, localize(32504) + " " + localize(32509)):
          tools_downloadLibBoblight(platform,settings.other_misc_notifications)
          loaded = bob.bob_loadLibBoblight(libpath,platform)
      
        
    elif loaded == 2:         #no ctypes available
      xbmcgui.Dialog().ok(__scriptname__, localize(32507) + " " + localize(32508))
  
    return loaded  

def check_state(monitor):
  if xbmc.Player().isPlaying():
    state = 'start'
  else:
    state = 'stop'  
  myPlayerChanged(state, monitor)

def myPlayerChanged(state, monitor):
  log('PlayerChanged(%s)' % state)
  monitor.waitForAbort(1.0)
  if state == 'stop':
    ret = "static"
  else:
    ret = "movie"
    # Possible Videoplayer options: files, movies, episodes, musicvideos, livetv
    if xbmc.getCondVisibility("Player.HasVideo()"):
      if xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
        ret = "movie"
      elif xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)"):
        ret = "musicvideo"
      elif xbmc.getCondVisibility("VideoPlayer.Content(episodes)"):
        ret = "tvshow"
      elif xbmc.getCondVisibility("VideoPlayer.Content(livetv)"):
        ret = "livetv"
      elif xbmc.getCondVisibility("VideoPlayer.Content(files)"):
        ret = "files"

      #handle overwritten category
      if settings.overwrite_cat:                  # fix his out when other isn't
        if settings.overwrite_cat_val == 0:       # the static light anymore
          ret = "movie"
        elif settings.overwrite_cat_val == 1:
          ret = "musicvideo"
        elif settings.overwrite_cat_val == 2:
          ret = "tvshow"
        elif settings.overwrite_cat_val == 3:
          ret = "livetv"
        elif settings.overwrite_cat_val == 4:
          ret = "files"

    elif xbmc.getCondVisibility("Player.HasAudio()"):
      ret = "static"
    else:
      ret = "movie"

  settings.handleCategory(ret)
  settings.handleStereoscopic(xbmc.getInfoLabel("System.StereoscopicMode") != "0")

def run_boblight():
  main = Main()
  xbmc_monitor   = MyMonitor()
  player_monitor = MyPlayer(xbmc_monitor)
  player_monitor.playing = xbmc.Player().isPlaying()
  if main.startup() == 0:
    while not xbmc_monitor.abortRequested():
      xbmc_monitor.waitForAbort(0.1)
      if not settings.bobdisable:
        if not bob.bob_ping() or settings.reconnect:
          if not main.connectBoblight():
            continue
          if settings.bob_init():
            check_state(xbmc_monitor)
          settings.reconnect = False
          
        if not settings.staticBobActive:
          startReadOut = False
          pixels = capture.getImage(1000)
          if len(pixels) > 0 and player_monitor.isPlaying():
            startReadOut = True

          if startReadOut:
            width = capture.getWidth();
            height = capture.getHeight();

            bob.bob_setscanrange(width, height)
            rgb = (c_int * 3)()
            for y in range(height):
              row = width * y * 4
              for x in range(width):
                rgb[0] = pixels[row + x * 4 + 2]
                rgb[1] = pixels[row + x * 4 + 1]
                rgb[2] = pixels[row + x * 4]
                bob.bob_addpixelxy(x, y, byref(rgb))

            bob.bob_set_priority(128)
            if not bob.bob_sendrgb():
              log("error sending values: %s" % bob.bob_geterror())
              return   
                        
      else:
        log('boblight disabled in Addon Settings')
        bob.bob_set_priority(255)
        continue

  del main                  #cleanup
  del player_monitor
  del xbmc_monitor

def localize(id):
    return __language__(id).encode('utf-8','ignore')

if ( __name__ == "__main__" ):
  run_boblight()
  bob.bob_set_priority(255) # we are shutting down, kill the LEDs     
  bob.bob_destroy()
