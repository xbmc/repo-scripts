"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import xbmc
import xbmcvfs
import time
import json
import hashlib

from .commonatv import *

from urllib.request import urlopen


class Downloader:

    def __init__(self,):
        self.stop = False
        self.dp = None
        self.path = None

    def downloadall(self,urllist):
        self.dp = xbmcgui.DialogProgress()
        self.dp.create(translate(32000), translate(32019))
        # video checksums - download only the videos that were not downloaded previously
        if addon.getSettingBool("enable-checksums"):
            with open(os.path.join(addon_path, "resources", "checksums.json")) as f:
                checksums = f.read()

            checksums = json.loads(checksums)

        for url in urllist:
            if not self.stop:
                video_file = url.split("/")[-1]
                localfile = os.path.join(addon.getSetting("download-folder"), video_file)

                if xbmcvfs.exists(localfile):
                    if addon.getSettingBool("enable-checksums"):
                        with xbmcvfs.File(xbmcvfs.translatePath(localfile)) as f:
                            file_checksum = hashlib.md5(f.read()).hexdigest()

                        if video_file in checksums.keys() and checksums[video_file] != file_checksum:
                            self.download(localfile,url,url.split("/")[-1])
                    else:
                        self.download(localfile,url,url.split("/")[-1])
                else:
                    self.download(localfile,url,url.split("/")[-1])
            else:
                break

    def download(self,path,url,name):
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)

        self.dp.update(0,name)
        self.path = xbmcvfs.translatePath(path)
        xbmc.sleep(500)
        start_time = time.time()

        u = urlopen(url)
        meta = u.info()
        meta_func = meta.getheaders if hasattr(meta, 'getheaders') else meta.get_all
        meta_length = meta_func("Content-Length")
        file_size = None
        block_sz = 8192
        if meta_length:
            file_size = int(meta_length[0])

        file_size_dl = 0
        with xbmcvfs.File(self.path, 'wb') as f:
            numblocks = 0
            while not self.stop:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                f.write(buffer)
                file_size_dl += len(buffer)
                numblocks += 1
                self.dialogdown(name, numblocks, block_sz, file_size, self.dp, start_time)


    def dialogdown(self, name, numblocks, blocksize, filesize, dp, start_time):
        try:
            percent = int(min(numblocks * blocksize * 100 / filesize, 100))
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024)
            kbps_speed = numblocks * blocksize / (time.time() - start_time)
            if kbps_speed > 0:
                eta = (filesize - numblocks * blocksize) / kbps_speed
            else:
                eta = 0
            kbps_speed = kbps_speed / 1024
            total = float(filesize) / (1024 * 1024)
            mbs = '%.02f MB %s %.02f MB' % (currently_downloaded, translate(32015), total)
            e = ' (%.0f Kb/s) ' % kbps_speed
            tempo = translate(32016) + ' %02d:%02d' % divmod(eta, 60)
            dp.update(percent, f"{name} - {mbs}{e}\n{tempo}")
        except Exception:
            percent = 100
            dp.update(percent)

        if dp.iscanceled():
            self.stop = True
            dp.close()
            try:
                xbmcvfs.delete(self.path)
            except Exception:
                xbmc.log(msg='[Aerial ScreenSavers] Could not remove file', level=xbmc.LOGERROR)
            xbmc.log(msg='[Aerial ScreenSavers] Download canceled', level=xbmc.LOGDEBUG)
