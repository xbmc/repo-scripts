#  Copyright (C) 2026 Team-Kodi
#
#  This file is part of script.kodi.windows.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-

import platform, traceback, sys
import os, time, datetime, re, json
import subprocess

from bs4 import BeautifulSoup
from simplecache import SimpleCache
from six.moves import urllib
from contextlib import contextmanager
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs

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
SHUTDOWN  = 10 #Seconds shown in the pre-install shutdown countdown.
GRACE     = 5  #Seconds to wait for Kodi to exit before forcing it closed.
TRIES     = 3  #mirrors.kodi.tv 302s to a random mirror, retry re-rolls unreachable ones.
DEBUG     = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLEAN     = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'
BASE_URL  = 'https://mirrors.kodi.tv/'
WIND_URL  = BASE_URL + '%s/windows/%s/'
BRANCHS   =  {22:'piers',21:'omega',20:'nexus',19:'matrix',18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham','':''}
BUILD_OPT = {'nightlies':LANGUAGE(30017),'releases':LANGUAGE(30016),'snapshots':LANGUAGE(30015),'test-builds':LANGUAGE(30018)}
VERSION   = REAL_SETTINGS.getSetting("Version")

try:    
    BUILD  = json.loads(REAL_SETTINGS.getSetting("Build"))
    BRANCH = BRANCHS[int(BUILD.get('major',''))]
except: 
    BUILD = ''
    BRANCH = 'master'

MACHINE = (REAL_SETTINGS.getSetting("Platform") or '').lower()
if   'arm64' in MACHINE or 'aarch64' in MACHINE: PLATFORM = 'winarm64'
elif '64' in MACHINE:                             PLATFORM = 'win64'
elif MACHINE:                                     PLATFORM = 'win32'
else:                                             PLATFORM = ''

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
    # Warn the user Kodi is about to close, Cancel keeps Kodi (and the installer) running.
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

def shortPath(path, keep=2):
    # '~' the Kodi userdata root and elide middle folders so the label stays short.
    home = xbmcvfs.translatePath('special://home').rstrip('\\/')
    if path.lower().startswith(home.lower()): path = '~' + path[len(home):]
    parts = path.replace('/', '\\').split('\\')
    if len(parts) > keep + 1: parts = parts[:1] + ['...'] + parts[-keep:]
    return '\\'.join(parts)

def deleteFile(file):
    monitor = xbmc.Monitor()
    try:
        if not xbmcvfs.exists(file): return log(f'Installer: deleteFile skipped, file does not exist: {file}', xbmc.LOGDEBUG)
        for count in range(15):
            if xbmcvfs.delete(file):
                log(f'Installer: deleteFile success = {file}')
                return
            log(f'Installer: File locked, retrying deletion... ({count+1}/15)', xbmc.LOGDEBUG)
            if monitor.abortRequested() or monitor.waitForAbort(1): return
    except Exception as e: log("Installer: deleteFile Failed! " + str(e), xbmc.LOGERROR)

def killME():
    # waitForAbort only reports Kodi's shutdown request, so confirm the process is still alive first.
    running = subprocess.run('tasklist /fi "imagename eq kodi.exe" /nh', capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    if 'kodi.exe' not in running.lower(): return log('Installer: Kodi already exited, nothing to force close.')
    log('Installer: Kodi did not exit on its own, force closing.')
    subprocess.run('taskkill /f /im kodi.exe', capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

def quitKodi():
    # Quit Kodi, force close it only if it is still running once the grace period is over.
    xbmc.executebuiltin('Quit')
    if not xbmc.Monitor().waitForAbort(GRACE): killME()


class Installer(object):
    def __init__(self):
        self.myMonitor = xbmc.Monitor()
        self.cache     = SimpleCache()
        self.lastURL   = REAL_SETTINGS.getSetting("LastURL").replace('http://mirrors.kodi.tv/', BASE_URL) #Migrate saved http links to https.
        self.lastPATH  = REAL_SETTINGS.getSetting("LastPath")
        self.aborted   = self.chkUWP()


    def _run(self):
        if self.aborted: return
        if not self.lastURL: self.lastURL = self.buildMain()
        self.selectPath(self.lastURL)
        
        
    def chkUWP(self): # Returns True when the installer must not run.
        isUWP = (xbmc.getCondVisibility("system.platform.uwp") or sys.platform == "win10" or re.search(r"[/\\]WindowsApps[/\\]XBMCFoundation\.Kodi_", xbmcvfs.translatePath("special://xbmc/")))
        if not isUWP: return False
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
                    if   label.lower() == PLATFORM.lower(): label2 = LANGUAGE(30014)%REAL_SETTINGS.getSetting("Platform")
                    elif BUILD and label.lower() == BRANCH.lower(): label2 = LANGUAGE(30021)%(BUILD.get('major',''),BUILD.get('minor',''),BUILD.get('revision',''))
                    else:                                   label2 = '' #Don't use time-stamp for folders
                    liz = (xbmcgui.ListItem(label.title(),label2,path=(url + label)))
                    liz.setArt({'icon':ICON,'thumb':ICON})
                    yield liz
                except: #files
                    label, label2 = re.compile(r"(.*?)\s(.*)").match(item).groups()
                    if '.exe' in label: 
                        liz = (xbmcgui.ListItem('%s.exe'%label.split('.exe')[0],'%s %s'%(label.split('.exe')[1], label2.replace('MiB','MB ').strip()),path='%s%s.exe'%(url,label.split('.exe')[0])))
                        liz.setArt({'icon':ICON,'thumb':ICON})
                        yield liz


    def setLastPath(self, url, path):
        REAL_SETTINGS.setSetting("LastURL",url)
        REAL_SETTINGS.setSetting("LastPath",path)
        
    
    def selectPath(self, url, bypass=False):
        log('selectPath, url = ' + str(url))
        newURL  = url
        while not self.myMonitor.abortRequested():
            items = list(self.buildItems(url))
            if   len(items) == 0: break
            elif len(items) == 2  and not bypass and items[0].getLabel().lower() == 'parent directory' and not items[1].getLabel().endswith('.exe'): select = 1 #If one folder bypass selection.
            else: select = selectDialog(url.replace(BASE_URL,'./').replace('//','/'), items, [idx for idx, item in enumerate(items) if item.getLabel() in self.lastPATH])
            if select is None: return #return on cancel.
            label  = items[select].getLabel()
            newURL = items[select].getPath()
            preURL = url.rsplit('/', 2)[0] + '/'
            if newURL.endswith('.exe'): 
                dest = xbmcvfs.translatePath(os.path.join(SETTINGS_LOC,label))
                self.setLastPath(url,dest)
                return self.downloadFile(newURL,dest)
            elif label.lower() == 'parent directory' and "windows" in preURL.lower():
                return self.selectPath(preURL, True)
            elif label.lower() == 'parent directory' and "windows" not in preURL.lower():
                return self.selectPath(self.buildMain(), False)
            url = newURL.replace('Master','master') + '/'
            
            
    def fileExists(self, dest):
        if xbmcvfs.exists(dest):
            if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(30004), os.path.basename(dest), nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return True
        return False
        
        
    def downloadFile(self, url, dest):
        if not self.fileExists(dest):
            start_time = time.time()
            dia = xbmcgui.DialogProgress()
            fle = os.path.basename(dest)
            dia.create(ADDON_NAME, '%s\n%s' % (LANGUAGE(30002), fle))
            try:
                for attempt in range(TRIES):
                    try:
                        urllib.request.urlretrieve(url.rstrip('/'), dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time, fle))
                        break
                    except Exception as e:
                        if attempt == TRIES - 1 or 'User canceled download' in str(e): raise
                        log('downloadFile, attempt %d failed (%s), retrying...' % (attempt + 1, e))
                        start_time = time.time()
            except Exception as e:
                deleteFile(dest)
                if 'User canceled download' in str(e): log("downloadFile, Download canceled by user.", xbmc.LOGINFO)
                else:
                    xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
                    log("downloadFile, Failed! (%s) %s"%(url,str(e)), xbmc.LOGERROR)
                return
            finally:
                dia.close()
        return self.installFile(dest)

            
    def pbhook(self, numblocks, blocksize, filesize, dia, start_time, fle):
        if dia.iscanceled(): raise RuntimeError("User canceled download")
        try: 
            if filesize <= 0: filesize = 1 # Fallback to prevent division by zero or negative
            elapsed_time = time.time() - start_time
            if elapsed_time <= 0: elapsed_time = 0.001 # Prevent ZeroDivisionError on instant hooks
            downloaded_bytes = numblocks * blocksize
            percent = min((downloaded_bytes * 100) / filesize, 100)
            currently_downloaded_mb = float(downloaded_bytes) / (1024 * 1024)
            total_mb = float(filesize) / (1024 * 1024)
            # Speed in bytes per second, converted to KB/s
            bytes_per_sec = downloaded_bytes / elapsed_time
            kbps_speed = bytes_per_sec / 1024
            if bytes_per_sec > 0: eta_seconds = max(0, (filesize - downloaded_bytes) / bytes_per_sec)
            else:                 eta_seconds = 0
            eta_minutes, eta_remaining_seconds = divmod(int(eta_seconds), 60)
            label   = '%s %s'%(LANGUAGE(30023), shortPath(xbmcvfs.translatePath(SETTINGS_LOC)))
            label2  = '%.02f MB of %.02f MB'%(currently_downloaded_mb,total_mb)
            label2 += '%s %.02f Kb/s'%(LANGUAGE(30024),kbps_speed)
            label2 += '%s %02d:%02d'%(LANGUAGE(30025),eta_minutes,eta_remaining_seconds)
            dia.update(int(percent), '%s\n%s\n%s'%(label,fle,label2))
        except Exception as e: 
            log("pbhook failed! %s" % str(e), xbmc.LOGERROR)


    def installFile(self, exefile=None):
        if not (exefile and xbmcvfs.exists(exefile)): return
        if not countdownDialog(): return log('installFile, canceled by user, installation aborted.')
        try:
            os.startfile(exefile) #Shell launch so a manifest requesting elevation gets its UAC prompt.
        except OSError as e:
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return log('installFile, failed to launch %s: %s' % (exefile, e), xbmc.LOGERROR)
        quitKodi()
        
        
if __name__ == '__main__': Installer()._run()
