#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests, urllib
import base64
from xml.dom.minidom import Document
import xml.etree.ElementTree as ET
from Utils import *
import musicbrainzngs as m

tmdb_apiKey = base64.b64decode("NDc2N2I0YjJiYjk0YjEwNGZhNTUxNWM1ZmY0ZTFmZWM=")
m.set_useragent("script.skin.helper.service", "1.0.0", "https://github.com/marcelveldt/script.skin.helper.service")

def getPVRThumbs(title,channel,type="channels",path="",genre="",ignoreCache=False, manualLookup=False):
    cacheFound = False
    ignore = False
    artwork = {}
    pvrThumbPath = None

    if title: title = urllib.unquote(title)
    if channel: channel = urllib.unquote(channel)
        
    #should we ignore this path ?
    ignoretitles = WINDOW.getProperty("SkinHelper.ignoretitles")
    ignorechannels = WINDOW.getProperty("SkinHelper.ignorechannels")
    stripwords = WINDOW.getProperty("SkinHelper.stripwords")
    splittitlechar = WINDOW.getProperty("SkinHelper.splittitlechar")
    if splittitlechar:
        if splittitlechar in title:
            title = title.split(splittitlechar)[0]
    if ignorechannels:
        for item in ignorechannels.split(";"):
            if item.lower() == channel.lower(): ignore = True
    if ignoretitles:
        for item in ignoretitles.split(";"):
            if item.lower() in title.lower(): ignore = True
    if stripwords:
        for word in stripwords.split(";"): title = title.replace(word,"")
        
    if ignore and not manualLookup:
        logMsg("getPVRThumb ignore filter active for %s %s--> "%(title,channel))
        return {}
        
    # Strip channel from title
    title = title.replace(channel,"")
    if title.endswith("-"): title = title[:-1]
    if title.endswith(" - "): title = title[:-3]

    comparetitle = getCompareString(title)
    dbID = comparetitle + channel
    logMsg("getPVRThumb for %s %s--> "%(title,channel))
    
    #make sure we have our settings cached in memory...
    if not WINDOW.getProperty("SkinHelper.pvrthumbspath"):
        setAddonsettings()
        
    if type=="channels" and WINDOW.getProperty("SkinHelper.enablePVRThumbsRecordingsOnly")=="true":
        #pvr artwork disabled for channels
        return {}
    if type=="channels" and WINDOW.getProperty("SkinHelper.cacheGuideEntries")=="true":
        downloadLocal = True
    elif type=="recordings" and WINDOW.getProperty("SkinHelper.cacheRecordings")=="true":
        downloadLocal = True
    else:
        downloadLocal = False
        
    #get the items from cache first
    cache = WINDOW.getProperty("SkinHelper.PVR.Artwork").decode('utf-8')
    if cache and ignoreCache==False:
        cache = eval(cache)
        if cache.has_key(dbID): 
            artwork = cache[dbID]
            cacheFound = True
            logMsg("getPVRThumb cache found for dbID--> " + dbID)
    else: cache = {}
    
    if not cacheFound:
        logMsg("getPVRThumb no cache found for dbID--> " + dbID)
        
        pvrThumbPath = getPvrThumbPath(channel,title)
        logMsg("pvr thumbs path --> " + pvrThumbPath)
        
        #Do we have a persistant cache file (pvrdetails.xml) for this item ?
        cachefile = os.path.join(pvrThumbPath, "pvrdetails.xml")
        if not ignoreCache:
            artwork = getArtworkFromCacheFile(cachefile,artwork)
        if artwork:
            cacheFound = True
            #modify cachefile with last access date for future auto cleanup
            artwork["last_accessed"] = "%s" %datetime.now()
            createNFO(cachefile,artwork)
                
        if not cacheFound:
        
            searchtitle = title
            if manualLookup:
                searchtitle = xbmcgui.Dialog().input(ADDON.getLocalizedString(32147), title, type=xbmcgui.INPUT_ALPHANUM)
            
            #lookup actual recordings to get details for grouped recordings
            #also grab a thumb provided by the pvr
            #NOTE: for episode level in series recordings, skinners should just get the pvr provided thumbs (listitem.thumb) in the skin itself because the cache is based on title not episode
            #the thumb image will be filled with just one thumb from the series (or google image if pvr doesn't provide a thumb)
            json_query = getJSON('PVR.GetRecordings', '{ "properties": [ %s ]}' %( fields_pvrrecordings))
            for item in json_query:
                if (path and path in item["file"]) or (not path and title in item["file"]) or (not channel and title in item["file"]):
                    logMsg("getPVRThumbs - title or path matches an existing recording: " + title)
                    if not channel: 
                        channel = item["channel"]
                        artwork["channel"] = channel
                    if not genre:
                        artwork["genre"] = " / ".join(item["genre"])
                        genre = " / ".join(item["genre"])
                    if item.get("art"):
                        artwork = item["art"]
                    if item.get("plot"):
                        artwork["plot"] = item["plot"]
                        break
            
            #lookup existing artwork in pvrthumbs paths
            if xbmcvfs.exists(pvrThumbPath):
                logMsg("thumbspath found on disk for " + title)
                for artType in KodiArtTypes:
                    artpath = os.path.join(pvrThumbPath,artType[1])
                    if xbmcvfs.exists(artpath) and not artwork.get(artType[0]):
                        artwork[artType[0]] = artpath
                        logMsg("%s found on disk for %s" %(artType[0],title))
                        
            #lookup local library
            if WINDOW.getProperty("SkinHelper.useLocalLibraryLookups") == "true":
                item = None
                json_result = getJSON('VideoLibrary.GetTvShows','{ "filter": {"operator":"is", "field":"title", "value":"%s"}, "properties": [ %s ] }' %(searchtitle,fields_tvshows))
                if len(json_result) > 0:
                    item = json_result[0]
                else:
                    json_result = getJSON('VideoLibrary.GetMovies','{ "filter": {"operator":"is", "field":"title", "value":"%s"}, "properties": [ %s ] }' %(searchtitle,fields_movies))
                    if len(json_result) > 0:
                        item = json_result[0]
                if item and item.has_key("art"): 
                    artwork = item["art"]
                    if item.get("plot"): artwork["plot"] = item["plot"]
                    logMsg("getPVRThumb artwork found in local library for dbID--> " + dbID)
                    
            #get logo if none found
            if not artwork.has_key("channellogo") and channel:
                artwork["channellogo"] = searchChannelLogo(channel)
                    
            #if nothing in library or persistant cache, perform the internet scraping
            if not cacheFound and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
                    
                #grab artwork from tmdb/fanart.tv
                if WINDOW.getProperty("SkinHelper.useTMDBLookups") == "true" or manualLookup:
                    if "movie" in genre.lower():
                        artwork = getOfficialArtWork(searchtitle,artwork,"movie")
                    else:
                        artwork = getOfficialArtWork(searchtitle,artwork)
                    
                #lookup thumb on google as fallback
                if not artwork.get("thumb") and channel and WINDOW.getProperty("SkinHelper.useGoogleLookups") == "true":
                    artwork["thumb"] = searchGoogleImage("'%s' '%s'" %(searchtitle, channel) )
                
                #lookup thumb on youtube as fallback
                if not artwork.get("thumb") and channel and WINDOW.getProperty("SkinHelper.useYoutubeLookups") == "true":
                    artwork["thumb"] = searchYoutubeImage("'%s' '%s'" %(searchtitle, channel) )
                
                if downloadLocal == True:
                    #download images if we want them local
                    for artType in KodiArtTypes:
                        if artwork.has_key(artType[0]) and artType[0] != "channellogo": artwork[artType[0]] = downloadImage(artwork[artType[0]],pvrThumbPath,artType[1])
                
                #extrafanart images
                if artwork.get("extrafanarts"):
                    if downloadLocal:
                        efadir = os.path.join(pvrThumbPath,"extrafanart/")
                        count = 1
                        for fanart in artwork.get("extrafanarts"):
                            downloadImage(fanart,efadir,"fanart%s.jpg"%count)
                            count += 1
                        artwork["extrafanart"] = efadir
                    else: artwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=%s" %(single_urlencode(try_encode(cachefile)))
                    artwork["extrafanarts"] = repr(artwork["extrafanarts"])
                else:
                    artwork.pop("extrafanarts", None)
                
                #create persistant cache pvrdetails.xml file...
                if title and channel:
                    artwork["title"] = title
                    artwork["channel"] = channel
                    artwork["date_scraped"] = "%s" %datetime.now()
                    if path: artwork["path"] = path
                    if genre: artwork["genre"] = genre
                    if not xbmcvfs.exists(pvrThumbPath): xbmcvfs.mkdirs(pvrThumbPath)
                    createNFO(cachefile,artwork)
                    
        #store in cache for quick access later
        cache[dbID] = artwork
        WINDOW.setProperty("SkinHelper.PVR.ArtWork",repr(cache).encode('utf-8'))
    else:
        logMsg("getPVRThumb cache found for dbID--> " + dbID)
    
    return artwork

