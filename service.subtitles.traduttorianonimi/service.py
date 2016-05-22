# -*- coding: utf-8 -*-
#
#  service.py
#  
#  Copyright 2016 ShellAddicted <shelladdicted@gmail.com<>
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

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

import os
import sys
import unicodedata
import urllib
import requests
import zipfile
import StringIO
import shutil

addon = xbmcaddon.Addon()
cwd = xbmc.translatePath(addon.getAddonInfo("path")).decode("utf-8")
resource = xbmc.translatePath(os.path.join(cwd, "resources", "lib")).decode("utf-8")

sys.path.append(resource)
from utils import *
log=log.getChild("Service")

import TraduttoriAnonimi

def CleanJunk():
    #cleanup junk files
    for x in [profile,temp]:
        if (xbmcvfs.exists(x)):
            shutil.rmtree(x)
            
        xbmcvfs.mkdirs(x)

def GetParams():
    param={}
    if (len(sys.argv[2])>=2):
        for pairsofparam in sys.argv[2].replace("?","").split("&"):
            tmp=pairsofparam.split("=")
            if (len(tmp)==2):
                param[tmp[0]]=tmp[1]
    return param

def search(item):
    CleanJunk()
    if ('ita' in item['languages']):
        if (item['tvshow']):
            x=TraduttoriAnonimi.TraduttoriAnonimi()
            results=x.GrabSubtitle(item["tvshow"], int(item["season"]), int(item["episode"]))
            if (results!=None):
                for result in results:
                    subs=download(result["URL"])
                    for sub in subs:
                        listitem = xbmcgui.ListItem(label='Italian',label2=os.path.basename(sub),thumbnailImage='it') #sub["Name"]
                        xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = "plugin://{}/?action=download&url={}".format(scriptid,sub), listitem = listitem, isFolder = False)#sub["URL"]
                    xbmcplugin.endOfDirectory(int(sys.argv[1]))	# send end of directory to XBMC
            else:
                log.info("NO RESULTS")
        else:
            notify(language(30002),time=12000) #The Subtitles are available only for TV Shows,MOVIES will be supported in future
            log.info('TraduttoriAnonimi only works with tv shows. Skipped')
    else:
        notify(language(30003),time=17000) #The Subtitles are available only in Italian,Check Your Kodi Settings [Video->Subtitles->Languages to download subtitles for]
        log.info('TraduttoriAnonimi only works with italian. Skipped')
        
def download(url):
    log.debug("Downloading => {}".format(url))
    if (os.path.isfile(url)):
        log.info("url is a local path")
        return [url]
    exts=["srt"]
    out=[]
    
    r=RetriveURL(url)
    if (r!=None):
        content=r.content
        tmp=StringIO.StringIO(content) # "with" can't be used because StringIO has not __exit__
        if (content[0]=="P"):
            log.info("ZipFile Detected")
            with zipfile.ZipFile(tmp) as q:
                for name in q.namelist():
                    if (name.split(".")[-1] in exts):
                        q.extract(name, temp)
                        out.append(os.path.join(temp,name))
        else:
            log.info("Unpacked file detected")
            if (os.path.basename(url).split(".")[-1] in exts):
                with open(os.path.join(temp,os.path.basename(url)),"wb") as q:
                    q.write(content)
                out.append(os.path.join(temp,os.path.basename(url)))
            else:
                log.info("Downloaded File ({}) is not in exts[{}]".format(os.path.basename(url),str(exts)))
    return out

def main():
    log.info("Application version: {}".format(version))
    if (xbmc.Player().isPlayingVideo()):
        params = GetParams()
    
        if (params["action"] == "search" or params["action"] == "manualsearch"):
            item = {}
            item["mansearch"] = params["action"] == "manualsearch"
            
            if (item['mansearch']):
                notify(language(30004),time=7000) #The Manual Search is not supported yet, but it will be in the future.
            
            item["season"] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
            item["episode"] = str(xbmc.getInfoLabel("VideoPlayer.Episode")).zfill(2)					# Episode
            item["tvshow"] = MagicUnicode(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))			# Show
            item["file_original_path"] = xbmc.Player().getPlayingFile().decode("utf-8")           	# Full path
            item["languages"] = []
            
            if ("searchstring" in params):
                item["mansearch"] = True
                item["mansearchstr"] = urllib.unquote(params["searchstring"])
            
            for lang in urllib.unquote(params["languages"]).decode("utf-8").split(","):
                item["languages"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
            
            if (item["episode"].lower().find("s") > -1): # Check if season is "Special"
                item["season"] = "0"
                item["episode"] = item["episode"][-1:]
            search(item)
        
        elif (params["action"] == "download"):
            subs=download(params["url"])
            for sub in subs:
                listitem = xbmcgui.ListItem(label = sub)
                xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = sub, listitem = listitem, isFolder = False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
main()
