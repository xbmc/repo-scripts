#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import random
import urllib
import datetime
from traceback import print_exc
from time import gmtime, strftime
import xml.etree.ElementTree as etree

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)
import MainModule


__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString

lastEpPath = None
win = xbmcgui.Window( 10000 )

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    
    def __init__(self):
        
        count = 120
        unwatched = 1
        lastEpPath = ""
        PlexEnabled = xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc)")
         
        while (not xbmc.abortRequested):
            xbmc.sleep(250)
            
            if not xbmc.Player().isPlayingVideo():
                
                # Update home backgrounds every minute
                count += 1
                if (count >= 240 and xbmc.getCondVisibility("Window.IsActive(home.xml)")):
                    MainModule.UpdateBackgrounds()
                    if PlexEnabled:
                        MainModule.updatePlexBackgrounds()
                    count = 0
                               
                # monitor extra fanart
                if xbmc.getCondVisibility("Skin.HasSetting(EnableExtraFanart)"):
                    if (xbmc.getCondVisibility("Window.IsActive(myvideonav.xml)") and not xbmc.getCondVisibility("Container.Scrolling")):
                        MainModule.checkExtraFanArt()
                    else:
                        win.clearProperty("ExtraFanArtPath")
                
                # monitor movie sets
                if (xbmc.getCondVisibility("Container.Content(movies) | Container.Content(sets)") and not xbmc.getCondVisibility("Container.Scrolling")):
                    if xbmc.getCondVisibility("SubString(ListItem.Path,videodb://movies/sets/,left)"):
                        MainModule.setMovieSetDetails()
                    else:
                        win.clearProperty('MovieSet.Title')
                        win.clearProperty('MovieSet.Runtime')
                        win.clearProperty('MovieSet.Writer')
                        win.clearProperty('MovieSet.Director')
                        win.clearProperty('MovieSet.Genre')
                        win.clearProperty('MovieSet.Country')
                        win.clearProperty('MovieSet.Studio')
                        win.clearProperty('MovieSet.Years')
                        win.clearProperty('MovieSet.Year')
                        win.clearProperty('MovieSet.Count')
                        win.clearProperty('MovieSet.Plot')
                
                # monitor episodes for auto focus first unwatched
                if xbmc.getCondVisibility("Skin.HasSetting(AutoFocusUnwatchedEpisode)"):
                    
                    #store unwatched episodes
                    if ((xbmc.getCondVisibility("Container.Content(seasons) | Container.Content(tvshows)")) and xbmc.getCondVisibility("!IsEmpty(ListItem.Property(UnWatchedEpisodes))")):
                        try:
                            unwatched = int(xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)"))
                        except: pass
                    
                    if (xbmc.getCondVisibility("Window.IsActive(myvideonav.xml)") and (xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)"))):
                        if (xbmc.getInfoLabel("Container.FolderPath") != lastEpPath and unwatched != 0):
                            try:
                                MainModule.focusEpisode()
                            except: 
                                xbmc.log("Titanskin Helper: Exception while trying to focus episode")
                                pass
                                
                    lastEpPath = xbmc.getInfoLabel("Container.FolderPath")       

      
   
xbmc.log('titan helper version %s started' % __addonversion__)
Main()
xbmc.log('titan helper version %s stopped' % __addonversion__)