def getPvrThumbPath(channel,title):
    pvrThumbPath = ""
    comparetitle = getCompareString(title)
    #lookup existing pvrthumbs paths - try to find a match in custom path
    #images will be looked up or stored to that path
    customlookuppath = WINDOW.getProperty("SkinHelper.customlookuppath").decode("utf-8")
    if customlookuppath: 
        dirs, files = xbmcvfs.listdir(customlookuppath)
        for dir in dirs:
            dir = dir.decode("utf-8")
            #try to find a match...
            comparedir = getCompareString(dir)
            if comparedir == comparetitle:
                pvrThumbPath = os.path.join(customlookuppath,dir)
                break
            elif channel and dir.lower() == channel.lower():
                #user has setup subfolders per channel on their pvr
                dirs2, files2 = xbmcvfs.listdir(os.path.join(customlookuppath,dir))
                for dir2 in dirs2:
                    dir2 = dir2.decode("utf-8")
                    comparedir = getCompareString(dir2,channel)
                    if comparedir == comparetitle:
                        pvrThumbPath = os.path.join(customlookuppath,dir,dir2)
                        break
    
    if not pvrThumbPath:
        #nothing found in user custom path so use the global one...
        directory_structure = WINDOW.getProperty("SkinHelper.directory_structure")
        pvrthumbspath = WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")
        if directory_structure == "1": pvrThumbPath = os.path.join(pvrthumbspath,normalize_string(channel),normalize_string(title))
        elif directory_structure == "2": os.path.join(pvrthumbspath,normalize_string(channel + " - " + title))
        else: pvrThumbPath = pvrThumbPath = os.path.join(pvrthumbspath,normalize_string(title))
   
    #make sure our path ends with a slash
    if "/" in pvrThumbPath: sep = "/"
    else: sep = "\\"
    if not pvrThumbPath.endswith(sep): pvrThumbPath = pvrThumbPath + sep
    
    return pvrThumbPath
    
