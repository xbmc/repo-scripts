#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of OnMute
#
# OnMute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnMute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnMute.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, re, traceback, json
import xbmc, xbmcplugin, xbmcaddon, xbmcgui

# Plugin Info
ADDON_ID = 'service.onmute'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
DEBUG = REAL_SETTINGS.getSetting('enableDebug') == "true"

def log(msg, level = xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR:
        return
    elif level == xbmc.LOGERROR:
        msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
       
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')
    return string
    
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('utf-8', 'ignore' )
        else:
           string = ascii(string)
    return string
     
def loadJson(string):
    if len(string) == 0:
        return {}
    try:
        return json.loads(uni(string))
    except:
        return json.loads(ascii(string))
        
def dumpJson(mydict, sortkey=True):
    return json.dumps(mydict, sort_keys=sortkey)

def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
    
class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player())
        
        
    def onPlayBackStarted(self):
        log('onPlayBackStarted')
        self.subFound = False
        
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.subFound = False
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.subFound = False
        
        
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self, xbmc.Monitor())
        self.searchSub = REAL_SETTINGS.getSetting('searchSub') == "true"
        self.enableCC =  REAL_SETTINGS.getSetting('enableCC') == "true"
        
        
    def onSettingsChanged(self):
        log("onSettingsChanged")
        self.searchSub = REAL_SETTINGS.getSetting('searchSub') == "true"
        self.enableCC =  REAL_SETTINGS.getSetting('enableCC') == "true"
        
        
class Service():
    def __init__(self):
        self.userCC = self.getCC()
        self.Player = Player()
        self.Monitor = Monitor()
        self.autoSub = False
        self.Player.subFound = False
        self.searchSub = self.Monitor.searchSub
        self.start()

        
    def searchSubtitle(self):
        log("searchSubtitle")
        self.Player.subFound = True
        xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
        
        
    def isSubtitle(self):
        state = xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled') == 1
        log("isSubtitle = " + str(state))
        return state
         
         
    def setSubtitle(self, state):
        log("setSubtitle = " + str(state))
        self.Player.showSubtitles(state)
         
         
    def hasSubtitle(self):
        state = xbmc.getCondVisibility('VideoPlayer.HasSubtitles') == 1
        log("hasSubtitle = " + str(state))
        return state

        
    def isMute(self):
        state = xbmc.getCondVisibility('Player.Muted') == 1
        log("isMute = " + str(state))
        return state


    def getCC(self):
        # save user parsecaptions settings prior to change
        state = False
        json_query = '{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"subtitles.parsecaptions"}, "id": 1}'
        json_responce = loadJson(sendJSON(json_query))
        if 'result' in json_responce and 'value' in json_responce:
            state = json_responce['result']['value']
        log("getCC = " + str(state))
        return state
        
    
    def setCC(self, state):
        # change parsecaptions setting
        log("setCC = " + str(state))
        json_query = '{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"subtitles.parsecaptions","value":%s}, "id": 1}'%str(state).lower()
        sendJSON(json_query)
        
    
    def start(self):
        # enable closed caption if user enables.
        if self.Monitor.enableCC == True and self.getCC() == False:
            self.setCC(True)
            
        while not self.Monitor.abortRequested():
            if self.Player.isPlayingVideo() == True:
                log("autoSub = " + str(self.autoSub))
                log("subFound = " + str(self.Player.subFound))
                
                if xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True":
                    self.searchSub = self.Monitor.searchSub
                    self.Monitor.searchSub = False
                else:
                    self.Monitor.searchSub = self.searchSub
                
                '''
                    missing subs return false positive isSubtitle = True,
                    compare with hasSubtitle to detect true status.
                '''
                # check if user has subs already enabled.
                if self.isSubtitle() == True and self.hasSubtitle() == True and self.isMute() == True and self.autoSub == False:
                    self.Monitor.waitForAbort(2)
                    continue
                    
                # on mute if subs are disabled, enable them.
                elif (self.isSubtitle() + self.hasSubtitle()) == 1 and self.isMute() == True and self.autoSub == False:
                    # search for missing sub only once per playback
                    if self.Monitor.searchSub == True and self.hasSubtitle() == False and self.Player.subFound == False:
                        self.searchSubtitle()
                    self.autoSub = True
                    self.setSubtitle(True)
                    
                # off mute if subs are enabled, disable them.
                elif self.isSubtitle() == True and self.isMute() == False and self.autoSub == True:
                    self.autoSub = False
                    self.setSubtitle(False)
                    
            if self.Monitor.waitForAbort(2):
                break
             
        # restore users closed caption preference .
        if self.userCC == False and self.getCC() == True:
            self.setCC(self.userCC)
Service()