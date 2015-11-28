#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading
import thread
import random
import xml.etree.ElementTree as etree
from Utils import *
from ArtworkUtils import *
from SkinShortcutsIntegration import *


class ListItemMonitor(threading.Thread):
    
    event = None
    exit = False
    delayedTaskInterval = 1795
    lastWeatherNotificationCheck = None
    lastNextAiredNotificationCheck = None
    liPath = ""
    liPathLast = ""
    liLabel = ""
    liLabelLast = ""
    folderPath = ""
    folderPathLast = ""
    unwatched = 1
    lastpvrDbId = ""
    contentType = ""
    lastListItem = ""
    allStudioLogos = {}
    allStudioLogosColor = {}
    LastCustomStudioImagesPath = ""
    delayedTaskInterval = 1795
    widgetTaskInterval = 590
    moviesetCache = {}
    extraFanartCache = {}
    musicArtCache = {}
    streamdetailsCache = {}
    pvrArtCache = {}
    rottenCache = {}
    cachePath = os.path.join(ADDON_DATA_PATH,"librarycache.json")
    ActorImagesCachePath = os.path.join(ADDON_DATA_PATH,"actorimages.json")
    
    def __init__(self, *args):
        logMsg("HomeMonitor - started")
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)
    
    def stop(self):
        logMsg("HomeMonitor - stop called",0)
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

        while (self.exit != True):
        
            if xbmc.getCondVisibility("Player.HasAudio"):
                #set some globals
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
            
            if xbmc.getCondVisibility("Window.IsActive(videoosd) | Window.IsActive(musicosd)"):
                #auto close OSD after X seconds of inactivity
                secondsToDisplay = 0
                window = "videoosd"
                try:
                    if xbmc.getCondVisibility("Window.IsActive(VideoOSD.xml)"):
                        secondsToDisplay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseVideoOSD)"))
                        window = "videoosd"
                    if xbmc.getCondVisibility("Window.IsActive(MusicOSD.xml)"):
                        secondsToDisplay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseMusicOSD)"))
                        window = "musicosd"
                except: pass
                if secondsToDisplay != 0:
                    currentcount = 0
                    secondsToDisplay = secondsToDisplay*4
                    liControlLast = ""
                    while secondsToDisplay >= currentcount:
                        #reset the count if user changed focused control, close osd when control didn't change in the given amount of seconds
                        liControl = xbmc.getInfoLabel("System.CurrentControl").decode('utf-8')
                        if liControl == liControlLast: currentcount += 1
                        else: currentcount = 0
                        xbmc.sleep(250)
                        liControlLast = liControl
                    
                    #only auto close osd if no osd related dialogs are opened
                    if not xbmc.getCondVisibility("Window.IsActive(visualisationpresetlist) | Window.IsActive(osdvideosettings) | Window.IsActive(osdaudiosettings) | Window.IsActive(videobookmarks) | Window.IsActive(videobookmarks)"):
                        xbmc.executebuiltin("Dialog.Close(%s)"%window)
                
            if not xbmc.getCondVisibility("Window.IsActive(fullscreenvideo) | Window.IsActive(script.pseudotv.TVOverlay.xml) | Window.IsActive(script.pseudotv.live.TVOverlay.xml)"):
        
                #set some globals
                try:
                    self.liPath = xbmc.getInfoLabel("ListItem.Path").decode('utf-8')
                    self.liLabel = xbmc.getInfoLabel("ListItem.Label").decode('utf-8')
                    self.folderPath = xbmc.getInfoLabel("Container.FolderPath").decode('utf-8')
                    if not self.folderPath and self.liPath.startswith("pvr://guide"): self.folderPath = "pvr://guide"
                except Exception as e: print e
                curListItem = self.liPath + self.liLabel
                
                #perform actions if the container path has changed
                #always wait for the contenttype because plugins can be slow
                if self.folderPath != self.folderPathLast:
                    self.contentType = getCurrentContentType()
                    self.setForcedView()
                    self.focusEpisode()
                    self.resetWindowProps()
                    self.folderPathLast = self.folderPath
                    self.lastListItem = ""
                    WINDOW.setProperty("curListItem",curListItem)
                
                #only perform actions when the listitem has actually changed
                if curListItem and curListItem != self.lastListItem and self.contentType:
                    
                    WINDOW.setProperty("curListItem",curListItem)
                    
                    #clear all window props first
                    self.resetWindowProps()
                    
                    if not self.liLabel == "..":
                        # monitor listitem props when musiclibrary is active
                        if self.contentType == "albums" or self.contentType == "artists" or self.contentType == "songs":
                            try:
                                self.setMusicDetails(xbmc.getInfoLabel("ListItem.Artist").decode('utf-8'),xbmc.getInfoLabel("ListItem.Album").decode('utf-8'),xbmc.getInfoLabel("ListItem.DBID"),self.contentType)
                                self.setGenre()
                            except Exception as e:
                                logMsg("ERROR in setMusicDetails ! --> " + str(e), 0)
                                    
                        # monitor listitem props when videolibrary is active
                        elif xbmc.getCondVisibility("Window.IsActive(videos) | Window.IsActive(movieinformation)"):
                            try:
                                self.setDuration()
                                self.setStudioLogo()
                                self.setGenre()
                                self.setDirector()
                                self.checkExtraFanArt()
                                self.setMovieSetDetails()
                                self.setAddonName()
                                self.setStreamDetails()
                                self.setRottenRatings()
                            except Exception as e:
                                logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                        
                        # monitor listitem props when PVR is active
                        elif self.contentType == "tvchannels" or self.contentType == "tvrecordings":
                            try:
                                self.setDuration()
                                self.setPVRThumbs()
                                self.setGenre()
                            except Exception as e:
                                logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                            
                    #set some globals
                    self.liPathLast = self.liPath
                    self.liLabelLast = self.liLabel
                    self.lastListItem = curListItem
                
                #monitor listitem props when special info active
                elif xbmc.getCondVisibility("Window.IsActive(script-skin_helper_service-CustomInfo.xml)"):
                    try:                
                        self.resetWindowProps()
                        self.setDuration(xbmc.getInfoLabel("Container(999).ListItem.Duration"))
                        self.setStudioLogo(xbmc.getInfoLabel("Container(999).ListItem.Studio").decode('utf-8'))
                        self.setDirector(xbmc.getInfoLabel("Container(999).ListItem.Director").decode('utf-8'))
                        self.setGenre(xbmc.getInfoLabel("Container(999).ListItem.Genre").decode('utf-8'))
                        self.setStreamDetails(xbmc.getInfoLabel("Container(999).ListItem.Property(dbid)"),xbmc.getInfoLabel("Container(999).ListItem.Property(contenttype)"))
                        self.setRottenRatings(xbmc.getInfoLabel("Container(999).ListItem.Property(imdbnumber)"),xbmc.getInfoLabel("Container(999).ListItem.Property(contenttype)"))
                        #for tv show items, trigger nextaired addon
                        nextaired = False
                        if xbmc.getInfoLabel("Container(999).ListItem.TvShowTitle") and xbmc.getCondVisibility("System.HasAddon(script.tv.show.next.aired)"):
                            xbmc.executebuiltin("RunScript(script.tv.show.next.aired,tvshowtitle=%s)" %xbmc.getInfoLabel("Container(999).ListItem.TvShowTitle"))
                            nextaired = True
                        #wait untill the dialog is closed again
                        while xbmc.getCondVisibility("Window.IsActive(script-skin_helper_service-CustomInfo.xml)") and not self.exit:
                            xbmc.sleep(150)
                        self.resetWindowProps()
                        if nextaired:
                            #fake show id to flush nextaired props
                            xbmc.executebuiltin("RunScript(script.tv.show.next.aired,tvshowtitle=165628787629692696)")
                    except Exception as e:
                        logMsg("ERROR in LibraryMonitor HomeWidget ! --> " + str(e), 0)
                
                #monitor listitem props when home active
                elif xbmc.getCondVisibility("Window.IsActive(Home) + !IsEmpty(Window(home).Property(SkinHelper.WidgetContainer))"):
                    try:                
                        #set listitem window props for widget container
                        widgetContainer = WINDOW.getProperty("SkinHelper.WidgetContainer")
                        curListItem = xbmc.getInfoLabel("Container(%s).ListItem.Label" %widgetContainer)
                        if curListItem and curListItem != self.lastListItem:
                            self.resetWindowProps()
                            self.setDuration(xbmc.getInfoLabel("Container(%s).ListItem.Duration" %widgetContainer))
                            self.setStudioLogo(xbmc.getInfoLabel("Container(%s).ListItem.Studio" %widgetContainer).decode('utf-8'))
                            self.setDirector(xbmc.getInfoLabel("Container(%s).ListItem.Director" %widgetContainer).decode('utf-8'))
                            self.setGenre(xbmc.getInfoLabel("Container(%s).ListItem.Genre" %widgetContainer).decode('utf-8'))
                            #music artwork for music widgets...
                            if xbmc.getInfoLabel("Container(%s).ListItem.Artist" %widgetContainer):
                                contenttype = xbmc.getInfoLabel("Container(%s).ListItem.Property(type)")
                                artist = xbmc.getInfoLabel("Container(%s).ListItem.Artist" %widgetContainer).decode('utf-8')
                                album = xbmc.getInfoLabel("Container(%s).ListItem.Album" %widgetContainer).decode('utf-8')
                                title = xbmc.getInfoLabel("Container(%s).ListItem.Title" %widgetContainer).decode('utf-8')
                                dbid = xbmc.getInfoLabel("Container(%s).ListItem.DBID" %widgetContainer).decode('utf-8')
                                if contenttype and contenttype == "song": contenttype = "songs"
                                elif contenttype and contenttype == "album": contenttype = "albums"
                                elif contenttype and contenttype == "artist": contenttype = "artists"
                                elif artist and artist == curListItem: contenttype = "artists"
                                elif album and album == curListItem: contenttype = "albums"
                                elif dbid: contenttype = "songs"
                                self.setMusicDetails(artist,album,dbid,contenttype)
                            #pvr artwork if pvr widget...
                            if "pvr://" in xbmc.getInfoLabel("Container(%s).ListItem.FolderPath" %widgetContainer).decode('utf-8'):
                                self.setPVRThumbs(xbmc.getInfoLabel("Container(%s).ListItem.Title" %widgetContainer).decode('utf-8'),xbmc.getInfoLabel("Container(%s).ListItem.ChannelName" %widgetContainer).decode('utf-8'),xbmc.getInfoLabel("Container(%s).ListItem.Genre" %widgetContainer).decode('utf-8'))
                            self.lastListItem = curListItem
                    except Exception as e:
                        logMsg("ERROR in LibraryMonitor HomeWidget ! --> " + str(e), 0)
                   
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
            else:
                #fullscreen video is playing
                xbmc.sleep(2000)
                self.delayedTaskInterval += 2
                self.widgetTaskInterval += 2
    
    def checkNetflixReady(self):
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.netflixbmc)"):
            #set windowprop if netflix addon has a username filled in to prevent login loop box
            nfaddon = xbmcaddon.Addon(id='plugin.video.netflixbmc')
            if nfaddon.getSetting("username") and nfaddon.getSetting("html5MessageShown"):
                WINDOW.setProperty("netflixready","ready")
            else:
                WINDOW.clearProperty("netflixready")
                        
    def doBackgroundWork(self):
        try:
            logMsg("Started Background worker...")
            self.getStudioLogos()
            self.genericWindowProps()
            self.checkNetflixReady()
            self.updatePlexlinks()
            self.checkNotifications()
            self.saveCacheToFile()
            logMsg("Ended Background worker...")
        except Exception as e:
            logMsg("ERROR in HomeMonitor doBackgroundWork ! --> " + str(e), 0)
    
    def saveCacheToFile(self):
        libraryCache = {}
        libraryCache["SetsCache"] = self.moviesetCache
        libraryCache["streamdetailsCache"] = self.streamdetailsCache
        libraryCache["rottenCache"] = self.rottenCache
        widgetcache = WINDOW.getProperty("skinhelper-widgetcontenttype").decode("utf-8")
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
        if data.has_key("rottenCache"):
            self.rottenCache = data["rottenCache"]
        if data.has_key("widgetcache"):
            WINDOW.setProperty("skinhelper-widgetcontenttype",repr(data["widgetcache"]).encode("utf-8"))
            
        #actorimagescache
        data = getDataFromCacheFile(self.ActorImagesCachePath)
        if data: WINDOW.setProperty("SkinHelper.ActorImages", repr(data))

    def updatePlexlinks(self):
        
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc) + Skin.HasSetting(SmartShortcuts.plex)"): 
            logMsg("update plexlinks started...")
            
            #initialize plex window props by using the amberskin entrypoint for now
            if not WINDOW.getProperty("plexbmc.0.title"):
                xbmc.executebuiltin('RunScript(plugin.video.plexbmc,amberskin)')
                #wait for max 40 seconds untill the plex nodes are available
                count = 0
                while (count < 160 and not WINDOW.getProperty("plexbmc.0.title")):
                    xbmc.sleep(250)
                    count += 1
            
            #fallback to normal skin init
            if not WINDOW.getProperty("plexbmc.0.title"):
                xbmc.executebuiltin('RunScript(plugin.video.plexbmc,skin)')
                count = 0
                while (count < 80 and not WINDOW.getProperty("plexbmc.0.title")):
                    xbmc.sleep(250)
                    count += 1
            
            #get the plex setting if there are subnodes
            plexaddon = xbmcaddon.Addon(id='plugin.video.plexbmc')
            hasSecondayMenus = plexaddon.getSetting("secondary") == "true"
            del plexaddon
            
            #update plex window properties
            linkCount = 0
            while linkCount !=50:
                plexstring = "plexbmc." + str(linkCount)
                link = WINDOW.getProperty(plexstring + ".title")
                link = link.replace("VideoLibrary","10025")
                if not link:
                    break
                logMsg(plexstring + ".title --> " + link)
                plexType = WINDOW.getProperty(plexstring + ".type")
                logMsg(plexstring + ".type --> " + plexType)            

                if hasSecondayMenus == True:
                    recentlink = WINDOW.getProperty(plexstring + ".recent")
                    progresslink = WINDOW.getProperty(plexstring + ".ondeck")
                    alllink = WINDOW.getProperty(plexstring + ".all")
                else:
                    link = WINDOW.getProperty(plexstring + ".path")
                    alllink = link
                    link = link.replace("mode=1", "mode=0")
                    link = link.replace("mode=2", "mode=0")
                    recentlink = link.replace("/all", "/recentlyAdded")
                    progresslink = link.replace("/all", "/onDeck")
                    WINDOW.setProperty(plexstring + ".recent", recentlink)
                    WINDOW.setProperty(plexstring + ".ondeck", progresslink)
                    
                logMsg(plexstring + ".all --> " + alllink)
                
                WINDOW.setProperty(plexstring + ".recent.content", getContentPath(recentlink))
                WINDOW.setProperty(plexstring + ".recent.path", recentlink)
                WINDOW.setProperty(plexstring + ".recent.title", "recently added")
                logMsg(plexstring + ".recent --> " + recentlink)       
                WINDOW.setProperty(plexstring + ".ondeck.content", getContentPath(progresslink))
                WINDOW.setProperty(plexstring + ".ondeck.path", progresslink)
                WINDOW.setProperty(plexstring + ".ondeck.title", "on deck")
                logMsg(plexstring + ".ondeck --> " + progresslink)
                
                unwatchedlink = alllink.replace("mode=1", "mode=0")
                unwatchedlink = alllink.replace("mode=2", "mode=0")
                unwatchedlink = alllink.replace("/all", "/unwatched")
                WINDOW.setProperty(plexstring + ".unwatched", unwatchedlink)
                WINDOW.setProperty(plexstring + ".unwatched.content", getContentPath(unwatchedlink))
                WINDOW.setProperty(plexstring + ".unwatched.path", unwatchedlink)
                WINDOW.setProperty(plexstring + ".unwatched.title", "unwatched")
                
                WINDOW.setProperty(plexstring + ".content", getContentPath(alllink))
                WINDOW.setProperty(plexstring + ".path", alllink)
                
                linkCount += 1
                
            #add plex channels as entry - extract path from one of the nodes as a workaround because main plex addon channels listing is in error
            link = WINDOW.getProperty("plexbmc.0.path")
            
            if link:
                link = link.split("/library/")[0]
                link = link + "/channels/all&mode=21"
                link = link + ", return)"
                plexstring = "plexbmc.channels"
                WINDOW.setProperty(plexstring + ".title", "Channels")
                logMsg(plexstring + ".path --> " + link)
                WINDOW.setProperty(plexstring + ".path", link)
                WINDOW.setProperty(plexstring + ".content", getContentPath(link))
                
            logMsg("update plexlinks ended...")

    def checkNotifications(self):
        
        currentHour = time.strftime("%H")
        
        #weather notifications
        winw = xbmcgui.Window(12600)
        if (winw.getProperty("Alerts.RSS") and winw.getProperty("Current.Condition") and currentHour != self.lastWeatherNotificationCheck):
            dialog = xbmcgui.Dialog()
            dialog.notification(xbmc.getLocalizedString(31294), winw.getProperty("Alerts"), xbmcgui.NOTIFICATION_WARNING, 8000)
            self.lastWeatherNotificationCheck = currentHour
        
        #nextaired notifications
        if (xbmc.getCondVisibility("Skin.HasSetting(EnableNextAiredNotifications) + System.HasAddon(script.tv.show.next.aired)") and currentHour != self.lastNextAiredNotificationCheck):
            if (WINDOW.getProperty("NextAired.TodayShow")):
                dialog = xbmcgui.Dialog()
                dialog.notification(xbmc.getLocalizedString(31295), WINDOW.getProperty("NextAired.TodayShow"), xbmcgui.NOTIFICATION_WARNING, 8000)
                self.lastNextAiredNotificationCheck = currentHour
    
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

        #GET RADIO CHANNELS COUNT
        if xbmc.getCondVisibility("Pvr.HasRadioChannels"):
            allRadioChannelsCount = 0
            media_array = getJSON('PVR.GetChannels','{"channelgroupid": "allradio" }' )
            for item in media_array:
                allRadioChannelsCount += 1
            WINDOW.setProperty("SkinHelper.TotalRadioChannels",str(allRadioChannelsCount))        
               
    def resetWindowProps(self):
        #reset all window props provided by the script...
        WINDOW.setProperty("SkinHelper.ListItemStudioLogo","")
        WINDOW.setProperty("SkinHelper.ListItemStudioLogoColor","")
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
        WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
        WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
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
        WINDOW.setProperty("SkinHelper.PVR.ExtraFanArt","")
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
        WINDOW.clearProperty('SkinHelper.RottenTomatoesRating')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesAudienceRating')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesConsensus')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesAwards')
        WINDOW.clearProperty('SkinHelper.RottenTomatoesBoxOffice')
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
        if xbmc.getCondVisibility("SubString(ListItem.Path,videodb://movies/sets/,left)"):
            dbId = xbmc.getInfoLabel("ListItem.DBID")   
            if dbId:
                #try to get from cache first
                if self.moviesetCache.get(dbId):
                    json_response = self.moviesetCache[dbId]
                else:
                    json_response = getJSON('VideoLibrary.GetMovieSetDetails', '{"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer", "playcount", "genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country", "streamdetails"], "sort": { "order": "ascending",  "method": "year" }} }' % dbId)
                    #save to cache
                    self.moviesetCache[dbId] = json_response
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
                        set_fanart.append(art.get('fanart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Title',item['label'])
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Poster',art.get('poster', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.FanArt',art.get('fanart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Landscape',art.get('landscape', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.DiscArt',art.get('discart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.ClearLogo',art.get('clearlogo', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.ClearArt',art.get('clearart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Banner',art.get('banner', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Rating',str(item.get('rating', '')))
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
                                    WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Resolution',resolution)
                                if stream.get("codec",""):
                                    WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Codec',str(stream["codec"]))    
                                if stream.get("aspect",""):
                                    WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.AspectRatio',str(round(stream["aspect"], 2)))
                            if len(audiostreams) > 0:
                                #grab details of first audio stream
                                stream = audiostreams[0]
                                WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.AudioCodec',stream.get('codec',''))
                                WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.AudioChannels',str(stream.get('channels','')))
                                WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.AudioLanguage',stream.get('language',''))
                            if len(subtitles) > 0:
                                #grab details of first subtitle
                                WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.SubTitle',subtitles[0].get('language',''))

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
                    WINDOW.setProperty('SkinHelper.MovieSet.Plot', plot)
                    if json_response['limits']['total'] > 1:
                        WINDOW.setProperty('SkinHelper.MovieSet.ExtendedPlot', title_header + title_list + "[CR]" + plot)
                    else:
                        WINDOW.setProperty('SkinHelper.MovieSet.ExtendedPlot', plot)
                    WINDOW.setProperty('SkinHelper.MovieSet.Title', title_list)
                    WINDOW.setProperty('SkinHelper.MovieSet.Runtime', str(runtime / 60))
                    self.setDuration(str(runtime / 60))
                    durationString = self.getDurationString(runtime / 60)
                    if durationString:
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration', durationString[2])
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration.Hours', durationString[0])
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration.Minutes', durationString[1])
                    WINDOW.setProperty('SkinHelper.MovieSet.Writer', " / ".join(writer))
                    WINDOW.setProperty('SkinHelper.MovieSet.Director', " / ".join(director))
                    self.setDirector(" / ".join(director))
                    WINDOW.setProperty('SkinHelper.MovieSet.Genre', " / ".join(genre))
                    self.setGenre(" / ".join(genre))
                    WINDOW.setProperty('SkinHelper.MovieSet.Country', " / ".join(country))
                    studioString = " / ".join(studio)
                    WINDOW.setProperty('SkinHelper.MovieSet.Studio', studioString)
                    self.setStudioLogo(studioString)
                   
                    WINDOW.setProperty('SkinHelper.MovieSet.Years', " / ".join(years))
                    WINDOW.setProperty('SkinHelper.MovieSet.Year', years[0] + " - " + years[-1])
                    WINDOW.setProperty('SkinHelper.MovieSet.Count', str(json_response['limits']['total']))
                    WINDOW.setProperty('SkinHelper.MovieSet.WatchedCount', str(watchedcount))
                    WINDOW.setProperty('SkinHelper.MovieSet.UnWatchedCount', str(unwatchedcount))
                    
                    #rotate fanart from movies in set while listitem is in focus
                    if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtraFanart)"):
                        fanartcount = 5
                        delaycount = 5
                        backgroundDelayStr = xbmc.getInfoLabel("skin.string(extrafanartdelay)")
                        if backgroundDelayStr:
                            fanartcount = int(backgroundDelayStr)
                            delaycount = int(backgroundDelayStr)
                        while dbId == xbmc.getInfoLabel("ListItem.DBID") and set_fanart != []:
                            
                            if fanartcount == delaycount:
                                random.shuffle(set_fanart)
                                WINDOW.setProperty('SkinHelper.ExtraFanArtPath', set_fanart[0])
                                fanartcount = 0
                            else:
                                xbmc.sleep(1000)
                                fanartcount += 1

    def setAddonName(self):
        # set addon name as property
        if not xbmc.Player().isPlayingAudio():
            if (xbmc.getCondVisibility("Container.Content(plugins) | !IsEmpty(Container.PluginName)")):
                AddonName = xbmc.getInfoLabel('Container.PluginName').decode('utf-8')
                AddonName = xbmcaddon.Addon(AddonName).getAddonInfo('name')
                WINDOW.setProperty("SkinHelper.Player.AddonName", AddonName)
    
    def setGenre(self, genre=None):
        if not genre:
            genre = xbmc.getInfoLabel('ListItem.Genre').decode('utf-8')
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
    
    def setDirector(self, director=None):
        if not director:
            director = xbmc.getInfoLabel('ListItem.Director').decode('utf-8')
        directors = []
        if "/" in director:
            directors = director.split(" / ")
        else:
            directors.append(director)
        
        WINDOW.setProperty('SkinHelper.ListItemDirectors', "[CR]".join(directors))
       
    def setPVRThumbs(self,title="",channel="",path="",genre=""):
                
        if not title: title = xbmc.getInfoLabel("ListItem.Title").decode('utf-8')
        if not channel: channel = xbmc.getInfoLabel("ListItem.ChannelName").decode('utf-8')
        if not path: path = xbmc.getInfoLabel("ListItem.FileNameAndPath").decode('utf-8')
        if not genre: genre = xbmc.getInfoLabel("ListItem.Genre").decode('utf-8')
        
        if xbmc.getCondVisibility("ListItem.IsFolder") and not channel and not title:
            #assume grouped recordings folderPath
            title = xbmc.getInfoLabel("ListItem.Label").decode('utf-8')
        
        if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnablePVRThumbs)") or not title or xbmc.getInfoLabel("ListItem.Label").decode('utf-8') == "..":
            return
        
        dbID = title + channel
            
        logMsg("setPVRThumb dbID--> %s  - path: %s" %( dbID,path))
        
        if self.pvrArtCache.has_key(dbID + "SkinHelper.PVR.Artwork"):
            artwork = self.pvrArtCache[dbID + "SkinHelper.PVR.Artwork"]
        else:           
            if self.contentType == "tvrecordings": type = "recordings"
            else: type = "channels"
            
            artwork = getPVRThumbs(title, channel, type, path, genre)
            self.pvrArtCache[dbID + "SkinHelper.PVR.Artwork"] = artwork
        
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.PVR." + key,value)

    def setStudioLogo(self, studio=None):
        
        if xbmc.getCondVisibility("Container.Content(studios)"):
            studio = self.liLabel
        
        if not studio:
            studio = xbmc.getInfoLabel('ListItem.Studio').decode('utf-8')
        
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
    
    def setDuration(self,currentDuration=None):
        if not currentDuration:
            currentDuration = xbmc.getInfoLabel("ListItem.Duration")
        
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
                        album = json_result.get("album")
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
                    if artist and title: artwork = getMusicArtworkByName(artist,title,album)
                break

        #set properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.Player.Music." + key,value.encode("utf-8"))
    
    def setMusicDetails(self,artist,album,dbid,contenttype):
        artwork = {}
        cacheId = artist+album
        logMsg("setMusicDetails artist: %s - album: %s - dbid: %s - contenttype: %s"%(artist,album,dbid,contenttype))
        
        #get the items from cache first
        if self.musicArtCache.has_key(cacheId + "SkinHelper.Music.Art"):
            artwork = self.musicArtCache[cacheId + "SkinHelper.Music.Art"]
            
        elif dbid and contenttype and dbid !='-1':
            logMsg("setMusicDetails no cache found for artist: %s - album: %s - dbid: %s - contenttype: %s  -- perform lookup by dbid"%(artist,album,dbid,contenttype))
            artwork = getMusicArtworkByDbId(dbid, contenttype)
            self.musicArtCache[cacheId + "SkinHelper.Music.Art"] = artwork
        elif artist and album:
            logMsg("setMusicDetails no cache found for artist: %s - album: %s - dbid: %s - contenttype: %s  -- perform lookup by artist/album name"%(artist,album,dbid,contenttype))
            artwork = getMusicArtworkByName(artist, "", album)
            self.musicArtCache[cacheId + "SkinHelper.Music.Art"] = artwork

        #set properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.Music." + key,value)
              
    def setStreamDetails(self,dbId="",contenttype=""):
        streamdetails = {}
        if not dbId:
            dbId = xbmc.getInfoLabel("ListItem.DBID")
        if not contenttype:
            contenttype = self.contentType
            
        if not dbId or dbId == "-1": return
        
        if self.streamdetailsCache.get(dbId+contenttype):
            #get data from cache
            streamdetails = self.streamdetailsCache[dbId+contenttype]
        else:
            json_result = {}
            # get data from json
            if "movies" in contenttype and dbId:
                json_result = getJSON('VideoLibrary.GetMovieDetails', '{ "movieid": %d, "properties": [ "title", "streamdetails" ] }' %int(dbId))
            elif contenttype == "episodes" and dbId:
                json_result = getJSON('VideoLibrary.GetEpisodeDetails', '{ "episodeid": %d, "properties": [ "title", "streamdetails" ] }' %int(dbId))
            elif contenttype == "musicvideos" and dbId:
                json_result = getJSON('VideoLibrary.GetMusicVideoDetails', '{ "musicvideoid": %d, "properties": [ "title", "streamdetails" ] }' %int(dbId))       
            if json_result.has_key("streamdetails"):
                audio = json_result["streamdetails"]['audio']
                subtitles = json_result["streamdetails"]['subtitle']
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
                
                self.streamdetailsCache[dbId+contenttype] = streamdetails
                
        if streamdetails:
            #set the window properties
            for key, value in streamdetails.iteritems():
                WINDOW.setProperty(key,value)
          
    def setForcedView(self):
        currentForcedView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %self.contentType)
        if self.contentType and currentForcedView and currentForcedView != "None" and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)"):
            WINDOW.setProperty("SkinHelper.ForcedView",currentForcedView)
            xbmc.executebuiltin("Container.SetViewMode(%s)" %currentForcedView)
            if not xbmc.getCondVisibility("Control.HasFocus(%s)" %currentForcedView):
                xbmc.sleep(100)
                xbmc.executebuiltin("Container.SetViewMode(%s)" %currentForcedView)
                xbmc.executebuiltin("SetFocus(%s)" %currentForcedView)
        else:
            WINDOW.clearProperty("SkinHelper.ForcedView")
        
    def checkExtraFanArt(self):
        
        lastPath = None
        efaPath = None
        efaFound = False
        liArt = None
        
        if xbmc.getCondVisibility("Window.IsActive(movieinformation) | !Skin.HasSetting(SkinHelper.EnableExtraFanart)"):
            return
        
        #get the item from cache first
        if self.extraFanartCache.has_key(self.liPath):
            if self.extraFanartCache[self.liPath][0] == "None":
                return
            else:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath",self.extraFanartCache[self.liPath][0])
                count = 0
                for file in self.extraFanartCache[self.liPath][1]:
                    WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),file)
                    count +=1  
                return
        
        if (self.liPath != None and self.liPath != self.liPathLast and (xbmc.getCondVisibility("Container.Content(movies) | Container.Content(seasons) | Container.Content(episodes) | Container.Content(tvshows)")) and not "videodb:" in self.liPath):
                           
            if xbmc.getCondVisibility("Container.Content(episodes)"):
                liArt = xbmc.getInfoLabel("ListItem.Art(tvshow.fanart)").decode('utf-8')
            
            # do not set extra fanart for virtuals
            if (("plugin://" in self.liPath) or ("addon://" in self.liPath) or ("sources" in self.liPath) or ("plugin://" in self.folderPath) or ("sources://" in self.folderPath) or ("plugin://" in self.folderPath)):
                self.extraFanartCache[self.liPath] = "None"
            else:
                if xbmcvfs.exists(self.liPath + "extrafanart/"):
                    efaPath = self.liPath + "extrafanart/"
                else:
                    pPath = self.liPath.rpartition("/")[0]
                    pPath = pPath.rpartition("/")[0]
                    if xbmcvfs.exists(pPath + "/extrafanart/"):
                        efaPath = pPath + "/extrafanart/"
                        
                if xbmcvfs.exists(efaPath):
                    dirs, files = xbmcvfs.listdir(efaPath)
                    count = 0
                    extraFanArtfiles = []
                    for file in files:
                        if file.lower().endswith(".jpg"):
                            efaFound = True
                            WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),efaPath+file)
                            extraFanArtfiles.append(efaPath+file)
                            count +=1  
       
                if (efaPath != None and efaFound == True):
                    WINDOW.setProperty("SkinHelper.ExtraFanArtPath",efaPath)
                    self.extraFanartCache[self.liPath] = [efaPath, extraFanArtfiles]     
                else:
                    self.extraFanartCache[self.liPath] = ["None",[]]

    def setRottenRatings(self,imdbnumber="",contenttype=""):
        if not imdbnumber:
            dbId = xbmc.getInfoLabel("ListItem.IMDBNumber")
        if not contenttype:
            contenttype = self.contentType
        result = None
        if (contenttype == "movies" or contenttype=="setmovies") and imdbnumber:
            if self.rottenCache.get(imdbnumber):
                #get data from cache
                result = self.rottenCache[imdbnumber]
            elif not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
                url = 'http://www.omdbapi.com/?i=%s&plot=short&tomatoes=true&r=json' %imdbnumber
                res = requests.get(url)
                result = json.loads(res.content.decode('utf-8','replace'))
                if result:
                    self.rottenCache[imdbnumber] = result
            if result:
                criticsscore = result.get('tomatoMeter',"")
                criticconsensus = result.get('tomatoConsensus',"")
                audiencescore = result.get('Metascore',"")
                awards = result.get('Awards',"")
                boxoffice = result.get('BoxOffice',"")
                if criticsscore:
                    WINDOW.setProperty("SkinHelper.RottenTomatoesRating",criticsscore)
                if audiencescore:
                    WINDOW.setProperty("SkinHelper.RottenTomatoesAudienceRating",audiencescore)
                if criticconsensus:
                    WINDOW.setProperty("SkinHelper.RottenTomatoesConsensus",criticconsensus)
                if awards:
                    WINDOW.setProperty("SkinHelper.RottenTomatoesAwards",awards)
                if boxoffice:
                    WINDOW.setProperty("SkinHelper.RottenTomatoesBoxOffice",boxoffice)

    def focusEpisode(self):
        # monitor episodes for auto focus first unwatched - Helix only as it is included in Kodi as of Isengard by default
        if xbmc.getCondVisibility("Skin.HasSetting(AutoFocusUnwatchedEpisode)"):
            
            #store unwatched episodes
            if ((xbmc.getCondVisibility("Container.Content(seasons) | Container.Content(tvshows)")) and xbmc.getCondVisibility("!IsEmpty(ListItem.Property(UnWatchedEpisodes))")):
                try:
                    self.unwatched = int(xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)"))
                except: pass
            
            if (xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")):
                
                if self.unwatched != 0:
                    totalItems = 0
                    curView = xbmc.getInfoLabel("Container.Viewmode") 
                    
                    # get all views from views-file
                    viewId = None
                    skin_view_file = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
                    tree = etree.parse(skin_view_file)
                    root = tree.getroot()
                    for view in root.findall('view'):
                        if curView == xbmc.getLocalizedString(int(view.attrib['languageid'])):
                            viewId=view.attrib['value']
                    
                    wid = xbmcgui.getCurrentWindowId()
                    window = xbmcgui.Window( wid )        
                    control = window.getControl(int(viewId))
                    totalItems = int(xbmc.getInfoLabel("Container.NumItems"))
                    
                    if (xbmc.getCondVisibility("Container.SortDirection(ascending)")):
                        curItem = 0
                        while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and totalItems >= curItem):
                            if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png" and xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label") != ".." and not xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label").startswith("*")):
                                if curItem != 0:
                                    #control.selectItem(curItem)
                                    xbmc.executebuiltin("Control.Move(%s,%s)" %(str(viewId),str(curItem)))
                                break
                            else:
                                curItem += 1
                    
                    elif (xbmc.getCondVisibility("Container.SortDirection(descending)")):
                        curItem = totalItems
                        while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and curItem != 0):
                            
                            if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png"):
                                xbmc.executebuiltin("Control.Move(%s,%s)" %(str(viewId),str(curItem)))
                                break
                            else:    
                                curItem -= 1
           