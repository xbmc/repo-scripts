# -*- coding: utf-8 -*-
#  Copyright 2018 ShellAddicted <shelladdicted@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
__author__ = "ShellAddicted"
__copyright__ = "Copyright 2018, ShellAddicted"
__license__ = "GPL"
__version__ = "2.2.1"
__maintainer__ = "ShellAddicted"
__email__ = "shelladdicted@gmail.com"
__status__ = "Development"

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

import os
import sys
import logging

try:
    from urllib import unquote
except (ImportError, AttributeError):
    from urllib.parse import unquote

try:
    import StringIO
except ImportError:
    from io import StringIO

import requests
import zipfile
import shutil

addon = xbmcaddon.Addon()
cwd = xbmc.translatePath(addon.getAddonInfo("path")).decode("utf-8")
resource = xbmc.translatePath(os.path.join(cwd, "resources", "lib")).decode("utf-8")
profile = xbmc.translatePath(addon.getAddonInfo("profile")).decode("utf-8")
temp = xbmc.translatePath(os.path.join(profile, "temp", "")).decode("utf-8")
dialog = xbmcgui.Dialog()
author = addon.getAddonInfo("author")
scriptid = addon.getAddonInfo("id")
scriptname = addon.getAddonInfo("name")
version = addon.getAddonInfo("version")
language = addon.getLocalizedString
main_url = "http://traduttorianonimi.it"

NotifyLogo = xbmc.translatePath(os.path.join(cwd, "resources", "likelogo.png")).decode("utf-8")

if not os.path.isfile(NotifyLogo):
    NotifyLogo = None

def notify(message, header=scriptname, icon=NotifyLogo, time=5000):
    dialog.notification(header, message, icon=icon, time=time)

class KodiLogHandler(logging.StreamHandler):
    _levels = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def __init__(self):
        logging.StreamHandler.__init__(self)
        addon_id = xbmcaddon.Addon().getAddonInfo('id')
        formatter = logging.Formatter(b'[{}]'.format(addon_id) + b'{%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        try:
            xbmc.log(self.format(record), self._levels[record.levelno])
        except UnicodeEncodeError:
            xbmc.log(self.format(record).encode(
                'utf-8', 'ignore'), self._levels[record.levelno])

    def flush(self):pass

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        KodiLogHandler()
    ]
)
log = logging.getLogger("TraduttoriAnonimiKodiService")

sys.path.append(resource)
import TraduttoriAnonimi

core = TraduttoriAnonimi.TraduttoriAnonimi()

def cleanup():
    # cleanup junk files
    for x in [profile, temp]:
        if xbmcvfs.exists(x):
            shutil.rmtree(x)
        xbmcvfs.mkdirs(x)

def getParams():
    param = {}
    if len(sys.argv[2]) >= 2:
        for pairsofparam in sys.argv[2].replace("?", "").split("&"):
            tmp = pairsofparam.split("=")
            if len(tmp) == 2:
                param[tmp[0]] = tmp[1]
    return param

def checkSync(fnvideo, fnsub):
    #TODO: implement this
    return True

def search(item):
    cleanup()
    if "ita" in item["languages"]:
        if item["tvshow"]:
            results = core.getSubtitles(item["tvshow"], int(item["season"]), int(item["episode"]))
            if results is not None:
                for result in results:
                    subs = download(result["URL"])
                    for sub in subs:
                        # sub["Name"]
                        listitem = xbmcgui.ListItem(label='Italian', label2=os.path.basename(sub),thumbnailImage='it')
                        listitem.setProperty('sync', 'true' if checkSync(item["file_original_path"],os.path.basename(sub)) else 'false')
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                                    url="plugin://{0}/?action=download&url={1}".format(scriptid, sub),
                                                    listitem=listitem, isFolder=False)  # sub["URL"]
                xbmcplugin.endOfDirectory(int(sys.argv[1]))  # send end of directory to XBMC
            else:
                log.info("NO RESULTS")
        else:
            # The Subtitles are available only for TV Shows, MOVIES will be supported in future
            notify(language(30002), time=18000)
            log.info('TraduttoriAnonimi only works with tv shows. Skipped')
    else:
        # The Subtitles are available only in Italian,Check Your Kodi Settings
        # [Video->Subtitles->Languages to download subtitles for]
        notify(language(30003), time=31000)
        log.info('TraduttoriAnonimi only works with italian. Skipped')


def download(url):
    if os.path.isfile(url):
        return [url]
    exts = ["srt"]
    out = []

    r = core._retriveURL(url)
    if r is not None:
        content = r.content
        tmp = StringIO.StringIO(content)  # "with" can't be used because StringIO has not __exit__
        if content[0] == "P":
            log.info("ZipFile Detected")
            q = zipfile.ZipFile(tmp)  # "with" can't be used because zipfile has not __exit__
            for name in q.namelist():
                if name.split(".")[-1] in exts:
                    q.extract(name, temp)
                    out.append(os.path.join(temp, name))
        else:
            log.info("Unpacked file detected")
            if os.path.basename(url).split(".")[-1] in exts:
                with open(os.path.join(temp, os.path.basename(url)), "wb") as q:
                    q.write(content)
                out.append(os.path.join(temp, os.path.basename(url)))
            else:
                log.info("Downloaded File ({0}) is not in exts[{1}]".format(os.path.basename(url), str(exts)))
    return out


def main():
    log.info("Traduttori Anonimi Kodi Service version: {0}".format(version))
    if xbmc.Player().isPlayingVideo():
        params = getParams()

        if params["action"] == "search" or params["action"] == "manualsearch":
            item = {}

            if params["action"] == "manualsearch": #ignore manual search is not supported
                notify(language(30004), time=5000)  # Manual Search is not supported yet, but it will be in the future.

            item["season"] = str(xbmc.getInfoLabel("VideoPlayer.Season"))
            item["episode"] = str(xbmc.getInfoLabel("VideoPlayer.Episode")).zfill(2)
            item["tvshow"] = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
            item["file_original_path"] = xbmc.Player().getPlayingFile().decode("utf-8")
            item["languages"] = []

            for lang in unquote(params["languages"]).decode("utf-8").split(","):
                item["languages"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

            if item["episode"].lower().find("s") > -1:  # Check if season is "Special"
                item["season"] = "0"
                item["episode"] = item["episode"][-1:]
            search(item)

        elif params["action"] == "download":
            subs = download(params["url"])
            for sub in subs:
                listitem = xbmcgui.ListItem(label=sub)
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]))

if __name__ == "__main__":
    main()
