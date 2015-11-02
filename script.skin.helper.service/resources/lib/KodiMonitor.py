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

    def resetPlayerWindowProps(self):
        #reset all window props provided by the script...
        WINDOW.setProperty("SkinHelper.Player.Music.Banner","") 
        WINDOW.setProperty("SkinHelper.Player.Music.ClearLogo","") 
        WINDOW.setProperty("SkinHelper.Player.Music.DiscArt","") 
        WINDOW.setProperty("SkinHelper.Player.Music.FanArt","") 
        WINDOW.setProperty("SkinHelper.Player.Music.Thumb","") 
        WINDOW.setProperty("SkinHelper.Player.Music.Info","") 
        WINDOW.setProperty("SkinHelper.Player.Music.TrackList","") 
        WINDOW.setProperty("SkinHelper.Player.Music.SongCount","") 
        WINDOW.setProperty("SkinHelper.Player.Music.albumCount","") 
        WINDOW.setProperty("SkinHelper.Player.Music.AlbumList","")
        WINDOW.setProperty("SkinHelper.Player.Music.ExtraFanArt","")
    
    def resetMusicWidgets(self):
        #clear the cache for the music widgets
        WINDOW.clearProperty("skinhelper-recentalbums")
        WINDOW.clearProperty("skinhelper-recentplayedalbums")
        WINDOW.clearProperty("skinhelper-recentplayedsongs")
        WINDOW.clearProperty("skinhelper-recentsongs")
        WINDOW.setProperty("widgetreloadmusic", datetime.now().strftime('%Y-%m-%d %H:%M:%S') + str(randint(0,9)))
        WINDOW.setProperty("resetMusicArtCache","reset")
    
    def resetVideoWidgets(self):
        #clear the cache for the video widgets
        WINDOW.clearProperty("skinhelper-recommendedmovies")
        WINDOW.clearProperty("skinhelper-InProgressAndRecommendedMedia")
        WINDOW.clearProperty("skinhelper-InProgressMedia")
        WINDOW.clearProperty("skinhelper-RecommendedMedia")
        WINDOW.clearProperty("skinhelper-nextepisodes")
        WINDOW.clearProperty("skinhelper-similarmovies")
        WINDOW.clearProperty("skinhelper-similarshows")
        WINDOW.clearProperty("skinhelper-moviesforgenre")
        WINDOW.clearProperty("skinhelper-showsforgenre")
        WINDOW.clearProperty("skinhelper-recentmedia")
        WINDOW.clearProperty("skinhelper-favouritemedia")
        xbmc.sleep(500)
        WINDOW.setProperty("widgetreload", datetime.now().strftime('%Y-%m-%d %H:%M:%S') + str(randint(0,9)))
        WINDOW.setProperty("resetVideoDbCache","reset")
    
    def onDatabaseUpdated(self,database):
        if database == "video":
            self.resetVideoWidgets()
        if database == "music" :
            self.resetMusicWidgets()
           
    def onNotification(self,sender,method,data):
        
        logMsg("Kodi_Monitor: sender %s - method: %s  - data: %s"%(sender,method,data))
               
        if method == "VideoLibrary.OnUpdate":
            self.resetVideoWidgets()
        
        if method == "AudioLibrary.OnUpdate":
            self.resetMusicWidgets()
        
        if method == "Player.OnStop":
            WINDOW.clearProperty("Skinhelper.PlayerPlaying")
            self.resetPlayerWindowProps()
        
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