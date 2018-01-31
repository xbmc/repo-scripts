#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of System 47 Live in HD Screensaver.
#
# System 47 Live in HD Screensaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# System 47 Live in HD Screensaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with System 47 Live in HD Screensaver.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcvfs, xbmcaddon, xbmcgui
import os, random, traceback, json, base64
    
# Plugin Info
ADDON_ID      = 'screensaver.system47'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
ACTION_STOP   = 13
YT_URL        = 'plugin://plugin.video.youtube/play/?video_id=Y_4iAWobejY&suggested=false&incognito=true'
FILENAME      = 'screensaver.system47.mp4'
MUTE          = REAL_SETTINGS.getSetting('Enable_Mute') == 'true'
RANDOM        = REAL_SETTINGS.getSetting('Enable_Random') == 'true'

#CONFIGS for upcoming plugin.video.youtube developer key support. https://github.com/jdf76/plugin.video.youtube/issues/184
CONFIGS       = json.dumps({"origin": ADDON_ID,
                            "main"  :{"system": "All",
                                      "key"   : base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('AKEY')),
                                      "id"    : base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('CKEY')),
                                      "secret": base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('SKEY'))}})

def log(msg, level = xbmc.LOGDEBUG):
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), xbmc.LOGERROR)
    
def isMute():
    state = False
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    if json_response and 'result' in json_response: state = json_response['result']['muted']
    log('isMute, state = ' + str(state))
    return state
    
def setMute(state):
    log('setMute, state = ' + str(state))
    if isMute() == state: return
    json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}'%str(state).lower()
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    
class Player(xbmc.Player):        
    def onPlayBackStarted(self):
        log('onPlayBackStarted')
        seekValue = int(self.getTotalTime()//(random.randint(1,16))) if RANDOM else 0
        xbmc.Monitor().waitForAbort(9.0)
        if seekValue > 9.0: xbmc.executebuiltin('Seek(%s)'%seekValue)

        
class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.myPlayer = Player()
        self.myPlayer.Background = self
        if MUTE: setMute(True)
    
    
    def playFile(self):
        filePath = os.path.join(SETTINGS_LOC,FILENAME)
        if xbmcvfs.exists(filePath): return filePath
        else: return YT_URL
        
        
    def onInit(self):
        xbmc.executebuiltin("PlayerControl(RepeatAll)")
        xbmcgui.Window(10000).setProperty('plugin.video.youtube-configs', CONFIGS)
        self.myPlayer.play(self.playFile())
    
        
    def onAction(self, act):
        self.closeBackground()
        
        
    def closeBackground(self):
        log('closeBackground')
        xbmcgui.Window(10000).clearProperty('plugin.video.youtube-configs')
        self.myPlayer.stop()
        if MUTE: setMute(False)
        self.close()
        
      
class Start(object):
    def __init__(self):
        self.background = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default")
        self.background.doModal()
        
if __name__ == '__main__': Start()
