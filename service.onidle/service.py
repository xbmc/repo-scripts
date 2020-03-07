#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of OnIdle
#
# OnIdle is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnIdle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnIdle.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
import time, traceback, json
import xbmc, xbmcgui, xbmcaddon

# Plugin Info
ADDON_ID            = 'service.onidle'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString
DEBUG               = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

USER_MANUAL_RUN     = REAL_SETTINGS.getSetting('Manual_Run') == 'true'
USER_IDLE           = int(REAL_SETTINGS.getSetting('User_Idle_Min'))
USER_COUNTDOWN      = int(REAL_SETTINGS.getSetting('User_Countdown_Sec'))
USER_IGNORE_MUSIC   = REAL_SETTINGS.getSetting('Ignore_Music') == "true"
USER_SOFT_MUTE      = REAL_SETTINGS.getSetting('Soft_Mute') == "true"
USER_DEFINED_ACTION = REAL_SETTINGS.getSetting('User_Action')
USER_EXIT_ACTION    = {0:'ActivateScreensaver',
                       1:'Quit',
                       2:'ShutDown',
                       3:'Suspend',
                       4:'Hibernate',
                       5:'CECStandby',
                       6:'CECToggleState',
                       7:USER_DEFINED_ACTION}[int(REAL_SETTINGS.getSetting('User_Exit_Action') or '0')]
                       # https://kodi.wiki/view/List_of_built-in_functions
try:
  basestring      #py2
except NameError: #py3
  basestring = str
  unicode = str
  
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%(uni(msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,uni(msg)),level)
    
def uni(string, encoding='utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding)
        else: string = string.encode('ascii', 'ignore')
    return string

def getProperty(key, id=10000):
    try: 
        key = '%s.%s'%(ADDON_NAME,key)
        value = xbmcgui.Window(id).getProperty(key)
        if value: log("getProperty, key = " + key + ", value = " + value)
        return value
    except Exception as e: return ''
          
def setProperty(key, value, id=10000):
    key = '%s.%s'%(ADDON_NAME,key)
    if not isinstance(value, basestring): value = str(value)
    log("setProperty, key = " + key + ", value = " + value)
    try: xbmcgui.Window(id).setProperty(key, value)
    except Exception as e: log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(key, id=10000):
    key = '%s.%s'%(ADDON_NAME,key)
    xbmcgui.Window(id).clearProperty(key)
    
def getIdle(min=True):
    idleTime = xbmc.getGlobalIdleTime()
    if min: return int(idleTime)/60
    return idleTime
    
def getTime():
    return time.time()

def getVol():
    response = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume"] }, "id": 1}'))
    if response and "result" in response: return response.get("result",{}).get("volume",None)
    return None

def getIdleTime():
    return (getProperty('USER_IDLE') or USER_IDLE)

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.activeScreensaver = False
        
        
    def onScreensaverActivated(self):
        log('onScreensaverActivated')
        self.activeScreensaver = True
        
        
    def onScreensaverDeactivated(self):
        log('onScreensaverDeactivated')
        self.activeScreensaver = False


class Service(object):
    def __init__(self):
        self.myMonitor = Monitor()
        self.myPlayer  = Player()
        self.myMonitor.myService = self
        self.myPlayer.myService  = self
        
        
    def softMute(self, curVol):
        log('softMute')
        if USER_SOFT_MUTE:
            muteVol = 10
            for i in range(curVol - 1, muteVol - 1, -1):
                xbmc.executebuiltin('SetVolume(%d,showVolumeBar)' % (i))
                xbmc.sleep(500)
        return True
        
        
    def checkShutdown(self, idleTime):
        log('checkShutdown')
        if USER_IGNORE_MUSIC and self.myPlayer.isPlayingAudio(): return False
        diaProgress = xbmcgui.DialogProgress()
        diaProgress.create(ADDON_NAME,LANGUAGE(32017))
        secs        = 0
        percent     = 0
        increment   = 100*100 / USER_COUNTDOWN
        while not self.myMonitor.abortRequested() and secs < USER_COUNTDOWN:
            if (diaProgress.iscanceled() or (idleTime > getIdle())): return False
            secs     = secs + 1
            percent  = int(increment*secs/100)
            waitTime = (USER_COUNTDOWN - secs)
            diaProgress.update(percent,LANGUAGE(32018),LANGUAGE(32019)%(waitTime))
            xbmc.sleep(1000)
        diaProgress.close()
        return True


    def startShutdown(self):
        log('startShutdown')
        curVol = getVol()
        if self.softMute(curVol): self.myPlayer.stop()
        while self.myPlayer.isPlaying():
            if self.myMonitor.waitForAbort(1): break
        xbmc.executebuiltin('SetVolume(%d,showVolumeBar)' % (curVol))
        clearProperty('USER_IDLE')
        xbmc.executebuiltin(USER_EXIT_ACTION)
        
        
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(5): break
            if not self.myPlayer.isPlaying() or self.myMonitor.activeScreensaver: continue #ignore when not playing or during screensaver.
            idleTime = getIdle()
            if idleTime >= getIdleTime():
                if self.checkShutdown(idleTime): self.startShutdown()
                else: continue
                    
                    
    # def run(self):
        # if not USER_MANUAL_RUN: 
        
if __name__ == '__main__': Service().startService()