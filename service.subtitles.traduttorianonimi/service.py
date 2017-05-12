# -*- coding: utf-8 -*-
#
#  service.py
#  
#  Copyright 2017 ShellAddicted <shelladdicted@gmail.com<>
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
#
__author__ = "ShellAddicted"
__copyright__ = "Copyright 2017, ShellAddicted"
__license__ = "GPL"
__version__ = "2.1.1"
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
try:
    from urllib import unquote
except (ImportError, AttributeError):
    from urllib.parse import unquote

import requests
import zipfile
import StringIO
import shutil
import logging

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

NotifyLogo = os.path.join(cwd, "likelogo.png")

if not os.path.isfile(NotifyLogo):
    NotifyLogo = None

HEADERS = {"user-agent": "Kodi-SubtitleService-TraduttoriAnonimi"}


def notify(message, header=scriptname, icon=NotifyLogo, time=5000):
    dialog.notification(header, message, icon=icon, time=time)


class LogStream(object):
    def write(self, data):
        xbmc.log("*** [service.subtiles.traduttorianonimi] -> {0}".format(data.encode('utf-8', "ignore")),
                 level=xbmc.LOGNOTICE)


log = logging.getLogger("TraduttoriAnonimi")
log.setLevel(logging.DEBUG)
style = logging.Formatter("{%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s")
consoleHandler = logging.StreamHandler(LogStream())
consoleHandler.setFormatter(style)
log.addHandler(consoleHandler)


def magicUnicode(data):
    """
    Return Unicode (utf-8) text encoded or exactly the input data (if already encoded)
    :param data: data (text) to encode
    :return:
    """
    # unicode is not defined in python3.x
    if type(data) != bytes:
        return str(data).encode("utf-8")
    else:
        return data


def retriveURL(url, headers=HEADERS):
    try:
        log.debug("GET Request => HEADERS={0} ; URL={1}".format(headers, url))
        q = requests.get(url, headers=headers)
        log.debug("GET Request <= Response HEADERS={0}".format(q.headers))
        return q
    except:
        log.error("An Error is occurred", exc_info=True)
        notify(language(30001), time=3000)  # Network Error. Check your Connection
        return None

def overrideRetriveURL(self, url, headers=HEADERS):
    return retriveURL(url, headers)

def ovverideLogging(self):
    self.log = log


sys.path.append(resource)
import TraduttoriAnonimi

# Overwrite _retriveURL() with the retriveURL() to show Error Message (Notify) On Connection Error
TraduttoriAnonimi.TraduttoriAnonimi._retriveURL = overrideRetriveURL

# Overwrite _initLogger() to force to use the current logger (connected to kodi/xbmc logging system)
TraduttoriAnonimi.TraduttoriAnonimi._initLogger = ovverideLogging

# TraduttoriAnonimi.TraduttoriAnonimi._magicUnicode = magicUnicode


def CleanJunk():
    # cleanup junk files
    for x in [profile, temp]:
        if xbmcvfs.exists(x):
            shutil.rmtree(x)
        xbmcvfs.mkdirs(x)


def GetParams():
    param = {}
    if len(sys.argv[2]) >= 2:
        for pairsofparam in sys.argv[2].replace("?", "").split("&"):
            tmp = pairsofparam.split("=")
            if len(tmp) == 2:
                param[tmp[0]] = tmp[1]
    return param

def CheckSync(fnvideo,fnsub):
    fnvideo=fnvideo.lower()
    fnsub=fnsub.lower()
    if "720p" in fnvideo and "hdtv" in fnvideo and "720p" in fnsub:
        return True

def search(item):
    CleanJunk()
    if "ita" in item["languages"]:
        if item["tvshow"]:
            x = TraduttoriAnonimi.TraduttoriAnonimi()
            results = x.getSubtitles(item["tvshow"], int(item["season"]), int(item["episode"]))
            if results is not None:
                for result in results:
                    subs = download(result["URL"])
                    for sub in subs:
                        # sub["Name"]
                        listitem = xbmcgui.ListItem(label='Italian', label2=os.path.basename(sub),thumbnailImage='it')
                        listitem.setProperty('sync', 'true' if CheckSync(item["file_original_path"],os.path.basename(sub)) else 'false')
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                                    url="plugin://{0}/?action=download&url={1}".format(scriptid, sub),
                                                    listitem=listitem, isFolder=False)  # sub["URL"]
                xbmcplugin.endOfDirectory(int(sys.argv[1]))  # send end of directory to XBMC
            else:
                log.info("NO RESULTS")
        else:
            # The Subtitles are available only for TV Shows,MOVIES will be supported in future
            notify(language(30002), time=18000)
            log.info('TraduttoriAnonimi only works with tv shows. Skipped')
    else:
        # The Subtitles are available only in Italian,Check Your Kodi Settings
        # [Video->Subtitles->Languages to download subtitles for]
        notify(language(30003), time=31000)
        log.info('TraduttoriAnonimi only works with italian. Skipped')


def download(url):
    log.debug("Downloading => {0}".format(url))
    if os.path.isfile(url):
        log.info("url is a local path")
        return [url]
    exts = ["srt"]
    out = []

    r = retriveURL(url)
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
    log.info("Application version: {0}".format(version))
    if xbmc.Player().isPlayingVideo():
        params = GetParams()

        if params["action"] == "search" or params["action"] == "manualsearch":
            item = {"mansearch": params["action"] == "manualsearch"}

            if item['mansearch']:
                notify(language(30004), time=7000)  # Manual Search is not supported yet, but it will be in the future.

            # Season
            item["season"] = str(xbmc.getInfoLabel("VideoPlayer.Season"))
            # Episode
            item["episode"] = str(xbmc.getInfoLabel("VideoPlayer.Episode")).zfill(2)
            # Show Name
            item["tvshow"] = magicUnicode(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
            # FullPath
            item["file_original_path"] = xbmc.Player().getPlayingFile().decode("utf-8")
            item["languages"] = []

            if "searchstring" in params:
                item["mansearch"] = True
                item["mansearchstr"] = unquote(params["searchstring"])

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


main()
