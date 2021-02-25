#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Video ScreenSaver.
#
# Video ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Video ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Video ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, random, datetime, itertools, traceback

from contextlib    import contextmanager
from simplecache   import use_cache, SimpleCache
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

# Plugin Info
ADDON_ID       = 'screensaver.videosaver'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

ACTION_STOP    = 13
MEDIA_EXTS     = (xbmc.getSupportedMedia('video')).split('|')
VIDEO_LIMIT    = int(REAL_SETTINGS.getSetting("VideoLimit"))
SINGLE_FLE     = int(REAL_SETTINGS.getSetting("VideoSource")) == 0
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
PLAYLIST_FLE   = REAL_SETTINGS.getSetting("VideoFile").endswith(('.xsp','.xml'))
RANDOM_PLAY    = REAL_SETTINGS.getSetting("VideoRandom") == "true"
KEYLOCK        = REAL_SETTINGS.getSetting("LockAction") == 'true'
DISABLE_TRAKT  = REAL_SETTINGS.getSetting("TraktDisable") == 'true'
VIDEO_FILE     = REAL_SETTINGS.getSetting("VideoFile")
VIDEO_PATH     = REAL_SETTINGS.getSetting("VideoFolder")

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: '%s, %s'%(msg,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
def sendJSON(command):
    log('sendJSON, command = %s'%(command))
    return json.loads(xbmc.executeJSONRPC(command))
  
def isMute():
    state = False
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
    json_response = (sendJSON(json_query))
    if json_response and 'result' in json_response: state = json_response['result']['muted']
    log('isMute, state = ' + str(state))
    return state
    
def saveVolume():
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["volume"]},"id":1}'
    json_response = (sendJSON(json_query))
    xbmcgui.Window(10000).setProperty('%s.RESTORE'%ADDON_ID,str(json_response.get('result',{}).get('volume',0)))
    if 'OK' in json_response: return True
    return False
    
def setVolume(state):
    log('setVolume, state = ' + str(state))
    if isMute() == True: return
    json_query = '{"jsonrpc":"2.0","method":"Application.SetVolume","params":{"volume":%s},"id":2}'%str(state)
    json_response = (sendJSON(json_query))
    if 'OK' in json_response: return True
    return False
    
def exeAction(action):
    log('exeAction, action = ' + action)
    json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"%s"},"id":1}'%(action)
    json_response = (sendJSON(json_query))
    if 'OK' in json_response: return True
    return False
    
def setRepeat(state='off'):
    log('setRepeat, state = ' + str(state)) 
    json_query = '{"jsonrpc":"2.0","method":"Player.SetRepeat","params":{"playerid":%d,"repeat":"%s"},"id":1}'%(getActivePlayer(),state)
    json_response = (sendJSON(json_query))
    if 'OK' in json_response: return True
    return False
    
def getActivePlayer():
    json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
    json_response = sendJSON(json_query)
    try: id = json_response['result'][0]['playerid']
    except: id = 1
    log("getActivePlayer, id = " + str(id)) 
    return id

def getFileDetails(path):
    log('getFileDetails')
    json_query    = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"video","properties":["file"]},"id":1}' % (path))
    json_response = sendJSON(json_query)
    return (json_response)
               
def progressDialog(percent=0, control=None, string1='', header=ADDON_NAME):
    if percent == 0 and control is None:
        control = xbmcgui.DialogProgress()
        control.create(header, ADDON_NAME)
        control.update(percent, string1)
    if control is not None:
        if control.iscanceled() or percent >= 100: return control.close()
        else: control.update(percent, string1)
    return control

@contextmanager
def busy_dialog(escape=False):
    if not escape:
        log('globals: busy_dialog')
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try: yield
        finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    else: yield


