import xbmc
import xbmcgui
import xbmcaddon
import json
import threading
from datetime import datetime, timedelta, time
import urllib
import urllib2
import random
import time
import os

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)


class TitanThread ():

    favorites_art_links = []
    channels_art_links = []
    global_art_links = []
    musicvideo_art_links = []
    photo_art_links = []
    current_fav_art = 0
    current_channel_art = 0
    current_musicvideo_art = 0
    current_photo_art = 0
    current_global_art = 0
    fullcheckinterval = 900
    shortcheckinterval = 30
    doDebugLog = False

    def updateArtLinks(self):
        try:
            result01 = self.updateCollectionArtLinks()
            result02 = self.updateTypeArtLinks()
            if (result01 == True and result02 == True):
                return True
            else:
                return False            
        except Exception, e:
            return False        

    def logMsg(self, msg, level = 1):
        if self.doDebugLog == True:
            xbmc.log(msg)

    def findNextLink(self, linkList, startIndex, filterOnName):
        currentIndex = startIndex

        isParentMatch = False

        while(isParentMatch == False):

            currentIndex = currentIndex + 1

            if(currentIndex == len(linkList)):
                currentIndex = 0

            if(currentIndex == startIndex):
                return (currentIndex, linkList[currentIndex]) # we checked everything and nothing was ok so return the first one again

            isParentMatch = True
            if(filterOnName != None and filterOnName != ""):
                isParentMatch = filterOnName in linkList[currentIndex]["collections"]

        nextIndex = currentIndex + 1

        if(nextIndex == len(linkList)):
            nextIndex = 0

        return (nextIndex, linkList[currentIndex])                 


    def updateCollectionArtLinks(self):
        
        from DownloadUtils import DownloadUtils
        downloadUtils = DownloadUtils()        

        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')

        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')    

        # get the user ID
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"

        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("urlopen : " + str(e) + " (" + userUrl + ")", level=0)
            return False  

        result = []

        try:
            result = json.loads(jsonData)
        except Exception, e:
            self.logMsg("jsonload : " + str(e) + " (" + jsonData + ")", level=0)
            return False

        userid = ""
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break        


        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/Root?format=json"
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateCollectionArtLinks urlopen : " + str(e) + " (" + userUrl + ")", level=0)
            return False

        self.logMsg("updateCollectionArtLinks UserData : " + str(jsonData), 2)
        result = json.loads(jsonData)

        parentid = result.get("Id")
        self.logMsg("updateCollectionArtLinks ParentID : " + str(parentid), 2)

        userRootPath = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?ParentId=&SortBy=SortName&Fields=CollectionType,Overview,RecursiveItemCount&format=json"
        try:
            requesthandle = urllib.urlopen(userRootPath, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateCollectionArtLinks urlopen : " + str(e) + " (" + userRootPath + ")", level=0)
            return False


        result = json.loads(jsonData)
        result = result.get("Items")

        artLinks = {}
        collection_count = 0
        WINDOW = xbmcgui.Window( 10000 )

        # process collections
        for item in result:

            collectionType = item.get("CollectionType", "")
            name = item.get("Name")
            childCount = item.get("RecursiveItemCount")
            if(childCount == None or childCount == 0):
                continue

            # Process collection item backgrounds
            collectionUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?ParentId=" + item.get("Id") + "&IncludeItemTypes=Movie,Series,MusicArtist,MusicAlbum,Trailer,MusicVideo,Photo,Video,Audio&Fields=ParentId,Overview&SortOrder=Descending&Recursive=true&CollapseBoxSetItems=false&format=json"
            try:
                requesthandle = urllib2.urlopen(collectionUrl, timeout=60)
                jsonData = requesthandle.read()
                requesthandle.close()   
            except Exception, e:
                self.logMsg("[Titanskin ERROR] updateCollectionArtLinks urlopen : " + str(e) + " (" + collectionUrl + ")", level=0)
                return False    
            collectionResult = json.loads(jsonData)
            
            self.logMsg("[Titanskin COLLECTION] -- " + item.get("Name") + " -- " + collectionUrl)

            collectionResult = collectionResult.get("Items")
            if(collectionResult == None):
                collectionResult = []   

            for col_item in collectionResult:

                id = col_item.get("Id")
                name = col_item.get("Name")
                MB3type = col_item.get("Type")
                images = col_item.get("BackdropImageTags")
                images2 = col_item.get("ImageTags")
                
                stored_item = artLinks.get(id)

                if(stored_item == None):

                    stored_item = {}
                    collections = []
                    collections.append(item.get("Name"))
                    stored_item["collections"] = collections
                    links = []
                    images = col_item.get("BackdropImageTags")
                    images2 = col_item.get("ImageTags")
                    images3 = col_item.get("ParentBackdropImageTags")
                    parentID = col_item.get("ParentId")
                    name = col_item.get("Name")
                    if (images == None):
                        images = []
                    if (images2 == None):
                        images2 = [] 
                    if (images3 == None):
                        images3 = []                            
                    index = 0
                  
                    if(col_item.get("Type") == "Photo") or images == []:
                        for imagetag in images2:
                            info = {}
                            info["url"] = downloadUtils.getArtwork(col_item, "Primary", index=str(index))
                            info["type"] = MB3type
                            info["index"] = index
                            info["id"] = id
                            info["parent"] = parentID
                            info["name"] = name
                            links.append(info)
                            index = index + 1
                        
                            stored_item["links"] = links
                            artLinks[id] = stored_item 
    
                    for backdrop in images:
                        info = {}
                        info["url"] = downloadUtils.getArtwork(col_item, "Backdrop", index=str(index))
                        info["type"] = MB3type
                        info["index"] = index
                        info["id"] = id
                        info["parent"] = parentID
                        info["name"] = name
                        links.append(info)
                        if(col_item.get("Type") == "Series"):
                            self.logMsg("[Titanskin IMAGE] -- " + name + " -- " + downloadUtils.getArtwork(col_item, "Backdrop", index=str(index)))
                        index = index + 1
                    
                        stored_item["links"] = links
                        artLinks[id] = stored_item
                else:
                    stored_item["collections"].append(item.get("Name"))

        collection_count = collection_count + 1

        # build global link list
        final_global_art = []

        for id in artLinks:
            item = artLinks.get(id)
            collections = item.get("collections")
            links = item.get("links")

            for link_item in links:
                link_item["collections"] = collections
                final_global_art.append(link_item)

        self.global_art_links = final_global_art
        random.shuffle(self.global_art_links)

        return True        



    def setBackgroundLink(self, windowPropertyName, filterOnCollectionName):

        WINDOW = xbmcgui.Window( 10000 )
        backGroundUrl = ""

        if (filterOnCollectionName == "favorites"):
            if(len(self.favorites_art_links) > 0):
                next, nextItem = self.findNextLink(self.favorites_art_links, self.current_fav_art, "")
                self.current_fav_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "channels"):
            if(len(self.channels_art_links) > 0):
                next, nextItem = self.findNextLink(self.channels_art_links, self.current_channel_art, "")
                self.current_channel_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "musicvideos"):
            if(len(self.channels_art_links) > 0):
                next, nextItem = self.findNextLink(self.musicvideo_art_links, self.current_musicvideo_art, "")
                self.current_musicvideo_art = next
                backGroundUrl = nextItem["url"] 
        elif (filterOnCollectionName == "photos"):
            if(len(self.photo_art_links) > 0):
                next, nextItem = self.findNextLink(self.photo_art_links, self.current_photo_art, "")
                self.current_photo_art = next
                backGroundUrl = nextItem["url"]          
        else:
            if(len(self.global_art_links) > 0):
                next, nextItem = self.findNextLink(self.global_art_links, self.current_global_art, filterOnCollectionName)
                self.current_global_art = next
                backGroundUrl = nextItem["url"]

        WINDOW.setProperty(windowPropertyName, backGroundUrl)


    def updateTypeArtLinks(self):
        
        from DownloadUtils import DownloadUtils
        downloadUtils = DownloadUtils()        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')

        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     

        # get the user ID
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"

        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateTypeArtLinks urlopen : " + str(e) + " (" + userUrl + ")", level=0)
            return False

        result = []

        try:
            result = json.loads(jsonData)
        except Exception, e:
            self.logMsg("jsonload : " + str(e) + " (" + jsonData + ")", level=0)
            return False

        userid = ""
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break

        self.logMsg("updateTypeArtLinks UserID : " + userid)

        # load Favorite Movie BG's
        favMoviesUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=Movie&Filters=IsFavorite&format=json"

        try:
            requesthandle = urllib2.urlopen(favMoviesUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateTypeArtLinks urlopen : " + str(e) + " (" + favMoviesUrl + ")", level=0)
            return False

        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:

                info = {}
                info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                info["index"] = index
                info["id"] = id
                info["parent"] = parentID
                info["name"] = name
                self.logMsg("BG Favorite Movie Image Info : " + str(info), level=0)

                if (info not in self.favorites_art_links):
                    self.favorites_art_links.append(info)
                index = index + 1

        random.shuffle(self.favorites_art_links)
        self.logMsg("Background Favorite Movie Art Links : " + str(len(self.favorites_art_links)))
        
        
        # load Music Video BG's
        musicMoviesUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=MusicVideo&format=json"

        try:
            requesthandle = urllib2.urlopen(musicMoviesUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateTypeArtLinks urlopen : " + str(e) + " (" + musicMoviesUrl + ")", level=0)
            return False

        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:

                info = {}
                info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                info["index"] = index
                info["id"] = id
                info["parent"] = parentID
                info["name"] = name
                self.logMsg("BG MusicVideo Image Info : " + str(info), level=0)

                if (info not in self.musicvideo_art_links):
                    self.musicvideo_art_links.append(info)
                index = index + 1

        random.shuffle(self.musicvideo_art_links)
        self.logMsg("Background MusicVideo Art Links : " + str(len(self.musicvideo_art_links))) 
        
        
        
        # load Photo BG's
        photosUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=30&Fields=ParentId,Overview&SortOrder=Descending&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=Photo&format=json"

        try:
            requesthandle = urllib2.urlopen(photosUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateTypeArtLinks urlopen : " + str(e) + " (" + photosUrl + ")", level=0)
            return False

        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            index = 0

            info = {}
            info["url"] = downloadUtils.getArtwork(item, "Primary", index=str(index))
            info["index"] = index
            info["id"] = id
            info["parent"] = parentID
            info["name"] = name
            self.logMsg("BG Photo Image Info : " + str(info), level=0)

            if (info not in self.photo_art_links):
                self.photo_art_links.append(info)
            index = index + 1

        random.shuffle(self.photo_art_links)
        self.logMsg("Background Photo Art Links : " + str(len(self.photo_art_links)))         
        
        
        


        # load Channels BG links
        channelsUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Channels?format=json"
        try:
            requesthandle = urllib2.urlopen(channelsUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateTypeArtLinks urlopen : " + str(e) + " (" + channelsUrl + ")", level=0)
            return False

        result = json.loads(jsonData)        

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            plot = item.get("Overview")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
                info = {}
                info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                info["index"] = index
                info["id"] = id
                info["plot"] = plot
                info["parent"] = parentID
                info["name"] = name
                self.logMsg("BG Channel Image Info : " + str(info), level=0)

            if (info not in self.channels_art_links):
                self.channels_art_links.append(info)    
            index = index + 1

        random.shuffle(self.channels_art_links)
        self.logMsg("Background Channel Art Links : " + str(len(self.channels_art_links)))

        return True         

    def waitForAbort(self, timeout):
        while (True):
            if timeout == 0:
                return False
        
            if (xbmc.abortRequested):
                xbmc.log("[TitanSkin] XBMC Shutdown detected....exiting now")
                return True
                
            time.sleep(timeout)
            timeout -= 1
        

    def run(self):
        self.logMsg("Started")
        
        fullcheckinterval_current = 0
        shortcheckinterval_current = 0

        doAbort = False
        while (not doAbort):
            
            WINDOW = xbmcgui.Window( 10000 )
            
            self.logMsg("[TitanSkin] fullscan interval currently " + str(fullcheckinterval_current))
            self.logMsg("[TitanSkin] shortscan interval currently " + str(shortcheckinterval_current))
            
            # actions only needed for XBMB3C add-on currently
            if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):

                # get images from server only if fullcheckinterval has reached
                if fullcheckinterval_current == 0:
                    self.logMsg("[TitanSkin] loading images from server...") 
                    if (self.updateArtLinks() == True):
                        fullcheckinterval_current = self.fullcheckinterval
                        self.logMsg("[TitanSkin] ...load images complete")
                        
                        # set MB3 content links
                        self.updateMB3links()                        
                    else:
                        self.logMsg("[TitanSkin] ...load images failed, will try again later")
                        
                
                
                # set pictures on properties only every X seconds    
                if shortcheckinterval_current == 0:
                    self.logMsg("[TitanSkin] setting tile images")
                    self.setBackgroundLink("xbmb3c.std.movies.3.image", "favorites")
                    self.setBackgroundLink("xbmb3c.std.channels.0.image", "channels")
                    self.setBackgroundLink("xbmb3c.std.music.3.image", "musicvideos")
                    self.setBackgroundLink("xbmb3c.std.photo.0.image", "photos")
                    
                    linkCount = 0
                    while linkCount !=20:
                        mbstring = "titanmb3." + str(linkCount)
                        self.logMsg("set backgroundlink for: " + mbstring)
                        if not "virtual" in WINDOW.getProperty(mbstring + ".type"):
                            self.setBackgroundLink(mbstring + ".image", WINDOW.getProperty(mbstring + ".title"))
                        linkCount += 1
                    
                    self.logMsg("[TitanSkin] setting images complete")
                    shortcheckinterval_current = self.shortcheckinterval
            
            fullcheckinterval_current -= 2
            shortcheckinterval_current -= 2
            doAbort = self.waitForAbort(2)


    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
    
    def updateMB3links(self):
        win = xbmcgui.Window( 10000 )
        linkCount = 0
        while linkCount !=20:
            orgmbstring = "xbmb3c." + str(linkCount)
            mbstring = "titanmb3." + str(linkCount)
            
            if "mediabrowser" in win.getProperty(orgmbstring + ".recent.path"):
                win.setProperty(mbstring + ".title", win.getProperty(orgmbstring + ".title"))
                win.setProperty(mbstring + ".type", win.getProperty(orgmbstring + ".type"))
                win.setProperty(mbstring + ".fanart", win.getProperty(orgmbstring + ".fanart"))
                win.setProperty(mbstring + ".path", win.getProperty(orgmbstring + ".path"))
                
                link = win.getProperty(orgmbstring + ".recent.path")
                link = link.replace("ActivateWindow(VideoLibrary,", "")
                link = link.replace(",return)", "")
                win.setProperty(mbstring + ".recent.content", link)
                
                if "musicvideo" in win.getProperty(orgmbstring + ".type"):
                    win.setProperty("xbmb3c.std.music.3.content", link)                
                
                link = win.getProperty(orgmbstring + ".unwatched.path")
                link = link.replace("ActivateWindow(VideoLibrary,", "")
                link = link.replace(",return)", "")
                win.setProperty(orgmbstring + ".unwatched.content", link)
                
                link = win.getProperty(orgmbstring + ".inprogress.path")
                link = link.replace("ActivateWindow(VideoLibrary,", "")
                link = link.replace(",return)", "")
                win.setProperty(mbstring + ".inprogress.content", link)  
                
                link = win.getProperty(orgmbstring + ".nextepisodes.path")
                link = link.replace("ActivateWindow(VideoLibrary,", "")
                link = link.replace(",return)", "")
                win.setProperty(mbstring + ".nextepisodes.content", link)
       

            linkCount += 1




xbmc.log("[TitanSkin] Started... fetching background images now")
pollingthread = TitanThread()
pollingthread.run()
