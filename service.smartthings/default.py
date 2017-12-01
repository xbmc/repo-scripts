#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Smartthing Monitor.
#
# Smartthing Monitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartthing Monitor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smartthing Monitor.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import service
import sys, time, datetime, re, traceback
import urllib, urllib2, socket, requests
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

# Plugin Info
ADDON_ID      = 'service.smartthings'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
CONTENT_TYPE  = 'files'
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
MENU          = [('Devices','',0),('Events','',1),('Monitors','',2),('Settings','',9)]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def getParams():
    param=[]
    if len(sys.argv[2])>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'): params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2: param[splitparams[0]]=splitparams[1]
    return param
                
class STLIST(object):
    def __init__(self):
        self.service = service.STHUB()
        
        
    def buildMenu(self):
        log('buildMenu')
        for item in MENU: self.addDir(*item)
        
        
    def browseDevices(self):
        log('browseDevices')
        devices = (self.service.getDeviceList(ALL=True) or None)
        if devices is None: return self.addDir(LANGUAGE(30021),'','')
        for device in devices: self.addDir(device,'',3)
        
        
    def browseMonitors(self):
        log('browseMonitors')
        devices = (self.service.deviceLST or None)
        # self.addDir('[B]+ Add Device[/B]','',4)
        if devices is None: return self.addDir(LANGUAGE(30022),'','')
        for device in devices: self.addDir(device,'',3)
        

    def browseEvents(self):
        log('browseEvents')
        events = (self.service.getEvents(LAST=False,ALL=True) or None)
        if events is None: return self.addDir(LANGUAGE(30023),'','')
        for event in events: self.addDir(event,'','')

        
    def getDeviceInfo(self, name):
        log('getDeviceInfo')
        '''[{u'Switch': u'off', 'name': u'Bedroom Light', u'Checkinterval': 1920.0, u'Level': 99.0}]'''
        info = list(self.service.getDeviceInfo([name]) or None)[0]
        if info is None: return
        label = '[B]%s[/B]'%(name.title())
        self.addDir(label,'','',{"mediatype":"files","label":label,"title":label})
        for key, val in info.iteritems():
            if key == 'name': continue
            try:label2 = val.title() 
            except: label2 = str(val) 
            label = '%s - %s'%(key.title(),label2)
            self.addDir(label,'','',{"mediatype":"files","label":label,"title":label})
            
        
    def addMonitor(self):
        self.service.getDeviceList(ALL=False,OPEN=False)
        self.browseMonitors()
        xbmc.executebuiltin("Container.Refresh")
            
            
    def openSettings(self):
        REAL_SETTINGS.openSettings() 
        self.buildMenu()
        
            
    def addLink(self, name, u, mode, infoList=False, infoArt=False, total=0):
        name = name.encode("utf-8")
        log('addLink, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'true')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, u, mode, infoList=False, infoArt=False):
        name = name.encode("utf-8")
        log('addDir, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
  
params=getParams()
try: url=urllib.unquote_plus(params["url"])
except: url=None
try: name=urllib.unquote_plus(params["name"])
except: name=None
try: mode=int(params["mode"])
except: mode=None
log("Mode: "+str(mode))
log("URL : "+str(url))
log("Name: "+str(name))

if mode==None:  STLIST().buildMenu()
elif mode == 0: STLIST().browseDevices()
elif mode == 1: STLIST().browseEvents()
elif mode == 2: STLIST().browseMonitors()
elif mode == 3: STLIST().getDeviceInfo(name)
elif mode == 4: STLIST().addMonitor()
elif mode == 9: STLIST().openSettings()

xbmcplugin.setContent(int(sys.argv[1])    , CONTENT_TYPE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)