def getfanartTVimages(type,id,artwork=None):
    #gets fanart.tv images for given id
    if not artwork: artwork={}
    api_key = "639191cb0774661597f28a47e7e2bad5"
    logMsg("get fanart.tv images for type: %s - id: %s" %(type,id))
    
    if type == "movie":
        url = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s' %(id,api_key)
    elif type == "artist":
        url = 'http://webservice.fanart.tv/v3/music/%s?api_key=%s' %(id,api_key)
    elif type == "album":
        url = 'http://webservice.fanart.tv/v3/music/albums/%s?api_key=%s' %(id,api_key)
    else:
        url = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s' %(id,api_key)
    try:
        response = requests.get(url, timeout=5)
    except Exception as e:
        logMsg("getfanartTVimages lookup failed--> " + str(e), 0)
        return artwork
    if response and response.content and response.status_code == 200:
        data = json.loads(response.content.decode('utf-8','replace'))
    else:
        return artwork
    if data:
        cdart = None
        cover = None
        if type == "album" and data.has_key("albums"):
            for key, value in data["albums"].iteritems():
                if value.has_key("cdart") and not artwork.get("discart"):
                    artwork["discart"] = value["cdart"][0].get("url")
                elif value.has_key("albumcover") and not artwork.get("folder"):
                    artwork["folder"] = value["albumcover"][0].get("url")
        
        else:
            #we need to use a little mapping between fanart.tv arttypes and kodi artttypes
            fanartTVTypes = [ ("logo","clearlogo"),("disc","discart"),("clearart","clearart"),("banner","banner"),("artistthumb","folder"),("thumb","landscape"),("clearlogo","clearlogo"),("poster","poster"),("background","fanart"),("showbackground","fanart"),("characterart","characterart"),("artistbackground","fanart")]
            prefixes = ["",type,"hd","hd"+type]
            for fanarttype in fanartTVTypes:
                for prefix in prefixes:
                    fanarttvimage = prefix+fanarttype[0]
                    if data.has_key(fanarttvimage):
                        for item in data[fanarttvimage]:
                            if item.get("lang","") == KODILANGUAGE:
                                #select image in preferred language
                                artwork[fanarttype[1]] = item.get("url")
                                break
                        if not artwork.has_key(fanarttype[1]) and len(data.get(fanarttvimage)) > 0:
                            #just grab the first english one as fallback
                            for item in data[fanarttvimage]:
                                if item.get("lang","") == "en":
                                    artwork[fanarttype[1]] = item.get("url")
                                    break
                        #grab extrafanarts in list
                        if "background" in fanarttvimage:
                            if not artwork.get("extrafanarts"): 
                                artwork["extrafanarts"] = []
                            try:
                                maxfanarts = WINDOW.getProperty("SkinHelper.maxNumFanArts")
                                if maxfanarts: maxfanarts = int(maxfanarts)
                            except: maxfanarts = 0
                            fanartcount = 0
                            for item in data[fanarttvimage]:
                                if fanartcount >= maxfanarts: break
                                artwork["extrafanarts"].append(item.get("url"))
                                fanartcount += 1
                    
    return artwork

def getOfficialArtWork(title,artwork=None,type=None):
    #perform search on TMDB and return artwork
    if not artwork: artwork={}
    coverUrl = ""
    fanartUrl = ""
    matchFound = {}
    media_id = None
    media_type = None
    if not type: type="multi"
    try: 
        url = 'http://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s' %(type,tmdb_apiKey,KODILANGUAGE,try_encode(title))
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = json.loads(response.content.decode('utf-8','replace'))
            #find exact match first
            if data and data.get("results",None):
                for item in data["results"]:
                    name = item.get("name")
                    if not name: name = item.get("title")
                    original_name = item.get("original_name","")
                    title_alt = title.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    name_alt = name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    org_name_alt = original_name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    if name == title or original_name == title:
                        #match found for exact title name
                        matchFound = item
                        break
                    elif name.split(" (")[0] == title or title_alt == name_alt or title_alt == org_name_alt:
                        #match found with substituting some stuff
                        matchFound = item
                        break
            
                #if a match was not found, we accept the closest match from TMDB
                if not matchFound and len(data.get("results")) > 0 and not len(data.get("results")) > 5:
                    matchFound = item = data.get("results")[0]
   
        if matchFound and not type=="person":
            coverUrl = matchFound.get("poster_path","")
            fanartUrl = matchFound.get("backdrop_path","")
            id = str(matchFound.get("id",""))
            media_type = matchFound.get("media_type","")
            name = item.get("name")
            if not name: name = item.get("title")
            artwork["tmdb_title"] = name
            artwork["tmdb_type"] = media_type
            logMsg("getTMDBimage - TMDB match found for %s !" %title)
            #lookup external tmdb_id and perform artwork lookup on fanart.tv
            languages = [KODILANGUAGE,"en"]
            for language in languages:
                if WINDOW.getProperty("SkinHelper.useFanArtTv") == "true" and id:
                    if media_type == "movie" or not media_type:
                        url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s' %(id,tmdb_apiKey,language)
                    else:
                        url = 'http://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=external_ids&language=%s' %(id,tmdb_apiKey,language)
                    response = requests.get(url)
                    data = json.loads(response.content.decode('utf-8','replace'))
                    if data:
                        if not media_id and data.get("imdb_id"):
                            media_id = str(data.get("imdb_id"))
                            artwork["imdb_id"] = media_id
                        if not media_id and data.get("external_ids"): 
                            media_id = str(data["external_ids"].get("tvdb_id"))
                            artwork["tvdb_id"] = media_id
                        if data.get("vote_average"):
                            artwork["rating"] = str(data.get("vote_average"))
                        if data.get("overview"):
                            artwork["plot"] = data.get("overview")
                            #break if we've found the plot
                            break
                            
        
        #lookup artwork on fanart.tv
        if media_id and media_type:
            artwork = getfanartTVimages(media_type,media_id,artwork)
        
        #use tmdb art as fallback when no fanart.tv art
        if coverUrl and not artwork.get("poster"):
            artwork["poster"] = "http://image.tmdb.org/t/p/original"+coverUrl  
        if fanartUrl and not artwork.get("fanart"):
            artwork["fanart"] = "http://image.tmdb.org/t/p/original"+fanartUrl
        if type=="person" and matchFound.get("profile_path"):
            artwork["thumb"] = "http://image.tmdb.org/t/p/original"+matchFound.get("profile_path")
    
    except Exception as e:
        if "getaddrinfo failed" in str(e):
            #no internet access - disable lookups for now
            WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
            logMsg("getOfficialArtWork - no internet access, disabling internet lookups for now",0)
        else:
            logMsg("getOfficialArtWork - Error in getOfficialArtWork --> " + str(e),0)
            
    return artwork

