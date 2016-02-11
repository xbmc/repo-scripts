#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading
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
    skinShortcutsActive = False
    
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
            self.updateWallImages()
        except Exception as e:
            logMsg("ERROR in BackgroundsUpdater ! --> " + str(e), 0)
        
        #clear images cache once to get some fresh images
        self.allBackgrounds = {}
        self.smartShortcuts = {}
         
        while (self.exit != True):
        
            # Update Day/Night theme if enabled
            if (self.daynightThemeTaskInterval >= 30):
                self.daynightThemeTaskInterval = 0
                try:
                    self.setDayNightColorTheme()
                except Exception as e:
                    logMsg("ERROR in setDayNightColorTheme ! --> " + str(e), 0)
            
            #Process backgrounds
            if xbmc.getCondVisibility("![Window.IsActive(fullscreenvideo) | Window.IsActive(script.pseudotv.TVOverlay.xml) | Window.IsActive(script.pseudotv.live.TVOverlay.xml)] | Window.IsActive(script.pseudotv.live.EPG.xml)") and xbmc.getInfoLabel("skin.string(SkinHelper.RandomFanartDelay)"):

                # force refresh smart shortcuts when skin settings launched (so user sees any newly added smartshortcuts)
                if xbmc.getCondVisibility("Window.IsActive(script-skinshortcuts.xml) | Window.IsActive(SkinSettings)"):
                    if not self.skinShortcutsActive:
                        try: self.UpdateBackgrounds(refreshSmartshortcuts=True)
                        except Exception as e: logMsg("ERROR in UpdateBackgrounds ! --> " + str(e), 0)
                        self.skinShortcutsActive = True
                else: self.skinShortcutsActive = False      

                # Update home backgrounds every interval (if enabled by skinner)
                if self.backgroundDelay != 0:
                    if (self.backgroundsTaskInterval >= self.backgroundDelay):
                        self.backgroundsTaskInterval = 0
                        try:
                            self.UpdateBackgrounds()
                            self.setDayNightColorTheme()
                            self.getSkinConfig()
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
    
    def setDayNightColorTheme(self):
        #check if a colro theme should be conditionally set
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
        if self.exit:
            return False
            
        libPath = getContentPath(libPath)
        
        #special treatment for emby nodes...
        if "plugin.video.emby" in libPath and "browsecontent" in libPath and not "filter" in libPath:
            libPath = libPath + "&filter=random"
        
        logMsg("getting images for path " + libPath)

        #is path in the temporary blacklist ?
        if libPath in self.tempBlacklist:
            logMsg("path blacklisted - skipping for path " + libPath)
            return False
        
        #no blacklist so read cache and/or path
        logMsg("path is NOT blacklisted - continuing for path " + libPath)
        images = []
               
        #cache entry exists and cache is not expired, load cache entry
        if self.allBackgrounds.has_key(windowProp):
            logMsg("load random image from the cache file... " + libPath)
            image = random.choice(self.allBackgrounds[windowProp])
            if image:
                for key, value in image.iteritems():
                    if key == "fanart": WINDOW.setProperty(windowProp, value)
                    else: WINDOW.setProperty(windowProp + "." + key, value)
                return True
            else:
                logMsg("cache entry empty ?...skipping...")
                return False
        else:
            #no cache file so try to load images from the path
            logMsg("get images from the path or plugin... " + libPath)
            media_array = None
            #safety check: check if no library windows are active to prevent any addons setting the view
            if xbmc.getInfoLabel("$INFO[Window.Property(xmlfile)]").endswith("Nav.xml"):
                return
            if customJson:
                media_array = getJSON(customJson[0],customJson[1])
            else:
                media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art","thumbnail","fanart","album","artist"], "directory": "%s", "media": "files", "limits": {"end":250}, "sort": { "order": "ascending", "method": "random", "ignorearticle": true } }' %libPath)
            if media_array:
                for media in media_array:
                    image = {}
                    if media.get("thumbnail"):
                        image["thumbnail"] =  media.get("thumbnail")
                    if media.get('art') and not media['title'].lower() == "next page":
                        if media['art'].get('fanart'):
                            image["fanart"] = getCleanImage(media['art']['fanart'])
                        elif media['art'].get('tvshow.fanart'):
                            image["fanart"] = getCleanImage(media['art']['tvshow.fanart'])
                        #also append other mediatypes to the dict
                        if media['art'].get('landscape'): image["landscape"] = media['art']['landscape']
                        if media['art'].get('poster'): image["poster"] = media['art']['poster']
                        if media['art'].get('clearlogo'): image["clearlogo"] = media['art']['clearlogo']
                    elif media.get('fanart') and not media['title'].lower() == "next page":
                        image["fanart"] = media['fanart']
                    if not image and "musicdb" in libPath:
                        logMsg("get music artwork for libpath: %s  - artist: %s  - album: %s" %(libPath,media.get('artist',''),media.get('album','')))
                        if isinstance(media.get('artist'), list) and len(media.get('artist')) > 0: artist = media.get('artist')[0]
                        else: artist = media.get('artist','')
                        image = artutils.getMusicArtwork(artist,media.get('album',''))
                    if image:
                        image["title"] = media['title']
                        images.append(image)
                    
            else:
                logMsg("media array empty or error so add this path to blacklist..." + libPath)
                #add path to temporary blacklist
                self.tempBlacklist.add(libPath)
                WINDOW.setProperty(windowProp, fallbackImage)

        #all is fine, we have some images to randomize and return one
        if images:
            self.allBackgrounds[windowProp] = images
            random.shuffle(images)
            image = images[0]
            for key, value in image.iteritems():
                if key == "fanart": WINDOW.setProperty(windowProp, value)
                else: WINDOW.setProperty(windowProp + "." + key, value)
            return True
        else:
            logMsg("image array or cache empty so skipping this path until next restart - " + libPath)
            self.tempBlacklist.add(libPath)
            
        WINDOW.setProperty(windowProp, fallbackImage)
        return False

    def setPicturesBackground(self,windowProp):
        customPath = xbmc.getInfoLabel("skin.string(SkinHelper.CustomPicturesBackgroundPath)").decode("utf-8")
        
        #flush cache if custompath changed
        if (self.lastPicturesPath != customPath):
            self.allBackgrounds[windowProp] = []
            self.lastPicturesPath = customPath

        try:
            #get random image from cache
            if self.allBackgrounds.get(windowProp):
                image = random.choice(self.allBackgrounds[windowProp])
                if image:
                    for key, value in image.iteritems():
                        if key == "fanart": WINDOW.setProperty(windowProp, value)
                        else: WINDOW.setProperty(windowProp + "." + key, value)
                return 
            else:
                #load the pictures from the custom path or from all picture sources
                images = []
                
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
                else:
                    logMsg("image sources array or cache empty so skipping image-sources background untill next restart")
        #if something fails, return None
        except:
            logMsg("exception occured in getPicturesBackground.... ",0)           
    
    def setPvrBackground(self,windowProp):
        logMsg("setting pvr background...")
        try:
            if (self.allBackgrounds.has_key(windowProp)):
                #get random image from our global cache file
                if self.allBackgrounds[windowProp]:
                    image = random.choice(self.allBackgrounds[windowProp])
                    if image:
                        for key, value in image.iteritems():
                            if key == "fanart": WINDOW.setProperty(windowProp, value)
                            else: WINDOW.setProperty(windowProp + "." + key, value)
                    return True 
            else:
                images = []
                import ArtworkUtils as artutils
                if not WINDOW.getProperty("SkinHelper.pvrthumbspath"): setAddonsettings()
                customlookuppath = WINDOW.getProperty("SkinHelper.customlookuppath").decode("utf-8")
                pvrthumbspath = WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")
                paths = [customlookuppath, pvrthumbspath]
                for path in paths:
                    dirs, files = xbmcvfs.listdir(path)
                    for dir in dirs:
                        dir = try_decode(dir)
                        thumbdir = os.path.join(path,dir)
                        dirs2, files2 = xbmcvfs.listdir(thumbdir)
                        for file in files2:
                            if "pvrdetails.xml" in file:
                                artwork = artutils.getArtworkFromCacheFile(os.path.join(thumbdir,"pvrdetails.xml"))
                                fanart = getCleanImage(artwork.get("fanart",""))
                                if fanart and xbmcvfs.exists(fanart): images.append({"fanart": fanart, "title": artwork.get("title",""), "landscape": artwork.get("landscape",""), "poster": artwork.get("poster","")})
                                del artwork
                        for dir2 in dirs2:
                            thumbdir = os.path.join(dir,dir2.decode("utf-8"))
                            dirs3, files3 = xbmcvfs.listdir(thumbdir)
                            for file in files3:
                               if "pvrdetails.xml" in file:
                                    artwork = artutils.getArtworkFromCacheFile(os.path.join(thumbdir,"pvrdetails.xml"))
                                    fanart = getCleanImage(artwork.get("fanart",""))
                                    if fanart and xbmcvfs.exists(fanart): images.append({"fanart": fanart, "title": artwork.get("title",""), "landscape": artwork.get("landscape",""), "poster": artwork.get("poster","")})
                                    del artwork
                del artutils
                    
                #store images in the cache
                self.allBackgrounds[windowProp] = images
                
                # return a random image
                if images != []:
                    random.shuffle(images)
                    image = images[0]
                    if image:
                        for key, value in image.iteritems():
                            if key == "fanart": WINDOW.setProperty(windowProp, value)
                            else: WINDOW.setProperty(windowProp + "." + key, value)
                    return True
                else:
                    logMsg("pvrfanart empty so skipping pvrfanart background untill next restart")
                    return True
        #if something fails, return None
        except:
            logMsg("exception occured in getPvrBackground.... ",0)
            return False            
            
    def setGlobalBackground(self, windowProp, keys=[], fallbackImage=""):
        #gets a random background from multiple other collections
        image = fallbackImage
        images = []
        if self.allBackgrounds:
            #get images from the global cache...
            for key, value in self.allBackgrounds.iteritems():
                if (key in keys or windowProp == "SkinHelper.GlobalFanartBackground") and not "wall" in key.lower():
                    images += value
            #pick a random image from the collection of images
            if images:  
                image = random.choice(images)
                for key, value in image.iteritems():
                    if key == "fanart": WINDOW.setProperty(windowProp, value)
                    else: WINDOW.setProperty(windowProp + "." + key, value)
    
    def UpdateBackgrounds(self,refreshSmartshortcuts=False):
        
        allSmartShortcuts = []
        
        if self.backgroundDelay == 0:
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
            self.setImageFromPath("SkinHelper.AllMusicBackground","musicdb://artists/")
            self.setImageFromPath("SkinHelper.AllMusicSongsBackground","musicdb://songs/")
            self.setImageFromPath("SkinHelper.RecentMusicBackground","SkinHelper.RecentMusicBackground","",['AudioLibrary.GetRecentlyAddedAlbums','{ "properties": ["title","fanart"], "limits": {"end":50} }'])
        
        #tmdb backgrounds (extendedinfo)
        if xbmc.getCondVisibility("System.HasAddon(script.extendedinfo)"):
            self.setImageFromPath("SkinHelper.TopRatedMovies","plugin://script.extendedinfo/?info=topratedmovies")
            self.setImageFromPath("SkinHelper.TopRatedShows","plugin://script.extendedinfo/?info=topratedtvshows")
        
        #global backgrounds
        self.setGlobalBackground("SkinHelper.GlobalFanartBackground")
        self.setGlobalBackground("SkinHelper.AllVideosBackground", [ "SkinHelper.AllMoviesBackground", "SkinHelper.AllTvShowsBackground", "SkinHelper.AllMusicVideosBackground" ])
        self.setGlobalBackground("SkinHelper.RecentVideosBackground", [ "SkinHelper.RecentMoviesBackground", "SkinHelper.RecentEpisodesBackground" ])
        self.setGlobalBackground("SkinHelper.InProgressVideosBackground", [ "SkinHelper.InProgressMoviesBackground", "SkinHelper.InProgressShowsBackground" ])

        #pictures background
        picturesbg = self.setPicturesBackground("SkinHelper.PicturesBackground")
        
        #pvr background 
        pvrbackground = self.setPvrBackground("SkinHelper.PvrBackground")
        
        #smart shortcuts --> emby nodes
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.emby) + Skin.HasSetting(SmartShortcuts.emby)"):
            logMsg("Processing smart shortcuts for emby nodes.... ")
            
            if self.smartShortcuts.has_key("emby") and not refreshSmartshortcuts:
                logMsg("get emby entries from cache.... ")
                nodes = self.smartShortcuts["emby"]
                for node in nodes:
                    key = node[0]
                    label = node[1]
                    path = node[2]
                    self.setImageFromPath(key + ".image",node[2])
                    WINDOW.setProperty(key + ".title", label)
                    WINDOW.setProperty(key + ".path", path)
            
            elif WINDOW.getProperty("emby.nodes.total"):
                
                logMsg("no cache - Get emby entries from file.... ")            
               
                embyProperty = WINDOW.getProperty("emby.nodes.total")
                contentStrings = ["", ".recent", ".inprogress", ".unwatched", ".recentepisodes", ".inprogressepisodes", ".nextepisodes", "recommended"]
                if embyProperty:
                    nodes = []
                    totalNodes = int(embyProperty)
                    for i in range(totalNodes):
                        for contentString in contentStrings:
                            key = "emby.nodes.%s%s"%(str(i),contentString)
                            path = WINDOW.getProperty("emby.nodes.%s%s.path"%(str(i),contentString))
                            label = WINDOW.getProperty("emby.nodes.%s%s.title"%(str(i),contentString))
                            if path:
                                nodes.append( (key, label, path ) )
                                self.setImageFromPath("emby.nodes.%s%s.image"%(str(i),contentString),path)
                                if contentString == "": 
                                    allSmartShortcuts.append("emby.nodes." + str(i) )
                                    createSmartShortcutSubmenu("emby.nodes." + str(i),"special://home/addons/plugin.video.emby/icon.png")
                                
                    self.smartShortcuts["emby"] = nodes
                                        
        #smart shortcuts --> playlists
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.playlists)"):
            logMsg("Processing smart shortcuts for playlists.... ")
            if self.smartShortcuts.has_key("playlists") and not refreshSmartshortcuts:
                logMsg("get playlist entries from cache.... ")
                playlists = self.smartShortcuts["playlists"]
                for playlist in playlists:
                    playlistCount = playlist[0]
                    self.setImageFromPath("playlist." + str(playlistCount) + ".image",playlist[3])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".label",  playlist[1])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".title",  playlist[1])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".action", playlist[2])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".path", playlist[2])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".content", playlist[3])
                    WINDOW.setProperty("playlist." + str(playlistCount) + ".type", playlist[4])
            else:
                logMsg("no cache - Get playlist entries from file.... ")
                playlistCount = 0
                playlists = []
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
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".label", label)
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".title", label)
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".action", path)
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".path", path)
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".content", playlist)
                                    WINDOW.setProperty("playlist." + str(playlistCount) + ".type", type)
                                    allSmartShortcuts.append("playlist." + str(playlistCount) )
                                    playlists.append( (playlistCount, label, path, playlist, type ))
                                    playlistCount += 1
                        except: logMsg("Error while processing smart shortcuts for playlist %s  --> "%label, 0)
                self.smartShortcuts["playlists"] = playlists
                        
        #smart shortcuts --> favorites
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.favorites)"):
            logMsg("Processing smart shortcuts for favourites.... ")
            try:
                if self.smartShortcuts.has_key("favourites") and not refreshSmartshortcuts:
                    logMsg("get favourites entries from cache.... ")
                    favourites = self.smartShortcuts["favourites"]
                    for favourite in favourites:
                        favoritesCount = favourite[0]
                        if self.setImageFromPath("favorite." + str(favoritesCount) + ".image",favourite[2]):
                            WINDOW.setProperty("favorite." + str(favoritesCount) + ".label", favourite[1])
                            WINDOW.setProperty("favorite." + str(favoritesCount) + ".title", favourite[1])
                            WINDOW.setProperty("favorite." + str(favoritesCount) + ".action", favourite[2])
                            WINDOW.setProperty("favorite." + str(favoritesCount) + ".path", favourite[2])
                            WINDOW.setProperty("favorite." + str(favoritesCount) + ".content", favourite[3])
                else:
                    logMsg("no cache - Get favourite entries from file.... ")
                    favoritesCount = 0
                    favourites = []
                    fav_file = xbmc.translatePath( 'special://profile/favourites.xml' ).decode("utf-8")
                    if xbmcvfs.exists( fav_file ):
                        doc = parse( fav_file )
                        listing = doc.documentElement.getElementsByTagName( 'favourite' )
                        
                        for count, favourite in enumerate(listing):
                            name = favourite.attributes[ 'name' ].nodeValue
                            path = favourite.childNodes [ 0 ].nodeValue
                            content = getContentPath(path).lower()
                            if (path.startswith("activateWindow(videos") or path.startswith("activateWindow(10025") or path.startswith("activateWindow(videos") or path.startswith("activateWindow(music") or path.startswith("activateWindow(10502")) and not "script://" in path and not "mode=9" in path and not "search" in path and not "play" in path:
                                if self.setImageFromPath("favorite." + str(favoritesCount) + ".image",path):
                                    WINDOW.setProperty("favorite." + str(favoritesCount) + ".label", name)
                                    WINDOW.setProperty("favorite." + str(favoritesCount) + ".title", name)
                                    WINDOW.setProperty("favorite." + str(favoritesCount) + ".action", path)
                                    WINDOW.setProperty("favorite." + str(favoritesCount) + ".path", path)
                                    WINDOW.setProperty("favorite." + str(favoritesCount) + ".content", content)
                                    allSmartShortcuts.append("favorite." + str(favoritesCount) )
                                    favourites.append( (favoritesCount, name, path, content) )
                                    favoritesCount += 1
                                    
                    self.smartShortcuts["favourites"] = favourites
            except Exception as e:
                #something wrong so disable the smartshortcuts for this section for now
                xbmc.executebuiltin("Skin.Reset(SmartShortcuts.favorites)")
                logMsg("Error while processing smart shortcuts for favourites - set disabled.... ",0)
                logMsg(str(e),0)                
               
        #smart shortcuts --> plex nodes
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.plex)"):
            nodes = []
            logMsg("Processing smart shortcuts for plex nodes.... ")
            
            if self.smartShortcuts.get("plex") and not refreshSmartshortcuts:
                logMsg("get plex entries from cache.... ")
                nodes = self.smartShortcuts["plex"]
                for node in nodes:
                    key = node[0]
                    label = node[1]
                    path = node[2]
                    self.setImageFromPath(key + ".background",node[2])
                    self.setImageFromPath(key + ".image",node[2])
            elif WINDOW.getProperty("plexbmc.0.title"):
                logMsg("no cache - Get plex entries from file.... ")                      
                contentStrings = ["", ".ondeck", ".recent", ".unwatched"]
                if WINDOW.getProperty("plexbmc.0.title"):
                    nodes = []
                    totalNodes = 50
                    for i in range(totalNodes):
                        for contentString in contentStrings:
                            key = "plexbmc.%s%s"%(str(i),contentString)
                            path = WINDOW.getProperty("plexbmc.%s%s.content"%(str(i),contentString))
                            label = WINDOW.getProperty("plexbmc.%s%s.title"%(str(i),contentString))
                            plextype = WINDOW.getProperty("plexbmc.%s.type" %str(i))
                            if path:
                                nodes.append( (key, label, path ) )
                                if self.setImageFromPath("plexbmc.%s%s.background"%(str(i),contentString),path):
                                    self.setImageFromPath("plexbmc.%s%s.image"%(str(i),contentString),path)
                                    if contentString == "":
                                        allSmartShortcuts.append("plexbmc." + str(i) )
                                        createSmartShortcutSubmenu("plexbmc." + str(i),"special://home/addons/plugin.video.plexbmc/icon.png")
                            else:
                                break
                
                    #channels
                    plextitle = WINDOW.getProperty("plexbmc.channels.title")
                    key = "plexbmc.channels"
                    plexcontent = WINDOW.getProperty("plexbmc.channels.path")
                    if plexcontent:
                        if self.setImageFromPath("plexbmc.channels.background",plexcontent):
                            nodes.append( (key, plextitle, plexcontent ) )
                            self.setImageFromPath("plexbmc.channels.image",plexcontent)
                            allSmartShortcuts.append("plexbmc.channels")
                            
                    
                    self.smartShortcuts["plex"] = nodes
                 
        #smart shortcuts --> netflix nodes
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.netflixbmc) + Skin.HasSetting(SmartShortcuts.netflix)") and WINDOW.getProperty("netflixready") == "ready":
            
            if self.smartShortcuts.has_key("netflix") and not refreshSmartshortcuts:
                logMsg("get netflix entries from cache.... ")
                nodes = self.smartShortcuts["netflix"]
                for node in nodes:
                    key = node[0]
                    label = node[1]
                    content = node[2]
                    path = node[3]
                    type = node[4]
                    if len(node) == 6:
                        imagespath = node[5]
                    else:
                        imagespath = content
                    self.setImageFromPath(key + ".image",imagespath,"special://home/addons/plugin.video.netflixbmc/fanart.jpg")
                    WINDOW.setProperty(key + ".title", label)
                    WINDOW.setProperty(key + ".content", content)
                    WINDOW.setProperty(key + ".path", path)
          
            
            else:
                nodes = []
                netflixAddon = xbmcaddon.Addon('plugin.video.netflixbmc')
                logMsg("no cache - Generate netflix entries.... ")
                
                #generic netflix shortcut
                key = "netflix.generic"
                label = netflixAddon.getAddonInfo('name')
                content = "plugin://plugin.video.netflixbmc/?mode=main&widget=true&url"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                imagespath = "plugin://plugin.video.netflixbmc/?mode=listViewingActivity&thumb=&type=both&url&widget=true"
                type = "media"
                nodes.append( (key, label, content, path, type, imagespath ) )
                createSmartShortcutSubmenu("netflix.generic","special://home/addons/plugin.video.netflixbmc/icon.png")
                
                #generic netflix mylist
                key = "netflix.generic.mylist"
                label = netflixAddon.getLocalizedString(30002)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=both&widget=true&url=slider_38"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #generic netflix suggestions
                key = "netflix.generic.suggestions"
                label = netflixAddon.getLocalizedString(30143)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=both&widget=true&url=slider_2"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #generic netflix inprogress
                key = "netflix.generic.inprogress"
                label = netflixAddon.getLocalizedString(30121)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=both&widget=true&url=slider_0"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #generic netflix recent
                key = "netflix.generic.recent"
                label = netflixAddon.getLocalizedString(30003)
                content = "plugin://plugin.video.netflixbmc/?mode=listVideos&thumb&type=both&widget=true&url=http%3a%2f%2fwww.netflix.com%2fWiRecentAdditionsGallery%3fnRR%3dreleaseDate%26nRT%3dall%26pn%3d1%26np%3d1%26actionMethod%3djson"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )

                #netflix movies
                key = "netflix.movies"
                label = netflixAddon.getAddonInfo('name') + " " + netflixAddon.getLocalizedString(30011)
                content = "plugin://plugin.video.netflixbmc/?mode=main&thumb&type=movie&url&widget=true"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                imagespath = "plugin://plugin.video.netflixbmc/?mode=listViewingActivity&thumb=&type=movie&url&widget=true"
                type = "movies"
                nodes.append( (key, label, content, path, type, imagespath ) )
                createSmartShortcutSubmenu("netflix.movies","special://home/addons/plugin.video.netflixbmc/icon.png")
                
                #netflix movies mylist
                key = "netflix.movies.mylist"
                label = netflixAddon.getLocalizedString(30011) + " - " + netflixAddon.getLocalizedString(30002)
                content = "plugin://plugin.video.netflixbmc/?mode=listVideos&thumb&type=movie&widget=true&url=http%3a%2f%2fwww.netflix.com%2fMyList%3fleid%3d595%26link%3dseeall"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #netflix movies suggestions
                key = "netflix.movies.suggestions"
                label = netflixAddon.getLocalizedString(30011) + " - " + netflixAddon.getLocalizedString(30143)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=movie&widget=true&url=slider_2"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )

                #netflix movies inprogress
                key = "netflix.movies.inprogress"
                label = netflixAddon.getLocalizedString(30011) + " - " + netflixAddon.getLocalizedString(30121)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=movie&widget=true&url=slider_4"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #netflix movies recent
                key = "netflix.movies.recent"
                label = netflixAddon.getLocalizedString(30011) + " - " + netflixAddon.getLocalizedString(30003)
                content = "plugin://plugin.video.netflixbmc/?mode=listVideos&thumb&type=movie&widget=true&url=http%3a%2f%2fwww.netflix.com%2fWiRecentAdditionsGallery%3fnRR%3dreleaseDate%26nRT%3dall%26pn%3d1%26np%3d1%26actionMethod%3djson"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "movies"
                nodes.append( (key, label, content, type, path ) )
                
                #netflix tvshows
                key = "netflix.tvshows"
                label = netflixAddon.getAddonInfo('name') + " " + netflixAddon.getLocalizedString(30012)
                content = "plugin://plugin.video.netflixbmc/?mode=main&thumb&type=tv&url"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                imagespath = "plugin://plugin.video.netflixbmc/?mode=listViewingActivity&thumb=&type=movie&url&widget=true"
                type = "tvshows"
                nodes.append( (key, label, content, path, type, imagespath ) )
                createSmartShortcutSubmenu("netflix.tvshows","special://home/addons/plugin.video.netflixbmc/icon.png")
                
                #netflix tvshows mylist
                key = "netflix.tvshows.mylist"
                label = netflixAddon.getLocalizedString(30012) + " - " + netflixAddon.getLocalizedString(30002)
                content = "plugin://plugin.video.netflixbmc/?mode=listVideos&thumb&type=tv&widget=true&url=http%3a%2f%2fwww.netflix.com%2fMyList%3fleid%3d595%26link%3dseeall"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "tvshows"
                nodes.append( (key, label, content, type, path ) )
                
                #netflix tvshows suggestions
                key = "netflix.tvshows.suggestions"
                label = netflixAddon.getLocalizedString(30012) + " - " + netflixAddon.getLocalizedString(30143)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=tv&widget=true&url=slider_2"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "tvshows"
                nodes.append( (key, label, content, type, path ) )

                #netflix tvshows inprogress
                key = "netflix.tvshows.inprogress"
                label = netflixAddon.getLocalizedString(30012) + " - " + netflixAddon.getLocalizedString(30121)
                content = "plugin://plugin.video.netflixbmc/?mode=listSliderVideos&thumb&type=tv&widget=true&url=slider_4"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "tvshows"
                nodes.append( (key, label, content, type, path ) )
                
                #netflix tvshows recent
                key = "netflix.tvshows.recent"
                label = netflixAddon.getLocalizedString(30012) + " - " + netflixAddon.getLocalizedString(30003)
                content = "plugin://plugin.video.netflixbmc/?mode=listVideos&thumb&type=tv&widget=true&url=http%3a%2f%2fwww.netflix.com%2fWiRecentAdditionsGallery%3fnRR%3dreleaseDate%26nRT%3dall%26pn%3d1%26np%3d1%26actionMethod%3djson"
                path = "ActivateWindow(Videos,%s,return)" %content.replace("&widget=true","")
                type = "tvshows"
                nodes.append( (key, label, content, type, path ) )
                
                for node in nodes:
                    key = node[0]
                    label = node[1]
                    content = node[2]
                    path = node[3]
                    type = node[4]
                    if len(node) == 6:
                        imagespath = node[5]
                    else:
                        imagespath = content
                    self.setImageFromPath(key + ".image",imagespath, "special://home/addons/plugin.video.netflixbmc/fanart.jpg")
                    WINDOW.setProperty(key + ".title", label)
                    WINDOW.setProperty(key + ".content", content)
                    WINDOW.setProperty(key + ".path", path)
                    WINDOW.setProperty(key + ".type", type) 
                    
                self.smartShortcuts["netflix"] = nodes
                allSmartShortcuts.append("netflix.generic")
                allSmartShortcuts.append("netflix.movies")
                allSmartShortcuts.append("netflix.tvshows")
                
        if allSmartShortcuts:
            self.smartShortcuts["allSmartShortcuts"] = allSmartShortcuts
            WINDOW.setProperty("allSmartShortcuts", repr(allSmartShortcuts))
        elif self.smartShortcuts.has_key("allSmartShortcuts"):
            WINDOW.setProperty("allSmartShortcuts", repr(self.smartShortcuts["allSmartShortcuts"]))
      
                
        #wall backgrounds
        self.setWallImageFromPath("SkinHelper.AllMoviesBackground.Wall","SkinHelper.AllMoviesBackground")
        self.setWallImageFromPath("SkinHelper.AllMoviesBackground.Poster.Wall","SkinHelper.AllMoviesBackground","poster")
        self.setWallImageFromPath("SkinHelper.AllMusicBackground.Wall","SkinHelper.AllMusicBackground")
        self.setWallImageFromPath("SkinHelper.AllMusicSongsBackground.Wall","SkinHelper.AllMusicSongsBackground","thumbnail")
        self.setWallImageFromPath("SkinHelper.AllTvShowsBackground.Wall","SkinHelper.AllTvShowsBackground")
        self.setWallImageFromPath("SkinHelper.AllTvShowsBackground.Poster.Wall","SkinHelper.AllTvShowsBackground","poster")
                
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
                
        logMsg("Building Wall background %s DONE" %windowProp,0)
        return return_images         