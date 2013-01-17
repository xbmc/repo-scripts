# -*- coding: utf-8 -*- 
'''
    Boblight for XBMC
    Copyright (C) 2012 Team XBMC

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
import os

__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__icon__       = __addon__.getAddonInfo('icon')
__ID__         = __addon__.getAddonInfo('id')
__language__   = __addon__.getLocalizedString

__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

from settings import *
from tools import *

log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

capture_width  = 32
capture_height = 32
settings       = settings()

class MyPlayer( xbmc.Player ):
  def __init__( self, *args, **kwargs ):
    xbmc.Player.__init__( self )
    log('MyPlayer - init')
        
  def onPlayBackStopped( self ):
    myPlayerChanged( 'stop' )
  
  def onPlayBackEnded( self ):
    myPlayerChanged( 'stop' )     
  
  def onPlayBackStarted( self ):
    myPlayerChanged( 'start' )

class MyMonitor( xbmc.Monitor ):
  def __init__( self, *args, **kwargs ):
    xbmc.Monitor.__init__( self )
    log('MyMonitor - init')
        
  def onSettingsChanged( self ):
    settings.start()
    if not settings.reconnect:
      check_state()
      
  def onScreensaverDeactivated( self ):
    settings.screensaver = False
    settings.handleStaticBgSettings()
      
  def onScreensaverActivated( self ):    
    settings.screensaver = True
    settings.handleStaticBgSettings()

class Main():
  def __init__( self, *args, **kwargs ):
    self.warning   = 0
  
  def connectBoblight(self, force_warning):
    if force_warning:
      self.warning = 0
    
    bob.bob_set_priority(255)
    
    if settings.hostip == None:
      log("connecting to local boblightd")
    else:
      log("connecting to boblightd %s:%s" % (settings.hostip, str(settings.hostport)))
  
    ret = bob.bob_connect(settings.hostip, settings.hostport)
  
    if not ret:
      log("connection to boblightd failed: %s" % bob.bob_geterror())
      text = __language__(500)
      if self.warning < 3 and settings.other_misc_notifications:
        xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,750,__icon__))
        self.warning += 1
      return False
    else:
      self.warning = 0
      if settings.other_misc_notifications:
        text = __language__(501)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,750,__icon__))
      log("connected to boblightd")
      bob.bob_set_priority(128)  
      return True
  
  def startup(self):
    platform = get_platform()
    libpath  = get_libpath(platform)
    loaded   = bob.bob_loadLibBoblight(libpath,platform)
  
    if loaded == 1:                                #libboblight not found                                               
      if platform == 'linux':
        t1 = __language__(504)
        t2 = __language__(505)
        t3 = __language__(506)
        xbmcgui.Dialog().ok(__scriptname__,t1,t2,t3)
      
      else:                                        # ask user if we should fetch the
        t1 = __language__(504)                     # lib for osx, ios and windows
        t2 = __language__(509)
        if xbmcgui.Dialog().yesno(__scriptname__,t1,t2):
          tools_downloadLibBoblight(platform,settings.other_misc_notifications)
          loaded = bob.bob_loadLibBoblight(libpath,platform)
      
        
    elif loaded == 2:         #no ctypes available
      t1 = __language__(507)
      t2 = __language__(508)
      xbmcgui.Dialog().ok(__scriptname__,t1,t2)
  
    return loaded  

def check_state(): 
  if xbmc.Player().isPlaying():
    state = 'start'
  else:
    state = 'stop'  
  myPlayerChanged( state )    

def myPlayerChanged(state):
  log('PlayerChanged(%s)' % state)
  xbmc.sleep(100)
  if state == 'stop':
    ret = "static"
  else:
    if xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)"):
      ret = "musicvideo"
    elif xbmc.getCondVisibility("Player.HasAudio()"):
      ret = "static"
    else:
      ret = "movie"  
  
    if settings.overwrite_cat:                  # fix his out when other isn't
      if settings.overwrite_cat_val == 0:       # the static light anymore
        ret = "movie"
      else:
        ret = "musicvideo"
  settings.handleCategory(ret)


def run_boblight():
  main = Main()
  xbmc_monitor   = MyMonitor()
  player_monitor = MyPlayer()
  if main.startup() == 0:
    capture        = xbmc.RenderCapture()
    capture.capture(capture_width, capture_height, xbmc.CAPTURE_FLAG_CONTINUOUS)
    while not xbmc.abortRequested:
      xbmc.sleep(100)
      if not settings.bobdisable:
        if not bob.bob_ping() or settings.reconnect:
          if main.connectBoblight(settings.reconnect):
            if settings.bob_init():
              check_state()
          settings.reconnect = False        
          
        if not settings.staticBobActive:
          capture.waitForCaptureStateChangeEvent(1000)
          if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
            bob.bob_set_priority(128)
            width = capture.getWidth();
            height = capture.getHeight();
            pixels = capture.getImage();
            bob.bob_setscanrange(width, height)
            rgb = (c_int * 3)()
            for y in range(height):
              row = width * y * 4
              for x in range(width):
                rgb[0] = pixels[row + x * 4 + 2]
                rgb[1] = pixels[row + x * 4 + 1]
                rgb[2] = pixels[row + x * 4]
                bob.bob_addpixelxy(x, y, byref(rgb))
            
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

if ( __name__ == "__main__" ):
  run_boblight()
  bob.bob_set_priority(255) # we are shutting down, kill the LEDs     
  bob.bob_destroy()


