#   Copyright (C) 2019 Lunatixz
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

import urllib, json, os, traceback
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.videosaver'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
XSP_CACHE_LOC  = os.path.join(SETTINGS_LOC, 'cache','')
MEDIA_EXTS     = (xbmc.getSupportedMedia('video')).split('|')
ACTION_STOP    = 13
VOLUME         = int(REAL_SETTINGS.getSetting('Set_Volume'))
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
LANGUAGE       = REAL_SETTINGS.getLocalizedString

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)
    
def isMute():
    state = False
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    if json_response and 'result' in json_response: state = json_response['result']['muted']
    log('isMute, state = ' + str(state))
    return state
    
def saveVolume():
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["volume"]},"id":1}'
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    xbmcgui.Window(10000).setProperty('%s.RESTORE'%ADDON_ID,str(json_response.get('result',{}).get('volume',0)))
    
def setVolume(state):
    log('setVolume, state = ' + str(state))
    if isMute() == True: return
    json_query = '{"jsonrpc":"2.0","method":"Application.SetVolume","params":{"volume":%s},"id":2}'%str(state)
    json_response = json.loads(xbmc.executeJSONRPC(json_query))

def ProgressDialogBG(percent=0, control=None, string1='', header=ADDON_NAME):
    if percent == 0 and not control:
        control = xbmcgui.DialogProgressBG()
        control.create(header, string1)
    elif percent == 100 and control: return control.close()
    elif control: control.update(percent, string1)
    return control
    
    
class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.myPlayer = Player()
        saveVolume()
        setVolume(VOLUME)
        
        
    def onAction(self, act):
        log('onAction')
        if REAL_SETTINGS.getSetting("LockAction") == 'true' and act.getId() != ACTION_STOP: return
        setVolume(int(xbmcgui.Window(10000).getProperty('%s.RESTORE'%ADDON_ID)))
        self.myPlayer.stop()
        self.close()
        

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player()) 
        if REAL_SETTINGS.getSetting("TraktDisable") == 'true': xbmcgui.Window(10000).setProperty('script.trakt.paused','true')


    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        xbmc.executebuiltin("PlayerControl(RepeatOff)")
        xbmcgui.Window(10000).clearProperty('script.trakt.paused')
        self.stop()  
        
        
class Start():
    def __init__(self):
        self.fileCount     = 0
        self.dirCount      = 0
        self.busy          = None
        self.myPlayer      = Player()
        self.singleVideo   = int(REAL_SETTINGS.getSetting("VideoSource")) == 0
        self.smartPlaylist = REAL_SETTINGS.getSetting("VideoFile")[-3:] == 'xsp' 
        self.videoRandom   = REAL_SETTINGS.getSetting("VideoRandom") == "true"
        self.background    = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default")
        self.buildPlaylist()
        
      
    def sendJSON(self, command):
        log('sendJSON, command = %s'%(command))
        return xbmc.executeJSONRPC(command)
              
              
    def loadJson(self, string):
        if len(string) == 0: return {}
        try: return json.loads(string)
        except Exception as e: return {}
            
           
    def getFileDetails(self, path):
        log('getFileDetails')
        json_query    = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"video","properties":["file"]},"id":1}' % (self.escapeDirJSON(path)))
        json_response = self.sendJSON(json_query)
        return self.loadJson(json_response)
          
          
    def getDirectory(self, path, media='video', ignore='false', method='random', order='ascending', end=0, start=0, filter={}):
        log('getDirectory, path = %s'%(path))
        json_query    = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"%s","sort":{"ignorearticle":%s,"method":"%s","order":"%s"},"limits":{"end":%s,"start":%s}},"id":1}' % (self.escapeDirJSON(path), media, ignore, method, order, end, start))
        json_response = self.sendJSON(json_query)
        return self.loadJson(json_response)


    def buildDirectory(self, path, limit):
        log('buildDirectory, path = %s'%(path))
        itemLST = []
        dirLST  = []
        if self.busy is None: self.busy = ProgressDialogBG(0, string1=LANGUAGE(32013))
        json_response = self.getDirectory(path, end=limit)
        if 'result' in json_response and json_response['result'] != None and 'files' in json_response['result']:
            response = json_response['result']['files']
            for i, item in enumerate(response):
                if self.fileCount >= limit: break
                file     = item.get('file','')
                fileType = item.get('filetype','')
                if fileType == 'file':
                    self.fileCount += 1
                    itemLST.append(file)
                    ProgressDialogBG(i*100//limit, self.busy, string1=item['label'])
                elif fileType == 'directory': 
                    self.dirCount += 1
                    dirLST.append(file)
            if self.fileCount < limit:
                for dir in dirLST:
                    if self.fileCount >= limit: break
                    itemLST.extend(self.buildDirectory(file, limit))  
        ProgressDialogBG(100, self.busy, string1=LANGUAGE(32013))    
        return itemLST
        

    def buildItems(self, responce):
        log('buildItems')
        if 'result' in responce and 'filedetails' in responce['result']: key = 'filedetails'
        elif 'result' in responce and 'files' in responce['result']: key = 'files'
        else: xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
        for item in responce['result'][key]:
            if key == 'files' and item.get('filetype','') == 'directory': continue
            yield responce['result'][key]['file']

                
    def escapeDirJSON(self, dir_name):
        mydir = dir_name
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir
        

    def getSmartPlaylist(self, path):
        log('getSmartPlaylist')
        if not xbmcvfs.exists(XSP_CACHE_LOC): xbmcvfs.mkdirs(XSP_CACHE_LOC)
        if xbmcvfs.copy(path, os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])):
            if xbmcvfs.exists(os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])): return os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])
        return path
        
        
    def buildPlaylist(self):
        log('buildPlaylist')
        self.playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playList.clear()
        xbmc.sleep(1000)
        if not self.singleVideo:
            videoLimit   = int(REAL_SETTINGS.getSetting("VideoLimit"))
            videoPath    = REAL_SETTINGS.getSetting("VideoFolder")
            playListItem = self.buildDirectory(videoPath,videoLimit)
        else:
            if self.smartPlaylist:
                videoLimit   = int(REAL_SETTINGS.getSetting("VideoLimit"))
                videoPath    = REAL_SETTINGS.getSetting("VideoFile")
                playListItem = self.buildDirectory(self.getSmartPlaylist(videoPath),videoLimit)
            else:
                videoPath = REAL_SETTINGS.getSetting("VideoFile")
                if not videoPath.startswith(('plugin','upnp','pvr')): playListItem = list(self.buildItems(self.getFileDetails(videoPath)))
                else: playListItem = [videoPath]
                    
        for idx, playItem in enumerate(playListItem): self.playList.add(playItem, index=idx)
        if not self.videoRandom: self.playList.unshuffle()
        else: self.playList.shuffle()
        self.myPlayer.play(self.playList)
        xbmc.executebuiltin("PlayerControl(RepeatAll)")
        xbmc.executebuiltin("Action(Fullscreen)")
        self.background.doModal()
        self.myPlayer.onPlayBackStopped()
if __name__ == '__main__': Start()