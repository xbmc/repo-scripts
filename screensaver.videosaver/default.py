#   Copyright (C) 2017 Lunatixz
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

import urllib, json, os
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.videosaver'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
XSP_CACHE_LOC  = os.path.join(SETTINGS_LOC, 'cache','')
MEDIA_EXTS     = (xbmc.getSupportedMedia('video')).split('|')
ACTION_STOP    = 13

class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.myPlayer = Player()
        
        
    def onAction(self, act):
        if REAL_SETTINGS.getSetting("LockAction") == 'true' and act.getId() != ACTION_STOP: return
        xbmc.executebuiltin("PlayerControl(RepeatOff)")
        xbmcgui.Window(10000).clearProperty('script.trakt.paused')
        self.myPlayer.stop()        
        self.close()
        
        
class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player()) 
        if REAL_SETTINGS.getSetting("TraktDisable") == 'true': xbmcgui.Window(10000).setProperty('script.trakt.paused','true')
        
        
class Start():
    def __init__(self):
        self.fileCount     = 0
        self.dirCount      = 0
        self.myPlayer      = Player()
        self.singleVideo   = int(REAL_SETTINGS.getSetting("VideoSource")) == 0
        self.smartPlaylist = REAL_SETTINGS.getSetting("VideoFile")[-3:] == 'xsp' 
        self.videoRandom   = REAL_SETTINGS.getSetting("VideoRandom") == "true"
        self.background    = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default")
        self.buildPlaylist()
        
      
    def sendJSON(self, command):
        return xbmc.executeJSONRPC(command)
              
              
    def loadJson(self, string):
        if len(string) == 0: return {}
        try: return json.loads(string)
        except Exception as e: return {}
            
           
    def getFileDetails(self, path):
        json_query    = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"video","properties":["file"]},"id":1}' % (self.escapeDirJSON(path)))
        json_response = self.sendJSON(json_query)
        return self.loadJson(json_response)
          
          
    def getDirectory(self, path, media='video', ignore='false', method='random', order='ascending', end=0, start=0, filter={}):
        json_query    = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"%s","sort":{"ignorearticle":%s,"method":"%s","order":"%s"},"limits":{"end":%s,"start":%s}},"id":1}' % (self.escapeDirJSON(path), media, ignore, method, order, end, start))
        json_response = self.sendJSON(json_query)
        return self.loadJson(json_response)


    def buildDirectory(self, path, limit):
        itemLST = []
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
                elif fileType == 'directory' and (self.fileCount < limit and self.dirCount < limit):
                    self.dirCount += 1
                    itemLST.extend(self.buildDirectory(file, limit))        
        return itemLST
        

    def buildItems(self, responce):
        if 'result' in responce and 'filedetails' in responce['result']: key = 'filedetails'
        elif 'result' in responce and 'files' in responce['result']: key = 'files'
        for item in responce['result'][key]:
            if key == 'files' and item.get('filetype','') == 'directory': continue
            yield responce['result'][key]['file']

                
    def escapeDirJSON(self, dir_name):
        mydir = dir_name
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir
        

    def getSmartPlaylist(self, path):
        if not xbmcvfs.exists(XSP_CACHE_LOC): xbmcvfs.mkdirs(XSP_CACHE_LOC)
        if xbmcvfs.copy(path, os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])):
            if xbmcvfs.exists(os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])): return os.path.join(XSP_CACHE_LOC,os.path.split(path)[1])
        return path
        
        
    def buildPlaylist(self):
        xbmc.executebuiltin("PlayerControl(RepeatAll)")
        playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playList.clear()
        xbmc.sleep(100)
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
                if not videoPath.startswith(('plugin','upnp')): playListItem = list(self.buildItems(self.getFileDetails(videoPath)))
                else: playListItem = [videoPath]
                    
        for idx, playItem in enumerate(playListItem): playList.add(playItem, index=idx)
        if not self.videoRandom: playList.unshuffle()
        else: playList.shuffle()
        if REAL_SETTINGS.getSetting("TraktDisable") == 'true': xbmcgui.Window(10000).setProperty('script.trakt.paused','true')
        self.myPlayer.play(playList)
        self.background.doModal()

if __name__ == '__main__': Start()