def getActorImage(actorname):
    thumb = ""
    #get the item from cache first
    cache = WINDOW.getProperty("SkinHelper.ActorImages").decode('utf-8')
    if cache:
        cache = eval(cache)
        if cache.has_key(actorname): 
            return cache[actorname]
    else: cache = {}
    
    #lookup image online
    thumb = getOfficialArtWork(actorname,None,"person")
    #save in cache
    cache[actorname] = thumb
    WINDOW.setProperty("SkinHelper.ActorImages",repr(cache))
    return thumb
            
def downloadImage(imageUrl,thumbsPath, filename):
    try:
        if not xbmcvfs.exists(thumbsPath):
            xbmcvfs.mkdirs(thumbsPath)
        newFile = os.path.join(thumbsPath,filename)
        if not xbmcvfs.exists(newFile):
            #do not overwrite existing images
            xbmcvfs.copy(imageUrl,newFile)
        return newFile
    except: return imageUrl

def createNFO(cachefile, artwork):
    try:
        tree = ET.ElementTree( ET.Element( "artdetails" ) )
        root = tree.getroot()
        for key, value in artwork.iteritems():
            if value:
                child = ET.SubElement( root, key )
                child.text = try_decode(value)
        
        indentXML( tree.getroot() )
        xmlstring = ET.tostring(tree.getroot(), encoding="utf-8")
        f = xbmcvfs.File(cachefile, 'w')
        f.write(xmlstring)
        f.close()
    except Exception as e:
        logMsg("ERROR in createNFO --> " + str(e), 0)
      
def getArtworkFromCacheFile(cachefile,artwork=None):
    if not artwork: artwork={}
    if xbmcvfs.exists(cachefile):
        try:
            f = xbmcvfs.File(cachefile, 'r')
            root = ET.fromstring(f.read())
            f.close()
            cacheFound = True
            for child in root:
                if not artwork.get(child.tag):
                    artwork[child.tag] = try_decode(child.text)
            del root
        except Exception as e:
            logMsg("ERROR in getArtworkFromCacheFile %s  --> %s" %(cachefile,str(e)), 0)
    return artwork
         
def searchChannelLogo(searchphrase):
    #get's a thumb image for the given search phrase
    image = ""
    
    cache = WINDOW.getProperty(searchphrase.encode('utf-8') + "SkinHelper.PVR.ChannelLogo")
    if cache: return cache
    else:
        try:
            #lookup in channel list
            # Perform a JSON query to get all channels
            json_query = getJSON('PVR.GetChannels', '{"channelgroupid": "alltv", "properties": [ "thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed", "broadcastnow" ]}' )
            for item in json_query:
                channelname = item["label"]
                if channelname == searchphrase:
                    channelicon = item['thumbnail']
                    if channelicon: 
                        channelicon = getCleanImage(channelicon)
                        if xbmcvfs.exists(channelicon):
                            image = getCleanImage(channelicon)
                    break

            #lookup with thelogodb
            if not image:
                url = 'http://www.thelogodb.com/api/json/v1/1/tvchannel.php?s=%s' %try_encode(searchphrase)
                response = requests.get(url)
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.has_key('channels'):
                    results = data['channels']
                    if results:
                        for i in results: 
                            rest = i['strLogoWide']
                            if rest:
                                if ".jpg" in rest or ".png" in rest:
                                    image = rest
                                    break
                
            if not image:
                search_alt = searchphrase.replace(" HD","")
                url = 'http://www.thelogodb.com/api/json/v1/1/tvchannel.php?s=%s' %try_encode(search_alt)
                response = requests.get(url)
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.has_key('channels'):
                    results = data['channels']
                    if results:
                        for i in results: 
                            rest = i['strLogoWide']
                            if rest:
                                if ".jpg" in rest or ".png" in rest:
                                    image = rest
                                    break
        except Exception as e:
            if "getaddrinfo failed" in str(e):
                #no internet access - disable lookups for now
                WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
                logMsg("searchChannelLogo - no internet access, disabling internet lookups for now")
            else:
                logMsg("ERROR in searchChannelLogo ! --> " + str(e), 0)

        if image:
            if ".jpg/" in image:
                image = image.split(".jpg/")[0] + ".jpg"
        
        WINDOW.setProperty(searchphrase.encode('utf-8') + "SkinHelper.PVR.ChannelLogo",image)
        return image

def searchGoogleImage(searchphrase):
    image = ""
   
    try:
        ip_address = xbmc.getInfoLabel("Network.IPAddress")
        url = 'http://ajax.googleapis.com/ajax/services/search/images'
        params = {'v' : '1.0', 'safe': 'off', 'userip': ip_address, 'q': searchphrase, 'imgsz': 'medium|large|xlarge'}
        response = requests.get(url, params=params)
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("responseData"):
            if data['responseData'].get("results"):
                results = data['responseData']['results']
                for i in results: 
                    image = i['unescapedUrl']
                    if image:
                        if ".jpg" in image or ".png" in image:
                            logMsg("getTMDBimage - GOOGLE match found for %s !" %searchphrase)
                            return image
    except Exception as e:
        if "getaddrinfo failed" in str(e):
            #no internet access - disable lookups for now
            WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
            logMsg("searchGoogleImage - no internet access, disabling internet lookups for now")
        else:
            logMsg("getTMDBimage - ERROR in searchGoogleImage ! --> " + str(e))
    
    logMsg("getTMDBimage - GOOGLE match NOT found for %s" %searchphrase)
    return image
 
def searchYoutubeImage(searchphrase):
    image = ""
    matchFound = False
    #safety check: prevent multiple youtube searches at once...
    waitForYouTubeCount = 0
    if WINDOW.getProperty("youtubescanrunning") == "running":
        xbmc.sleep(100)
        return "skip"
    
    WINDOW.setProperty("youtubescanrunning","running")
    libPath = "plugin://plugin.video.youtube/kodion/search/query/?q=%s" %searchphrase
    media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art"], "directory": "' + libPath + '", "media": "files" }')
    for media in media_array:
        if not media["filetype"] == "directory":
            if media.has_key('art'):
                if media['art'].has_key('thumb'):
                    image = getCleanImage(media['art']['thumb'])
                    matchFound = True
                    break
    if matchFound:
        logMsg("searchYoutubeImage - YOUTUBE match found for %s" %searchphrase)
    else:
        logMsg("searchYoutubeImage - YOUTUBE match NOT found for %s" %searchphrase)
    
    WINDOW.clearProperty("youtubescanrunning")
    return image
 
