#  Copyright (C) 2023 Team-Kodi
#
#  This file is part of script.kodi.windows.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-

import os, time, datetime, traceback, re, threading, json
import socket, subprocess, sys
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

from bs4 import BeautifulSoup
from simplecache import SimpleCache
from six.moves import urllib
from contextlib import contextmanager

# Plugin Info
ADDON_ID      = 'script.kodi.windows.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
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
BRANCHS   =  {21:'omega',20:'nexus',19:'matrix',18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham','':''}
BUILD_OPT = {'nightlies':LANGUAGE(30017),'releases':LANGUAGE(30016),'snapshots':LANGUAGE(30015),'test-builds':LANGUAGE(30018)}
VERSION   = REAL_SETTINGS.getSetting("Version")

try:    
    BUILD  = json.loads(REAL_SETTINGS.getSetting("Build"))
    BRANCH = BRANCHS[int(BUILD.get('major',''))]
except: 
    BUILD = ''
    BRANCH = 'master'

PLATFORM  = {True:"win64", False:"win32", None:""}[('64' in REAL_SETTINGS.getSetting("Platform") or None)]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)

def selectDialog(label, items, pselect=-1, uDetails=True):
    select = xbmcgui.Dialog().select(label, items, preselect=pselect, useDetails=uDetails)
    if select >= 0: return select
    return None
        
@contextmanager
def busy_dialog():
    log('globals: busy_dialog')
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

