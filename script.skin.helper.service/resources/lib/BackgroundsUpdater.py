#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading, thread
import random
import io
import base64
import ConditionalBackgrounds as conditionalBackgrounds
import ArtworkUtils as artutils
from Utils import *

class BackgroundsUpdater(threading.Thread):
    
    event = None
    exit = False
    allBackgrounds = {}
    tempBlacklist = set()
    lastPicturesPath = None
    smartShortcuts = {}
    cachePath = None
    SmartShortcutsCachePath = None
    backgroundsTaskInterval = 30
    wallTaskInterval = 30
    daynightThemeTaskInterval = 30
    backgroundDelay = 0
    wallImagesDelay = 0
    lastWindow = None
    manualWallsLoaded = list()
    manualWalls = {}
    smartShortcutsFirstRunDone = False
    
    def __init__(self, *args):
        self.lastPicturesPath = xbmc.getInfoLabel("skin.string(SkinHelper.PicturesBackgroundPath)").decode("utf-8")
        self.cachePath = os.path.join(ADDON_DATA_PATH,"AllBackgrounds.json")
        self.SmartShortcutsCachePath = os.path.join(ADDON_DATA_PATH,"smartshotcutscache.json")
        self.monitor = xbmc.Monitor()

        logMsg("BackgroundsUpdater - started")
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)

    def stop(self):
        logMsg("BackgroundsUpdater - stop called",0)
        self.saveCacheToFile()
        self.exit = True
        self.event.set()

    def run(self):

        #first run get backgrounds immediately from filebased cache and reset the cache in memory to populate all images from scratch
        try:
            self.getCacheFromFile()
            self.getSkinConfig()
            self.UpdateBackgrounds()
            self.UpdateSmartShortCuts()
            self.updateWallImages()
            self.UpdateWallBackgrounds()
            self.allBackgrounds = {}
            self.smartShortcuts = {}
            self.smartShortcuts["allSmartShortcuts"] = []
            self.UpdateSmartShortCuts(True)
            self.saveCacheToFile()
        except Exception as e:
            logMsg("ERROR in BackgroundsUpdater ! --> " + str(e), 0)
         
        while (self.exit != True):
        
            # Update Day/Night theme if enabled
            if (self.daynightThemeTaskInterval >= 30):
                self.daynightThemeTaskInterval = 0
                try:
                    self.setDayNightColorTheme()
                except Exception as e:
                    logMsg("ERROR in setDayNightColorTheme ! --> " + str(e), 0)
            
            #Process backgrounds
            if xbmc.getCondVisibility("![Window.IsActive(fullscreenvideo) | Window.IsActive(script.pseudotv.TVOverlay.xml) | Window.IsActive(script.pseudotv.live.TVOverlay.xml)] | Window.IsActive(script.pseudotv.live.EPG.xml)") and self.backgroundDelay != 0:

                # force refresh smart shortcuts on request
                if WINDOW.getProperty("refreshsmartshortcuts") and self.smartShortcutsFirstRunDone:
                    try: self.UpdateSmartShortCuts(True)
                    except Exception as e: logMsg("ERROR in UpdateSmartShortCuts ! --> " + str(e), 0)
                    WINDOW.clearProperty("refreshsmartshortcuts")   

                # Update home backgrounds every interval (if enabled by skinner)
                if self.backgroundDelay != 0:
                    if (self.backgroundsTaskInterval >= self.backgroundDelay):
                        self.backgroundsTaskInterval = 0
                        try:
                            self.UpdateBackgrounds()
                            if self.smartShortcutsFirstRunDone:
                                self.UpdateSmartShortCuts()
                            self.setDayNightColorTheme()
                            self.getSkinConfig()
                            self.UpdateWallBackgrounds()
                        except Exception as e:
                            logMsg("ERROR in UpdateBackgrounds ! --> " + str(e), 0)
                            
                # Update manual wall images - if enabled by the skinner
                if self.wallImagesDelay != 0:
                    if (self.wallTaskInterval >= self.wallImagesDelay):
                        self.wallTaskInterval = 0
                        try:
                            self.updateWallImages()
                        except Exception as e:
                            logMsg("ERROR in UpdateBackgrounds.updateWallImages ! --> " + str(e), 0)
                            
            self.monitor.waitForAbort(1)
            self.backgroundsTaskInterval += 1
            self.wallTaskInterval += 1
            self.daynightThemeTaskInterval += 1
    
    def getSkinConfig(self):
        #gets the settings for the script as set by the skinner..
        try: self.backgroundDelay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.RandomFanartDelay)"))
        except: self.backgroundDelay = 0
        
        try: 
            wallImagesDelay = xbmc.getInfoLabel("Skin.String(SkinHelper.WallImagesDelay)")
            if wallImagesDelay:
                self.wallImagesDelay = int(wallImagesDelay)
                #enumerate through all background collections to check wether we should want a wall collection provided
                #store in memory so wo do not have to query the skin settings too often
                if self.wallImagesDelay != 0:
                    for key, value in self.allBackgrounds.iteritems():
                        if self.exit: return
                        if value:
                            limitrange = xbmc.getInfoLabel("Skin.String(%s.EnableWallImages)" %key)
                            if limitrange:
                                self.manualWalls[key] = int(limitrange)
        except Exception as e:
            logMsg("ERROR in UpdateBackgrounds.getSkinConfig ! --> " + str(e), 0)
            self.wallImagesDelay = 0
    
    def saveCacheToFile(self):
        saveDataToCacheFile(self.cachePath,self.allBackgrounds)
        saveDataToCacheFile(self.SmartShortcutsCachePath,self.smartShortcuts)
                       
    def getCacheFromFile(self):
        self.allBackgrounds = getDataFromCacheFile(self.cachePath)
        self.smartShortcuts = getDataFromCacheFile(self.SmartShortcutsCachePath)
        if self.smartShortcuts.get("allSmartShortcuts"):
            WINDOW.setProperty("allSmartShortcuts", repr(self.smartShortcuts["allSmartShortcuts"]))
        else: self.smartShortcuts["allSmartShortcuts"] = []
    
    def setDayNightColorTheme(self):
        #check if a color theme should be conditionally set
        if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableDayNightThemes) + Skin.String(SkinHelper.ColorTheme.Day.time) + Skin.String(SkinHelper.ColorTheme.Night.time)"):
            try:
                daytime = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.Day.time)")
                daytime = datetime(*(time.strptime(daytime, "%H:%M")[0:6])).time()
                nighttime = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.Night.time)")
                nighttime = datetime(*(time.strptime(nighttime, "%H:%M")[0:6])).time()
                timestamp = datetime.now().time()
                if (daytime <= timestamp <= nighttime):
                    #it's daytime - set daytime theme
                    timestr = "Day"
                else:
                    timestr = "Night"
                    
                currentTheme = xbmc.getInfoLabel("Skin.String(SkinHelper.LastColorTheme)")
                newtheme = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.theme)" %timestr)
                if currentTheme != newtheme:
                    themefile = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.file)" %timestr)
                    if themefile:
                        import resources.lib.ColorThemes as colorThemes
                        colorThemes.loadColorTheme(themefile)
            except Exception as e:
                logMsg("ERROR in setDayNightColorTheme ! --> " + str(e), 0)
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    
    def setWallImageFromPath(self, windowProp, libPath, type="fanart"):
        image = None
        windowPropBW = windowProp + ".BW"
        
        #load wall from cache    
        if self.allBackgrounds.get(windowProp):
            image = random.choice(self.allBackgrounds[windowProp])
            if image.get("wall"):
                if not xbmcvfs.exists(image.get("wall")): 
                    logMsg("Wall images cleared - starting rebuild...",0)
                    del self.allBackgrounds[windowProp]
                else:
                    WINDOW.setProperty(windowProp, image.get("wall"))
                    WINDOW.setProperty(windowPropBW, image.get("wallbw"))
                    return True
               
        #load images for libPath and generate wall
        if self.allBackgrounds.get(libPath):
            images = []
            try:
                images = self.createImageWall(self.allBackgrounds[libPath],windowProp,type)
            except Exception as e:
                logMsg("ERROR in createImageWall ! --> " + str(e), 0)
            self.allBackgrounds[windowProp] = images
            if images:
                image = random.choice(images)
                if image:
                    WINDOW.setProperty(windowProp, image.get("wall",""))
                    WINDOW.setProperty(windowPropBW, image.get("wallbw",""))
    
    def setManualWallFromPath(self, windowProp, numItems=20):
        #only continue if the cache is prefilled
        if self.allBackgrounds.get(windowProp):
            if windowProp in self.manualWallsLoaded:
                #only refresh one random image...
                image = random.choice(self.allBackgrounds[windowProp])
                if image:
                    for key, value in image.iteritems():
                        if key == "fanart": WINDOW.setProperty("%s.Wall.%s" %(windowProp,random.randint(0, numItems)), value)
                        else: WINDOW.setProperty("%s.Wall.%s.%s" %(windowProp,random.randint(0, numItems),key), value)
            else:
                #first run: set all images
                for i in range(numItems):
                    image = random.choice(self.allBackgrounds[windowProp])
                    if image:
                        for key, value in image.iteritems():
                            if key == "fanart": WINDOW.setProperty("%s.Wall.%s" %(windowProp,i), value)
                            else: WINDOW.setProperty("%s.Wall.%s.%s" %(windowProp,i,key), value)
                    self.manualWallsLoaded.append(windowProp)
    
    def updateWallImages(self):
        #manual wall images, provides a collection of images which are randomly changing
        if self.wallImagesDelay == 0 or not self.manualWalls:
            return
        
        #we have a list stored in memory for the wall collections the skinner wants to be generated
        for key, value in self.manualWalls.iteritems():
            self.setManualWallFromPath(key, value)

    def setImageFromPath(self, windowProp, libPath, fallbackImage="", customJson=None):
        images = []
        if self.exit:
            return False

        #cache entry exists and cache is not expired, load cache entry
        if self.allBackgrounds.has_key(windowProp):
            images = self.allBackgrounds[windowProp]
        else:
            #no cache file so try to load images from the path

            #safety check: check if no library windows are active to prevent any addons setting the view
            if xbmc.getCondVisibility("Window.IsMedia"):
                return False
                
            libPath = getContentPath(libPath)
            if "plugin.video.emby" in libPath and "browsecontent" in libPath and not "filter" in libPath:
                libPath = libPath + "&filter=random"
            
            #get the images from json
            if customJson: media_array = getJSON(customJson[0],customJson[1])
            else: media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art","thumbnail","fanart","album","artist"], "directory": "%s", "media": "files", "limits": {"end":250}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }' %libPath)
            
            for media in media_array:
                image = {}
                
                if media['label'].lower() == "next page":
                    continue
                
                #append music artwork...
                if media.get('songid'):
                    media['art'] = artutils.getMusicArtwork(media['artist'][0], albumName=media['album'], trackName=media['label'])
                elif media.get('artistid') and not media.get('albumid'):
                    media['art'] = artutils.getMusicArtwork(media['label'], albumName="", trackName="")
                elif media.get('albumid'):
                    media['art'] = artutils.getMusicArtwork(media['artist'][0], albumName=media['label'], trackName="")
                
                if media.get('art'):
                    if media['art'].get('fanart'):
                        image["fanart"] = getCleanImage(media['art']['fanart'])
                    elif media['art'].get('tvshow.fanart'):
                        image["fanart"] = getCleanImage(media['art']['tvshow.fanart'])
                    if media['art'].get('thumb'):
                        image["thumbnail"] = getCleanImage(media['art']['thumb'])
                    if media['art'].get('thumbnail'):
                        image["thumbnail"] = getCleanImage(media['art']['thumbnail'])
                
                if not image.get('fanart'):
                    image["fanart"] = media.get('fanart','')
                if not image.get("thumbnail"):
                    image["thumbnail"] =  media.get("thumbnail","")
                
                #only append items which have a fanart image
                if image.get("fanart"):
                    #also append other art to the dict
                    image["title"] = media.get('title',media['label'])
                    image["landscape"] = media.get('art',{}).get('landscape','')
                    image["poster"] = media.get('art',{}).get('poster','')
                    image["clearlogo"] = media.get('art',{}).get('clearlogo','')
                    images.append(image)
            
            #store images in cache
            self.allBackgrounds[windowProp] = images

        if images:
            image = random.choice(images)
            for key, value in image.iteritems():
                if key == "fanart": WINDOW.setProperty(windowProp, value)
                else: WINDOW.setProperty(windowProp + "." + key, value)
            return True
        else:
            WINDOW.setProperty(windowProp, fallbackImage)
            return False
            
    def setPicturesBackground(self,windowProp):
        customPath = xbmc.getInfoLabel("skin.string(SkinHelper.CustomPicturesBackgroundPath)").decode("utf-8")
        images = []
        
        #flush cache if custompath changed
        if (self.lastPicturesPath != customPath):
            self.allBackgrounds[windowProp] = []
            self.lastPicturesPath = customPath

        #get images from cache
        if self.allBackgrounds.has_key(windowProp):
            images = self.allBackgrounds[windowProp]
        else:
            #load the pictures from the custom path or from all picture sources
            if customPath:
                #load images from custom path
                dirs, files = xbmcvfs.listdir(customPath)
                #pick all images from path
                for file in files:
                    if file.lower().endswith(".jpg") or file.lower().endswith(".png"):
                        image = os.path.join(customPath,file.decode("utf-8"))
                        images.append({"fanart": image, "title": file.decode("utf-8")})
            else:
                #load pictures from all sources
                media_array = getJSON('Files.GetSources','{"media": "pictures"}')
                for source in media_array:
                    if source.has_key('file'):
                        if not "plugin://" in source["file"]:
                            dirs, files = xbmcvfs.listdir(source["file"])
                            if dirs:
                                #pick 10 random dirs
                                randomdirs = []
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                randomdirs.append(os.path.join(source["file"],random.choice(dirs).decode("utf-8","ignore")))
                                
                                #pick 5 images from each dir
                                for dir in randomdirs:
                                    subdirs, files2 = xbmcvfs.listdir(dir)
                                    count = 0
                                    for file in files2:
                                        if ((file.endswith(".jpg") or file.endswith(".png") or file.endswith(".JPG") or file.endswith(".PNG")) and count < 5):
                                            image = os.path.join(dir,file.decode("utf-8","ignore"))
                                            images.append({"fanart": image, "title": file})
                                            count += 1
                            if files:
                                #pick 10 images from root
                                count = 0
                                for file in files:
                                    if ((file.endswith(".jpg") or file.endswith(".png") or file.endswith(".JPG") or file.endswith(".PNG")) and count < 10):
                                        image = os.path.join(source["file"],file.decode("utf-8","ignore"))
                                        images.append({"fanart": image, "title": file})
                                        count += 1
            
            #store images in the cache
            self.allBackgrounds[windowProp] = images
            
        # return a random image
        if images:
            random.shuffle(images)
            image = images[0]
            for key, value in image.iteritems():
                if key == "fanart": WINDOW.setProperty(windowProp, value)
                else: WINDOW.setProperty(windowProp + "." + key, value)
    
    def getPVRArtworkPersistantCacheFiles(self):
        pvrthumbspath = WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")
        allcachefiles = []
        if pvrthumbspath:
            dirs, files = xbmcvfs.listdir(pvrthumbspath)
            for dir in dirs:
                cachefile = os.path.join(pvrthumbspath, dir.decode("utf-8"), "pvrdetails.xml")
                if xbmcvfs.exists( cachefile ):
                    allcachefiles.append(cachefile)
                else:
                    dirs, files = xbmcvfs.listdir(dir)
                    for dir2 in dirs:
                        cachefile = os.path.join(pvrthumbspath, dir.decode("utf-8"), dir2.decode("utf-8"), "pvrdetails.xml")
                        if xbmcvfs.exists( cachefile ):
                            allcachefiles.append(cachefile)
        return allcachefiles
    
    def setPvrBackground(self,windowProp):
        images = []
        if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnablePVRThumbs) + PVR.HasTVChannels"):
            return
        #get pvr images from cache first
        if (self.allBackgrounds.has_key(windowProp)):
            images = self.allBackgrounds[windowProp]
        else:
            images = []
            if not WINDOW.getProperty("SkinHelper.pvrthumbspath"): 
                setAddonsettings()
                
            #only get pvr images from recordings
            if SETTING("pvrBackgroundRecordingsOnly") == "true":
                json_query = getJSON('PVR.GetRecordings', '{ "properties": [ %s ]}' %( fields_pvrrecordings))
                for item in json_query:
                    genre = " / ".join(item["genre"])
                    artwork = artutils.getPVRThumbs(item["title"],item["channel"],"recordings",item["file"],genre)
                    fanart = getCleanImage(artwork.get("fanart",""))
                    if fanart and xbmcvfs.exists(fanart): 
                        images.append({"fanart": fanart, "title": artwork.get("title",""), "landscape": artwork.get("landscape",""), "poster": artwork.get("poster",""), "clearlogo": artwork.get("clearlogo","")})
                    
            #grab max 50 random images from persistant pvr cache files
            if not SETTING("pvrBackgroundRecordingsOnly") == "true":
                cachefiles = self.getPVRArtworkPersistantCacheFiles()
                random.shuffle(cachefiles)
                count = 0
                for cachefile in cachefiles:
                    artwork = artutils.getArtworkFromCacheFile(cachefile)
                    fanart = getCleanImage(artwork.get("fanart",""))
                    if fanart and xbmcvfs.exists(fanart):
                        count += 1
                        images.append({"fanart": fanart, "title": artwork.get("title",""), "landscape": artwork.get("landscape",""), "poster": artwork.get("poster",""), "clearlogo": artwork.get("clearlogo","")})
                    if count >= 50: break
                
            #store images in the cache
            self.allBackgrounds[windowProp] = images
            
        # return a random image
        if images:
            image = random.choice(images)
            for key, value in image.iteritems():
                if key == "fanart": WINDOW.setProperty(windowProp, value)
                else: WINDOW.setProperty(windowProp + "." + key, value)      
            
    def setGlobalBackground(self, windowProp, keys=[], fallbackImage=""):
        #gets a random background from multiple other collections
        image = fallbackImage
        images = []
        if self.allBackgrounds:
            #get images from the global cache...
            for key, value in self.allBackgrounds.iteritems():
                if key in keys or (windowProp == "SkinHelper.GlobalFanartBackground" and not "wall" in key.lower() and not "pvr" in key.lower() and not "netflix" in key.lower() ):
                    images += value
            #pick a random image from the collection of images
            if images:  
                image = random.choice(images)
                for key, value in image.iteritems():
                    if key == "fanart": WINDOW.setProperty(windowProp, value)
                    else: WINDOW.setProperty(windowProp + "." + key, value)
    
    def UpdateBackgrounds(self):

        if self.backgroundDelay == 0 or self.exit:
            return

        #conditional background
        WINDOW.setProperty("SkinHelper.ConditionalBackground", conditionalBackgrounds.getActiveConditionalBackground())
        
        #movies backgrounds 
        if xbmc.getCondVisibility("Library.HasContent(movies)"):
            self.setImageFromPath("SkinHelper.AllMoviesBackground","SkinHelper.AllMoviesBackground","",['VideoLibrary.GetMovies','{ "properties": ["title","art"], "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            self.setImageFromPath("SkinHelper.InProgressMoviesBackground","SkinHelper.InProgressMoviesBackground","",['VideoLibrary.GetMovies','{ "properties": ["title","art"], "filter": {"and": [{"operator":"true", "field":"inprogress", "value":""}]}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            self.setImageFromPath("SkinHelper.RecentMoviesBackground","SkinHelper.RecentMoviesBackground","",['VideoLibrary.GetRecentlyAddedMovies','{ "properties": ["title","art"], "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            self.setImageFromPath("SkinHelper.UnwatchedMoviesBackground","SkinHelper.UnwatchedMoviesBackground","",['VideoLibrary.GetMovies','{ "properties": ["title","art"], "filter": {"and": [{"operator":"is", "field":"playcount", "value":""}]}, "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            
        #tvshows backgrounds
        if xbmc.getCondVisibility("Library.HasContent(tvshows)"):
            self.setImageFromPath("SkinHelper.AllTvShowsBackground","SkinHelper.AllTvShowsBackground","",['VideoLibrary.GetTVShows','{ "properties": ["title","art"], "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            self.setImageFromPath("SkinHelper.InProgressShowsBackground","SkinHelper.InProgressShowsBackground","",['VideoLibrary.GetTVShows','{ "properties": ["title","art"], "filter": {"and": [{"operator":"true", "field":"inprogress", "value":""}]}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            self.setImageFromPath("SkinHelper.RecentEpisodesBackground","SkinHelper.RecentEpisodesBackground","",['VideoLibrary.GetRecentlyAddedEpisodes','{ "properties": ["title","art"], "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
            
        #all musicvideos
        if xbmc.getCondVisibility("Library.HasContent(musicvideos)"):
            self.setImageFromPath("SkinHelper.AllMusicVideosBackground","SkinHelper.AllMusicVideosBackground","",['VideoLibrary.GetMusicVideos','{ "properties": ["title","art"], "limits": {"end":50}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }'])
        
        #all music
        if xbmc.getCondVisibility("Library.HasContent(music)"):
            self.setImageFromPath("SkinHelper.AllMusicBackground","SkinHelper.AllMusicBackground","",['AudioLibrary.GetArtists','{ "properties": ["fanart","thumbnail"], "limits": {"end":250}, "sort": { "order": "ascending", "method": "random" } }'])
            self.setImageFromPath("SkinHelper.AllMusicSongsBackground","SkinHelper.AllMusicSongsBackground","",['AudioLibrary.GetSongs','{ "properties": ["title","fanart","artist","album","thumbnail"], "limits": {"end":250}, "sort": { "order": "ascending", "method": "random" } }'])
            self.setImageFromPath("SkinHelper.RecentMusicBackground","SkinHelper.RecentMusicBackground","",['AudioLibrary.GetRecentlyAddedAlbums','{ "properties": ["title","fanart","artist","thumbnail","artistid"], "limits": {"end":50} }'])
        
        #tmdb backgrounds (extendedinfo)
        if xbmc.getCondVisibility("System.HasAddon(script.extendedinfo)"):
            self.setImageFromPath("SkinHelper.TopRatedMovies","plugin://script.extendedinfo/?info=topratedmovies")
            self.setImageFromPath("SkinHelper.TopRatedShows","plugin://script.extendedinfo/?info=topratedtvshows")
        
        #pictures background
        self.setPicturesBackground("SkinHelper.PicturesBackground")
        
        #pvr background 
        self.setPvrBackground("SkinHelper.PvrBackground")
        
        #global backgrounds
        self.setGlobalBackground("SkinHelper.GlobalFanartBackground")
        self.setGlobalBackground("SkinHelper.AllVideosBackground", [ "SkinHelper.AllMoviesBackground", "SkinHelper.AllTvShowsBackground", "SkinHelper.AllMusicVideosBackground" ])
        self.setGlobalBackground("SkinHelper.RecentVideosBackground", [ "SkinHelper.RecentMoviesBackground", "SkinHelper.RecentEpisodesBackground" ])
        self.setGlobalBackground("SkinHelper.InProgressVideosBackground", [ "SkinHelper.InProgressMoviesBackground", "SkinHelper.InProgressShowsBackground" ])

    def UpdateWallBackgrounds(self):
        if WINDOW.getProperty("SkinHelper.enablewallbackgrounds") == "true":
            self.setWallImageFromPath("SkinHelper.AllMoviesBackground.Wall","SkinHelper.AllMoviesBackground")
            self.setWallImageFromPath("SkinHelper.AllMoviesBackground.Poster.Wall","SkinHelper.AllMoviesBackground","poster")
            self.setWallImageFromPath("SkinHelper.AllMusicBackground.Wall","SkinHelper.AllMusicBackground")
            self.setWallImageFromPath("SkinHelper.AllMusicSongsBackground.Wall","SkinHelper.AllMusicSongsBackground","thumbnail")
            self.setWallImageFromPath("SkinHelper.AllTvShowsBackground.Wall","SkinHelper.AllTvShowsBackground")
            self.setWallImageFromPath("SkinHelper.AllTvShowsBackground.Poster.Wall","SkinHelper.AllTvShowsBackground","poster")
    
    def UpdateSmartShortCuts(self,buildSmartshortcuts=False):
        
        #smart shortcuts --> emby nodes
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.emby) + Skin.HasSetting(SmartShortcuts.emby)"):
            if self.smartShortcuts.get("emby") and not buildSmartshortcuts:
                #randomize background image from cache
                nodes = self.smartShortcuts["emby"]
                for node in nodes:
                    self.setImageFromPath(node[0] + ".image",node[2])
            #build node listing
            elif WINDOW.getProperty("emby.nodes.total"):
                embyProperty = WINDOW.getProperty("emby.nodes.total")
                contentStrings = ["", ".recent", ".inprogress", ".unwatched", ".recentepisodes", ".inprogressepisodes", ".nextepisodes", "recommended"]
                nodes = []
                totalNodes = int(embyProperty)
                for i in range(totalNodes):
                    #stop if shutdown requested in the meanwhile
                    if self.exit: return
                    for contentString in contentStrings:
                        key = "emby.nodes.%s%s"%(str(i),contentString)
                        path = WINDOW.getProperty("emby.nodes.%s%s.path"%(str(i),contentString))
                        label = WINDOW.getProperty("emby.nodes.%s%s.title"%(str(i),contentString))
                        if path:
                            nodes.append( (key, label, path ) )
                            self.setImageFromPath("emby.nodes.%s%s.image"%(str(i),contentString),path)
                            if contentString == "": 
                                if not "emby.nodes.%s"%i in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append("emby.nodes.%s"%i )
                                createSmartShortcutSubmenu("emby.nodes.%s"%i,"special://home/addons/plugin.video.emby/icon.png")
                self.smartShortcuts["emby"] = nodes
                logMsg("Generated smart shortcuts for emby nodes: %s" %nodes)
        
        #stop if shutdown requested in the meanwhile
        if self.exit: return
        
        #smart shortcuts --> playlists
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.playlists)"):
            playlists = []
            if self.smartShortcuts.has_key("playlists") and not buildSmartshortcuts:
                #randomize background image from cache
                playlists = self.smartShortcuts["playlists"]
            else:
                #build node listing
                playlistCount = 0
                paths = [['special://videoplaylists/','VideoLibrary'], ['special://musicplaylists/','MusicLibrary']]
                for playlistpath in paths:
                    if not xbmcvfs.exists(playlistpath[0]): continue
                    media_array = getJSON('Files.GetDirectory','{ "directory": "%s", "media": "files" }' % playlistpath[0] )
                    for item in media_array:
                        try:
                            label = ""
                            if item["file"].endswith(".xsp"):
                                playlist = item["file"]
                                contents = xbmcvfs.File(playlist, 'r')
                                contents_data = contents.read()
                                contents.close()
                                xmldata = xmltree.fromstring(contents_data)
                                type = "unknown"
                                label = item["label"]
                                if self.setImageFromPath("playlist." + str(playlistCount) + ".image",playlist):
                                    for line in xmldata.getiterator():
                                        if line.tag == "smartplaylist":
                                            type = line.attrib['type']
                                        if line.tag == "name":
                                            label = line.text
                                    path = "ActivateWindow(%s,%s,return)" %(playlistpath[1],playlist)
                                    if not "playlist.%s"%playlistCount in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append("playlist.%s"%playlistCount )
                                    playlists.append( (playlistCount, label, path, playlist, type ))
                                    playlistCount += 1
                        except: 
                            logMsg("Error while processing smart shortcuts for playlist %s  --> This file seems to be corrupted, please remove it from your system to prevent any further errors."%item["file"], 0)
                self.smartShortcuts["playlists"] = playlists
                logMsg("Generated smart shortcuts for playlists: %s" %playlists)
            
            for playlist in playlists:
                self.setImageFromPath("playlist." + str(playlist[0]) + ".image",playlist[3])
                if not self.smartShortcutsFirstRunDone or buildSmartshortcuts:
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".label", playlist[1])
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".title", playlist[1])
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".action", playlist[2])
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".path", playlist[2])
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".content", playlist[3])
                    WINDOW.setProperty("playlist." + str(playlist[0]) + ".type", playlist[4])
                    
        #stop if shutdown requested in the meanwhile
        if self.exit: return
        
        #smart shortcuts --> favorites
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.favorites)"):
            favourites = []
            if self.smartShortcuts.has_key("favourites") and not buildSmartshortcuts:
                #randomize background image from cache
                favourites = self.smartShortcuts["favourites"]
            else:
                #build node listing
                try:
                    json_result = getJSON('Favourites.GetFavourites', '{"type": null, "properties": ["path", "thumbnail", "window", "windowparameter"]}')
                    for count, fav in enumerate(json_result):
                        if "windowparameter" in fav:
                            content = fav["windowparameter"]
                            #check if this is a valid path with content
                            if not "script://" in content.lower() and not "mode=9" in content.lower() and not "search" in content.lower() and not "play" in content.lower():
                                path = "ActivateWindow(%s,%s,return)" %(fav["window"],content)
                                if "&" in content and "?" in content and "=" in content and not content.endswith("/"): 
                                    content += "&widget=true"
                                type = detectPluginContent(content)
                                if type:
                                    if not "favorite.%s" %count in self.smartShortcuts["allSmartShortcuts"]: 
                                        self.smartShortcuts["allSmartShortcuts"].append("favorite.%s" %count )
                                    favourites.append( (count, fav["title"], path, content, type) )
                except Exception as e:
                    #something wrong so disable the smartshortcuts for this section for now
                    xbmc.executebuiltin("Skin.Reset(SmartShortcuts.favorites)")
                    logMsg("Error while processing smart shortcuts for favourites - set disabled.... ",0)
                    logMsg(str(e),0)
                self.smartShortcuts["favourites"] = favourites
                logMsg("Generated smart shortcuts for favourites: %s" %favourites)
                    
            for favourite in favourites:
                self.setImageFromPath("favorite." + str(favourite[0]) + ".image",favourite[2])
                if not self.smartShortcutsFirstRunDone or buildSmartshortcuts:
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".label", favourite[1] )
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".title", favourite[1] )
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".action", favourite[2] )
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".path", favourite[2] )
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".content", favourite[3] )
                    WINDOW.setProperty("favorite." + str(favourite[0]) + ".type", favourite[4] )
               
        #stop if shutdown requested in the meanwhile
        if self.exit: return
        
        #smart shortcuts --> plex nodes
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc) + Skin.HasSetting(SmartShortcuts.plex)"):
            nodes = []
            if self.smartShortcuts.has_key("plex") and not buildSmartshortcuts:
                #get plex nodes from cache...
                nodes = self.smartShortcuts["plex"]
            else:
                #build the plex listing...
                nodes = self.getPlexNodes()
                self.smartShortcuts["plex"] = nodes
                logMsg("Generated smart shortcuts for plex: %s" %nodes)
            for node in nodes:
                #randomize background image from cache
                self.setImageFromPath(node[0] + ".image",node[3])
                if buildSmartshortcuts or not self.smartShortcutsFirstRunDone:
                    #set other properties at first load only
                    WINDOW.setProperty(node[0] + ".label", node[1])
                    WINDOW.setProperty(node[0] + ".title", node[1])
                    WINDOW.setProperty(node[0] + ".action", node[2])
                    WINDOW.setProperty(node[0] + ".path", node[2])
                    WINDOW.setProperty(node[0] + ".content", node[3])
                    WINDOW.setProperty(node[0] + ".type", node[4])
                
        #stop if shutdown requested in the meanwhile
        if self.exit: return
                
        #smart shortcuts --> netflix nodes
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.flix2kodi) + Skin.HasSetting(SmartShortcuts.netflix)"):
            nodes = []
            if self.smartShortcuts.has_key("netflix") and not buildSmartshortcuts:
                #get the netflix nodes from cache...
                nodes = self.smartShortcuts["netflix"]
            else:
                #build the netflix listing...
                nodes = self.getNetflixNodes()
                self.smartShortcuts["netflix"] = nodes
            if nodes:
                for node in nodes:
                    key = node[0]
                    if len(node) == 6: imagespath = node[5]
                    else: imagespath = node[2]
                    #randomize background image from cache
                    if not key.startswith("netflix.generic.suggestions"):
                        self.setImageFromPath(key + ".image",imagespath,"special://home/addons/plugin.video.flix2kodi/fanart.jpg")
                    if buildSmartshortcuts or not self.smartShortcutsFirstRunDone:
                        #set other properties at first load only
                        WINDOW.setProperty(key + ".title", node[1])
                        WINDOW.setProperty(key + ".content", node[2])
                        WINDOW.setProperty(key + ".path", node[4])
                        WINDOW.setProperty(key + ".type", node[3])

        #store all smart shortcuts for exchange with skinshortcuts
        WINDOW.setProperty("allSmartShortcuts", repr(self.smartShortcuts["allSmartShortcuts"]))
            
        self.smartShortcutsFirstRunDone = True
    
    def getNetflixNodes(self):
        #build a listing of netflix nodes...
        
        if not xbmc.getCondVisibility("System.HasAddon(plugin.video.flix2kodi) + Skin.HasSetting(SmartShortcuts.netflix)") or self.exit:
            return []
        
        nodes = []
        netflixAddon = xbmcaddon.Addon('plugin.video.flix2kodi')
        profilename = netflixAddon.getSetting('profile_name').decode("utf-8")
        
        if profilename and netflixAddon.getSetting("username") and netflixAddon.getSetting("authorization_url"):
            logMsg("Generating netflix entries for profile %s .... "%profilename)
            #generic netflix shortcut
            key = "netflix.generic"
            label = netflixAddon.getAddonInfo('name')
            content = "plugin://plugin.video.flix2kodi/?mode=main&widget=true&url&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            imagespath = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=both&url=list%3f%26mylist&widget=true"
            type = "media"
            nodes.append( (key, label, content, type, path, imagespath ) )
            createSmartShortcutSubmenu("netflix.generic","special://home/addons/plugin.video.flix2kodi/icon.png")
            
            #generic netflix mylist
            key = "netflix.generic.mylist"
            label = netflixAddon.getLocalizedString(30104)
            content = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=both&url=list%3f%26mylist&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            type = "movies"
            nodes.append( (key, label, content, type, path ) )
            
            if self.exit: return
            
            #get mylist items...
            mylist = []
            media_array = getJSON('Files.GetDirectory','{ "properties": ["title"], "directory": "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=both&url=list%3f%26mylist&widget=true", "media": "files", "limits": {"end":50} }')
            for item in media_array:
                mylist.append(item["label"])
            
            #get dynamic entries...
            media_array = getJSON('Files.GetDirectory','{ "properties": ["title"], "directory": "plugin://plugin.video.flix2kodi/?mode=main&type=dynamic&widget=true", "media": "files", "limits": {"end":50} }')
            if media_array:
                itemscount = 0
                suggestionsNodefound = False
                for item in media_array:
                    if self.exit: return
                    if ("list_viewing_activity" in item["file"]) or ("mode=search" in item["file"]) or ("mylist" in item["file"]):
                        continue
                    elif profilename in item["label"] and not suggestionsNodefound: 
                        #this is the suggestions node!
                        suggestionsNodefound = True
                        #generic suggestions node
                        key = "netflix.generic.suggestions"
                        content = item["file"] + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #movies suggestions node
                        key = "netflix.movies.suggestions"
                        newpath = item["file"].replace("type=both","type=movie")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #tvshows suggestions node
                        key = "netflix.tvshows.suggestions"
                        newpath = item["file"].replace("type=both","type=show")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "tvshows", path ) )
                    elif profilename in item["label"] and suggestionsNodefound: 
                        #this is the continue watching node!
                        #generic inprogress node
                        key = "netflix.generic.inprogress"
                        content = item["file"] + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #movies inprogress node
                        key = "netflix.movies.inprogress"
                        newpath = item["file"].replace("type=both","type=movie")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #tvshows inprogress node
                        key = "netflix.tvshows.inprogress"
                        newpath = item["file"].replace("type=both","type=show")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "tvshows", path ) )
                    elif item["label"].lower().endswith("releases"): 
                        #this is the recent node!
                        #generic recent node
                        key = "netflix.generic.recent"
                        content = item["file"] + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #movies recent node
                        key = "netflix.movies.recent"
                        newpath = item["file"].replace("type=both","type=movie")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                        #tvshows recent node
                        key = "netflix.tvshows.recent"
                        newpath = item["file"].replace("type=both","type=show")
                        content = newpath + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "tvshows", path ) )
                    elif item["label"] == "Trending": 
                        #this is the trending node!
                        key = "netflix.generic.trending"
                        content = item["file"] + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        nodes.append( (key, item["label"], content, "movies", path ) )
                    else:
                        key = "netflix.generic.suggestions.%s" %itemscount
                        content = item["file"] + "&widget=true"
                        path = "ActivateWindow(Videos,%s,return)" %content
                        type = "movies"
                        nodes.append( (key, item["label"], content, type, path ) )
                        itemscount += 1
                        
                    #get recommended node...
                    for mylist_item in mylist:
                        if mylist_item in item["label"]:
                            key = "netflix.generic.recommended"
                            content = item["file"] + "&widget=true"
                            path = "ActivateWindow(Videos,%s,return)" %item["file"]
                            nodes.append( (key, item["label"], content, "movies", path ) )

            #netflix movies
            key = "netflix.movies"
            label = netflixAddon.getAddonInfo('name') + " " + netflixAddon.getLocalizedString(30100)
            content = "plugin://plugin.video.flix2kodi/?mode=main&thumb&type=movie&url&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            imagespath = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=movie&url=list%3f%26mylist&widget=true"
            type = "movies"
            nodes.append( (key, label, content, type, path, imagespath ) )
            createSmartShortcutSubmenu("netflix.movies","special://home/addons/plugin.video.flix2kodi/icon.png")
            
            #netflix movies mylist
            key = "netflix.movies.inprogress"
            label = netflixAddon.getLocalizedString(30100) + " - " + netflixAddon.getLocalizedString(30104)
            content = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=movie&url=list%3f%26mylist&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            type = "movies"
            nodes.append( (key, label, content, type, path ) )
                        
            #netflix movies genres
            key = "netflix.movies.genres"
            label = netflixAddon.getLocalizedString(30100) + " - " + netflixAddon.getLocalizedString(30108)
            content = "plugin://plugin.video.flix2kodi/?mode=list_genres&thumb&type=movie&url&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            type = "genres"
            nodes.append( (key, label, content, type, path ) )
            
            #netflix tvshows
            key = "netflix.tvshows"
            label = netflixAddon.getAddonInfo('name') + " " + netflixAddon.getLocalizedString(30101)
            content = "plugin://plugin.video.flix2kodi/?mode=main&thumb&type=show&url&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            imagespath = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=show&url=list%3f%26mylist&widget=true"
            type = "tvshows"
            nodes.append( (key, label, content, type, path, imagespath ) )
            createSmartShortcutSubmenu("netflix.tvshows","special://home/addons/plugin.video.flix2kodi/icon.png")
            
            #netflix tvshows mylist
            key = "netflix.tvshows.inprogress"
            label = netflixAddon.getLocalizedString(30101) + " - " + netflixAddon.getLocalizedString(30104)
            content = "plugin://plugin.video.flix2kodi/?mode=list_videos&thumb&type=show&url=list%3f%26mylist&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            type = "tvshows"
            nodes.append( (key, label, content, type, path ) )
            
            #netflix tvshows genres
            key = "netflix.tvshows.genres"
            label = netflixAddon.getLocalizedString(30101) + " - " + netflixAddon.getLocalizedString(30108)
            content = "plugin://plugin.video.flix2kodi/?mode=list_genres&thumb&type=show&url&widget=true"
            path = "ActivateWindow(Videos,%s,return)" %content
            type = "genres"
            nodes.append( (key, label, content, type, path ) )
            
            if not "netflix.generic" in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append("netflix.generic")
            if not "netflix.generic.movies" in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append("netflix.movies")
            if not "netflix.generic.tvshows" in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append("netflix.tvshows")
            
            logMsg("DONE Generating netflix entries --> %s"%repr(nodes))
            
        else:
            logMsg("SKIP Generating netflix entries - addon is not ready!")
        
        return nodes

    def getPlexNodes(self):
        nodes = []
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc) + Skin.HasSetting(SmartShortcuts.plex)") and not self.exit:
            xbmc.executebuiltin('RunScript(plugin.video.plexbmc,amberskin)')
            #wait a few seconds for the initialization to be finished
            self.monitor.waitForAbort(5)
            
            #get the plex setting if there are subnodes
            plexaddon = xbmcaddon.Addon(id='plugin.video.plexbmc')
            hasSecondaryMenus = plexaddon.getSetting("secondary") == "true"
            del plexaddon
            
            contentStrings = ["", ".ondeck", ".recent", ".unwatched"]
            totalNodes = 50
            for i in range(totalNodes):
                if not WINDOW.getProperty("plexbmc.%s.title"%i): break
                if self.exit: return
                for contentString in contentStrings:
                    key = "plexbmc.%s%s"%(i,contentString)
                    label = WINDOW.getProperty("plexbmc.%s.title"%i).decode("utf-8")
                    type = WINDOW.getProperty("plexbmc.%s.type"%i).decode("utf-8")
                    if type == "movie": type = "movies"
                    if hasSecondaryMenus: path = WINDOW.getProperty("plexbmc.%s.all"%i).decode("utf-8")
                    else: path = WINDOW.getProperty("plexbmc.%s.path"%i).decode("utf-8")
                    alllink = path
                    alllink = alllink.replace("mode=1", "mode=0")
                    alllink = alllink.replace("mode=2", "mode=0")
                    if contentString == ".recent":
                        label += " - Recently Added"
                        if type == "show": type = "episodes"
                        if hasSecondaryMenus: path = WINDOW.getProperty(key).decode("utf-8")
                        else: path = alllink.replace("/all", "/recentlyAdded")
                    elif contentString == ".ondeck":
                        label += " - On deck"
                        if type == "show": type = "episodes"
                        if hasSecondaryMenus: path = WINDOW.getProperty(key).decode("utf-8")
                        else: path = alllink.replace("/all", "/onDeck")
                    elif contentString == ".unwatched":
                        if type == "show": type = "episodes"
                        label += " - Unwatched"
                        path = alllink.replace("/all", "/unwatched")
                    elif contentString == "":
                        if type == "show": type = "tvshows"
                        if not key in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append(key)
                        createSmartShortcutSubmenu("plexbmc.%s"%i,"special://home/addons/plugin.video.plexbmc/icon.png")
                    
                    #append type to path
                    if "&" in path: 
                        path = path + "&type=" + type
                    else: 
                        path = path + "?type=" + type
                    content = getContentPath(path)
                    nodes.append( (key, label, path, content, type ) )
            
            #add plex channels as entry
            #extract path from one of the nodes as a workaround because main plex addon channels listing is in error
            if nodes:
                path = WINDOW.getProperty("plexbmc.0.path").decode("utf-8")
                if not path: path = WINDOW.getProperty("plexbmc.0.all").decode("utf-8")
                path = path.split("/library/")[0]
                path = path + "/channels/all&mode=21"
                path = path + ", return)"
                key = "plexbmc.channels"
                label = "Channels"
                content = getContentPath(path)
                nodes.append( (key, label, path, content, "episodes" ) )
                if not key in self.smartShortcuts["allSmartShortcuts"]: self.smartShortcuts["allSmartShortcuts"].append(key)
        
        return nodes
    
    def createImageWall(self,images,windowProp,type="fanart"):
        
        if SETTING("maxNumWallImages"):
            numWallImages = int(SETTING("maxNumWallImages"))
        else: 
            logMsg("Building WALL background disabled",0)
            return []
        
        #PIL fails on Android devices ?
        hasPilModule = True
        try:
            from PIL import Image
            im = Image.new("RGB", (1, 1))
            del im
        except:
            hasPilModule = False
        
        if not hasPilModule:
            logMsg("Building WALL background skipped - no PIL module present on this system!",0)
            return []
        
        if type=="thumbnail":
            #square images
            img_columns = 11
            img_rows = 7
            img_width = 260
            img_height = 260
        elif type=="poster":
            #poster images
            img_columns = 15
            img_rows = 5
            img_width = 128
            img_height = 216
        else:
            #landscaped images
            img_columns = 8
            img_rows = 8
            img_width = 240
            img_height = 135
        size = img_width, img_height
        
        wallpath = "special://profile/addon_data/script.skin.helper.service/wallbackgrounds/"
        if not xbmcvfs.exists(wallpath):
            xbmcvfs.mkdirs(wallpath)
        
        wall_images = []
        return_images = []

        if SETTING("reuseWallBackgrounds") == "true":
            #reuse the existing images - do not rebuild
            dirs, files = xbmcvfs.listdir(wallpath)
            for file in files:
                image = {}
                #return color and bw image combined - only if both are found
                if file.startswith(windowProp + "_BW.") and xbmcvfs.exists(os.path.join(wallpath.decode("utf-8"),file.replace("_BW",""))):
                    return_images.append({"wallbw": os.path.join(wallpath.decode("utf-8"),file), "wall": os.path.join(wallpath.decode("utf-8"),file.replace("_BW",""))})
        
        #build wall images if we do not already have (enough) images
        if len(return_images) < numWallImages: 
            #build the wall images
            logMsg("Building Wall background for %s - this might take a while..." %windowProp,0)
            images_required = img_columns*img_rows
            for image in images:
                image = image.get(type,"")
                if self.exit: return []
                if image and not image.startswith("music@") and not ".mp3" in image:
                    file = xbmcvfs.File(image)
                    try:
                        img_obj = io.BytesIO(bytearray(file.readBytes()))
                        img = Image.open(img_obj)
                        img = img.resize(size)
                        wall_images.append(img)
                    except: pass
                    finally: file.close()
            if wall_images:
                #duplicate images if we don't have enough
                
                while len(wall_images) < images_required:
                    wall_images += wall_images
                    
                for i in range(numWallImages):
                    if self.exit: return []
                    random.shuffle(wall_images)
                    img_canvas = Image.new("RGBA", (img_width * img_columns, img_height * img_rows))
                    counter = 0
                    for x in range(img_rows):
                        for y in range(img_columns):
                            img_canvas.paste(wall_images[counter], (y * img_width, x * img_height))
                            counter += 1
                    
                    #save the files..
                    out_file = xbmc.translatePath(os.path.join(wallpath.decode("utf-8"),windowProp + "." + str(i) + ".jpg")).decode("utf-8")
                    if xbmcvfs.exists(out_file): 
                        xbmcvfs.delete(out_file)
                        xbmc.sleep(500)
                    img_canvas.save(out_file, "JPEG")
                    
                    out_file_bw = xbmc.translatePath(os.path.join(wallpath.decode("utf-8"),windowProp + "_BW." + str(i) + ".jpg")).decode("utf-8")
                    if xbmcvfs.exists(out_file_bw): 
                        xbmcvfs.delete(out_file_bw)
                        xbmc.sleep(500)
                    img_canvas_bw = img_canvas.convert("L")
                    img_canvas_bw.save(out_file_bw, "JPEG")
                    
                    #add our images to the dict
                    return_images.append({"wall": out_file, "wallbw": out_file_bw })
                
            logMsg("Building Wall background %s DONE" %windowProp)
        return return_images         