def searchThumb(searchphrase, searchphrase2=""):
    #get's a thumb image for the given search phrase
    
    #is this item already in the cache?
    image = WINDOW.getProperty(try_encode(searchphrase + searchphrase2) + "SkinHelper.PVR.Thumb").decode("utf-8")
    if not image and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
        if searchphrase2:
            searchphrase = searchphrase + " " + searchphrase2
            
        WINDOW.setProperty("getthumbbusy","busy")
                  
        #lookup with Google images
        if not image:
            image = searchGoogleImage(searchphrase)
        
        # Do lookup with youtube addon as last resort
        if not image:
            searchYoutubeImage(searchphrase)
                
        if image:
            if ".jpg/" in image:
                image = image.split(".jpg/")[0] + ".jpg"
        WINDOW.clearProperty("getthumbbusy")
    return image

def getMusicBrainzId(artist, album="", track=""):
    albumid = ""
    artistid = ""
    album = album.replace(" (single)","")
    track = track.split(" (")[0]
    matchartist = getCompareString(artist)
    logMsg("getMusicBrainzId -- artist:  -  %s  - album:  %s  - track:  %s" %(artist,album,track))
    try:
        if not WINDOW.getProperty("SkinHelper.TempDisableMusicBrainz"):
            MBalbum = None
            if not MBalbum and artist and track:
                MBalbums = m.search_recordings(query=single_urlencode(try_encode(track)),limit=1,offset=None, strict=False, artist=single_urlencode(try_encode(artist)))
                if MBalbums and MBalbums.get("recording-list"): MBalbum = MBalbums.get("recording-list")[0]
            if not MBalbum and artist and album:
                MBalbums = m.search_release_groups(query=single_urlencode(try_encode(album)),limit=1,offset=None, strict=False, artist=single_urlencode(try_encode(artist)))
                if MBalbums and MBalbums.get("release-group-list"): MBalbum = MBalbums.get("release-group-list")[0]
            if MBalbum:
                albumid = MBalbum.get("id","")
                for MBartist in MBalbum.get("artist-credit"):
                    if isinstance(MBartist, dict) and MBartist.get("artist",""):
                        #safety check - only allow exact artist match
                        foundartist = getCompareString(MBartist.get("artist","").get("name").encode("utf-8").decode("utf-8"))
                        if foundartist and foundartist in matchartist:
                            artistid = MBartist.get("artist").get("id")
                            break
                    
    except Exception as e:
        logMsg("MusicBrainz ERROR (servers busy?) - temporary disabling musicbrainz lookups (fallback to theaudiodb)", 0)
        WINDOW.setProperty("SkinHelper.TempDisableMusicBrainz","disable")
    
    #use theaudiodb as fallback
    try:
        if not artistid and artist and track:
            audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/searchtrack.php'
            params = {'s' : artist, 't': track}
            response = requests.get(audiodb_url, params=params)
            if response and response.content:
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.get("track") and len(data.get("track")) > 0:
                    adbdetails = data["track"][0]
                    #safety check - only allow exact artist match
                    foundartist = getCompareString(adbdetails.get("strArtist",""))
                    if foundartist in matchartist:
                        albumid = adbdetails.get("strMusicBrainzAlbumID","")
                        artistid = adbdetails.get("strMusicBrainzArtistID","")
        if not artistid and artist and album:
            audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/searchalbum.php'
            params = {'s' : artist, 'a': album}
            response = requests.get(audiodb_url, params=params)
            if response and response.content:
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.get("album") and len(data.get("album")) > 0:
                    adbdetails = data["album"][0]
                    #safety check - only allow exact artist match
                    foundartist = getCompareString(adbdetails.get("strArtist",""))
                    if foundartist in matchartist:
                        albumid = adbdetails.get("strMusicBrainzID","")
                        artistid = adbdetails.get("strMusicBrainzArtistID","")
        
    except Exception as e:
        logMsg("getMusicArtworkByDbId AudioDb lookup failed --> " + str(e), 0)
    logMsg("getMusicBrainzId results for artist %s  - artistid:  %s  - albumid:  %s" %(artist,artistid,albumid))
    return (artistid, albumid)

def getArtistArtwork(musicbrainzartistid, artwork=None):
    if not artwork: artwork = {}
    #get fanart.tv artwork for artist
    artwork = getfanartTVimages("artist",musicbrainzartistid,artwork)
    #get audiodb info for artist  (and use as spare for artwork)
    try:
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/artist-mb.php?i=%s' %musicbrainzartistid
        response = requests.get(audiodb_url)
    except Exception as e:
        logMsg("getMusicArtworkByDbId AudioDb lookup failed --> " + str(e), 0)
        return {}
    if response and response.content:
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("artists") and len(data.get("artists")) > 0:
            adbdetails = data["artists"][0]
            if not artwork.get("banner") and adbdetails.get("strArtistBanner"): artwork["banner"] = adbdetails.get("strArtistBanner")
            artwork["extrafanarts"] = []
            if adbdetails.get("strArtistFanart"): artwork["extrafanarts"].append(adbdetails.get("strArtistFanart"))
            if adbdetails.get("strArtistFanart2"): artwork["extrafanarts"].append(adbdetails.get("strArtistFanart2"))
            if adbdetails.get("strArtistFanart3"): artwork["extrafanarts"].append(adbdetails.get("strArtistFanart3"))
            if not artwork.get("clearlogo") and adbdetails.get("strArtistLogo"): artwork["clearlogo"] = adbdetails.get("strArtistLogo")
            if not artwork.get("artistthumb") and adbdetails.get("strArtistThumb"): artwork["artistthumb"] = adbdetails.get("strArtistThumb")
            if not artwork.get("folder") and adbdetails.get("strArtistThumb"): artwork["folder"] = adbdetails.get("strArtistThumb")
            if not artwork.get("info") and adbdetails.get("strBiography" + KODILANGUAGE.upper()): artwork["info"] = adbdetails.get("strBiography" + KODILANGUAGE.upper())
            if not artwork.get("info") and adbdetails.get("strBiographyEN"): artwork["info"] = adbdetails.get("strBiographyEN")
            if artwork.get("info"): artwork["info"] = artwork.get("info").replace("\n","")
            
    return artwork

