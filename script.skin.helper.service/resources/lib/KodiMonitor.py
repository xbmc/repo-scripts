#!/usr/bin/python
# -*- coding: utf-8 -*-
import Utils as utils
import ArtworkUtils as artutils
import xbmc
import time

class Kodi_Monitor(xbmc.Monitor):
    
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    
    def onSettingsChanged(self):
        utils.setAddonsettings()
        utils.logMsg("onNotification - Addon settings changed!")
        utils.WINDOW.setProperty("resetPvrArtCache","reset")
    
    def onDatabaseUpdated(self,database):
        utils.logMsg("Kodi_Monitor: onDatabaseUpdated: " + database)
        if database == "video":
            self.resetVideoWidgetProps("",True)
            artutils.preCacheAllAnimatedArt()
        if database == "music" :
            self.resetMusicWidgetProps({},True)
    
    def onNotification(self,sender,method,data):
        
        utils.logMsg("Kodi_Monitor: sender %s - method: %s  - data: %s"%(sender,method,data))
        
        if method == "System.OnQuit":
            utils.WINDOW.setProperty("SkinHelperShutdownRequested","shutdown")
               
        if method == "VideoLibrary.OnUpdate":
            if not xbmc.getCondVisibility("Library.IsScanningVideo"):
                self.resetVideoWidgetProps(data)

        if method == "AudioLibrary.OnUpdate":
            self.resetMusicWidgetProps(data)
        
        if method == "Player.OnStop":
            utils.WINDOW.clearProperty("Skinhelper.PlayerPlaying")
            utils.WINDOW.clearProperty("TrailerPlaying")
            if xbmc.getCondVisibility("Skin.String(videoinfo_traileraction,fullscreen) + !IsEmpty(Window(Home).Property(TrailerPlaying)) + !Window.IsActive(movieinformation)"): xbmc.executebuiltin("Action(info)")
            self.resetPlayerWindowProps()
            self.resetVideoWidgetProps(data)
            self.resetMusicWidgetProps(data)

        if method == "Player.OnPlay":
            #skip if the player is already playing
            if utils.WINDOW.getProperty("Skinhelper.PlayerPlaying") == "playing": return
            try: secondsToDisplay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.ShowInfoAtPlaybackStart)"))
            except: return
            
            utils.logMsg("onNotification - ShowInfoAtPlaybackStart - number of seconds: " + str(secondsToDisplay))
            utils.WINDOW.setProperty("Skinhelper.PlayerPlaying","playing")
            #Show the OSD info panel on playback start
            if secondsToDisplay != 0:
                tryCount = 0
                if utils.WINDOW.getProperty("VideoScreensaverRunning") != "true":
                    while tryCount !=50 and xbmc.getCondVisibility("!Player.ShowInfo"):
                        xbmc.sleep(100)
                        if xbmc.getCondVisibility("!Player.ShowInfo + Window.IsActive(fullscreenvideo)"):
                            xbmc.executebuiltin('Action(info)')
                        tryCount += 1
                    
                    # close info again
                    self.waitForAbort(secondsToDisplay)
                    if xbmc.getCondVisibility("Player.ShowInfo"):
                        xbmc.executebuiltin('Action(info)')
                        
    def resetMusicWidgetProps(self,data={},resetAll=False):
        #clear the cache for the music widgets
        type = "unknown"
        if data:
            data = eval(data.replace("true","True").replace("false","False"))
            type = data.get("type","")

        if (type in ["song","artist","album"] or resetAll and not utils.WINDOW.getProperty("SkinHelperShutdownRequested")):
            artutils.updateMusicArt(type,data.get("id"))
            if not xbmc.getCondVisibility("Library.IsScanningMusic"):
                utils.logMsg("Music database changed - type: %s - resetAll: %s, refreshing widgets...." %(type,resetAll))
                timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
                utils.WINDOW.setProperty("widgetreloadmusic", timestr)
            
    def resetVideoWidgetProps(self,data="",resetAll=False):
        #clear the cache for the video widgets
        type = "unknown"
        if data:
            data = eval(data.replace("true","True").replace("false","False"))
            if data and data.get("item"):
                type = data["item"].get("type","unknown")

        if (type in ["movie","tvshow","episode"] and not utils.WINDOW.getProperty("skinhelper-refreshvideowidgetsbusy")) or resetAll:
            utils.logMsg("Video database changed - type: %s - resetAll: %s, refreshing widgets...." %(type,resetAll))
            utils.WINDOW.setProperty("skinhelper-refreshvideowidgetsbusy","busy")
            if resetAll: utils.WINDOW.setProperty("resetVideoDbCache","reset")
            timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
            #reset specific widgets, based on item that is updated
            if resetAll or type=="movie":
                utils.WINDOW.setProperty("widgetreload-movies", timestr)
            if resetAll or type=="episode":
                utils.WINDOW.setProperty("widgetreload-episodes", timestr)
            if resetAll or type=="tvshow":
                utils.WINDOW.setProperty("widgetreload-tvshows", timestr)
            utils.WINDOW.setProperty("widgetreload", timestr)
            utils.WINDOW.clearProperty("skinhelper-refreshvideowidgetsbusy")
            
    def resetPlayerWindowProps(self):
        #reset all window props provided by the script...
        utils.WINDOW.setProperty("SkinHelper.Player.Music.Banner","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.ClearLogo","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.DiscArt","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.FanArt","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.Thumb","")
        utils.WINDOW.setProperty("SkinHelper.Player.Music.ArtistThumb","")
        utils.WINDOW.setProperty("SkinHelper.Player.Music.AlbumThumb","")
        utils.WINDOW.setProperty("SkinHelper.Player.Music.Info","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.TrackList","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.SongCount","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.albumCount","") 
        utils.WINDOW.setProperty("SkinHelper.Player.Music.AlbumList","")
        utils.WINDOW.setProperty("SkinHelper.Player.Music.ExtraFanArt","")