class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player()) 
        

    def onPlayBackError(self):
        log('onPlayBackError')
        # exeAction('stop')


    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        # if SINGLE_FLE: exeAction('stop')
        # self.myPlayer.play(self.playList)
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.myBackground.onClose()
        
        
class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if DISABLE_TRAKT: xbmcgui.Window(10000).setProperty('script.trakt.paused','true')
        self.playList  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)        
        self.fileCount = 0
        self.cache     = SimpleCache()
        self.myPlayer  = Player()
        self.myPlayer.myBackground = self
        
        if saveVolume(): 
            setVolume(int(REAL_SETTINGS.getSetting('SetVolume')))
        setRepeat('all')
        
        
    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('ss_time', 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope')
        self.myPlayer.play(self.buildPlaylist())
        
        
    def onAction(self, act):
        log('onAction')
        if KEYLOCK and act.getId() != ACTION_STOP: return
        self.onClose()
            
            
    def onClose(self):
        log('onClose')
        setRepeat(REAL_SETTINGS.getSetting('RepeatState').lower())
        xbmcgui.Window(10000).clearProperty('script.trakt.paused')
        xbmcgui.Window(10000).clearProperty('%s.Running'%(ADDON_ID))
        setVolume(int(xbmcgui.Window(10000).getProperty('%s.RESTORE'%ADDON_ID)))
        self.myPlayer.stop()
        self.playList.clear()
        self.close()
        
        
    def getDirectory(self, path, media='video', ignore='false', method='episode', order='ascending', end=0, start=0, filter={}):
        log('getDirectory, path = %s'%(path))
        cacheresponse = self.cache.get('%s.getDirectory, path = %s'%(ADDON_NAME,path))
        if not cacheresponse:
            if RANDOM_PLAY: method = 'random'
            json_query    = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"%s","sort":{"ignorearticle":%s,"method":"%s","order":"%s"},"limits":{"end":%s,"start":%s}},"id":1}' % (path, media, ignore, method, order, end, start))
            cacheresponse = (sendJSON(json_query))
            if 'result' in cacheresponse: 
                self.cache.set('%s.getDirectory, path = %s'%(ADDON_NAME,path), json.dumps(cacheresponse), expiration=datetime.timedelta(minutes=15))
                return cacheresponse
        else: return json.loads(cacheresponse)


    def buildDirectory(self, path, limit):
        log('buildDirectory, path = %s'%(path))
        itemLST   = []
        dirLST    = []
        with busy_dialog():
            response = self.getDirectory(path, end=limit).get('result',{}).get('files',[])
            for idx, item in enumerate(response):
                if self.fileCount > limit: break
                file     = item.get('file','')
                fileType = item.get('filetype','')
                if fileType == 'file':
                    self.fileCount += 1
                    itemLST.append(file)
                elif fileType == 'directory': 
                    dirLST.append(file)  
            if self.fileCount < limit:
                for dir in dirLST:
                    if self.fileCount > limit: break 
                    itemLST.extend(self.buildDirectory(dir, limit))
            return itemLST
            

    def buildItem(self, responce):
        log('buildItem')
        if 'result' in responce and 'filedetails' in responce['result']: key = 'filedetails'
        elif 'result' in responce and 'files' in responce['result']: key = 'files'
        else: xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
        for item in responce['result'][key]:
            if key == 'files' and item.get('filetype','') == 'directory': continue
            yield responce['result'][key]['file']


    def buildPlaylist(self):
        log('buildPlaylist')
        self.playList.clear()
        xbmc.sleep(100)
        
        if not SINGLE_FLE: 
            playListItem = self.buildDirectory(VIDEO_PATH, VIDEO_LIMIT)
        elif PLAYLIST_FLE: 
            playListItem = self.buildDirectory(VIDEO_FILE, VIDEO_LIMIT)
        elif not VIDEO_FILE.startswith(('plugin://','upnp://','pvr://')): 
            playListItem = list(self.buildItem(getFileDetails(VIDEO_FILE)))
        else: return VIDEO_FILE
            
        for idx, playItem in enumerate(playListItem): 
            self.playList.add(playItem, index=idx)
            
        if RANDOM_PLAY: 
            self.playList.shuffle()
        else: 
            self.playList.unshuffle()
        return self.playList
        
        
class Start():
    def __init__(self):
        self.myBackground = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default")
        self.myBackground.doModal()
        del self.myBackground
        
if __name__ == '__main__': Start()