# -*- coding: utf-8 -*-
'''
Unpause jumpback  for XBMC
Copyright (C) 2013-2014 Team XBMC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.
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

global g_jumpBackSecsAfterFwdPauseAfterPause
global g_jumpBackSecsAfterFwdX2
global g_jumpBackSecsAfterFwdX4
global g_jumpBackSecsAfterFwdX8
global g_jumpBackSecsAfterFwdX16
global g_jumpBackSecsAfterFwdX32
global g_jumpBackSecsAfterRwdX2
global g_jumpBackSecsAfterRwdX4
global g_jumpBackSecsAfterRwdX8
global g_jumpBackSecsAfterRwdX16
global g_jumpBackSecsAfterRwdX32
global g_jumpBackSecsAfterResume
global g_lastPlaybackSpeed
global g_waitForJumpback
g_jumpBackSecsAfterFwdPause = 0
g_waitForJumpback = 0
g_lastPlaybackSpeed = 1

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

# helper function to get string type from settings
def getSetting(setting):
	return __addon__.getSetting(setting).strip()

# helper function to get bool type from settings
def getSettingAsBool(setting):
	return getSetting(setting).lower() == "true"

# check exclusion settings for filename passed as argument
def isExcluded(fullpath):

	if not fullpath:
		return True

	log("isExcluded(): Checking exclusion settings for '%s'." % fullpath)

	if (fullpath.find("pvr://") > -1) and getSettingAsBool('ExcludeLiveTV'):
		log("isExcluded(): Video is playing via Live TV, which is currently set as excluded location.")
		return True

	if (fullpath.find("http://") > -1) and getSettingAsBool('ExcludeHTTP'):
		log("isExcluded(): Video is playing via HTTP source, which is currently set as excluded location.")
		return True

	ExcludePath = getSetting('ExcludePath')
	if ExcludePath and getSettingAsBool('ExcludePathOption'):
		if (fullpath.find(ExcludePath) > -1):
			log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 1." % ExcludePath)
			return True

	ExcludePath2 = getSetting('ExcludePath2')
	if ExcludePath2 and getSettingAsBool('ExcludePathOption2'):
		if (fullpath.find(ExcludePath2) > -1):
			log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 2." % ExcludePath2)
			return True

	ExcludePath3 = getSetting('ExcludePath3')
	if ExcludePath3 and getSettingAsBool('ExcludePathOption3'):
		if (fullpath.find(ExcludePath3) > -1):
			log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 3." % ExcludePath3)
			return True

	return False

def loadSettings():
  global g_jumpBackSecsAfterFwdPause
  global g_waitForJumpback
  global g_jumpBackSecsAfterFwdX2
  global g_jumpBackSecsAfterFwdX4
  global g_jumpBackSecsAfterFwdX8
  global g_jumpBackSecsAfterFwdX16
  global g_jumpBackSecsAfterFwdX32
  global g_jumpBackSecsAfterRwdX2
  global g_jumpBackSecsAfterRwdX4
  global g_jumpBackSecsAfterRwdX8
  global g_jumpBackSecsAfterRwdX16
  global g_jumpBackSecsAfterRwdX32

  g_jumpBackSecsAfterFwdPause = int(float(__addon__.getSetting("jumpbacksecs")))
  g_jumpBackSecsAfterFwdX2 = int(float(__addon__.getSetting("jumpbacksecsfwdx2")))
  g_jumpBackSecsAfterFwdX4 = int(float(__addon__.getSetting("jumpbacksecsfwdx4")))
  g_jumpBackSecsAfterFwdX8 = int(float(__addon__.getSetting("jumpbacksecsfwdx8")))
  g_jumpBackSecsAfterFwdX16 = int(float(__addon__.getSetting("jumpbacksecsfwdx16")))
  g_jumpBackSecsAfterFwdX32 = int(float(__addon__.getSetting("jumpbacksecsfwdx32")))
  g_jumpBackSecsAfterRwdX2 = int(float(__addon__.getSetting("jumpbacksecsrwdx2")))
  g_jumpBackSecsAfterRwdX4 = int(float(__addon__.getSetting("jumpbacksecsrwdx4")))
  g_jumpBackSecsAfterRwdX8 = int(float(__addon__.getSetting("jumpbacksecsrwdx8")))
  g_jumpBackSecsAfterRwdX16 = int(float(__addon__.getSetting("jumpbacksecsrwdx16")))
  g_jumpBackSecsAfterRwdX32 = int(float(__addon__.getSetting("jumpbacksecsrwdx32")))
  g_waitForJumpback = int(float(__addon__.getSetting("waitforjumpback")))
  log('Settings loaded! JumpBackSecs: %d, WaitSecs: %d' % (g_jumpBackSecsAfterFwdPause, g_waitForJumpback))

class MyPlayer( xbmc.Player ):
  def __init__( self, *args, **kwargs ):
    xbmc.Player.__init__( self )
    log('MyPlayer - init')
    
  def onPlayBackPaused( self ):
    global g_jumpBackSecsAfterFwdPause
    global g_waitForJumpback

    if self.isPlayingVideo():
      _filename = self.getPlayingFile()
      if isExcluded(_filename):
        log("Playback paused - ignoring because '%s' is in exclusion settings." % _filename)
      elif g_jumpBackSecsAfterFwdPause > 0 and self.getTime() > g_jumpBackSecsAfterFwdPause:
        percentage = (self.getTime() - g_jumpBackSecsAfterFwdPause) / self.getTotalTime() * 100
        log('Playback paused, setting up alarm clock - getTime()=%f getTotalTime()=%f g_jumpBackSecsAfterFwdPause=%d percentage=%f' % (self.getTime(), self.getTotalTime(), g_jumpBackSecsAfterFwdPause, percentage))
        xbmc.executebuiltin('AlarmClock(JumpbackPaused, PlayerControl(SeekPercentage(%f)), 0:%d, silent)' % (percentage, g_waitForJumpback))

  def onPlayBackSpeedChanged( self, speed ):
    global g_lastPlaybackSpeed

    if speed == 1: #normal playback speed reached
      direction = 1
      absLastSpeed = abs(g_lastPlaybackSpeed)
      if g_lastPlaybackSpeed < 0:
        log('Resuming. Was rewinded with speed X%d.' % (abs(g_lastPlaybackSpeed)))
      if g_lastPlaybackSpeed > 1:
        direction = -1
        log('Resuming. Was forwarded with speed X%d.' % (abs(g_lastPlaybackSpeed)))
      #handle jumpafter fwd/rwd (humpback after fwd, jump forward after red)
      if direction == -1: #fwd
        if absLastSpeed == 2:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX2 * direction
        elif absLastSpeed == 4:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX4 * direction
        elif absLastSpeed == 8:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX8 * direction
        elif absLastSpeed == 16:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX16 * direction
        elif absLastSpeed == 32:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterFwdX32 * direction
      else: #rwd
        if absLastSpeed == 2:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX2 * direction
        elif absLastSpeed == 4:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX4 * direction
        elif absLastSpeed == 8:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX8 * direction
        elif absLastSpeed == 16:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX16 * direction
        elif absLastSpeed == 32:
          resumeTime = xbmc.Player().getTime() + g_jumpBackSecsAfterRwdX32 * direction
      
      if absLastSpeed != 1: #we really fwd'ed or rwd'ed
        xbmc.Player().seekTime(resumeTime) # do the jump

    g_lastPlaybackSpeed = speed

  def onPlayBackResumed( self ):
    log('Cancelling alarm - playback either resumed or stopped by the user')
    xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')

  # We don't care if playback was resumed or stopped, we just want to know when we're no longer paused
  onPlayBackStopped = onPlayBackResumed

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

