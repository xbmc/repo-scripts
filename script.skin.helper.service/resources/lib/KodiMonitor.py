#!/usr/bin/python
# -*- coding: utf-8 -*-
import Utils as utils
import xbmc

class Kodi_Monitor(xbmc.Monitor):
    
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    
    def onSettingsChanged(self):
        utils.setAddonsettings()
        utils.logMsg("onNotification - Addon settings changed!")
        utils.WINDOW.setProperty("resetPvrArtCache","reset")
    
    def onDatabaseUpdated(self,database):
        utils.logMsg("Kodi_Monitor: onDatabaseUpdated: " + database,0)
        if database == "video":
            utils.resetVideoWidgetWindowProps("",True)
        if database == "music" :
            utils.resetMusicWidgetWindowProps("",True)
    
    def onNotification(self,sender,method,data):
        
        utils.logMsg("Kodi_Monitor: sender %s - method: %s  - data: %s"%(sender,method,data))
               
        if method == "VideoLibrary.OnUpdate":
            if not xbmc.getCondVisibility("Library.IsScanningVideo"):
                utils.resetVideoWidgetWindowProps(data)

        if method == "AudioLibrary.OnUpdate":
            if not xbmc.getCondVisibility("Library.IsScanningMusic"):
                utils.resetMusicWidgetWindowProps(data)
        
        if method == "Player.OnStop":
            utils.WINDOW.clearProperty("Skinhelper.PlayerPlaying")
            utils.WINDOW.clearProperty("TrailerPlaying")
            if xbmc.getCondVisibility("Skin.String(videoinfo_traileraction,fullscreen) + !IsEmpty(Window(Home).Property(TrailerPlaying)) + !Window.IsActive(movieinformation)"): xbmc.executebuiltin("Action(info)")
            utils.resetPlayerWindowProps()
            utils.resetVideoWidgetWindowProps(data)
            utils.resetMusicWidgetWindowProps(data)

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