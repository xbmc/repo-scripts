# -*- coding: utf-8 -*-
#
#  utils.py
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

## ***----THIS FILE is used to share functions and variables between all *.py------***
import xbmc
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

import os
import requests
import logging
import unicodedata

addon = xbmcaddon.Addon()
dialog=xbmcgui.Dialog()
author = addon.getAddonInfo("author")
scriptid = addon.getAddonInfo("id")
scriptname = addon.getAddonInfo("name")
version = addon.getAddonInfo("version")
language = addon.getLocalizedString
main_url = "http://traduttorianonimi.it"

cwd = xbmc.translatePath(addon.getAddonInfo("path")).decode("utf-8")
profile = xbmc.translatePath(addon.getAddonInfo("profile")).decode("utf-8")
resource = xbmc.translatePath(os.path.join(cwd, "resources", "lib")).decode("utf-8")
temp = xbmc.translatePath(os.path.join(profile, "temp","")).decode("utf-8")
NotifyLogo=os.path.join(cwd,"likelogo.png")
if (not os.path.isfile(NotifyLogo)):NotifyLogo=None;

def notify(message,header=scriptname,icon=NotifyLogo,time=5000):
    dialog.notification(header,message,icon=icon,time=time)

class LogStream(object):
    def write(self,data):
        xbmc.log("*** [service.subtiles.traduttorianonimi] -> {}".format(data.encode('utf-8',"ignore")), level = xbmc.LOGNOTICE)
         
log=logging.getLogger("TraduttoriAnonimi")
log.setLevel(logging.DEBUG)
style=logging.Formatter("{%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s")
consoleHandler = logging.StreamHandler(LogStream())
consoleHandler.setFormatter(style)
log.addHandler(consoleHandler)

def RetriveURL(url):
    try:
        headers={"user-agent": "Kodi-SubtitleService-TraduttoriAnonimi"}
        log.debug("GET Request => HEADERS={} ; URL={}".format(headers,url))
        q=requests.get(url,headers=headers)
        log.debug("GET Request <= Response HEADERS={}".format(q.headers))
        return q
    except:
        log.error("An Error is occurred",exc_info=True)
        notify(language(30001),time=3000) #Network Error. Check your Connection
        return None
         
def MagicUnicode(data):
    if (type(data)!=unicode):
        return unicode(data,"utf-8")
    else:
        return data
        