def getAlbumArtwork(musicbrainzalbumid, artwork=None):
    if not artwork: artwork = {}
    #get fanart.tv artwork for album
    artwork = getfanartTVimages("album",musicbrainzalbumid,artwork)
    #get album info on theaudiodb (and use as spare for artwork)
    try:
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/album-mb.php?i=%s' %musicbrainzalbumid
        response = requests.get(audiodb_url)
    except Exception as e:
        logMsg("getMusicArtworkByDbId AudioDB lookup failed --> " + str(e), 0)
        return {}
    if response and response.content:
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("album") and len(data.get("album")) > 0:
            adbdetails = data["album"][0]
            if not artwork.get("folder") and adbdetails.get("strAlbumThumb"): artwork["folder"] = adbdetails.get("strAlbumThumb")
            if not artwork.get("discart") and adbdetails.get("strAlbumCDart"): artwork["discart"] = adbdetails.get("strAlbumCDart")
            if not artwork.get("info") and adbdetails.get("strDescription" + KODILANGUAGE.upper()): artwork["info"] = adbdetails.get("strDescription" + KODILANGUAGE.upper())
            if not artwork.get("info") and adbdetails.get("strDescriptionEN"): artwork["info"] = adbdetails.get("strDescriptionEN")
            if artwork.get("info"): artwork["info"] = normalize_string(artwork["info"])
    
    if not artwork.get("thumb") and not artwork.get("folder") and not WINDOW.getProperty("SkinHelper.TempDisableMusicBrainz"): 
        try: 
            new_file = "special://profile/addon_data/script.skin.helper.service/musicart/%s.jpg" %musicbrainzalbumid
            thumbfile = m.get_image_front(musicbrainzalbumid)
            if thumbfile: 
                f = xbmcvfs.File(new_file, 'w')
                f.write(thumbfile)
                f.close()
            artwork["folder"] = new_file
        except: pass
    
    if not artwork.get("thumb") and not artwork.get("folder") and not WINDOW.getProperty("SkinHelper.TempDisableMusicBrainz"): 
        try: 
            new_file = "special://profile/addon_data/script.skin.helper.service/musicart/%s.jpg" %musicbrainzalbumid
            thumbfile = m.get_release_group_image_front(musicbrainzalbumid)
            if thumbfile: 
                f = xbmcvfs.File(new_file, 'w')
                f.write(thumbfile)
                f.close()
            artwork["folder"] = new_file
        except: pass
    
    
    
    return artwork
            
