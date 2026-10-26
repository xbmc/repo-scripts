#  Copyright (C) 2026 Team-Kodi
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
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from contextlib import contextmanager

# Plugin Info
ADDON_ID      = 'script.kodi.android.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC = '/storage/emulated/0/Download/'
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT   = 15
SHUTDOWN  = 10 #Seconds shown in the pre-install shutdown countdown.
TRIES     = 3  #mirrors.kodi.tv 302s to a random mirror, retry re-rolls unreachable ones.
MIN_VER   = 5 #Minimum Android Version Compatible with Kodi
DEBUG     = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
VERSION   = REAL_SETTINGS.getSetting("Version") #VERSION = 'Android 4.0.0 API level 24, kernel: Linux ARM 64-bit version 3.10.96+' #Test
BASE_URL  = 'https://mirrors.kodi.tv/'
BRANCHS   =  {32:'z',31:'y',30:'x',29:'w',28:'v',27:'u',26:'t',25:'s',24:'r',23:'q',
              22:'piers',21:'omega',20:'nexus',19:'matrix',18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham','':''}
BUILD_OPT = {'nightlies':LANGUAGE(30017),'releases':LANGUAGE(30016),'snapshots':LANGUAGE(30015),'test-builds':LANGUAGE(30018)}

try:    
    BUILD  = json.loads(REAL_SETTINGS.getSetting("Build"))
    BRANCH = BRANCHS[int(BUILD.get('major',''))]
except: 
    BUILD  = ''
    BRANCH = 'master'
    
DROID_URL = BASE_URL + '%s/android/%s/'
DEVICESTR = (REAL_SETTINGS.getSetting("Platform") or None)
USERAPP   = REAL_SETTINGS.getSetting("USERAPP")
CUSTOM    = (REAL_SETTINGS.getSetting('Custom_Manager') or 'com.android.documentsui')
FMANAGER  = {0:'com.android.documentsui',1:CUSTOM}[int(REAL_SETTINGS.getSetting('File_Manager'))]

if   DEVICESTR is None: PLATFORM = ""
elif '86' in DEVICESTR: PLATFORM = "x86"       #x86 and x86_64 both use the mirror's x86 build.
elif '64' in DEVICESTR: PLATFORM = "arm64-v8a"
else:                   PLATFORM = "arm"

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)

def selectDialog(label, items, pselect=-1, uDetails=True):
    if isinstance(pselect, list):
        if len(pselect) > 0: pselect = pselect[0]
        else:                pselect = -1
    select = xbmcgui.Dialog().select(label, items, preselect=pselect, useDetails=uDetails)
    if select >= 0: return select
    return None
        
@contextmanager
def busy_dialog():
    log('globals: busy_dialog')
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def countdownDialog(seconds=SHUTDOWN):
    # Warn the user Kodi is about to close, Cancel keeps Kodi (and the install) running.
    monitor = xbmc.Monitor()
    dia = xbmcgui.DialogProgress()
    dia.create(ADDON_NAME, LANGUAGE(30027) % seconds)
    try:
        for left in range(seconds, -1, -1):
            if dia.iscanceled():
                log('countdownDialog, canceled by user, aborting shutdown')
                return False
            dia.update(int(left * 100 / seconds), LANGUAGE(30027) % left)
            if left > 0 and monitor.waitForAbort(1): return False
        return True
    finally:
        dia.close()