socket.setdefaulttimeout(TIMEOUT)
class Installer(object):
    def __init__(self):
        self.myMonitor = xbmc.Monitor()
        self.cache    = SimpleCache()
        if self.chkUWP(): return
        self.killKodi = threading.Timer(2.0, self.killME)
        self.lastURL  = (REAL_SETTINGS.getSetting("LastURL") or self.buildMain())
        self.lastPath = REAL_SETTINGS.getSetting("LastPath")
        self.selectPath(self.lastURL)
        
    
    def chkUWP(self):
        isUWP = (xbmc.getCondVisibility("system.platform.uwp") or sys.platform == "win10" or re.search(r"[/\\]WindowsApps[/\\]XBMCFoundation\.Kodi_", xbmcvfs.translatePath("special://xbmc/")))
        if isUWP: return self.disable()
        return isUWP
        
        
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
                request = urllib.request.Request(url)
                cacheResponce = urllib.request.urlopen(request, timeout = TIMEOUT).read()
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
        for label in sorted(BUILD_OPT.keys()):
            liz = xbmcgui.ListItem(label.title(),BUILD_OPT[label],path=WIND_URL%(label,PLATFORM))
            liz.setArt({'icon':ICON,'thumb':ICON})
            tmpLST.append(liz)
        select = selectDialog(ADDON_NAME, tmpLST)
        if select is None: return #return on cancel.
        return tmpLST[select].getPath()
            
            
    def buildItems(self, url):
        with busy_dialog():
            soup = self.openURL(url)
            if soup is None: return
            for item in self.getItems(soup):
                try: #folders
                    if 'uwp' in item.lower(): continue #ignore UWP builds
                    label, label2 = re.compile("(.*?)/-(.*)").match(item).groups()
                    if label.lower() == PLATFORM.lower(): label2 = LANGUAGE(30014)%REAL_SETTINGS.getSetting("Platform")
                    elif label.lower() == BRANCH.lower(): label2 = LANGUAGE(30021)%(BUILD.get('major',''),BUILD.get('minor',''),BUILD.get('revision',''))
                    else: label2 = '' #Don't use time-stamp for folders
                    liz = (xbmcgui.ListItem(label.title(),label2,path=(url + label)))
                    liz.setArt({'icon':ICON,'thumb':ICON})
                    yield liz
                except: #files
                    label, label2 = re.compile("(.*?)\s(.*)").match(item).groups()
                    if '.exe' in label: 
                        liz = (xbmcgui.ListItem('%s.exe'%label.split('.exe')[0],'%s %s'%(label.split('.exe')[1], label2.replace('MiB','MB ').strip()),path='%s%s.exe'%(url,label.split('.exe')[0])))
                        liz.setArt({'icon':ICON,'thumb':ICON})
                        yield liz


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
            
    def okDialog(self, str1, str2='', str3='', header=ADDON_NAME):
        xbmcgui.Dialog().ok(header, str1, str2, str3)
        
    
    def selectPath(self, url, bypass=False):
        log('selectPath, url = ' + str(url))
        newURL  = url
        while not self.myMonitor.abortRequested():
            items = list(self.buildItems(url))
            if   len(items) == 0: break
            elif len(items) == 2  and not bypass and items[0].getLabel().lower() == 'parent directory' and not items[1].getLabel().startswith('.exe'): select = 1 #If one folder bypass selection.
            else: select = selectDialog(url.replace(BASE_URL,'./').replace('//','/'), items)
            if select is None: return #return on cancel.
            label  = items[select].getLabel()
            newURL = items[select].getPath()
            preURL = url.rsplit('/', 2)[0] + '/'
            if newURL.endswith('.exe'): 
                dest = xbmcvfs.translatePath(os.path.join(SETTINGS_LOC,label))
                self.setLastPath(url,dest)
                return self.downloadEXE(newURL,dest)
            elif label.lower() == 'parent directory' and "windows" in preURL.lower():
                return self.selectPath(preURL, True)
            elif label.lower() == 'parent directory' and "windows" not in preURL.lower():
                return self.selectPath(self.buildMain(), False)
            url = newURL.replace('Master','master') + '/'
            
            
    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), dest.rsplit('/', 1)[-1], nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return False
        elif CLEAN and xbmcvfs.exists(self.lastPath): self.deleteEXE(self.lastPath)
        return False
        
        
    def deleteEXE(self, path):
        #some file systems don't release the file lock instantly.
        for count in range(3):
            if self.myMonitor.waitForAbort(1): return 
            try: 
                if xbmcvfs.delete(path): return
            except: pass
        
        
    def downloadEXE(self, url, dest):
        if self.fileExists(dest): return self.installEXE(dest)
        start_time = time.time()
        dia = xbmcgui.DialogProgress()
        fle = dest.rsplit('\\', 1)[1]
        dia.create(ADDON_NAME, LANGUAGE(30002))
        try: urllib.request.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time, fle))
        except Exception as e:
            dia.close()
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log("downloadAPK, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
            return self.deleteEXE(dest)
        return self.installEXE(dest)


    def pbhook(self, numblocks, blocksize, filesize, dia, start_time, fle):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: eta = 0 
            kbps_speed = kbps_speed / 1024 
            if eta < 0: eta = divmod(0, 60)
            else: eta = divmod(eta, 60)
            total   = (float(filesize) / (1024 * 1024))
            label   = '%s %s'%(LANGUAGE(30023),SETTINGS_LOC)
            label2  = '%.02f MB of %.02f MB'%(currently_downloaded,total)
            label2 += '%s %.02f Kb/s'%(LANGUAGE(30024),kbps_speed)
            label2 += '%s %02d:%02d'%(LANGUAGE(30025),eta[0],eta[1])
            dia.update(int(percent), '%s\n%s\n%s'%(label,fle,label2))
        except Exception as e: 
            log("pbhook failed! %s" + str(e), xbmc.LOGERROR)
            dia.update(100)
        if dia.iscanceled(): raise Exception


    def installEXE(self, exefile):
        if not xbmcvfs.exists(exefile): return
        xbmc.executebuiltin('AlarmClock(shutdowntimer,XBMC.Quit(),2.0,true)')
        self.killKodi.start()
        subprocess.call(exefile, shell=True)
        
        
    def killME(self):
        subprocess.call('taskkill /f /im kodi.exe')
        
        
if __name__ == '__main__': Installer()