def getMusicArtworkByDbId(dbid,itemtype):
        
    albumartwork = {}
    path = ""
    albumName = ""
    trackName = ""
    artistid = 0
    artistCacheFound = False
    albumCacheFound = False
    artistpath = ""
    albumpath = ""
    
    logMsg("getMusicArtworkByDbId dbid: %s  type: %s" %(dbid, itemtype))
    
    enableMusicArtScraper = WINDOW.getProperty("SkinHelper.enableMusicArtScraper") == "true"
    downloadMusicArt = WINDOW.getProperty("SkinHelper.downloadMusicArt") == "true"
    enableLocalMusicArtLookup = WINDOW.getProperty("SkinHelper.enableLocalMusicArtLookup") == "true"

    if itemtype == "artists":
        artistid = int(dbid)
    
    if itemtype == "songs":
        json_response = None
        json_response = getJSON('AudioLibrary.GetSongDetails', '{ "songid": %s, "properties": [ "file","artistid","albumid","album","comment","fanart","thumbnail","displayartist","artist","albumartist"] }'%int(dbid))
        if json_response:
            #don't return album info for various artists/compilations...
            if json_response.get("album") and json_response.get("albumid") and json_response.get("album","").lower() != "singles" and json_response.get("album","").lower() != "unknown title" and not "various" in json_response.get("file","").lower() and not "Various Artists" in json_response.get("displayartist").lower() and not "Various Artists" in json_response["artist"] and not "Various Artists" in json_response["albumartist"]:
                #album level is lowest level we get info from so change context to album once we have the song details...
                itemtype = "albums"
                dbid = str(json_response["albumid"])
            else:
                #search by trackname as fallback for songs without albums (singles) or compilations
                return getMusicArtworkByName(json_response.get("displayartist"),json_response.get("label"))

    ############# ALBUM DETAILS #########################
    if itemtype == "albums":
        albumartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicart/cache-albums-%s.xml" %dbid)
        if albumartwork and albumartwork.get("artistid"): 
            albumCacheFound = True
        else:
            json_response = None
            json_response = getJSON('AudioLibrary.GetAlbumDetails','{ "albumid": %s, "properties": [ "description","fanart","thumbnail","artistid","artist","displayartist" ] }'%int(dbid))
            logMsg("getMusicArtworkByDbId found album details --> " + repr(json_response))
            if json_response.get("description") and not albumartwork.get("info"): albumartwork["info"] = json_response["description"]
            if json_response.get("fanart") and not (json_response["label"].lower() == "singles" or "Various Artists" in json_response.get("displayartist").lower()): albumartwork["fanart"] = getCleanImage(json_response["fanart"])
            if json_response.get("thumbnail") and not (json_response["label"].lower() == "singles" or "Various Artists" in json_response.get("displayartist").lower()): albumartwork["folder"] = json_response["thumbnail"]
            if json_response.get("label") and not albumartwork.get("albumname"): albumartwork["albumname"] = json_response["label"]
            if json_response.get("artistid") and not albumartwork.get("artistid"): 
                albumartwork["artistid"] = str(json_response["artistid"][0])
            #get track listing for album
            json_response = None
            json_response = getJSON('AudioLibrary.GetSongs', '{ "filter":{"albumid": %s}, "properties": [ "file","artistid","track","title","albumid","album","displayartist","albumartistid","artist","albumartist","displayartist" ], "sort": {"method":"track"} }'%int(dbid))
            logMsg("getMusicArtworkByDbId found songs for album --> " + repr(json_response))
            albumartwork["songcount"] = 0
            albumartwork["albumcount"] = 0
            albumartwork["tracklist"] = []
            for song in json_response:
                if not path: path = song["file"]
                if song.get("track"): albumartwork["tracklist"].append("%s - %s" %(song["track"], song["title"]))
                else: albumartwork["tracklist"].append(song["title"])
                albumartwork["songcount"] += 1
        
            #make sure that our results are strings
            albumartwork["tracklist"] = "[CR]".join(albumartwork.get("tracklist",""))
            albumartwork["albumcount"] = "%s"%albumartwork.get("albumcount","")
            albumartwork["songcount"] = "%s"%albumartwork.get("songcount","")
        
        #set our global params
        albumName = albumartwork.get("albumname","")
        artistid = albumartwork.get("artistid","")
        
        
    ############## ARTIST DETAILS #######################################
    artistartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicart/cache-artists-%s.xml" %artistid)
    if artistartwork: artistCacheFound = True
    else:
        json_response = None
        json_response = getJSON('AudioLibrary.GetArtistDetails', '{ "artistid": %s, "properties": [ "description","fanart","thumbnail" ] }'%int(artistid))
        logMsg("getMusicArtworkByDbId found artist details --> " + repr(json_response))
        if json_response.get("description") and not artistartwork.get("info"): artistartwork["info"] = json_response["description"]
        if json_response.get("fanart"): artistartwork["fanart"] = getCleanImage(json_response["fanart"])
        if json_response.get("thumbnail") : artistartwork["folder"] = json_response["thumbnail"]
        if json_response.get("label") and not artistartwork.get("artistname",""): artistartwork["artistname"] = json_response["label"]
        #get track/album listing for artist
        json_response = None
        json_response = getJSON('AudioLibrary.GetSongs', '{ "filter":{"artistid": %d}, "properties": [ "file","artistid","track","title","albumid","album","albumartistid","artist","albumartist","displayartist" ] }'%int(artistid))
        logMsg("getMusicArtworkByDbId found songs for artist --> " + repr(json_response))
        artistartwork["songcount"] = 0
        artistartwork["albumcount"] = 0
        artistartwork["albums"] = []
        artistartwork["tracklist"] = []
        for song in json_response:
            if not trackName: trackName = song.get("label","")
            if song.get("album"):
                if not path: path = song["file"]
                if not albumName: albumName = song.get("album")
                artistartwork["tracklist"].append(song["title"])
                artistartwork["songcount"] += 1
                if song.get("album") and song["album"] not in artistartwork["albums"]:
                    artistartwork["albumcount"] +=1
                    artistartwork["albums"].append(song["album"])
        
        #make sure that our results are strings
        artistartwork["albums"] = "[CR]".join(artistartwork.get("albums",""))
        artistartwork["tracklist"] = "[CR]".join(artistartwork.get("tracklist",""))
        artistartwork["albumcount"] = "%s"%artistartwork.get("albumcount","")
        artistartwork["songcount"] = "%s"%artistartwork.get("songcount","")
        
    #LOOKUP LOCAL ARTWORK PATH PASED ON SONG FILE PATH
    if path and enableLocalMusicArtLookup and (not artistCacheFound or (itemtype=="albums" and not albumCacheFound)):
        
        #only use existing path if the artistname is actually in the path 
        if "\\" in path:
            delim = "\\"
        else:
            delim = "/"
        pathparts = path.split(delim)
        if len(pathparts) > 2:
            foldername = path.split(delim)[-2].lower()
            if foldername.startswith("disc"): 
                path = path.rsplit(delim, 1)[0] + delim #from disc level to album level
            albumpath = path.rsplit(delim, 1)[0] + delim #album level
            artistpath = path.rsplit(delim, 2)[0] + delim #artist level

            #lookup existing artwork in the paths (only if artistname in the path, to prevent lookups in various artists/compilations folders)
            if not normalize_string(artistartwork.get("artistname","").lower().replace("_","")) in normalize_string(artistpath.lower().replace("_","")):
                logMsg("getMusicArtworkByDbId - lookup on disk skipped for %s - not correct folder structure (artistname\albumname)" %artistartwork.get("artistname",""))
                albumpath = ""
                artistpath = ""
            else:    
                #lookup local artist artwork
                artistartwork["path"] = artistpath
                for artType in KodiArtTypes:
                    artpath = os.path.join(artistpath,artType[1])
                    if xbmcvfs.exists(artpath) and not artistartwork.get(artType[0]):
                        artistartwork[artType[0]] = artpath
                        logMsg("getMusicArtworkByDbId - %s found on disk for %s - itemtype: %s" %(artType[0],artistartwork.get("artistname",""), itemtype))
        
                #lookup local album artwork
                if itemtype == "albums":
                    albumartwork["path"] = albumpath
                    #lookup existing artwork in the paths
                    for artType in KodiArtTypes:
                        artpath = os.path.join(albumpath,artType[1])
                        if xbmcvfs.exists(artpath) and not albumartwork.get(artType[0]):
                            albumartwork[artType[0]] = artpath
                            logMsg("getMusicArtworkByDbId - %s found on disk for %s - itemtype: %s" %(artType[0],albumName, itemtype))
    
    #online lookup for details
    if enableMusicArtScraper and not artistCacheFound or (itemtype=="albums" and not albumCacheFound):
        #lookup details in musicbrainz
        #retrieve album id and artist id with a combined query of album name and artist name to get an accurate result
        musicbrainzartistid, musicbrainzalbumid = getMusicBrainzId(artistartwork.get("artistname",""),albumName,trackName)
        if itemtype=="albums" and musicbrainzalbumid: 
            albumartwork["musicbrainzalbumid"] = musicbrainzalbumid
        if musicbrainzartistid: 
            artistartwork["musicbrainzartistid"] = musicbrainzartistid
        
        ########################################################## ARTIST LEVEL #########################################################
        if musicbrainzartistid and not artistCacheFound:
            artistartwork = getArtistArtwork(musicbrainzartistid, artistartwork)

            #download images if we want them local
            if downloadMusicArt and artistpath:
                for artType in KodiArtTypes:
                    if artistartwork.has_key(artType[0]): artistartwork[artType[0]] = downloadImage(artistartwork[artType[0]],artistpath,artType[1])
            
            #extrafanart images
            if artistartwork.get("extrafanarts"):
                if downloadMusicArt and artistpath:
                    efadir = os.path.join(artistpath,"extrafanart/")
                    count = 1
                    for fanart in artistartwork.get("extrafanarts"):
                        downloadImage(fanart,efadir,"fanart%s.jpg"%count)
                        count += 1
                    artistartwork["extrafanart"] = efadir
                else: artistartwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=special://profile/addon_data/script.skin.helper.service/musicart/cache-artists-%s.xml" %(artistid)
                artistartwork["extrafanarts"] = repr(artistartwork["extrafanarts"])
            else:
                artistartwork["extrafanarts"] = ""
            
        ######################################################### ALBUM LEVEL #########################################################    
        if itemtype == "albums" and musicbrainzalbumid and not albumCacheFound:
            albumartwork = getAlbumArtwork(musicbrainzalbumid, albumartwork)
            
            #download images if we want them local
            if downloadMusicArt and albumpath:
                for artType in KodiArtTypes:
                    if albumartwork.has_key(artType[0]): albumartwork[artType[0]] = downloadImage(albumartwork[artType[0]],albumpath,artType[1])
    
    #write to persistant cache
    if artistartwork and not artistCacheFound:
        if artistartwork.get("landscape"): del artistartwork["landscape"]
        if artistartwork.get("folder") and not artistartwork.get("thumb"): artistartwork["thumb"] = artistartwork.get("folder")
        cachefile = "special://profile/addon_data/script.skin.helper.service/musicart/cache-artists-%s.xml" %(artistid)
        createNFO(cachefile,artistartwork)
    if albumartwork and itemtype=="albums" and not albumCacheFound:
        if albumartwork.get("landscape"): del albumartwork["landscape"]
        if albumartwork.get("folder") and not albumartwork.get("thumb"): albumartwork["thumb"] = albumartwork.get("folder")
        cachefile = "special://profile/addon_data/script.skin.helper.service/musicart/cache-albums-%s.xml" %(dbid)
        createNFO(cachefile,albumartwork)
    
    #return artwork combined
    artwork = artistartwork
    if itemtype == "albums" and albumartwork:
        for key, value in albumartwork.iteritems():
            if value: artwork[key] = value
    return artwork