# ponytail: global default covers urlretrieve, which takes no timeout= argument.
socket.setdefaulttimeout(TIMEOUT)
class Installer(object):
    def __init__(self):
        self.myMonitor = xbmc.Monitor()
        self.cache     = SimpleCache()
        self.lastURL   = REAL_SETTINGS.getSetting("LastURL").replace('http://mirrors.kodi.tv/', BASE_URL) #Migrate saved http links to https.
        self.lastPATH  = REAL_SETTINGS.getSetting("LastPath")
        self.aborted   = self.chkVer()
        
    def _run(self):
        if self.aborted: return
        if not self.lastURL: self.lastURL = self.buildMain()
        self.selectPath(self.lastURL)
        
        
    def chkVer(self): # Returns True when the installer must not run.
        try:    build = int(re.compile(r'Android (\d+)').findall(VERSION)[0])
        except: build = MIN_VER
        if build < MIN_VER:
            xbmcgui.Dialog().notification(ADDON_NAME, VERSION, ICON, 8000)
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30011)%(build), LANGUAGE(30012)): return False 
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":false}, "id": 1}'%(ADDON_ID))
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30009), ICON, 4000)
            return True
        return False


    def getURL(self, url):
        try:
            HEADER = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}
            return urllib.request.urlopen(urllib.request.Request(url, headers=HEADER)).read()
        except Exception as e:
            log(f"getURL failed! {e}", xbmc.LOGERROR)
       

    def openURL(self, url):
        if url is None: return
        log('openURL, url = ' + str(url))
        try:
            cacheResponce = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponce:
                cacheResponce = self.getURL(url)
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
                    if   BUILD and label.lower() == BRANCH.lower(): label2 = LANGUAGE(30022)%(BUILD.get('major',''),BUILD.get('minor',''),BUILD.get('revision',''))
                    else:                                            label2 = '' #Don't use time-stamp for folders
                    liz = xbmcgui.ListItem(label.title(),label2,path=(url + label))
                    liz.setArt({'icon':ICON,'thumb':ICON})
                    yield liz
                except: #files
                    label, label2 = re.compile(r"(.*?)\s(.*)").match(item).groups()
                    if '.apk' in label:
                        liz = xbmcgui.ListItem('%s.apk'%label.split('.apk')[0],'%s %s'%(label.split('.apk')[1], label2.replace('MiB','MB ').strip()),path='%s%s.apk'%(url,label.split('.apk')[0]))
                        liz.setArt({'icon':ICON,'thumb':ICON})
                        yield liz


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
        
    def selectPath(self, url, bypass=False):
        log('selectPath, initial url = ' + str(url))
        while not self.myMonitor.abortRequested():
            items = list(self.buildItems(url))
            if len(items) == 0: 
                break
                
            if len(items) == 2 and not bypass and items[0].getLabel().lower() == 'parent directory' and not items[1].getLabel().endswith('.apk'): 
                select = 1 
            else: 
                dialog_title = url.replace(BASE_URL, './').replace('//', '/')
                pre_selects = [idx for idx, item in enumerate(items) if item.getLabel() in self.lastPATH]
                select = selectDialog(dialog_title, items, pre_selects)
                
            if select is None: return # User canceled
            label = items[select].getLabel()
            newURL = items[select].getPath()
            
            if label.endswith('.apk') or newURL.endswith('.apk'):
                if not xbmcvfs.exists(SETTINGS_LOC): 
                    xbmcvfs.mkdir(SETTINGS_LOC)
                dest = xbmcvfs.translatePath(os.path.join(SETTINGS_LOC, label))
                self.setLastPath(url, dest)
                return self.downloadAPK(newURL, dest)
                
            elif label.lower() == 'parent directory':
                preURL = url.rstrip('/').rsplit('/', 1)[0] + '/'
                if "android" in preURL.lower() and preURL != url:
                    url = preURL
                    bypass = True
                    continue
                else:
                    url = self.buildMain()
                    bypass = False
                    continue
            
            if not newURL.endswith('/'): url = newURL + '/'
            else:                        url = newURL
            bypass = False
                
                
    def checkPermission(self, path):
        dummy_file = os.path.join(xbmcvfs.translatePath(path), ".perm_test.tmp")
        try:
            with open(dummy_file, 'w') as f:
                f.write('test')
            if os.path.exists(dummy_file):
                os.remove(dummy_file)
            return True
        except (IOError, OSError, PermissionError):
            return False
            
            
    def requestPermission(self):
        xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30026))
        xbmc.executebuiltin('StartAndroidActivity("", "android.settings.APPLICATION_DETAILS_SETTINGS", "", "package:org.xbmc.kodi")')
        
        
    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), os.path.basename(dest), nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): 
                return False
            return True
        return False
        
        
    def downloadAPK(self, url, dest):
        if self.fileExists(dest): return self.installAPK(dest) #Already downloaded, install as is.
        if not self.checkPermission(os.path.dirname(dest)):
            self.requestPermission()
            return log("downloadAPK, Download aborted: Missing Android Storage Permissions.", xbmc.LOGERROR)

        start_time = time.time()
        dia = xbmcgui.DialogProgress()
        fle = os.path.basename(dest)
        dia.create(ADDON_NAME, LANGUAGE(30002)%fle)
        try: 
            for attempt in range(TRIES):
                try:
                    urllib.request.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time, fle))
                    break
                except Exception as e:
                    if attempt == TRIES - 1 or "User canceled download" in str(e): raise
                    log('downloadAPK, attempt %d failed (%s), retrying...' % (attempt + 1, e))
                    start_time = time.time()
            self.installAPK(dest)
        except Exception as e:
            self.deleteAPK(dest)
            if "User canceled download" in str(e): log("downloadAPK, Download canceled by user.", xbmc.LOGINFO)
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
                log("downloadAPK, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
        finally:
            dia.close()
        
        
    def pbhook(self, numblocks, blocksize, filesize, dia, start_time, fle):
        if dia.iscanceled(): raise RuntimeError("User canceled download")
        try: 
            if filesize <= 0: filesize = 1# Fallback to prevent division by zero or negative
            elapsed_time = time.time() - start_time
            if elapsed_time <= 0: elapsed_time = 0.001 # Prevent ZeroDivisionError on instant hooks
                
            downloaded_bytes = numblocks * blocksize
            percent = min((downloaded_bytes * 100) / filesize, 100) 
            currently_downloaded_mb = float(downloaded_bytes) / (1024 * 1024) 
            total_mb = float(filesize) / (1024 * 1024)
            # Speed in bytes per second, converted to KB/s
            bytes_per_sec = downloaded_bytes / elapsed_time
            kbps_speed = bytes_per_sec / 1024 
            
            if bytes_per_sec > 0: 
                eta_seconds = max(0, (filesize - downloaded_bytes) / bytes_per_sec)
            else: 
                eta_seconds = 0 
            eta_minutes, eta_remaining_seconds = divmod(int(eta_seconds), 60)
            
            label = '%s %s' % (LANGUAGE(30023), SETTINGS_LOC)
            label2 = '%.02f MB of %.02f MB' % (currently_downloaded_mb, total_mb)
            label2 += '%s %.02f Kb/s' % (LANGUAGE(30024), kbps_speed)
            label2 += '%s %02d:%02d' % (LANGUAGE(30025), eta_minutes, eta_remaining_seconds)
            dia.update(int(percent), '%s\n%s\n%s' % (label, fle, label2))
        except Exception as e: 
            log("pbhook failed! %s" % str(e), xbmc.LOGERROR)
            
            
    def deleteAPK(self, file): # Renamed typo from deleleAPK
        try:
            count = 0
            while count < 15:
                if self.myMonitor.waitForAbort(1): 
                    log("Installer: Deletion aborted due to Kodi shutdown.")
                    break
                if xbmcvfs.exists(file):
                    if xbmcvfs.delete(file):
                        log(f'Installer: deleteAPK success = {file}')
                        break
                    else:
                        log(f'Installer: File locked, retrying deletion... ({count+1}/15)', xbmc.LOGDEBUG)
                else:
                    log(f'Installer: deleteAPK skipped, file does not exist: {file}', xbmc.LOGDEBUG)
                    break
                count += 1
        except Exception as e: 
            log("Installer: deleteAPK Failed! " + str(e), xbmc.LOGERROR)
            
        
    def installAPK(self, apkfile):
        if not countdownDialog(): return log('installAPK, canceled by user, installation aborted.')
        # Quotes keep file managers whose name contains spaces/commas a single parameter.
        xbmc.executebuiltin('StartAndroidActivity("%s",,,"content://%s")'%(FMANAGER,apkfile))
        xbmc.sleep(500) #Give the file manager time to launch before Kodi closes.
        xbmc.executebuiltin('Quit')


if __name__ == '__main__': Installer()._run()