#  Copyright (C) 2020 Team-Kodi
#
#  This file is part of script.kodi.android.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-

import os, time, datetime, traceback, re
import socket, json

from bs4 import BeautifulSoup
from simplecache import SimpleCache
from six.moves import urllib
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from contextlib import contextmanager

# Plugin Info
ADDON_ID      = 'script.kodi.android.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = '/storage/emulated/0/download'
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
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
BRANCHS   =  {20:'nexus',19:'matrix',18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham','':''}
BUILD_OPT = {'nightlies':LANGUAGE(30017),'releases':LANGUAGE(30016),'snapshots':LANGUAGE(30015),'test-builds':LANGUAGE(30018)}

try:    
    BUILD  = json.loads(REAL_SETTINGS.getSetting("Build"))
    BRANCH = BRANCHS[int(BUILD.get('major',''))]
except: 
    BUILD = ''
    BRANCH = 'master'
    
DROID_URL = BASE_URL + '%s/android/%s/'
DEVICESTR = (REAL_SETTINGS.getSetting("Platform") or None)
USERAPP   = REAL_SETTINGS.getSetting("USERAPP")
CUSTOM    = (REAL_SETTINGS.getSetting('Custom_Manager') or 'com.android.documentsui')
FMANAGER  = {0:'com.android.documentsui',1:CUSTOM}[int(REAL_SETTINGS.getSetting('File_Manager'))]

if DEVICESTR is None: PLATFORM = ""
elif '64' in DEVICESTR: PLATFORM = "arm64-v8a"
elif '86' in DEVICESTR: PLATFORM = "x86"
else: PLATFORM = "arm"

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
        self.cache = SimpleCache()
        if not self.chkVersion(): return
        self.lastURL  = (REAL_SETTINGS.getSetting("LastURL") or self.buildMain())
        self.lastPath = REAL_SETTINGS.getSetting("LastPath")
        self.selectPath(self.lastURL)
        
        
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
            liz = xbmcgui.ListItem(label.title(),BUILD_OPT[label],path=DROID_URL%(label,PLATFORM))
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
                    label, label2 = re.compile("(.*?)/-(.*)").match(item).groups()
                    if label == PLATFORM: label2 = LANGUAGE(30014)%PLATFORM
                    elif label.lower() == BRANCH.lower(): label2 = LANGUAGE(30022)%(BUILD.get('major',''),BUILD.get('minor',''),BUILD.get('revision',''))
                    else: label2 = '' #Don't use time-stamp for folders
                    liz = xbmcgui.ListItem(label.title(),label2,path=(url + label))
                    liz.setArt({'icon':ICON,'thumb':ICON})
                    yield liz
                except: #files
                    label, label2 = re.compile("(.*?)\s(.*)").match(item).groups()
                    if '.apk' in label:
                        liz = xbmcgui.ListItem('%s.apk'%label.split('.apk')[0],'%s %s'%(label.split('.apk')[1], label2.replace('MiB','MB ').strip()),path='%s%s.apk'%(url,label.split('.apk')[0]))
                        liz.setArt({'icon':ICON,'thumb':ICON})
                        yield liz


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
        
    def selectPath(self, url, bypass=False):
        log('selectPath, url = ' + str(url))
        newURL = url
        while not self.myMonitor.abortRequested():
            items  = list(self.buildItems(url))
            if len(items) == 0: break
            elif len(items) == 2 and not bypass and items[0].getLabel().lower() == 'parent directory' and not items[1].getLabel().startswith('.apk'): select = 1 #If one folder bypass selection.
            else: select = selectDialog(url.replace(BASE_URL,'./').replace('//','/'), items)
            if select is None: return #return on cancel.
            label  = items[select].getLabel()
            newURL = items[select].getPath()
            preURL = url.rsplit('/', 2)[0] + '/'
            if newURL.endswith('.apk'):
                if not xbmcvfs.exists(SETTINGS_LOC): xbmcvfs.mkdir(SETTINGS_LOC)
                dest = xbmcvfs.translatePath(os.path.join(SETTINGS_LOC,label))
                self.setLastPath(url,dest)
                return self.downloadAPK(newURL,dest)
            elif label.lower() == 'parent directory' and "android" in preURL.lower():
                return self.selectPath(preURL, True)
            elif label.lower() == 'parent directory' and "android" not in preURL.lower():
                return self.selectPath(self.buildMain(), False)
            url = newURL + '/'
                

    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), dest.rsplit('/', 1)[-1], nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return True
        elif CLEAN and xbmcvfs.exists(self.lastPath): self.deleleAPK(self.lastPath)
        return False
        
        
    def deleleAPK(self, path):
        count = 0
        #some file systems don't release the file lock instantly.
        while not self.myMonitor.abortRequested() and count < 3:
            count += 1
            if self.myMonitor.waitForAbort(1): return 
            try: 
                if xbmcvfs.delete(path): return
            except: pass
            
        
    def downloadAPK(self, url, dest):
        if self.fileExists(dest): return self.installAPK(dest)
        start_time = time.time()
        dia = xbmcgui.DialogProgress()
        fle = dest.rsplit('/', 1)[1]
        dia.create(ADDON_NAME, LANGUAGE(30002)%fle)
        try: urllib.request.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time, fle))
        except Exception as e:
            dia.close()
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log("downloadAPK, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
            return self.deleleAPK(dest)
        dia.close()
        return self.installAPK(dest)
        
        
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
            
            
    def installAPK(self, apkfile):
        xbmc.executebuiltin('StartAndroidActivity(%s,,,"content://%s")'%(FMANAGER,apkfile))
        # xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.INSTALL_PACKAGE ","application/vnd.android.package-archive","content://%s")'%apkfile)
        # xbmc.executebuiltin('XBMC.AlarmClock(shutdowntimer,XBMC.Quit(),0.5,true)')


if __name__ == '__main__': Installer()