def getMusicArtworkByName(artist, title="", album=""):
    logMsg("getMusicArtworkByName artist: %s  - track: %s  -  album: %s" %(artist,title,album))
    
    #try cache file first...
    cacheFile = "special://profile/addon_data/script.skin.helper.service/musicart/%s.xml" %normalize_string(artist + "-" + title)
    albumartwork = {}
    artistartwork = getArtworkFromCacheFile(cacheFile)
    if artistartwork: return artistartwork
    
    #query database for this track/album first
    json_response = getJSON('AudioLibrary.GetSongs', '{ "filter": {"and": [{"operator":"contains", "field":"artist", "value":"%s"},{"operator":"contains", "field":"title", "value":"%s"}]}, "properties": [ "file","artistid","track","title","albumid","album","displayartist","albumartistid","albumartist","artist" ] }'%(artist,title))
    if json_response:
        # local match found
        for item in json_response:
            #prevent returning details for a various artists entry
            if not "various" in item.get("file","").lower() and not "Various Artists" in item.get("displayartist").lower() and not "Various Artists" in item["artist"] and not "Various Artists" in item["albumartist"]:
                logMsg("getMusicArtworkByName found match in local DB --> " + repr(json_response))
                return getMusicArtworkByDbId(str(item["albumid"]),"albums")
            
    #lookup this artist by quering musicbrainz...
    if " & " in artist: artists= artist.split(" & ")
    elif " ft. " in artist: artists= artist.split(" ft. ")
    elif " Ft. " in artist: artists= artist.split(" Ft. ")
    elif " ft " in artist: artists= artist.split(" ft ")
    elif " feat. " in artist: artists= artist.split(" feat. ")
    elif " featuring " in artist: artists= artist.split(" featuring ")
    else: artists = [artist]
    for artist in artists:
        #retrieve musicbrainz id with a combined query of track name and artist name to get an accurate result
        artistid, albumid = getMusicBrainzId(artist,album,title)
        #get artwork for artist
        artistartwork = getArtistArtwork(artistid, artistartwork)
        if albumid:
            #if we also have album artwork use that too
            artistartwork = getAlbumArtwork(albumid,artistartwork)
        
    #process extrafanart
    if artistartwork.get("extrafanarts"):
        artistartwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=%s" %(single_urlencode(try_encode(cacheFile)))
        artistartwork["extrafanarts"] = repr(artistartwork["extrafanarts"])
    else: artistartwork["extrafanarts"] = ""
    
    if artistartwork.get("folder") and not artistartwork.get("thumb"): artistartwork["thumb"] = artistartwork.get("folder")
        
    #write cachefile for later use
    createNFO(cacheFile,artistartwork)

    return artistartwork