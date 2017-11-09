#   Copyright (C) 2017 Lunatixz
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

import os, time, urllib, urllib2, traceback
import xbmc, xbmcvfs, xbmcaddon, xbmcgui
from bs4 import BeautifulSoup
    
# Plugin Info
ADDON_ID      = 'screensaver.system47'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
DEBUG         = True
FILENAME      = 'screensaver.system47.mp4'
FILEPATH      = xbmc.translatePath(os.path.join(SETTINGS_LOC,FILENAME))
DOWNLOAD_URL  = 'http://www.mediafire.com/file/cvptnk5p5zk41zb/%s'%FILENAME


def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

class Download(object):
    def __init__(self):
        self.start()
        
    def start(self):
        try:
            if not xbmcvfs.exists(os.path.join(SETTINGS_LOC,'')): xbmcvfs.mkdir(SETTINGS_LOC)
            start_time = time.time()
            dia = xbmcgui.DialogProgress()
            dia.create(ADDON_NAME,LANGUAGE(30002))
            dia.update(0)
            soup = BeautifulSoup(urllib2.urlopen(DOWNLOAD_URL), "html.parser")
            url  = soup('a', {'class': 'DownloadButtonAd-startDownload gbtnSecondary'})[0]['href']
            urllib.urlretrieve(url.rstrip('/'), FILEPATH, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time))
        except Exception,e:
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log("start, Failed! " + str(e), xbmc.LOGERROR)
            self.deletefile()
            return
        
        
    def pbhook(self, numblocks, blocksize, filesize, dia, start_time):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: 
                eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: 
                eta = 0 
            kbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total) 
            e = 'Speed: %.02f Kb/s ' % kbps_speed 
            e += 'ETA: %02d:%02d' % divmod(eta, 60) 
            dia.update(percent, mbs, e)
        except: 
            percent = 100 
            dia.update(percent) 
        if dia.iscanceled():
            self.deletefile()
            dia.close()
        return
        
        
    def deletefile(self):
        try: xbmcvfs.delete(FILEPATH) 
        except: pass
        
        
if __name__ == '__main__':
    Download()