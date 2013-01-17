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
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''
import xbmc
import xbmcaddon
import xbmcgui
import os
from time import time

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString

__profile__ = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

global g_jumpBackSecs
global g_pausedTime
global g_waitForJumpback
g_jumpBackSecs = 0
g_pausedTime = 0
g_waitForJumpback = 0

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

def loadSettings():
  global g_jumpBackSecs
  global g_waitForJumpback
  g_jumpBackSecs = int(float(__addon__.getSetting("jumpbacksecs")))
  g_waitForJumpback = int(float(__addon__.getSetting("waitforjumpback")))
  log('Settings loaded! JumpBackSecs: %d, WaitSecs: %d' % (g_jumpBackSecs, g_waitForJumpback))

class MyPlayer( xbmc.Player ):
  def __init__( self, *args, **kwargs ):
    xbmc.Player.__init__( self )
    log('MyPlayer - init')
    
  def onPlayBackPaused( self ):
    global g_pausedTime
    g_pausedTime = time()
    log('Paused. Time: %d' % g_pausedTime)
  
  def onPlayBackResumed( self ):
    global g_jumpBackSecs
    global g_pausedTime
    global g_waitForJumpback
    log('Resuming. Was paused for %d seconds.' % (time() - g_pausedTime))
    if g_jumpBackSecs != 0 and xbmc.Player().isPlayingVideo() and xbmc.Player().getTime() > g_jumpBackSecs and g_pausedTime > 0 and (time() - g_pausedTime) > g_waitForJumpback:
      resumeTime = xbmc.Player().getTime() - g_jumpBackSecs
      xbmc.Player().seekTime(resumeTime)
      log( 'Resumed with %ds jumpback' % g_jumpBackSecs )
      
    g_pausedTime = 0
try:
  class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
      xbmc.Monitor.__init__( self )
      log('MyMonitor - init')
        
    def onSettingsChanged( self ):
      loadSettings()

  xbmc_monitor = MyMonitor()
except:
  log('Using Eden API - you need to restart addon for changing settings')    

player_monitor = MyPlayer()
loadSettings()

while not xbmc.abortRequested:
  xbmc.sleep(100)
