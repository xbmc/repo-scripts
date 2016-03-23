#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading, thread
import requests, re
import random
import xml.etree.ElementTree as etree
from Utils import *
import ArtworkUtils as artutils
import SkinShortcutsIntegration as skinshortcuts


class ListItemMonitor(threading.Thread):
    
    event = None
    exit = False
    delayedTaskInterval = 1795
    lastWeatherNotificationCheck = None
    lastNextAiredNotificationCheck = None
    widgetContainerPrefix = ""
    liPath = ""
    liFile = ""
    liLabel = ""
    liTitle = ""
    liDbId = ""
    liImdb = ""
    unwatched = 1
    contentType = ""
    allStudioLogos = {}
    allStudioLogosColor = {}
    LastCustomStudioImagesPath = ""
    widgetTaskInterval = 590
    moviesetCache = {}
    extraFanartCache = {}
    musicArtCache = {}
    streamdetailsCache = {}
    pvrArtCache = {}
    extendedinfocache = {}
    imdb_top250 = {}
    cachePath = os.path.join(ADDON_DATA_PATH,"librarycache.json")
    ActorImagesCachePath = os.path.join(ADDON_DATA_PATH,"actorimages.json")
    
    def __init__(self, *args):
        logMsg("ListItemMonitor - started")
        self.event =  threading.Event()
        self.monitor = xbmc.Monitor()
        threading.Thread.__init__(self, *args)
    
    def stop(self):
        logMsg("ListItemMonitor - stop called",0)
        self.saveCacheToFile()
        self.exit = True
        self.event.set()

    def run(self):
        
        setAddonsettings()
        self.getCacheFromFile()
        playerTitle = ""
        playerFile = ""
        lastPlayerItem = ""
        playerItem = ""
        liPathLast = ""
        curFolder = ""
        curFolderLast = ""
        lastListItem = ""
        nextairedActive = False
        screenSaverSetting = None

        while (self.exit != True):
        
            if xbmc.getCondVisibility("Player.HasAudio"):
                #set window props for music player
                try:
                    playerTitle = xbmc.getInfoLabel("Player.Title").decode('utf-8')
                    playerFile = xbmc.getInfoLabel("Player.Filenameandpath").decode('utf-8')
                    playerItem = playerTitle + playerFile
                    #only perform actions when the listitem has actually changed
                    if playerItem and playerItem != lastPlayerItem:
                        #clear all window props first
                        resetPlayerWindowProps()
                        self.setMusicPlayerDetails()
                        lastPlayerItem = playerItem       
                except Exception as e:
                    logMsg("ERROR in setMusicPlayerDetails ! --> " + str(e), 0)
            elif lastPlayerItem:
                #cleanup remaining window props
                resetPlayerWindowProps()
                playerItem = ""
                lastPlayerItem = ""
            
            if xbmc.getCondVisibility("Window.IsActive(visualisation) + Skin.HasSetting(SkinHelper.DisableScreenSaverOnFullScreenMusic)"):
                #disable the screensaver if fullscreen music playback
                if not screenSaverSetting:
                    screenSaverSetting = getJSON('Settings.GetSettingValue', '{"setting":"screensaver.mode"}')
                    if screenSaverSetting: setJSON('Settings.SetSettingValue', '{"setting":"screensaver.mode", "value": ""}')
            elif screenSaverSetting: 
                setJSON('Settings.SetSettingValue', '{"setting":"screensaver.mode", "value": "%s"}' %screenSaverSetting)        
                screenSaverSetting = None
                
            if xbmc.getCondVisibility("Window.IsActive(videoosd) | Window.IsActive(musicosd)"):
                #auto close OSD after X seconds of inactivity
                if xbmc.getCondVisibility("Window.IsActive(videoosd)"):
                    secondsToDisplay = xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseVideoOSD)")
                    window = "videoosd"
                elif xbmc.getCondVisibility("Window.IsActive(musicosd)"):
                    secondsToDisplay = xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseMusicOSD)")
                    window = "musicosd"
                else:
                    secondsToDisplay = ""
                
                if secondsToDisplay and secondsToDisplay != "0":
                    while xbmc.getCondVisibility("Window.IsActive(%s)"%window):
                        if xbmc.getCondVisibility("System.IdleTime(%s)" %secondsToDisplay):
                            xbmc.executebuiltin("Dialog.Close(%s)"%window)
                        else:
                            xbmc.sleep(250)
                
            if xbmc.getCondVisibility("[Window.IsMedia | !IsEmpty(Window(Home).Property(SkinHelper.WidgetContainer))]"):
                try:
                    widgetContainer = WINDOW.getProperty("SkinHelper.WidgetContainer").decode('utf-8')
                    if widgetContainer: 
                        self.widgetContainerPrefix = "Container(%s)."%widgetContainer
                        curFolder = xbmc.getInfoLabel("widget-%s-$INFO[Container(%s).NumItems]" %(widgetContainer,widgetContainer)).decode('utf-8')
                    else: 
                        self.widgetContainerPrefix = ""
                        curFolder = xbmc.getInfoLabel("$INFO[Container.FolderPath]$INFO[Container.NumItems]").decode('utf-8')
                    self.liTitle = xbmc.getInfoLabel("%sListItem.Title" %self.widgetContainerPrefix).decode('utf-8')
                    self.liLabel = xbmc.getInfoLabel("%sListItem.Label" %self.widgetContainerPrefix).decode('utf-8')
                except Exception as e: 
                    logMsg(str(e),0)
                    curFolder = ""
                    self.liLabel = ""
                    self.liTitle = ""
                
                curListItem = curFolder + self.liLabel + self.liTitle
                WINDOW.setProperty("curListItem",curListItem)
                    
                #perform actions if the container path has changed
                if (curFolder != curFolderLast):
                    self.resetWindowProps()
                    self.contentType = ""
                    curFolderLast = curFolder
                    if curFolder and self.liLabel:
                        #always wait for the contentType because plugins can be slow
                        for i in range(20):
                            self.contentType = getCurrentContentType(self.widgetContainerPrefix)
                            if self.contentType: break
                            else: xbmc.sleep(250)
                        if not self.widgetContainerPrefix and self.contentType:
                            self.setForcedView()
                            self.setContentHeader()

                #only perform actions when the listitem has actually changed
                if curListItem and curListItem != lastListItem and self.contentType:
                    #clear all window props first
                    self.resetWindowProps()

                    #generic props
                    self.liPath = xbmc.getInfoLabel("%sListItem.Path" %self.widgetContainerPrefix).decode('utf-8')
                    self.liFile = xbmc.getInfoLabel("%sListItem.FileNameAndPath" %self.widgetContainerPrefix).decode('utf-8')
                    self.liDbId = xbmc.getInfoLabel("%sListItem.DBID"%self.widgetContainerPrefix).decode('utf-8')
                    if not self.liDbId or self.liDbId == "-1": self.liDbId = xbmc.getInfoLabel("%sListItem.Property(DBID)"%self.widgetContainerPrefix).decode('utf-8')
                    if self.liDbId == "-1": self.liDbId = ""
                    self.liImdb = xbmc.getInfoLabel("%sListItem.IMDBNumber"%self.widgetContainerPrefix).decode('utf-8')
                    if not self.liImdb: self.liImdb = xbmc.getInfoLabel("%sListItem.Property(IMDBNumber)"%self.widgetContainerPrefix).decode('utf-8')
                    
                    if not self.liLabel == "..":
                        # monitor listitem props for music content
                        if self.contentType in ["albums","artists","songs"]:
                            try:
                                thread.start_new_thread(self.setMusicDetails, (True,))
                                self.setGenre()
                            except Exception as e:
                                logMsg("ERROR in setMusicDetails ! --> " + str(e), 0)
                                    
                        # monitor listitem props for video content
                        elif self.contentType in ["movies","setmovies","tvshows","seasons","episodes","sets"]:
                            try:
                                thread.start_new_thread(self.setExtendedMovieInfo, (True,))
                                thread.start_new_thread(self.setAnimatedPoster, (True,))
                                self.setDuration()
                                self.setStudioLogo()
                                self.setGenre()
                                self.setDirector()
                                if self.liPath.startswith("plugin://") and not ("plugin.video.emby" in self.liPath or "script.skin.helper.service" in self.liPath):
                                    #plugins only...
                                    thread.start_new_thread(self.setAddonDetails, (True,))
                                    self.setAddonName()
                                else:
                                    #library only...
                                    self.setStreamDetails()
                                    self.setMovieSetDetails()
                                    self.checkExtraFanArt()
                                #nextaired workaround for info dialog
                                if self.widgetContainerPrefix and xbmc.getCondVisibility("!IsEmpty(%sListItem.TvShowTitle) + System.HasAddon(script.tv.show.next.aired)" %self.widgetContainerPrefix):
                                    xbmc.executebuiltin("RunScript(script.tv.show.next.aired,tvshowtitle=%s)" %xbmc.getInfoLabel("%sListItem.TvShowTitle"%self.widgetContainerPrefix))
                                    nextairedActive = True
                                elif nextairedActive:
                                    nextairedActive = False
                                    xbmc.executebuiltin("RunScript(script.tv.show.next.aired,tvshowtitle=165628787629692696)")
                            except Exception as e:
                                logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                        
                        # monitor listitem props when PVR is active
                        elif self.contentType in ["tvchannels","tvrecordings"]:
                            try:
                                self.setDuration()
                                thread.start_new_thread(self.setPVRThumbs, (True,))
                                self.setGenre()
                            except Exception as e:
                                logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                            
                    #set some globals
                    liPathLast = self.liPath
                    lastListItem = curListItem

                #do some background stuff every 30 minutes
                if (self.delayedTaskInterval >= 1800):
                    thread.start_new_thread(self.doBackgroundWork, ())
                    self.delayedTaskInterval = 0          
                
                #reload some widgets every 10 minutes
                if (self.widgetTaskInterval >= 600):
                    resetGlobalWidgetWindowProps()
                    self.widgetTaskInterval = 0
                
                #flush cache if videolibrary has changed
                if WINDOW.getProperty("resetVideoDbCache") == "reset":
                    self.moviesetCache = {}
                    self.extraFanartCache = {}
                    self.streamdetailsCache = {}
                    WINDOW.clearProperty("resetVideoDbCache")

                #flush cache if pvr settings have changed
                if WINDOW.getProperty("resetPvrArtCache") == "reset":
                    self.pvrArtCache = {}
                    WINDOW.clearProperty("SkinHelper.PVR.ArtWork")
                    WINDOW.clearProperty("resetPvrArtCache")
                
                #flush cache if musiclibrary has changed
                if WINDOW.getProperty("resetMusicArtCache") == "reset":
                    self.musicArtCache = {}
                    WINDOW.clearProperty("resetMusicArtCache")
                
                xbmc.sleep(100)
                self.delayedTaskInterval += 0.1
                self.widgetTaskInterval += 0.1
            elif lastListItem:
                #flush any remaining window properties
                self.resetWindowProps()
                if nextairedActive:
                    nextairedActive = False
                    xbmc.executebuiltin("RunScript(script.tv.show.next.aired,tvshowtitle=165628787629692696)")
                lastListItem = ""
                curListItem = ""
                curFolder = ""
                curFolderLast = ""
                self.widgetContainerPrefix = ""
            elif xbmc.getCondVisibility("Window.IsActive(fullscreenvideo)"):
                #fullscreen video active
                self.monitor.waitForAbort(2)
                self.delayedTaskInterval += 2
                self.widgetTaskInterval += 2
            else:
                #other window visible
                self.monitor.waitForAbort(0.5)
                self.delayedTaskInterval += 0.5
                self.widgetTaskInterval += 0.5
                   
    def doBackgroundWork(self):
        try:
            logMsg("Started Background worker...")
            self.getStudioLogos()
            self.genericWindowProps()
            if not self.imdb_top250: self.imdb_top250 = artutils.getImdbTop250()
            self.checkNotifications()
            self.saveCacheToFile()
            logMsg("Ended Background worker...")
        except Exception as e:
            logMsg("ERROR in ListitemMonitor doBackgroundWork ! --> " + str(e), 0)
    
    def saveCacheToFile(self):
        libraryCache = {}
        libraryCache["SetsCache"] = self.moviesetCache
        libraryCache["streamdetailsCache"] = self.streamdetailsCache
        libraryCache["extendedinfocache"] = self.extendedinfocache
        widgetcache = WINDOW.getProperty("skinhelper-widgetself.contentType").decode("utf-8")
        if widgetcache: libraryCache["widgetcache"] = eval(widgetcache)
        saveDataToCacheFile(self.cachePath,libraryCache)
        actorcache = WINDOW.getProperty("SkinHelper.ActorImages").decode("utf-8")
        if actorcache:
            saveDataToCacheFile(self.ActorImagesCachePath,eval(actorcache))
             
    def getCacheFromFile(self):
        #library items cache
        data = getDataFromCacheFile(self.cachePath)
        if data.has_key("SetsCache"):
            self.moviesetCache = data["SetsCache"]
        if data.has_key("streamdetailsCache"):
            self.streamdetailsCache = data["streamdetailsCache"]
        if data.has_key("extendedinfocache"):
            self.extendedinfocache = data["extendedinfocache"]
            
        #actorimagescache
        data = getDataFromCacheFile(self.ActorImagesCachePath)
        if data: WINDOW.setProperty("SkinHelper.ActorImages", repr(data))

    def checkNotifications(self):
        try:
            currentHour = time.strftime("%H")
            #weather notifications
            winw = xbmcgui.Window(12600)
            if xbmc.getCondVisibility("Skin.HasSetting(EnableWeatherNotifications) + !IsEmpty(Window(Weather).Property(Alerts.RSS)) + !IsEmpty(Window(Weather).Property(Current.Condition))") and currentHour != self.lastWeatherNotificationCheck:
                dialog = xbmcgui.Dialog()
                dialog.notification(xbmc.getLocalizedString(31294), winw.getProperty("Alerts"), xbmcgui.NOTIFICATION_WARNING, 8000)
                self.lastWeatherNotificationCheck = currentHour
            
            #nextaired notifications
            if (xbmc.getCondVisibility("Skin.HasSetting(EnableNextAiredNotifications) + System.HasAddon(script.tv.show.next.aired)") and currentHour != self.lastNextAiredNotificationCheck):
                if (WINDOW.getProperty("NextAired.TodayShow")):
                    dialog = xbmcgui.Dialog()
                    dialog.notification(xbmc.getLocalizedString(31295), WINDOW.getProperty("NextAired.TodayShow"), xbmcgui.NOTIFICATION_WARNING, 8000)
                    self.lastNextAiredNotificationCheck = currentHour
        except Exception as e:
            logMsg("ERROR in checkNotifications ! --> " + str(e), 0)
    
    def genericWindowProps(self):
        
        #GET TOTAL ADDONS COUNT       
        allAddonsCount = 0
        media_array = getJSON('Addons.GetAddons','{ }')
        for item in media_array:
            allAddonsCount += 1
        WINDOW.setProperty("SkinHelper.TotalAddons",str(allAddonsCount))
        
        addontypes = []
        addontypes.append( ["executable", "SkinHelper.TotalProgramAddons", 0] )
        addontypes.append( ["video", "SkinHelper.TotalVideoAddons", 0] )
        addontypes.append( ["audio", "SkinHelper.TotalAudioAddons", 0] )
        addontypes.append( ["image", "SkinHelper.TotalPicturesAddons", 0] )

        for type in addontypes:
            media_array = getJSON('Addons.GetAddons','{ "content": "%s" }' %type[0])
            for item in media_array:
                type[2] += 1
            WINDOW.setProperty(type[1],str(type[2]))    
                
        #GET FAVOURITES COUNT        
        allFavouritesCount = 0
        media_array = getJSON('Favourites.GetFavourites','{ }')
        for item in media_array:
            allFavouritesCount += 1
        WINDOW.setProperty("SkinHelper.TotalFavourites",str(allFavouritesCount))

        #GET TV CHANNELS COUNT
        if xbmc.getCondVisibility("Pvr.HasTVChannels"):
            allTvChannelsCount = 0
            media_array = getJSON('PVR.GetChannels','{"channelgroupid": "alltv" }' )
            for item in media_array:
                allTvChannelsCount += 1
            WINDOW.setProperty("SkinHelper.TotalTVChannels",str(allTvChannelsCount))
        
        #GET MOVIE SETS COUNT
        allMovieSetsCount = 0
        allMoviesInSetCount = 0
        media_array = getJSON('VideoLibrary.GetMovieSets','{}' )
        for item in media_array:
            allMovieSetsCount += 1
            media_array2 = getJSON('VideoLibrary.GetMovieSetDetails','{"setid": %s}' %item["setid"])
            for item in media_array2:
                allMoviesInSetCount +=1
        WINDOW.setProperty("SkinHelper.TotalMovieSets",str(allMovieSetsCount))
        WINDOW.setProperty("SkinHelper.TotalMoviesInSets",str(allMoviesInSetCount))

        #GET RADIO CHANNELS COUNT
        if xbmc.getCondVisibility("Pvr.HasRadioChannels"):
            allRadioChannelsCount = 0
            media_array = getJSON('PVR.GetChannels','{"channelgroupid": "allradio" }' )
            for item in media_array:
                allRadioChannelsCount += 1
            WINDOW.setProperty("SkinHelper.TotalRadioChannels",str(allRadioChannelsCount))        
               
    def resetWindowProps(self):
        #reset all window props provided by the script...
        WINDOW.clearProperty("SkinHelper.ListItemStudioLogo")
        WINDOW.clearProperty("SkinHelper.ListItemStudioLogoColor")
        WINDOW.clearProperty("SkinHelper.ListItemStudios")
        WINDOW.clearProperty('SkinHelper.ListItemDuration')
        WINDOW.clearProperty('SkinHelper.ListItemDuration.Hours')
        WINDOW.clearProperty('SkinHelper.ListItemDuration.Minutes')
        WINDOW.clearProperty('SkinHelper.ListItemSubtitles')
        WINDOW.clearProperty('SkinHelper.ListItemSubtitles.Count')
        WINDOW.clearProperty('SkinHelper.ListItemAllAudioStreams')
        WINDOW.clearProperty('SkinHelper.ListItemAllAudioStreams.Count')
        WINDOW.clearProperty('SkinHelper.ListItemLanguages')
        WINDOW.clearProperty('SkinHelper.ListItemLanguages.Count')
        WINDOW.clearProperty('SkinHelper.ListItemAudioStreams.Count')
        WINDOW.clearProperty('SkinHelper.ListItemGenres')
        WINDOW.clearProperty('SkinHelper.ListItemDirectors')
        WINDOW.clearProperty("SkinHelper.ExtraFanArtPath")
        WINDOW.clearProperty("SkinHelper.Music.Banner") 
        WINDOW.clearProperty("SkinHelper.Music.ClearLogo") 
        WINDOW.clearProperty("SkinHelper.Music.DiscArt")
        WINDOW.clearProperty("SkinHelper.Music.FanArt")
        WINDOW.clearProperty("SkinHelper.Music.Thumb")
        WINDOW.clearProperty("SkinHelper.Music.Info")
        WINDOW.clearProperty("SkinHelper.Music.TrackList")
        WINDOW.clearProperty("SkinHelper.Music.SongCount")
        WINDOW.clearProperty("SkinHelper.Music.albumCount")
        WINDOW.clearProperty("SkinHelper.Music.AlbumList")
        WINDOW.clearProperty("SkinHelper.Music.ExtraFanArt")
        WINDOW.clearProperty("SkinHelper.PVR.Thumb") 
        WINDOW.clearProperty("SkinHelper.PVR.FanArt") 
        WINDOW.clearProperty("SkinHelper.PVR.ChannelLogo")
        WINDOW.clearProperty("SkinHelper.PVR.Poster")
        WINDOW.clearProperty("SkinHelper.PVR.Landscape")
        WINDOW.clearProperty("SkinHelper.PVR.ClearArt")
        WINDOW.clearProperty("SkinHelper.PVR.CharacterArt") 
        WINDOW.clearProperty("SkinHelper.PVR.ClearLogo")
        WINDOW.clearProperty("SkinHelper.PVR.Banner")
        WINDOW.clearProperty("SkinHelper.PVR.DiscArt")
        WINDOW.clearProperty("SkinHelper.PVR.Plot")
        WINDOW.clearProperty("SkinHelper.PVR.Channel")
        WINDOW.clearProperty("SkinHelper.PVR.Genre")
        WINDOW.clearProperty("SkinHelper.PVR.ExtraFanArt")
        WINDOW.clearProperty("SkinHelper.Player.AddonName")
        WINDOW.clearProperty("SkinHelper.ForcedView")
        WINDOW.clearProperty('SkinHelper.MovieSet.Title')
        WINDOW.clearProperty('SkinHelper.MovieSet.Runtime')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration.Hours')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration.Minutes')
        WINDOW.clearProperty('SkinHelper.MovieSet.Writer')
        WINDOW.clearProperty('SkinHelper.MovieSet.Director')
        WINDOW.clearProperty('SkinHelper.MovieSet.Genre')
        WINDOW.clearProperty('SkinHelper.MovieSet.Country')
        WINDOW.clearProperty('SkinHelper.MovieSet.Studio')
        WINDOW.clearProperty('SkinHelper.MovieSet.Years')
        WINDOW.clearProperty('SkinHelper.MovieSet.Year')
        WINDOW.clearProperty('SkinHelper.MovieSet.Count')
        WINDOW.clearProperty('SkinHelper.MovieSet.Plot')
        WINDOW.clearProperty('SkinHelper.MovieSet.ExtendedPlot')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesMeter')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesRating')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesAudienceRating')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesConsensus')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesAwards')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesBoxOffice')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesFresh')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesRotten')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesImage')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesAudienceMeter')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesDVDRelease')
        WINDOW.clearProperty('SkinHelper.MetaCritic.Rating')
        WINDOW.clearProperty('SkinHelper.IMDB.Rating')
        WINDOW.clearProperty('SkinHelper.IMDB.Votes')
        WINDOW.clearProperty('SkinHelper.TMDB.Budget')
        WINDOW.clearProperty('SkinHelper.Budget.formatted')
        WINDOW.clearProperty('SkinHelper.TMDB.Budget.mln')
        WINDOW.clearProperty('SkinHelper.TMDB.Budget.mln')
        WINDOW.clearProperty('SkinHelper.TMDB.Budget.mln')
        WINDOW.clearProperty('SkinHelper.TMDB.Budget.mln')
        WINDOW.clearProperty('SkinHelper.AnimatedPoster')
        WINDOW.clearProperty('SkinHelper.AnimatedFanart')
        
        totalNodes = 50
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.MovieSet.' + str(i) + '.Title'): break
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Title')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.FanArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Poster')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Landscape')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.DiscArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.ClearLogo')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.ClearArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Banner')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Rating')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Resolution')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Resolution.Type')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.AspectRatio')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Codec')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.AudioCodec')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.AudioChannels')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.AudioLanguage')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Subtitle')
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.ListItemGenre.' + str(i)): break
            WINDOW.clearProperty('SkinHelper.ListItemGenre.' + str(i))
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.ListItemAudioStreams.%d.AudioCodec' % i): break
            WINDOW.clearProperty('SkinHelper.ListItemAudioStreams.%d.Language' % i)
            WINDOW.clearProperty('SkinHelper.ListItemAudioStreams.%d.AudioCodec' % i)
            WINDOW.clearProperty('SkinHelper.ListItemAudioStreams.%d.AudioChannels' % i)
            WINDOW.clearProperty('SkinHelper.ListItemAudioStreams.%d'%i)
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.ExtraFanArt.' + str(i)):
                break
            WINDOW.clearProperty('SkinHelper.ExtraFanArt.' + str(i))
            
    def setMovieSetDetails(self):
        #get movie set details -- thanks to phil65 - used this idea from his skin info script
        allProperties = []
        if not self.liDbId or not self.liPath: return
        if self.liPath.startswith("videodb://movies/sets/"):
            #try to get from cache first
            cacheStr = self.liLabel+self.liDbId
            if self.moviesetCache.get(cacheStr):
                allProperties = self.moviesetCache.get(cacheStr)
                
            if self.liDbId and not allProperties:
                #get values from json api
                json_response = getJSON('VideoLibrary.GetMovieSetDetails', '{"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer", "playcount", "genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country", "streamdetails"], "sort": { "order": "ascending",  "method": "year" }} }' % self.liDbId)
                if json_response:
                    count = 0
                    unwatchedcount = 0
                    watchedcount = 0
                    runtime = 0
                    runtime_mins = 0
                    writer = []
                    director = []
                    genre = []
                    country = []
                    studio = []
                    years = []
                    plot = ""
                    title_list = ""
                    title_header = "[B]" + str(json_response['limits']['total']) + " " + xbmc.getLocalizedString(20342) + "[/B][CR]"
                    set_fanart = []
                    for item in json_response['movies']:
                        if item["playcount"] == 0:
                            unwatchedcount += 1
                        else:
                            watchedcount += 1
                        art = item['art']
                        fanart = art.get('fanart', '')
                        set_fanart.append(fanart)
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Title',item['label']) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Poster',art.get('poster', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.FanArt',fanart) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Landscape',art.get('landscape', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.DiscArt',art.get('discart', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.ClearLogo',art.get('clearlogo', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.ClearArt',art.get('clearart', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Banner',art.get('banner', '')) )
                        allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Rating',str(item.get('rating', ''))) )
                        if item.get('streamdetails',''):
                            streamdetails = item["streamdetails"]
                            audiostreams = streamdetails.get('audio',[])
                            videostreams = streamdetails.get('video',[])
                            subtitles = streamdetails.get('subtitle',[])
                            if len(videostreams) > 0:
                                stream = videostreams[0]
                                height = stream.get("height","")
                                width = stream.get("width","")
                                if height and width:
                                    resolution = ""
                                    if width <= 720 and height <= 480: resolution = "480"
                                    elif width <= 768 and height <= 576: resolution = "576"
                                    elif width <= 960 and height <= 544: resolution = "540"
                                    elif width <= 1280 and height <= 720: resolution = "720"
                                    elif width <= 1920 and height <= 1080: resolution = "1080"
                                    elif width * height >= 6000000: resolution = "4K"
                                    allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Resolution',resolution) )
                                if stream.get("codec",""):
                                    allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.Codec',str(stream["codec"]))   )  
                                if stream.get("aspect",""):
                                    allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.AspectRatio',str(round(stream["aspect"], 2))) )
                            if len(audiostreams) > 0:
                                #grab details of first audio stream
                                stream = audiostreams[0]
                                allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.AudioCodec',stream.get('codec','')) )
                                allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.AudioChannels',str(stream.get('channels',''))) )
                                allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.AudioLanguage',stream.get('language','')) )
                            if len(subtitles) > 0:
                                #grab details of first subtitle
                                allProperties.append( ('SkinHelper.MovieSet.' + str(count) + '.SubTitle',subtitles[0].get('language','')) )

                        title_list += item['label'] + " (" + str(item['year']) + ")[CR]"
                        if item['plotoutline']:
                            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plotoutline'] + "[CR][CR]"
                        else:
                            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plot'] + "[CR][CR]"
                        runtime += item['runtime']
                        count += 1
                        if item.get("writer"):
                            writer += [w for w in item["writer"] if w and w not in writer]
                        if item.get("director"):
                            director += [d for d in item["director"] if d and d not in director]
                        if item.get("genre"):
                            genre += [g for g in item["genre"] if g and g not in genre]
                        if item.get("country"):
                            country += [c for c in item["country"] if c and c not in country]
                        if item.get("studio"):
                            studio += [s for s in item["studio"] if s and s not in studio]
                        years.append(str(item['year']))
                    allProperties.append( ('SkinHelper.MovieSet.Plot', plot) )
                    if json_response['limits']['total'] > 1:
                        allProperties.append( ('SkinHelper.MovieSet.ExtendedPlot', title_header + title_list + "[CR]" + plot) )
                    else:
                        allProperties.append( ('SkinHelper.MovieSet.ExtendedPlot', plot) )
                    allProperties.append( ('SkinHelper.MovieSet.Title', title_list) )
                    allProperties.append( ('SkinHelper.MovieSet.Runtime', str(runtime / 60)) )
                    self.setDuration(str(runtime / 60))
                    durationString = self.getDurationString(runtime / 60)
                    if durationString:
                        allProperties.append( ('SkinHelper.MovieSet.Duration', durationString[2]) )
                        allProperties.append( ('SkinHelper.MovieSet.Duration.Hours', durationString[0]) )
                        allProperties.append( ('SkinHelper.MovieSet.Duration.Minutes', durationString[1]) )
                    allProperties.append( ('SkinHelper.MovieSet.Writer', " / ".join(writer)) )
                    allProperties.append( ('SkinHelper.MovieSet.Director', " / ".join(director)) )
                    self.setDirector(" / ".join(director))
                    allProperties.append( ('SkinHelper.MovieSet.Genre', " / ".join(genre)) )
                    self.setGenre(" / ".join(genre))
                    allProperties.append( ('SkinHelper.MovieSet.Country', " / ".join(country)) )
                    studioString = " / ".join(studio)
                    allProperties.append( ('SkinHelper.MovieSet.Studio', studioString) )
                    self.setStudioLogo(studioString)
                    allProperties.append( ('SkinHelper.MovieSet.Years', " / ".join(years)) )
                    allProperties.append( ('SkinHelper.MovieSet.Year', years[0] + " - " + years[-1]) )
                    allProperties.append( ('SkinHelper.MovieSet.Count', str(json_response['limits']['total'])) )
                    allProperties.append( ('SkinHelper.MovieSet.WatchedCount', str(watchedcount)) )
                    allProperties.append( ('SkinHelper.MovieSet.UnWatchedCount', str(unwatchedcount)) )
                    allProperties.append( ('SkinHelper.MovieSet.Extrafanarts', repr(set_fanart)) )
                #save to cache
                self.moviesetCache[cacheStr] = allProperties
            
            #Process properties
            for item in allProperties:
                if item[0] == "SkinHelper.MovieSet.Extrafanarts":
                    if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtraFanart)"):
                        efaProp = 'EFA_FROMWINDOWPROP_' + cacheStr
                        WINDOW.setProperty(efaProp, item[1])
                        WINDOW.setProperty('SkinHelper.ExtraFanArtPath', "plugin://script.skin.helper.service/?action=EXTRAFANART&path=%s" %single_urlencode(try_encode(efaProp)))
                else: WINDOW.setProperty(item[0],item[1])
            
    def setContentHeader(self):
        WINDOW.clearProperty("SkinHelper.ContentHeader")
        itemscount = xbmc.getInfoLabel("Container.NumItems")
        if itemscount:
            if xbmc.getInfoLabel("Container.ListItemNoWrap(0).Label").startswith("*") or xbmc.getInfoLabel("Container.ListItemNoWrap(1).Label").startswith("*"):
                itemscount = int(itemscount) - 1
            
            headerprefix = ""
            if self.contentType == "movies":
                headerprefix = xbmc.getLocalizedString(36901)
            elif self.contentType == "tvshows":
                headerprefix = xbmc.getLocalizedString(36903)
            elif self.contentType == "seasons":
                headerprefix = xbmc.getLocalizedString(36905)
            elif self.contentType == "episodes":
                headerprefix = xbmc.getLocalizedString(36907)
            elif self.contentType == "sets":
                headerprefix = xbmc.getLocalizedString(36911)
            elif self.contentType == "albums":
                headerprefix = xbmc.getLocalizedString(36919)
            elif self.contentType == "songs":
                headerprefix = xbmc.getLocalizedString(36921)
            elif self.contentType == "artists":
                headerprefix = xbmc.getLocalizedString(36917)
            
            if headerprefix:        
                WINDOW.setProperty("SkinHelper.ContentHeader","%s %s" %(itemscount,headerprefix) )
        
    def setAddonName(self):
        # set addon name as property
        if not xbmc.Player().isPlayingAudio():
            if (xbmc.getCondVisibility("Container.Content(plugins) | !IsEmpty(Container.PluginName)")):
                AddonName = xbmc.getInfoLabel('Container.PluginName').decode('utf-8')
                AddonName = xbmcaddon.Addon(AddonName).getAddonInfo('name')
                WINDOW.setProperty("SkinHelper.Player.AddonName", AddonName)
    
    def setGenre(self,genre=""):
        if not genre: genre = xbmc.getInfoLabel('%sListItem.Genre' %self.widgetContainerPrefix).decode('utf-8')
        genres = []
        if "/" in genre:
            genres = genre.split(" / ")
        else:
            genres.append(genre)
        WINDOW.setProperty('SkinHelper.ListItemGenres', "[CR]".join(genres))
        count = 0
        for genre in genres:
            WINDOW.setProperty("SkinHelper.ListItemGenre." + str(count),genre)
            count +=1
    
    def setDirector(self, director=""):
        if not director: director = xbmc.getInfoLabel('%sListItem.Director'%self.widgetContainerPrefix).decode('utf-8')
        directors = []
        if "/" in director:
            directors = director.split(" / ")
        else:
            directors.append(director)
        
        WINDOW.setProperty('SkinHelper.ListItemDirectors', "[CR]".join(directors))
       
    def setPVRThumbs(self, multiThreaded=False):
                
        title = self.liTitle
        channel = xbmc.getInfoLabel("%sListItem.ChannelName"%self.widgetContainerPrefix).decode('utf-8')
        #path = self.liFile
        path = self.liPath
        genre = xbmc.getInfoLabel("%sListItem.Genre"%self.widgetContainerPrefix).decode('utf-8')
        
        if xbmc.getCondVisibility("%sListItem.IsFolder"%self.widgetContainerPrefix) and not channel and not title:
            #assume grouped recordings curFolder
            title = self.liLabel
        
        if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnablePVRThumbs)") or not title:
            return
        
        cacheStr = title + channel + "SkinHelper.PVR.Artwork"
        
        if self.pvrArtCache.has_key(cacheStr):
            artwork = self.pvrArtCache[cacheStr]
        else:           
            if self.contentType == "tvrecordings": type = "recordings"
            else: type = "channels"
            
            artwork = artutils.getPVRThumbs(title, channel, type, path, genre)
            self.pvrArtCache[cacheStr] = artwork
        
        #return if another listitem was focused in the meanwhile
        if multiThreaded and not (title == xbmc.getInfoLabel("ListItem.Title").decode('utf-8') or title == xbmc.getInfoLabel("%sListItem.Title"%self.widgetContainerPrefix).decode('utf-8') or title == xbmc.getInfoLabel("%sListItem.Label"%self.widgetContainerPrefix).decode('utf-8')):
            return
        
        #set window props
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.PVR." + key,value)

    def setStudioLogo(self,studio=""):
        
        if not studio: studio = xbmc.getInfoLabel('%sListItem.Studio'%self.widgetContainerPrefix).decode('utf-8')

        studios = []
        if "/" in studio:
            studios = studio.split(" / ")
            WINDOW.setProperty("SkinHelper.ListItemStudio", studios[0])
            WINDOW.setProperty('SkinHelper.ListItemStudios', "[CR]".join(studios))    
        else:
            studios.append(studio)
            WINDOW.setProperty("SkinHelper.ListItemStudio", studio)
            WINDOW.setProperty("SkinHelper.ListItemStudios", studio)

        studiologo = matchStudioLogo(studio, self.allStudioLogos)
        studiologoColor = matchStudioLogo(studio, self.allStudioLogosColor)
        WINDOW.setProperty("SkinHelper.ListItemStudioLogo", studiologo)        
        WINDOW.setProperty("SkinHelper.ListItemStudioLogoColor", studiologoColor)        
        
        return studiologo
                
    def getStudioLogos(self):
        #fill list with all studio logos
        allLogos = {}
        allLogosColor = {}

        CustomStudioImagesPath = xbmc.getInfoLabel("Skin.String(SkinHelper.CustomStudioImagesPath)").decode('utf-8')
        if CustomStudioImagesPath + xbmc.getSkinDir() != self.LastCustomStudioImagesPath:
            #only proceed if the custom path or skin has changed...
            self.LastCustomStudioImagesPath = CustomStudioImagesPath + xbmc.getSkinDir()
            
            #add the custom path to the list
            if CustomStudioImagesPath:
                path = CustomStudioImagesPath
                if not (CustomStudioImagesPath.endswith("/") or CustomStudioImagesPath.endswith("\\")):
                    CustomStudioImagesPath = CustomStudioImagesPath + os.sep()
                    allLogos = listFilesInPath(CustomStudioImagesPath, allLogos)
            
            #add skin provided paths
            if xbmcvfs.exists("special://skin/extras/flags/studios/"):
                allLogos = listFilesInPath("special://skin/extras/flags/studios/", allLogos)
            if xbmcvfs.exists("special://skin/extras/flags/studioscolor/"):
                allLogosColor = listFilesInPath("special://skin/extras/flags/studioscolor/",allLogosColor)
            
            #add images provided by the image resource addons
            if xbmc.getCondVisibility("System.HasAddon(resource.images.studios.white)"):
                allLogos = getResourceAddonFiles("resource.images.studios.white", allLogos)
            if xbmc.getCondVisibility("System.HasAddon(resource.images.studios.coloured)"):
                allLogosColor = getResourceAddonFiles("resource.images.studios.coloured",allLogosColor)
            
            #assign all found logos in the list
            self.allStudioLogos = allLogos
            self.allStudioLogosColor = allLogosColor
            #also store the logos in window property for access by webservice
            WINDOW.setProperty("SkinHelper.allStudioLogos",repr(self.allStudioLogos))
            WINDOW.setProperty("SkinHelper.allStudioLogosColor",repr(self.allStudioLogosColor))
    
    def setDuration(self,currentDuration=""):
        if not currentDuration:
            currentDuration = xbmc.getInfoLabel("%sListItem.Duration"%self.widgetContainerPrefix)
        
        if ":" in currentDuration:
            durLst = currentDuration.split(":")
            if len(durLst) == 1:
                currentDuration = "0"
            elif len(durLst) == 2:
                currentDuration = durLst[0]
            elif len(durLst) == 3:
                currentDuration = str((int(durLst[0])*60) + int(durLst[1]))
                
        # monitor listitem to set duration
        if currentDuration:
            durationString = self.getDurationString(currentDuration)
            if durationString:
                WINDOW.setProperty('SkinHelper.ListItemDuration', durationString[2])
                WINDOW.setProperty('SkinHelper.ListItemDuration.Hours', durationString[0])
                WINDOW.setProperty('SkinHelper.ListItemDuration.Minutes', durationString[1])
        
    def getDurationString(self, duration):
        if duration == None or duration == 0:
            return None
        try:
            full_minutes = int(duration)
            minutes = str(full_minutes % 60)
            minutes = str(minutes).zfill(2)
            hours   = str(full_minutes // 60)
            durationString = hours + ':' + minutes
        except Exception as e:
            logMsg("ERROR in getDurationString ! --> " + str(e), 0)
            return None
        return ( hours, minutes, durationString )
              
    def setMusicPlayerDetails(self):
        artwork = {}
        artist = ""
        title = ""
        album = ""
        #get the playing item from the player...
        json_result = getJSON('Player.GetActivePlayers', '{}')
        for item in json_result:
            if item.get("type","") == "audio":
                json_result = getJSON('Player.GetItem', '{ "playerid": %d, "properties": [ "title","albumid","artist","album","displayartist" ] }' %item.get("playerid"))
                if json_result.get("title"):
                    if json_result.get("artist"):
                        artist = json_result.get("displayartist")
                        title = json_result.get("title")
                        album = json_result.get("album").split(" (")[0]
                    else:
                        if not artist:
                            #fix for internet streams
                            splitchar = None
                            if " - " in json_result.get("title"): splitchar = " - "
                            elif "- " in json_result.get("title"): splitchar = "- "
                            elif " -" in json_result.get("title"): splitchar = " -"
                            elif "-" in json_result.get("title"): splitchar = "-"
                            if splitchar:
                                artist = json_result.get("title").split(splitchar)[0]
                                title = json_result.get("title").split(splitchar)[1]
                    logMsg("setMusicPlayerDetails: " + repr(json_result))
        
        cacheId = artist+album+title
        #get the items from cache first
        if self.musicArtCache.has_key(cacheId + "SkinHelper.Music.Art"):
            artwork = self.musicArtCache[cacheId + "SkinHelper.Music.Art"]
            logMsg("setMusicPlayerDetails FOUND CACHE FOR  artist: %s - album: %s - title: %s "%(artist,album,title))
        else:
            logMsg("setMusicPlayerDetails CACHE NOT FOUND FOR  artist: %s - album: %s - title: %s "%(artist,album,title))
            artwork = artutils.getMusicArtwork(artist,album,title)
            if artwork.get("info") and xbmc.getInfoLabel("MusicPlayer.Comment"):
                artwork["info"] = normalize_string(xbmc.getInfoLabel("MusicPlayer.Comment")).replace('\n', ' ').replace('\r', '').split(" a href")[0] + "  -  " + artwork["info"]
            self.musicArtCache[cacheId + "SkinHelper.Music.Art"] = artwork

        #set properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.Player.Music." + key,value.encode("utf-8"))
    
    def setMusicDetails(self,multiThreaded=False):
        artwork = {}
        artist = xbmc.getInfoLabel("%sListItem.Artist"%self.widgetContainerPrefix).decode('utf-8')
        album = xbmc.getInfoLabel("%sListItem.Album"%self.widgetContainerPrefix).decode('utf-8')
        title = self.liTitle
        label = self.liLabel
        cacheId = artist+album
        
        #get the items from cache first
        if self.musicArtCache.has_key(cacheId + "SkinHelper.Music.Art"):
            artwork = self.musicArtCache[cacheId + "SkinHelper.Music.Art"]
        else:
            artwork = artutils.getMusicArtwork(artist,album,title)
            self.musicArtCache[cacheId + "SkinHelper.Music.Art"] = artwork
        
        #return if another listitem was focused in the meanwhile
        if multiThreaded and label != xbmc.getInfoLabel("%sListItem.Label"%self.widgetContainerPrefix).decode('utf-8'):
            return
        
        #set properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.Music." + key,value)
              
    def setStreamDetails(self):
        streamdetails = {}
        if not self.liDbId: return
        
        cacheStr = self.liDbId + self.contentType
        if self.streamdetailsCache.get(cacheStr):
            #get data from cache
            streamdetails = self.streamdetailsCache[cacheStr]
        else:
            json_result = {}
            # get data from json
            if "movies" in self.contentType and self.liDbId:
                json_result = getJSON('VideoLibrary.GetMovieDetails', '{ "movieid": %d, "properties": [ "title", "streamdetails" ] }' %int(self.liDbId))
            elif self.contentType == "episodes" and self.liDbId:
                json_result = getJSON('VideoLibrary.GetEpisodeDetails', '{ "episodeid": %d, "properties": [ "title", "streamdetails" ] }' %int(self.liDbId))
            elif self.contentType == "musicvideos" and self.liDbId:
                json_result = getJSON('VideoLibrary.GetMusicVideoDetails', '{ "musicvideoid": %d, "properties": [ "title", "streamdetails" ] }' %int(self.liDbId))       
            if json_result.has_key("streamdetails"):
                audio = json_result["streamdetails"]['audio']
                subtitles = json_result["streamdetails"]['subtitle']
                video = json_result["streamdetails"]['video']
                allAudio = []
                allAudioStr = []
                allSubs = []
                allLang = []
                count = 0
                for item in audio:
                    codec = item['codec']
                    channels = item['channels']
                    if "ac3" in codec: codec = "Dolby D"
                    elif "dca" in codec: codec = "DTS"
                    elif "dts-hd" in codec or "dtshd" in codec: codec = "DTS HD"
                    if channels == 1: channels = "1.0"
                    elif channels == 2: channels = "2.0"
                    elif channels == 3: channels = "2.1"
                    elif channels == 4: channels = "4.0"
                    elif channels == 5: channels = "5.0"
                    elif channels == 6: channels = "5.1"
                    elif channels == 7: channels = "6.1"
                    elif channels == 8: channels = "7.1"
                    elif channels == 9: channels = "8.1"
                    elif channels == 10: channels = "9.1"
                    else: channels = str(channels)
                    language = item.get('language','')
                    if language and language not in allLang:
                        allLang.append(language)
                    streamdetails['SkinHelper.ListItemAudioStreams.%d.Language'% count] = item['language']
                    streamdetails['SkinHelper.ListItemAudioStreams.%d.AudioCodec'%count] = item['codec']
                    streamdetails['SkinHelper.ListItemAudioStreams.%d.AudioChannels'%count] = str(item['channels'])
                    sep = "•".decode('utf-8')
                    audioStr = '%s %s %s %s %s' %(language,sep,codec,sep,channels)
                    streamdetails['SkinHelper.ListItemAudioStreams.%d'%count] = audioStr
                    allAudioStr.append(audioStr)
                    count += 1
                subscount = 0
                subscountUnique = 0
                for item in subtitles:
                    subscount += 1
                    if item['language'] not in allSubs:
                        allSubs.append(item['language'])
                        streamdetails['SkinHelper.ListItemSubtitles.%d'%subscountUnique] = item['language']
                        subscountUnique += 1
                streamdetails['SkinHelper.ListItemSubtitles'] = " / ".join(allSubs)
                streamdetails['SkinHelper.ListItemSubtitles.Count'] = str(subscount)
                streamdetails['SkinHelper.ListItemAllAudioStreams'] = " / ".join(allAudioStr)
                streamdetails['SkinHelper.ListItemAudioStreams.Count'] = str(len(allAudioStr))
                streamdetails['SkinHelper.ListItemLanguages'] = " / ".join(allLang)
                streamdetails['SkinHelper.ListItemLanguages.Count'] = str(len(allLang))
                if len(video) > 0:
                    stream = video[0]
                    streamdetails['SkinHelper.ListItemVideoHeight'] = str(stream.get("height",""))
                    streamdetails['SkinHelper.ListItemVideoWidth'] = str(stream.get("width",""))
                
                self.streamdetailsCache[cacheStr] = streamdetails
                
        if streamdetails:
            #set the window properties
            for key, value in streamdetails.iteritems():
                WINDOW.setProperty(key,value)
          
    def setForcedView(self):
        currentForcedView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %self.contentType)
        if xbmc.getCondVisibility("Control.IsVisible(%s) | IsEmpty(Container.Viewmode)" %currentForcedView):
            #skip if the view is already visible or if we're not in an actual media window
            return
        if self.contentType and currentForcedView and currentForcedView != "None" and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)") and not "pvr://guide" in self.liPath:
            WINDOW.setProperty("SkinHelper.ForcedView",currentForcedView)
            xbmc.executebuiltin("Container.SetViewMode(%s)" %currentForcedView)
            if not xbmc.getCondVisibility("Control.HasFocus(%s)" %currentForcedView):
                xbmc.sleep(100)
                xbmc.executebuiltin("Container.SetViewMode(%s)" %currentForcedView)
                xbmc.executebuiltin("SetFocus(%s)" %currentForcedView)
        else:
            WINDOW.clearProperty("SkinHelper.ForcedView")
        
    def checkExtraFanArt(self):
        efaPath = None
        efaFound = False
        extraFanArtfiles = []
        filename = self.liFile
        
        if xbmc.getCondVisibility("Window.IsActive(movieinformation) | !Skin.HasSetting(SkinHelper.EnableExtraFanart)"):
            return
        
        cachePath = self.liPath
        if "plugin.video.emby.movies" in self.liPath or "plugin.video.emby.musicvideos" in self.liPath:
            cachePath = filename
        
        #get the item from cache first
        if self.extraFanartCache.has_key(cachePath):
            if self.extraFanartCache[cachePath][0] == "None":
                return
            else:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath",self.extraFanartCache[cachePath][0])
                count = 0
                for file in self.extraFanartCache[cachePath][1]:
                    WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),file)
                    count +=1  
                return
        
        #support for emby addon
        if "plugin.video.emby" in self.liPath:
            efaPath = "plugin://plugin.video.emby/extrafanart?path=" + cachePath
            efaFound = True
        #lookup the extrafanart in the media location
        elif (self.liPath != None and (self.contentType in ["movies","seasons","episodes","tvshows","setmovies"] ) and not "videodb:" in self.liPath):
                           
            # do not set extra fanart for virtuals
            if "plugin://" in self.liPath or "addon://" in self.liPath or "sources" in self.liPath:
                self.extraFanartCache[self.liPath] = "None"
            else:
                
                if "/" in self.liPath: splitchar = "/"
                else: splitchar = "\\"
            
                if xbmcvfs.exists(self.liPath + "extrafanart"+splitchar):
                    efaPath = self.liPath + "extrafanart"+splitchar
                else:
                    pPath = self.liPath.rpartition(splitchar)[0]
                    pPath = pPath.rpartition(splitchar)[0]
                    if xbmcvfs.exists(pPath + splitchar + "extrafanart"+splitchar):
                        efaPath = pPath + splitchar + "extrafanart" + splitchar
                        
                if xbmcvfs.exists(efaPath):
                    dirs, files = xbmcvfs.listdir(efaPath)
                    count = 0
                    
                    for file in files:
                        if file.lower().endswith(".jpg"):
                            efaFound = True
                            WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),efaPath+file)
                            extraFanArtfiles.append(efaPath+file)
                            count +=1  
       
        if (efaPath != None and efaFound == True):
            WINDOW.setProperty("SkinHelper.ExtraFanArtPath",efaPath)
            self.extraFanartCache[cachePath] = [efaPath, extraFanArtfiles]     
        else:
            self.extraFanartCache[cachePath] = ["None",[]]
    
    def setAnimatedPoster(self,multiThreaded=False,liImdb=""):
        #check animated posters
        if not liImdb: liImdb = self.liImdb
        if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAnimatedPosters)") or not liImdb:
            return
        if (self.contentType == "movies" or self.contentType=="setmovies"):
            #check cache first
            cacheStr = "animatedartwork-%s"%liImdb
            if self.extendedinfocache.has_key(cacheStr):
                result = self.extendedinfocache[cacheStr]
            else:
                result = artutils.getAnimatedPosters(liImdb)
                self.extendedinfocache[cacheStr] = result
            #return if another listitem was focused in the meanwhile
            if multiThreaded and not liImdb == self.liImdb:
                return
            WINDOW.setProperty("SkinHelper.AnimatedPoster",result.get('animated_poster',""))
            WINDOW.setProperty("SkinHelper.AnimatedFanart",result.get('animated_fanart',""))
        
    def setExtendedMovieInfo(self,multiThreaded=False,liImdb=""):
        result = {}
        if not liImdb: liImdb = self.liImdb
        if (self.contentType == "movies" or self.contentType=="setmovies") and liImdb:
            if self.extendedinfocache.get(liImdb):
                #get data from cache
                result = self.extendedinfocache[liImdb]
            elif not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
                logMsg("Retrieving ExtendedMovieInfofor ImdbId--> %s  - contentType: %s" %(liImdb,self.contentType))
                #get info from OMDB 
                url = 'http://www.omdbapi.com/?i=%s&plot=short&tomatoes=true&r=json' %liImdb
                res = requests.get(url)
                result = json.loads(res.content.decode('utf-8','replace'))

                for key, value in result.iteritems():
                    if value == "N/A":
                        result[key] = ""
                
                #get info from TMDB
                url = 'http://api.themoviedb.org/3/find/%s?external_source=imdb_id&api_key=%s' %(liImdb,artutils.tmdb_apiKey)
                response = requests.get(url)
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.get("movie_results"):
                    data = data.get("movie_results")
                    if len(data) == 1:
                        url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s' %(data[0].get("id"),artutils.tmdb_apiKey)
                        response = requests.get(url)
                        data = json.loads(response.content.decode('utf-8','replace'))
                        if data.get("budget") and data.get("budget") > 0:
                            result["budget"] = str(data.get("budget",""))
                            mln = float(data.get("budget")) / 1000000
                            mln = "%.1f" % mln
                            result["budget.formatted"] = "$ %s mln." %mln.replace(".0","").replace(".",",")
                            result["budget.mln"] = mln
                        
                        if data.get("revenue","") and data.get("revenue") > 0:
                            result["revenue"] = str(data.get("revenue",""))
                            mln = float(data.get("revenue")) / 1000000
                            mln = "%.1f" % mln
                            result["revenue.formatted"] = "$ %s mln." %mln.replace(".0","").replace(".",",")
                            result["revenue.mln"] = mln
                            
                        result["tagline"] = data.get("tagline","")
                        result["homepage"] = data.get("homepage","")
                        result["status"] = data.get("status","")
                        result["popularity"] = str(data.get("popularity",""))
                
                #save to cache
                if result: self.extendedinfocache[self.liImdb] = result
            
            #return if another listitem was focused in the meanwhile
            if multiThreaded and not (liImdb == xbmc.getInfoLabel("%sListItem.IMDBNumber"%self.widgetContainerPrefix).decode('utf-8') or liImdb == xbmc.getInfoLabel("%sListItem.Property(IMDBNumber)"%self.widgetContainerPrefix).decode('utf-8')):
                return
            
            #set the window props
            if result:
                WINDOW.setProperty("SkinHelper.RottenTomatoesRating",result.get('tomatoRating',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesMeter",result.get('tomatoMeter',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesFresh",result.get('tomatoFresh',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesReviews",result.get('tomatoReviews',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesRotten",result.get('tomatoRotten',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesImage",result.get('tomatoImage',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesConsensus",result.get('tomatoConsensus',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesAwards",result.get('Awards',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesBoxOffice",result.get('BoxOffice',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesDVDRelease",result.get('DVD',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesAudienceMeter",result.get('tomatoUserMeter',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesAudienceRating",result.get('tomatoUserRating',""))
                WINDOW.setProperty("SkinHelper.RottenTomatoesAudienceReviews",result.get('tomatoUserReviews',""))
                WINDOW.setProperty("SkinHelper.MetaCritic.Rating",result.get('Metascore',""))
                WINDOW.setProperty("SkinHelper.IMDB.Rating",result.get('imdbRating',""))
                WINDOW.setProperty("SkinHelper.IMDB.Votes",result.get('imdbVotes',""))
                WINDOW.setProperty("SkinHelper.IMDB.MPAA",result.get('Rated',""))
                WINDOW.setProperty("SkinHelper.IMDB.Top250",self.imdb_top250.get(liImdb,""))
                WINDOW.setProperty("SkinHelper.IMDB.Runtime",result.get('Runtime',""))
                WINDOW.setProperty("SkinHelper.TMDB.Budget",result.get('budget',""))
                WINDOW.setProperty("SkinHelper.TMDB.Budget.formatted",result.get('budget.formatted',""))
                WINDOW.setProperty("SkinHelper.TMDB.Budget.mln",result.get('budget.mln',""))
                WINDOW.setProperty("SkinHelper.TMDB.revenue",result.get('revenue',""))
                WINDOW.setProperty("SkinHelper.TMDB.revenue.formatted",result.get('revenue.formatted',""))
                WINDOW.setProperty("SkinHelper.TMDB.revenue.mln",result.get('revenue.mln',""))
                WINDOW.setProperty("SkinHelper.TMDB.tagline",result.get('tagline',""))
                WINDOW.setProperty("SkinHelper.TMDB.homepage",result.get('homepage',""))
                WINDOW.setProperty("SkinHelper.TMDB.status",result.get('status',""))
                WINDOW.setProperty("SkinHelper.TMDB.popularity",result.get('popularity',""))
    
    def setAddonDetails(self, multiThreaded=False):
        #try to lookup additional artwork and properties for plugin content
        preftype = self.contentType
        title = self.liTitle
        year = xbmc.getInfoLabel("%sListItem.Year"%self.widgetContainerPrefix).decode("utf8")
        
        if not self.contentType in ["movies", "tvshows", "seasons", "episodes"] or not title or not self.contentType or not year or not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAddonsLookups)"):
            return

        if xbmc.getCondVisibility("!IsEmpty(%sListItem.TvShowTitle)" %self.widgetContainerPrefix):
            preftype = "tvshows"
            title = xbmc.getInfoLabel("%sListItem.TvShowTitle"%self.widgetContainerPrefix).decode("utf8")
        
        cacheStr = title + preftype + "SkinHelper.PVR.Artwork"

        if self.pvrArtCache.has_key(cacheStr):
            artwork = self.pvrArtCache[cacheStr]
        else:
            artwork = artutils.getAddonArtwork(title,year,preftype)
            self.pvrArtCache[cacheStr] = artwork
        
        #return if another listitem was focused in the meanwhile
        if multiThreaded and not (title == xbmc.getInfoLabel("%sListItem.Title"%self.widgetContainerPrefix).decode('utf-8') or title == xbmc.getInfoLabel("%sListItem.TvShowTitle"%self.widgetContainerPrefix).decode("utf8")):
            return
                
        #set window props
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.PVR." + key,value)
            
        #set extended movie details
        if (self.contentType == "movies" or self.contentType == "setmovies") and artwork.get("imdb_id"):
            self.setExtendedMovieInfo(False,artwork.get("imdb_id"))
            self.setAnimatedPoster(False,artwork.get("imdb_id"))
    