#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import threading
import xbmcvfs
import random
import xml.etree.ElementTree as etree
import base64
import json
from datetime import datetime
import Utils as utils


class LibraryMonitor(threading.Thread):
    
    event = None
    exit = False
    liPath = None
    liPathLast = None
    unwatched = 1
    lastEpPath = ""
    lastMusicDbId = None
    allStudioLogos = list()
    studioLogosPath = None
    LastStudioImagesPath = None
    delayedTaskInterval = 1800
    moviesetCache = {}
    extraFanartcache = {}
    musicArtCache = {}
    
    win = None
    addon = None
    addondir = None
    
    def __init__(self, *args):
        
        self.win = xbmcgui.Window( 10000 )
        self.addon = xbmcaddon.Addon(id='script.titanskin.helpers')
        self.addondir = xbmc.translatePath(self.addon.getAddonInfo('profile'))
        
        utils.logMsg("LibraryMonitor - started")
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)    
    
    def stop(self):
        utils.logMsg("LibraryMonitor - stop called",0)
        self.exit = True
        self.event.set()

    def run(self):

        lastListItemLabel = None
        KodiMonitor = xbmc.Monitor()

        while (self.exit != True):
            
            #do some background stuff every 30 minutes
            if (xbmc.getCondVisibility("!Window.IsActive(videolibrary) + !Window.IsActive(fullscreenvideo)")):
                if (self.delayedTaskInterval >= 1800):
                    self.getStudioLogos()
                    self.delayedTaskInterval = 0                   
            
            #flush cache if videolibrary has changed
            elif self.win.getProperty("widgetrefresh") == "refresh":
                self.moviesetCache = {}
            
            # monitor listitem props when musiclibrary is active
            elif (xbmc.getCondVisibility("Window.IsActive(musiclibrary) + !Container.Scrolling")):
                if self.win.getProperty("resetMusicArtCache") == "reset":
                    self.lastMusicDbId = None
                    self.musicArtCache = {}
                    self.win.clearProperty("resetMusicArtCache")
                try:
                    self.checkMusicArt()
                except Exception as e:
                    utils.logMsg("ERROR in checkMusicArt ! --> " + str(e), 0)
            
            # monitor listitem props when videolibrary is active
            elif (xbmc.getCondVisibility("[Window.IsActive(videolibrary) | Window.IsActive(movieinformation)] + !Window.IsActive(fullscreenvideo)")):
                
                self.liPath = xbmc.getInfoLabel("ListItem.Path")
                liLabel = xbmc.getInfoLabel("ListItem.Label")
                if ((liLabel != lastListItemLabel) and xbmc.getCondVisibility("!Container.Scrolling")):
                    
                    self.liPathLast = self.liPath
                    lastListItemLabel = liLabel
                    
                    # update the listitem stuff
                    try:
                        self.setDuration()
                        self.setStudioLogo()
                        self.focusEpisode()
                        self.checkExtraFanArt()
                        self.setMovieSetDetails()
                        self.setAddonName()
                    except Exception as e:
                        utils.logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
  
            else:
                #reset window props
                self.win.clearProperty("ListItemStudioLogo")
                self.win.clearProperty('Duration')
                self.win.setProperty("ExtraFanArtPath","") 
                self.win.clearProperty("bannerArt") 
                self.win.clearProperty("logoArt") 
                self.win.clearProperty("cdArt")
                self.win.clearProperty("songInfo")
                self.win.setProperty("ExtraFanArtPath","")
                
            
            xbmc.sleep(150)
            self.delayedTaskInterval += 0.15
                    
    def setMovieSetDetails(self):
        #get movie set details -- thanks to phil65 - used this idea from his skin info script
        
        self.win.clearProperty('MovieSet.Title')
        self.win.clearProperty('MovieSet.Runtime')
        self.win.clearProperty('MovieSet.Duration')
        self.win.clearProperty('MovieSet.Writer')
        self.win.clearProperty('MovieSet.Director')
        self.win.clearProperty('MovieSet.Genre')
        self.win.clearProperty('MovieSet.Country')
        self.win.clearProperty('MovieSet.Studio')
        self.win.clearProperty('MovieSet.Years')
        self.win.clearProperty('MovieSet.Year')
        self.win.clearProperty('MovieSet.Count')
        self.win.clearProperty('MovieSet.Plot')
            
        if xbmc.getCondVisibility("SubString(ListItem.Path,videodb://movies/sets/,left)"):
            
            dbId = xbmc.getInfoLabel("ListItem.DBID")
                    
            if dbId:
                
                #try to get from cache first
                if self.moviesetCache.has_key(dbId):
                    json_response = self.moviesetCache[dbId]
                else:
                    json_response = utils.getJSON('VideoLibrary.GetMovieSetDetails', '{"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer", "playcount", "genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country", "streamdetails"], "sort": { "order": "ascending",  "method": "year" }} }' % dbId)
                
                #save to cache
                self.moviesetCache[dbId] = json_response
                
                #clear_properties()
                if ("setdetails" in json_response):
                    
                    count = 1
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
                    title_header = "[B]" + str(json_response['setdetails']['limits']['total']) + " " + xbmc.getLocalizedString(20342) + "[/B][CR]"
                    set_fanart = []
                    for item in json_response['setdetails']['movies']:
                        
                        if item["playcount"] == 0:
                            unwatchedcount += 1
                        else:
                            watchedcount += 1
                        
                        art = item['art']
                        set_fanart.append(art.get('fanart', ''))
                        title_list += "[I]" + item['label'] + " (" + str(item['year']) + ")[/I][CR]"
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
                    self.win.setProperty('MovieSet.Plot', plot)
                    if json_response['setdetails']['limits']['total'] > 1:
                        self.win.setProperty('MovieSet.ExtendedPlot', title_header + title_list + "[CR]" + plot)
                    else:
                        self.win.setProperty('MovieSet.ExtendedPlot', plot)
                    self.win.setProperty('MovieSet.Title', title_list)
                    self.win.setProperty('MovieSet.Runtime', str(runtime / 60))
                    durationString = self.getDurationString(runtime / 60)
                    if durationString:
                        self.win.setProperty('MovieSet.Duration', durationString)
                    self.win.setProperty('MovieSet.Writer', " / ".join(writer))
                    self.win.setProperty('MovieSet.Director', " / ".join(director))
                    self.win.setProperty('MovieSet.Genre', " / ".join(genre))
                    self.win.setProperty('MovieSet.Country', " / ".join(country))
                    self.win.setProperty('MovieSet.Studio', " / ".join(studio))
                    listudio = None
                    for item in studio:
                        if item in self.allStudioLogos:
                            listudio = item
                            break
                    if listudio:
                        self.win.setProperty("ListItemStudio", listudio)
                    else:
                        self.win.clearProperty("ListItemStudio")
                    
                    self.win.setProperty('MovieSet.Years', " / ".join(years))
                    self.win.setProperty('MovieSet.Year', years[0] + " - " + years[-1])
                    self.win.setProperty('MovieSet.Count', str(json_response['setdetails']['limits']['total']))
                    self.win.setProperty('MovieSet.WatchedCount', str(watchedcount))
                    self.win.setProperty('MovieSet.UnWatchedCount', str(unwatchedcount))
                    
                    #rotate fanart from movies in set while listitem is in focus
                    if xbmc.getCondVisibility("Skin.HasSetting(EnableExtraFanart)"):
                        count = 5
                        delaycount = 5
                        backgroundDelayStr = xbmc.getInfoLabel("skin.string(extrafanartdelay)")
                        if backgroundDelayStr:
                            count = int(backgroundDelayStr)
                            delaycount = int(backgroundDelayStr)
                        while dbId == xbmc.getInfoLabel("ListItem.DBID") and set_fanart != []:
                            
                            if count == delaycount:
                                random.shuffle(set_fanart)
                                self.win.setProperty('ExtraFanArtPath', set_fanart[0])
                                count = 0
                            else:
                                xbmc.sleep(1000)
                                count += 1

    def setAddonName(self):
        # set addon name as property
        if not xbmc.Player().isPlayingAudio():
            if (xbmc.getCondVisibility("Container.Content(plugins) | !IsEmpty(Container.PluginName)")):
                AddonName = xbmc.getInfoLabel('Container.PluginName')
                AddonName = xbmcaddon.Addon(AddonName).getAddonInfo('name')
                self.win.setProperty("Player.AddonName", AddonName)
            else:
                self.win.clearProperty("Player.AddonName")
    
    def setStudioLogo(self):
        studio = xbmc.getInfoLabel('ListItem.Studio')
        studiologo = None
        
        #find logo if multiple found
        if "/" in studio:
            studios = studio.split(" / ")
            count = 0
            for item in studios:
                if item in self.allStudioLogos:
                    studiologo = self.studioLogosPath + studios[count]
                    break
                count += 1
        
        #find logo normal
        if studio in self.allStudioLogos:
            studiologo = self.studioLogosPath + studio
        else:
            #find logo by substituting characters
            studio = studio.replace(" (US)","")
            studio = studio.replace(" (UK)","")
            studio = studio.replace(" (CA)","")
            for logo in self.allStudioLogos:
                if logo.lower() == studio.lower():
                    studiologo = self.studioLogosPath + logo

        if studiologo:
            self.win.setProperty("ListItemStudioLogo", studiologo + ".png")
        else:
            self.win.clearProperty("ListItemStudioLogo")
                
    def getStudioLogos(self):
        #fill list with all studio logos
        StudioImagesCustompath = xbmc.getInfoLabel("Skin.String(StudioImagesCustompath)")
        if StudioImagesCustompath:
            path = StudioImagesCustompath
            if not (path.endswith("/") or path.endswith("\\")):
                path = path + os.sep()
        else:
            path = "special://skin/extras/flags/studios/"
        
        if path != self.LastStudioImagesPath:
            self.LastStudioImagesPath = path
            allLogos = list()
            dirs, files = xbmcvfs.listdir(path)
            for file in files:
                file = file.replace(".png","")
                file = file.replace(".PNG","")
                allLogos.append(file)
            
            self.studioLogosPath = path
            self.allStudioLogos = set(allLogos)
    
    def focusEpisode(self):
        # monitor episodes for auto focus first unwatched
        if xbmc.getCondVisibility("Skin.HasSetting(AutoFocusUnwatchedEpisode)"):
            
            #store unwatched episodes
            if ((xbmc.getCondVisibility("Container.Content(seasons) | Container.Content(tvshows)")) and xbmc.getCondVisibility("!IsEmpty(ListItem.Property(UnWatchedEpisodes))")):
                try:
                    self.unwatched = int(xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)"))
                except: pass
            
            if (xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")):
                
                if (xbmc.getInfoLabel("Container.FolderPath") != self.lastEpPath and self.unwatched != 0):
                    totalItems = 0
                    curView = xbmc.getInfoLabel("Container.Viewmode") 
                    viewId = int(self.getViewId(curView))
                    
                    wid = xbmcgui.getCurrentWindowId()
                    window = xbmcgui.Window( wid )        
                    control = window.getControl(int(viewId))
                    totalItems = int(xbmc.getInfoLabel("Container.NumItems"))
                    
                    #only do a focus if we're on top of the list, else skip to prevent bouncing of the list
                    if not int(xbmc.getInfoLabel("Container.Position")) > 1:
                        if (xbmc.getCondVisibility("Container.SortDirection(ascending)")):
                            curItem = 0
                            control.selectItem(0)
                            xbmc.sleep(250)
                            while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and totalItems >= curItem):
                                if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png" and xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label") != ".." and not xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label").startswith("*")):
                                    if curItem != 0:
                                        control.selectItem(curItem)
                                    break
                                else:
                                    curItem += 1
                        
                        elif (xbmc.getCondVisibility("Container.SortDirection(descending)")):
                            curItem = totalItems
                            control.selectItem(totalItems)
                            xbmc.sleep(250)
                            while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and curItem != 0):
                                
                                if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png"):
                                    control.selectItem(curItem-1)
                                    break
                                else:    
                                    curItem -= 1
                                        
            self.lastEpPath = xbmc.getInfoLabel("Container.FolderPath")
        
    def setDuration(self):
        # monitor listitem to set duration
        if (xbmc.getCondVisibility("!IsEmpty(ListItem.Duration)")):
            currentDuration = xbmc.getInfoLabel("ListItem.Duration")
            durationString = self.getDurationString(currentDuration)
            if durationString:
                self.win.setProperty('Duration', durationString)
            else:
                self.win.clearProperty('Duration')
        else:
            self.win.clearProperty('Duration')
        
    def getDurationString(self, duration):
        if duration == None or duration == 0:
            return None
        try:
            full_minutes = int(duration)
            minutes = full_minutes % 60
            hours   = full_minutes // 60
            durationString = str(hours) + ':' + str(minutes).zfill(2)
        except Exception as e:
            utils.logMsg("ERROR in getDurationString ! --> " + str(e), 0)
            return None
        return durationString
            
    def getViewId(self, viewString):
        # get all views from views-file
        viewId = None
        skin_view_file = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
        tree = etree.parse(skin_view_file)
        root = tree.getroot()
        for view in root.findall('view'):
            if viewString == xbmc.getLocalizedString(int(view.attrib['languageid'])):
                viewId=view.attrib['value']
        
        return viewId    

    def checkMusicArt(self):
        
        dbID = xbmc.getInfoLabel("ListItem.Label") + xbmc.getInfoLabel("ListItem.Artist") + xbmc.getInfoLabel("ListItem.Album")
        cacheFound = False

        if self.lastMusicDbId == dbID:
            return
        
        self.win.setProperty("ExtraFanArtPath","") 
        self.win.clearProperty("bannerArt") 
        self.win.clearProperty("logoArt") 
        self.win.clearProperty("cdArt")
        self.win.clearProperty("songInfo")
        
        self.lastMusicDbId = dbID
        
        if xbmc.getInfoLabel("ListItem.Label").startswith("..") or xbmc.getCondVisibility("![Container.Content(artists) | Container.Content(albums) | Container.Content(songs)]") or not xbmc.getInfoLabel("ListItem.FolderPath").startswith("musicdb"):
            return
        
        #get the items from cache first
        if self.musicArtCache.has_key(dbID + "cdArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "cdArt"] == "None":
                self.win.clearProperty("cdArt")   
            else:
                self.win.setProperty("cdArt",self.musicArtCache[dbID + "cdArt"])

        if self.musicArtCache.has_key(dbID + "logoArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "logoArt"] == "None":
                self.win.clearProperty("logoArt")   
            else:
                self.win.setProperty("logoArt",self.musicArtCache[dbID + "logoArt"])
                
        if self.musicArtCache.has_key(dbID + "bannerArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "bannerArt"] == "None":
                self.win.clearProperty("bannerArt")   
            else:
                self.win.setProperty("bannerArt",self.musicArtCache[dbID + "bannerArt"])
        
        if self.musicArtCache.has_key(dbID + "extraFanArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "extraFanArt"] == "None":
                self.win.setProperty("ExtraFanArtPath","")   
            else:
                self.win.setProperty("ExtraFanArtPath",self.musicArtCache[dbID + "extraFanArt"])
                
        if self.musicArtCache.has_key(dbID + "songInfo"):
            cacheFound = True
            if self.musicArtCache[dbID + "songInfo"] == "None":
                self.win.setProperty("songInfo","")   
            else:
                self.win.setProperty("songInfo",self.musicArtCache[dbID + "songInfo"])
               
        if not cacheFound:
            
            self.win.setProperty("fromcache","false")
            path = None
            json_response = None
            cdArt = None
            logoArt = None
            bannerArt = None
            extraFanArt = None
            songInfo = None
            folderPath = xbmc.getInfoLabel("ListItem.FolderPath")
            
            if xbmc.getCondVisibility("Container.Content(songs) | Container.Content(singles)"):
                if "singles/" in folderPath:
                    folderPath = folderPath.replace("musicdb://singles/","")
                    dbid = folderPath.replace(".mp3","").replace(".flac","").replace(".wav","").replace(".wma","").replace(".m4a","").replace(".dsf","").replace(".mka","").replace("?singles=true","")
                if "songs/" in folderPath:
                    folderPath = folderPath.replace("musicdb://songs/","")
                    dbid = folderPath.replace(".mp3","").replace(".flac","").replace(".wav","").replace(".wma","").replace(".m4a","").replace(".dsf","").replace(".mka","")
                elif "top100/" in folderPath:
                    folderPath = folderPath.replace("musicdb://top100/songs/","")
                    dbid = folderPath.replace(".mp3","").replace(".flac","").replace(".wav","").replace(".wma","").replace(".m4a","").replace(".dsf","").replace(".mka","")
                elif "artists/" in folderPath:
                    folderPath = folderPath.replace("musicdb://artists/","")
                    folderPath = folderPath.split("/")[2]
                    dbid = folderPath.split(".")[0]  
                json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongDetails", "params": { "songid": %s, "properties": [ "file","artistid","albumid","comment" ] }, "id": "libSongs"}'%int(dbid))
                
            elif xbmc.getCondVisibility("Container.Content(artists)"):
                if "/genres/" in folderPath:
                    folderPath = folderPath.replace("musicdb://genres/","")
                    dbid = folderPath.split("/")[1]
                else:    
                    folderPath = folderPath.replace("musicdb://artists/","")
                    dbid = folderPath.split("/")[0]
                json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "filter":{"artistid": %s}, "limits": { "start" : 0, "end": 5 }, "properties": [ "file","artistid" ] }, "id": "libSongs"}'%int(dbid))
            
            elif xbmc.getCondVisibility("Container.Content(albums)"):
                if "/artists/" in folderPath:
                    folderPath = folderPath.replace("musicdb://artists/","")
                    dbid = folderPath.split("/")[1]
                elif "/genres/" in folderPath:
                    folderPath = folderPath.replace("musicdb://genres/","")
                    dbid = folderPath.split("/")[1]
                elif "/years/" in folderPath:
                    folderPath = folderPath.replace("musicdb://years/","")
                    dbid = folderPath.split("/")[1]
                else:
                    folderPath = folderPath.replace("musicdb://albums/","")
                    folderPath = folderPath.replace("musicdb://recentlyaddedalbums/","")
                    folderPath = folderPath.replace("musicdb://recentlyplayedalbums/","")
                    folderPath = folderPath.replace("musicdb://top100/albums/","")
                    folderPath = folderPath.replace("musicdb://genres/","")
                    dbid = folderPath.split("/")[0]   
                json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "filter":{"albumid": %s}, "limits": { "start" : 0, "end": 5 }, "properties": [ "file","artistid" ] }, "id": "libSongs"}'%int(dbid))
            
            if json_response:
                song = None
                json_response = json.loads(json_response)
                if json_response.has_key("result"):
                    result = json_response["result"]
                    if result.has_key("songs"):
                        songs = result["songs"]
                        if len(songs) > 0:
                            song = songs[0]
                            path = song["file"]
                    elif result.has_key("songdetails"):
                        song = result["songdetails"]
                        path = song["file"]
                        if not songInfo:
                            json_response2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": { "albumid": %s, "properties": [ "musicbrainzalbumid","description" ] }, "id": "1"}'%song["albumid"])
                            json_response2 = json.loads(json_response2)
                            if json_response2.has_key("result"):
                                result = json_response2["result"]
                                if result.has_key("albumdetails"):
                                    albumdetails = result["albumdetails"]
                                    if albumdetails["description"]:
                                        songInfo = albumdetails["description"]
                    if not songInfo and song:
                        json_response2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": { "artistid": %s, "properties": [ "musicbrainzartistid","description" ] }, "id": "1"}'%song["artistid"][0])
                        json_response2 = json.loads(json_response2)
                        if json_response2.has_key("result"):
                            result = json_response2["result"]
                            if result.has_key("artistdetails"):
                                artistdetails = result["artistdetails"]
                                if artistdetails["description"]:
                                    songInfo = artistdetails["description"]

            if path:
                if "\\" in path:
                    delim = "\\"
                else:
                    delim = "/"
                        
                path = path.replace(path.split(delim)[-1],"")
                                      
                #extrafanart
                imgPath = os.path.join(path,"extrafanart" + delim)
                if xbmcvfs.exists(imgPath):
                    extraFanArt = imgPath
                else:
                    imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"extrafanart" + delim)
                    if xbmcvfs.exists(imgPath):
                        extraFanArt = imgPath
                
                #cdart
                if xbmcvfs.exists(os.path.join(path,"cdart.png")):
                    cdArt = os.path.join(path,"cdart.png")
                else:
                    imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"cdart.png")
                    if xbmcvfs.exists(imgPath):
                        cdArt = imgPath
                
                #banner
                if xbmcvfs.exists(os.path.join(path,"banner.jpg")):
                    bannerArt = os.path.join(path,"banner.jpg")
                else:
                    imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"banner.jpg")
                    if xbmcvfs.exists(imgPath):
                        bannerArt = imgPath
                        
                #logo
                imgPath = os.path.join(path,"logo.png")
                if xbmcvfs.exists(imgPath):
                    logoArt = imgPath
                else:
                    imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"logo.png")
                    if xbmcvfs.exists(imgPath):
                        logoArt = imgPath
   
            if extraFanArt:
                self.win.setProperty("ExtraFanArtPath",extraFanArt)
                self.musicArtCache[dbID + "extraFanArt"] = extraFanArt
            else:
                self.win.setProperty("ExtraFanArtPath","")
                self.musicArtCache[dbID + "extraFanArt"] = "None"
                    
            if cdArt:
                self.win.setProperty("CdArt",cdArt)
                self.musicArtCache[dbID + "cdArt"] = cdArt
            else:
                self.win.setProperty("ExtraFanArtPath","")
                self.musicArtCache[dbID + "cdArt"] = "None"
                
            if bannerArt:
                self.win.setProperty("bannerArt",bannerArt)
                self.musicArtCache[dbID + "bannerArt"] = bannerArt
            else:
                self.win.clearProperty("bannerArt")
                self.musicArtCache[dbID + "bannerArt"] = "None"

            if logoArt:
                self.win.setProperty("logoArt",logoArt)
                self.musicArtCache[dbID + "logoArt"] = logoArt
            else:
                self.win.clearProperty("logoArt")
                self.musicArtCache[dbID + "logoArt"] = "None"

            if songInfo:
                self.win.setProperty("songInfo",songInfo)
                self.musicArtCache[dbID + "songInfo"] = songInfo
            else:
                self.win.clearProperty("songInfo")
                self.musicArtCache[dbID + "songInfo"] = "None"
                
    def checkExtraFanArt(self):
        
        lastPath = None
        efaPath = None
        efaFound = False
        liArt = None
        containerPath = xbmc.getInfoLabel("Container.FolderPath")
        
        if xbmc.getCondVisibility("Window.IsActive(movieinformation)"):
            return
        
        #get the item from cache first
        if self.extraFanartcache.has_key(self.liPath):
            if self.extraFanartcache[self.liPath] == "None":
                self.win.setProperty("ExtraFanArtPath","")
                return
            else:
                self.win.setProperty("ExtraFanArtPath",self.extraFanartcache[self.liPath])
                return
        
        if not xbmc.getCondVisibility("Skin.HasSetting(EnableExtraFanart) + [Window.IsActive(videolibrary) | Window.IsActive(movieinformation)] + !Container.Scrolling"):
            self.win.setProperty("ExtraFanArtPath","")
            return
        
        if (self.liPath != None and (xbmc.getCondVisibility("Container.Content(movies) | Container.Content(seasons) | Container.Content(episodes) | Container.Content(tvshows)")) and not "videodb:" in self.liPath):
                           
            if xbmc.getCondVisibility("Container.Content(episodes)"):
                liArt = xbmc.getInfoLabel("ListItem.Art(tvshow.fanart)")
            
            # do not set extra fanart for virtuals
            if (("plugin://" in self.liPath) or ("addon://" in self.liPath) or ("sources" in self.liPath) or ("plugin://" in containerPath) or ("sources://" in containerPath) or ("plugin://" in containerPath)):
                self.win.setProperty("ExtraFanArtPath","")
                self.extraFanartcache[self.liPath] = "None"
                lastPath = None
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
                    if files.count > 1:
                        efaFound = True
                        
                if (efaPath != None and efaFound == True):
                    if lastPath != efaPath:
                        self.win.setProperty("ExtraFanArtPath",efaPath)
                        self.extraFanartcache[self.liPath] = efaPath
                        lastPath = efaPath       
                else:
                    self.win.setProperty("ExtraFanArtPath","")
                    self.extraFanartcache[self.liPath] = "None"
                    lastPath = None
        else:
            self.win.setProperty("ExtraFanArtPath","")
            lastPath = None

class Kodi_Monitor(xbmc.Monitor):
    
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    
    def onDatabaseUpdated(self, database):
        #update nextup list when library has changed
        WINDOW = xbmcgui.Window(10000)
        WINDOW.setProperty("widgetreload", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        #refresh some widgets when library has changed
        WINDOW.setProperty("widgetrefresh","refresh")
        xbmc.sleep(500)
        WINDOW.clearProperty("widgetrefresh")

    def onNotification(self,sender,method,data):
        if method == "VideoLibrary.OnUpdate":
            #update nextup list when library has changed
            WINDOW = xbmcgui.Window(10000)
            WINDOW.setProperty("widgetreload", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            #refresh some widgets when library has changed
            WINDOW.setProperty("widgetrefresh","refresh")
            xbmc.sleep(500)
            WINDOW.clearProperty("widgetrefresh")

                                           