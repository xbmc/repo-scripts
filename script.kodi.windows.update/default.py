#     Copyright (C) 2017 Team-Kodi
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

import os, time, datetime, traceback, re, fnmatch, glob
import urllib, urllib2, socket, subprocess
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

from bs4 import BeautifulSoup
from simplecache import SimpleCache

# Plugin Info
ADDON_ID      = 'script.kodi.windows.update'
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
DEBUG     = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLEAN     = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'
BASE_URL  = 'http://mirrors.kodi.tv/'
WIND_URL  = BASE_URL + '%s/windows/%s/'
BUILD_OPT = ['nightlies','releases','snapshots','test-builds']
BUILD_DEC = [LANGUAGE(30017),LANGUAGE(30016),LANGUAGE(30015),LANGUAGE(30018)]
UWP_PATH  = LANGUAGE(30010)
VERSION   = REAL_SETTINGS.getSetting("Version")
PLATFORM  = {True:"win64", False:"win32", None:""}[('64' in REAL_SETTINGS.getSetting("Platform") or None)]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

socket.setdefaulttimeout(TIMEOUT)
class Installer(object):
    def __init__(self):
        self.cache    = SimpleCache()
        if self.chkUWP(): return
        self.lastURL  = (REAL_SETTINGS.getSetting("LastURL") or self.buildMain())
        self.lastPath = REAL_SETTINGS.getSetting("LastPath")
        self.selectDialog(self.lastURL)
        
    
    def chkUWP(self):
        isUWP = len(fnmatch.filter(glob.glob(UWP_PATH),'*.*')) > 0
        # isUWP = True #Test
        if not isUWP: return isUWP
        else: return self.disable()
        
        
    def disable(self):
        xbmcgui.Dialog().notification(ADDON_NAME, VERSION, ICON, 8000)
        if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30009), LANGUAGE(30012)): return True 
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":false}, "id": 1}'%(ADDON_ID))
        xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30011), ICON, 4000)
        return True

        
    def openURL(self, url):
        if url is None: return
        log('openURL, url = ' + str(url))
        try:
            cacheResponce = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponce:
                request = urllib2.Request(url)
                responce = urllib2.urlopen(request, timeout = TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, responce, expiration=datetime.timedelta(minutes=5))
            return BeautifulSoup(self.cache.get(ADDON_NAME + '.openURL, url = %s'%url), "html.parser")
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
        return WIND_URL%(BUILD_OPT[select].lower().replace('//','/'),PLATFORM)
            
            
    def buildItems(self, url):
        soup = self.openURL(url)
        if soup is None: return
        for item in self.getItems(soup):
            try: #folders
                if 'uwp' in item.lower(): continue #ignore UWP builds
                label, label2 = re.compile("(.*?)/-(.*)").match(item).groups()
                if label == PLATFORM: label2 = LANGUAGE(30014)%PLATFORM
                else: label2 = '' #Don't use time-stamp for folders
                yield (xbmcgui.ListItem(label.strip(),label2.strip(),ICON))
            except: #files
                label, label2 = re.compile("(.*?)\s(.*)").match(item).groups()
                if label.endswith('.exe'): yield (xbmcgui.ListItem(label.strip(),label2.strip(),ICON))


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
            
    def okDialog(self, str1, str2='', str3='', header=ADDON_NAME):
        xbmcgui.Dialog().ok(header, str1, str2, str3)
        
    
    def selectDialog(self, url, bypass=False):
        log('selectDialog, url = ' + str(url))
        newURL  = url
        while not xbmc.Monitor().abortRequested():
            items = list(self.buildItems(url))
            if len(items) == 0: break
            elif len(items) == 2 and not bypass and items[0].getLabel().startswith('Parent directory') and not items[1].getLabel().startswith('.exe'): select = 1 #If one folder bypass selection.
            else:
                label  = url.replace(BASE_URL,'./').replace('//','/')
                select = xbmcgui.Dialog().select(label, items, preselect=-1, useDetails=True)
                if select < 0: return #return on cancel.
            label  = items[select].getLabel()
            newURL = url + items[select].getLabel()
            preURL = url.rsplit('/', 2)[0] + '/'
            
            if newURL.endswith('.exe'): 
                dest = xbmc.translatePath(os.path.join(SETTINGS_LOC,label))
                self.setLastPath(url,dest)
                return self.downloadEXE(newURL,dest)
            elif label.startswith('Parent directory') and "windows" in preURL:
                return self.selectDialog(preURL, True)
            elif label.startswith('Parent directory') and "windows" not in preURL:
                return self.selectDialog(self.buildMain(), False)
            url = newURL + '/'
        
        
    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), dest.rsplit('/', 1)[-1], nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return False
        elif CLEAN and xbmcvfs.exists(self.lastPath): self.deleteEXE(self.lastPath)
        return False
        
        
    def deleteEXE(self, path):
        count = 0
        #some file systems don't release the file lock instantly.
        while not xbmc.Monitor().abortRequested() and count < 3:
            count += 1
            if xbmc.Monitor().waitForAbort(1): return 
            try: 
                if xbmcvfs.delete(path): return
            except: pass
        
        
    def downloadEXE(self, url, dest):
        if self.fileExists(dest): return self.installEXE(dest)
        start_time = time.time()
        dia = xbmcgui.DialogProgress()
        dia.create(ADDON_NAME, LANGUAGE(30002))
        dia.update(0)
        try:
            urllib.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time))
        except Exception as e:
            dia.close()
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log("downloadAPK, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
            return self.deleteEXE(dest)
        return self.installEXE(dest)

        
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
            e += 'ETA: %02d:%02d' % divmod(eta, 60) 
            dia.update(percent, mbs, e)
        except Exception('Download Failed'): 
            percent = 100 
            dia.update(percent)
        if dia.iscanceled(): raise Exception('Download Canceled')
            
            
    def installEXE(self, exefile):
        if not xbmcvfs.exists(exefile): return
        xbmc.executebuiltin('XBMC.AlarmClock(shutdowntimer,XBMC.Quit(),0.5,true)')
        subprocess.call(['start', exefile], shell=True)
        # os.startfile(exefile)
        # subprocess.call('taskkill /f /im kodi.exe')
        
if __name__ == '__main__': Installer()