#!/usr/bin/python
# -*- coding: utf-8 -*-
from random import randint
from Utils import *

class Kodi_Monitor(xbmc.Monitor):
    
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    
    def onSettingsChanged(self):
        setAddonsettings()
        logMsg("onNotification - Addon settings changed!")
        WINDOW.setProperty("resetPvrArtCache","reset")
    
    def onDatabaseUpdated(self,database):
        if database == "video":
            resetVideoWidgetWindowProps()
        if database == "music" :
            resetMusicWidgetWindowProps()
           
    def onNotification(self,sender,method,data):
        
        logMsg("Kodi_Monitor: sender %s - method: %s  - data: %s"%(sender,method,data))
               
        if method == "VideoLibrary.OnUpdate":
            WINDOW.setProperty("resetVideoDbCache","reset")
            xbmc.sleep(2000)
            resetVideoWidgetWindowProps() 
        
        if method == "AudioLibrary.OnUpdate":
            WINDOW.setProperty("resetMusicArtCache","reset")
            resetMusicWidgetWindowProps()
        
        if method == "Player.OnStop":
            WINDOW.clearProperty("Skinhelper.PlayerPlaying")
            resetPlayerWindowProps()
            resetVideoWidgetWindowProps()
        
        if method == "Player.OnPlay":
            
            #skip if the player is already playing
            if WINDOW.getProperty("Skinhelper.PlayerPlaying") == "playing": return
            try: secondsToDisplay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.ShowInfoAtPlaybackStart)"))
            except: return
            
            logMsg("onNotification - ShowInfoAtPlaybackStart - number of seconds: " + str(secondsToDisplay))
            WINDOW.setProperty("Skinhelper.PlayerPlaying","playing")
            #Show the OSD info panel on playback start
            if secondsToDisplay != 0:
                tryCount = 0
                if WINDOW.getProperty("VideoScreensaverRunning") != "true":
                    while tryCount !=50 and xbmc.getCondVisibility("!Window.IsActive(fullscreeninfo)"):
                        xbmc.sleep(100)
                        if xbmc.getCondVisibility("!Window.IsActive(fullscreeninfo) + Window.IsActive(fullscreenvideo)"):
                            xbmc.executebuiltin('Action(info)')
                        tryCount += 1
                    
                    # close info again
                    xbmc.sleep(secondsToDisplay*1000)
                    if xbmc.getCondVisibility("Window.IsActive(fullscreeninfo)"):
                        xbmc.executebuiltin('Action(info)')