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



class TitanThread ():

    favorites_art_links = []
    channels_art_links = []
    global_art_links = []
    musicvideo_art_links = []
    current_fav_art = 0
    current_channel_art = 0
    current_musicvideo_art = 0
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

            self.logMsg("updateCollectionArtLinks Processing Collection : " + name + " of type : " + collectionType, level=0)

            # Process collection item backgrounds
            collectionUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?ParentId=" + item.get("Id") + "&IncludeItemTypes=Movie,Series,Trailer,BoxSet&Fields=ParentId,Overview&Recursive=true&CollapseBoxSetItems=false&format=json"

            try:
                requesthandle = urllib2.urlopen(collectionUrl, timeout=60)
                jsonData = requesthandle.read()
                requesthandle.close()   
            except Exception, e:
                self.logMsg("updateCollectionArtLinks urlopen : " + str(e) + " (" + collectionUrl + ")", level=0)
                return False    

            collectionResult = json.loads(jsonData)

            collectionResult = collectionResult.get("Items")
            if(collectionResult == None):
                collectionResult = []   

            for col_item in collectionResult:

                id = col_item.get("Id")
                name = col_item.get("Name")
                MB3type = col_item.get("Type")
                images = col_item.get("BackdropImageTags")

                if(images != None and len(images) > 0):
                    stored_item = artLinks.get(id)

                    if(stored_item == None):

                        stored_item = {}
                        collections = []
                        collections.append(item.get("Name"))
                        stored_item["collections"] = collections
                        links = []
                        images = col_item.get("BackdropImageTags")
                        parentID = col_item.get("ParentId")
                        name = col_item.get("Name")
                        if (images == None):
                            images = []
                        index = 0

                        imageTag = col_item.get("ImageTags").get("Primary")
                        if imageTag == None:
                            imageTag = ""
                        posterImage = "http://localhost:15001/?id=" + str(id) + "&type=Primary" + "&tag=" + imageTag
                        for backdrop in images:

                            info = {}
                            info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
                            info["type"] = MB3type
                            info["index"] = index
                            info["id"] = id
                            info["parent"] = parentID
                            info["name"] = name
                            links.append(info)
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
        else:
            if(len(self.global_art_links) > 0):
                next, nextItem = self.findNextLink(self.global_art_links, self.current_global_art, filterOnCollectionName)
                self.current_global_art = next
                backGroundUrl = nextItem["url"]

        WINDOW.setProperty(windowPropertyName, backGroundUrl)


    def updateTypeArtLinks(self):

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
                info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
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
                info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
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
                info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
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
                    else:
                        self.logMsg("[TitanSkin] ...load images failed, will try again later")
                
                # set pictures on properties only every X seconds    
                if shortcheckinterval_current == 0:
                    self.logMsg("[TitanSkin] setting tile images")
                    self.setBackgroundLink("xbmb3c.usr.tvshows.0.image", WINDOW.getProperty("xbmb3c.usr.tvshows.0.title"))
                    self.setBackgroundLink("xbmb3c.usr.tvshows.1.image", WINDOW.getProperty("xbmb3c.usr.tvshows.1.title"))
                    self.setBackgroundLink("xbmb3c.usr.tvshows.2.image", WINDOW.getProperty("xbmb3c.usr.tvshows.2.title"))
                    self.setBackgroundLink("xbmb3c.usr.tvshows.3.image", WINDOW.getProperty("xbmb3c.usr.tvshows.3.title"))
                    self.setBackgroundLink("xbmb3c.std.movies.3.image", "favorites")
                    self.setBackgroundLink("xbmb3c.std.channels.0.image", "channels")
                    self.setBackgroundLink("xbmb3c.std.music.3.image", "musicvideos")
                    self.setBackgroundLink("xbmb3c.usr.movies.0.image", WINDOW.getProperty("xbmb3c.usr.movies.0.title"))
                    self.setBackgroundLink("xbmb3c.usr.movies.1.image", WINDOW.getProperty("xbmb3c.usr.movies.1.title"))
                    self.setBackgroundLink("xbmb3c.usr.movies.2.image", WINDOW.getProperty("xbmb3c.usr.movies.2.title"))
                    self.setBackgroundLink("xbmb3c.usr.movies.3.image", WINDOW.getProperty("xbmb3c.usr.movies.3.title"))
                    self.setBackgroundLink("xbmb3c.usr.movies.4.image", WINDOW.getProperty("xbmb3c.usr.movies.4.title"))
                    self.logMsg("[TitanSkin] setting images complete")
                    shortcheckinterval_current = self.shortcheckinterval
            
            fullcheckinterval_current -= 2
            shortcheckinterval_current -= 2
            doAbort = self.waitForAbort(2)


    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()    


xbmc.log("[TitanSkin] Started... fetching background images now")
pollingthread = TitanThread()
pollingthread.run()
