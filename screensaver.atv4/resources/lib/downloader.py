# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import urllib
import urllib2
import xbmc
import xbmcaddon
import xbmcgui
import os
import time
from commonatv import *


class Downloader:

    def __init__(self,):
        self.stop = False


    def downloadall(self,urllist):
        self.dp = xbmcgui.DialogProgress()
        self.dp.create(translate(32000))
        for url in urllist:
            if not self.stop:
                self.download(os.path.join(addon.getSetting("download-folder"),url.split("/")[-1]),url,url.split("/")[-1])
            else: break


    def download(self,path,url,name):
        try:
            if os.path.isfile(path) is True:
                while os.path.exists(path): 
                    os.remove(path); break
        except: pass
        self.dp.update(0,name)
        self.path = path
        xbmc.sleep(500)
        start_time = time.time()
        try: 
            urllib.urlretrieve(url, path, lambda nb, bs, fs: self.dialogdown(name,nb, bs, fs, self.dp, start_time))
            self.total_downloaded += 1
            return True
        except:
            return False
            

    def dialogdown(self,name,numblocks, blocksize, filesize, dp, start_time):
        try:
            percent = min(numblocks * blocksize * 100 / filesize, 100)
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: eta = 0 
            kbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            mbs = '%.02f MB %s %.02f MB' % (currently_downloaded,translate(32015), total) 
            e = ' (%.0f Kb/s) ' % kbps_speed 
            tempo = translate(32016) + ' %02d:%02d' % divmod(eta, 60) 
            dp.update(percent,name +' - '+ mbs + e,tempo)
        except: 
            percent = 100 
            dp.update(percent) 
        if dp.iscanceled():
            self.stop = True
            dp.close()
            try: os.remove(self.path)
            except: pass
            raise StopDownloading('Stopped Downloading')
            
class StopDownloading(Exception):
    def __init__(self, value): self.value = value 
    def __str__(self): return repr(self.value)
