#     Copyright (C) 2018 Team-Kodi
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

import os, time, datetime, traceback, re
import urllib, urllib2, socket
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

from bs4 import BeautifulSoup
from simplecache import SimpleCache

# Plugin Info
ADDON_ID      = 'script.kodi.android.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT   = 15
MIN_VER   = 5 #Minimum Android Version Compatible with Kodi
DEBUG     = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLEAN     = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'
VERSION   = REAL_SETTINGS.getSetting("Version") #VERSION = 'Android 4.0.0 API level 24, kernel: Linux ARM 64-bit version 3.10.96+' #Test
BASE_URL  = 'http://mirrors.kodi.tv/'
DROID_URL = BASE_URL + '%s/android/%s/'
BUILD_OPT = ['nightlies','releases','snapshots','test-builds']
BUILD_DEC = [LANGUAGE(30017),LANGUAGE(30016),LANGUAGE(30015),LANGUAGE(30018)]
DEVICESTR = (REAL_SETTINGS.getSetting("Platform") or None)

if DEVICESTR is None: PLATFORM = ""
elif '64' in DEVICESTR: PLATFORM = "arm64-v8a"
elif '86' in DEVICESTR: PLATFORM = "x86"
else: PLATFORM = "arm"

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

socket.setdefaulttimeout(TIMEOUT)
class Installer(object):
    def __init__(self):
        self.cache    = SimpleCache()
        if not self.chkVersion(): return
        self.lastURL  = (REAL_SETTINGS.getSetting("LastURL") or self.buildMain())
        self.lastPath = REAL_SETTINGS.getSetting("LastPath")
        self.selectDialog(self.lastURL)
        
        
    def disable(self, build):
        xbmcgui.Dialog().notification(ADDON_NAME, VERSION, ICON, 8000)
        if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30011)%(build), LANGUAGE(30012)): return False 
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":false}, "id": 1}'%(ADDON_ID))
        xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30009), ICON, 4000)
        return False
        
        
    def chkVersion(self):
        try: 
            build = int(re.compile('Android (\d+)').findall(VERSION)[0])
        except: build = MIN_VER
        if build >= MIN_VER: return True
        else: return self.disable(build)
        

    def openURL(self, url):
        if url is None: return
        log('openURL, url = ' + str(url))
        try:
            cacheResponce = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponce:
                request = urllib2.Request(url)
                cacheResponce = urllib2.urlopen(request, timeout = TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheResponce, expiration=datetime.timedelta(minutes=5))
            return BeautifulSoup(cacheResponce, "html.parser")
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return None

            
    def getItems(self, soup):
        try: #folders
            items = (soup.find_all('tr'))
            del items[0]
        except: #files
            items = (soup.find_all('a'))
        return [x.get_text() for x in items if x.get_text() is not None]

        
    def buildMain(self):
        tmpLST = []
        for idx, item in enumerate(BUILD_OPT): tmpLST.append(xbmcgui.ListItem(item.title(),BUILD_DEC[idx],ICON))
        select = xbmcgui.Dialog().select(ADDON_NAME, tmpLST, preselect=-1, useDetails=True)
        if select < 0: return #return on cancel.
        return  DROID_URL%(BUILD_OPT[select].lower().replace('//','/'),PLATFORM)
            
            
    def buildItems(self, url):
        soup = self.openURL(url)
        if soup is None: return
        for item in self.getItems(soup):
            try: #folders
                label, label2 = re.compile("(.*?)/-(.*)").match(item).groups()
                if label == PLATFORM: label2 = LANGUAGE(30014)%PLATFORM
                else: label2 = '' #Don't use time-stamp for folders
                yield (xbmcgui.ListItem(label.strip(),label2,ICON))
            except: #files
                label, label2 = re.compile("(.*?)\s(.*)").match(item).groups()
                if label.endswith('.apk'): yield (xbmcgui.ListItem(label.strip(),label2.strip(),ICON))


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
        
    def selectDialog(self, url, bypass=False):
        log('selectDialog, url = ' + str(url))
        newURL = url
        while not xbmc.Monitor().abortRequested():
            items  = list(self.buildItems(url))
            if len(items) == 0: break
            elif len(items) == 2 and not bypass and items[0].getLabel().startswith('Parent directory') and not items[1].getLabel().startswith('.apk'): select = 1 #If one folder bypass selection.
            else:
                label  = url.replace(BASE_URL,'./').replace('//','/')
                select = xbmcgui.Dialog().select(label, items, preselect=-1, useDetails=True)
                if select < 0: return #return on cancel.
            label  = items[select].getLabel()
            newURL = url + items[select].getLabel()
            preURL = url.rsplit('/', 2)[0] + '/'
            
            if newURL.endswith('.apk'): 
                dest = xbmc.translatePath(os.path.join(SETTINGS_LOC,label))
                self.setLastPath(url,dest)
                return self.downloadAPK(newURL,dest)
            elif label.startswith('Parent directory') and "android" in preURL:
                return self.selectDialog(preURL, True)
            elif label.startswith('Parent directory') and "android" not in preURL:
                return self.selectDialog(self.buildMain(), False)
            url = newURL + '/'
                

    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), dest.rsplit('/', 1)[-1], nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return True
        elif CLEAN and xbmcvfs.exists(self.lastPath): self.deleleAPK(self.lastPath)
        return False
        
        
    def deleleAPK(self, path):
        count = 0
        #some file systems don't release the file lock instantly.
        while not xbmc.Monitor().abortRequested() and count < 3:
            count += 1
            if xbmc.Monitor().waitForAbort(1): return 
            try: 
                if xbmcvfs.delete(path): return
            except: pass
    
        
    def downloadAPK(self, url, dest):
        if self.fileExists(dest): return self.installAPK(dest)
        start_time = time.time()
        dia = xbmcgui.DialogProgress()
        dia.create(ADDON_NAME, LANGUAGE(30002))
        try:
            urllib.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time))
        except Exception as e:
            dia.close()
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log("downloadAPK, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
            return self.deleleAPK(dest)
        return self.installAPK(dest)
        
        
    def pbhook(self, numblocks, blocksize, filesize, dia, start_time):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: eta = 0 
            kbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total) 
            e = 'Speed: %.02f Kb/s ' % kbps_speed 
            if eta < 0: eta = divmod(0, 60)
            else: eta = divmod(eta, 60)
            e += 'ETA: %02d:%02d' % eta
            dia.update(percent, LANGUAGE(30002), mbs, e)
        except Exception('Download Failed'): dia.update(100)
        if dia.iscanceled(): raise Exception('Download Canceled')
            
            
    def installAPK(self, apkfile):
        xbmc.executebuiltin('XBMC.AlarmClock(shutdowntimer,XBMC.Quit(),0.5,true)')
        xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW","application/vnd.android.package-archive","file:'+apkfile+'")')
        
if __name__ == '__main__': Installer()