#!/usr/bin/python
# -*- coding: utf-8 -*-

from Utils import *
import requests
import base64
import musicbrainzngs as m
import BeautifulSoup
import htmlentitydefs
import urllib2, re
from difflib import SequenceMatcher as SM

m.set_useragent("script.skin.helper.service", "1.0.0", "https://github.com/marcelveldt/script.skin.helper.service")
tmdb_apiKey = "ae06df54334aa653354e9a010f4b81cb"

def getPVRThumbs(title,channel,type="channels",path="",genre="",year="",ignoreCache=False, manualLookup=False):
    cacheFound = False
    ignore = False
    artwork = {}
    pvrThumbPath = None
    
    #ignore back entry
    if title == ".." or not title: 
        logMsg("getPVRThumbs empty title, skipping...")
        return {}
    
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
    else: cache = {}
    
    if not cacheFound:
        
        pvrThumbPath = getPvrThumbPath(channel,title)
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
            logMsg("getPVRThumb for dbID: %s" %dbID)
            searchtitle = title
            if manualLookup:
                searchtitle = xbmcgui.Dialog().input(ADDON.getLocalizedString(32147), title, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
            
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
                        artwork = getTmdbDetails(searchtitle,artwork,"movie",year)
                    elif "tv" in genre.lower():
                        artwork = getTmdbDetails(searchtitle,artwork,"tv",year)
                    else:
                        artwork = getTmdbDetails(searchtitle,artwork,"",year)
                
                #set thumb to fanart or landscape to prevent youtube/google lookups
                if not artwork.get("thumb") and artwork.get("landscape"):
                    artwork["thumb"] = artwork.get("landscape")
                if not artwork.get("thumb") and artwork.get("fanart"):
                    artwork["thumb"] = artwork.get("fanart")
                
                #lookup thumb on google as fallback
                if not artwork.get("thumb") and channel and WINDOW.getProperty("SkinHelper.useGoogleLookups") == "true":
                    artwork["thumb"] = searchGoogleImage(searchtitle, channel, manualLookup)
                
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
                        for fanart in eval(artwork.get("extrafanarts")):
                            downloadImage(fanart,efadir,"fanart%s.jpg"%count)
                            count += 1
                        artwork["extrafanart"] = efadir
                    else: artwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=%s" %(single_urlencode(try_encode(cachefile)))
                
                #create persistant cache pvrdetails.xml file...
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
    
    return artwork

def getAddonArtwork(title,year="",preftype="",ignoreCache=False, manualLookup=False):
    artwork = {}
    downloadLocal = False
    includeCast = True
    cacheFound = False
    
    if not year: return {}
    
    try:
        dbID = "%s-%s" %(title,year)
        
        #get the items from window cache first
        cacheStr = "SkinHelper.Addons.Artwork-%s" %dbID
        cache = WINDOW.getProperty(try_encode(cacheStr)).decode("utf-8")
        if cache and not ignoreCache:
            return eval(cache)
            cacheFound = True
        
        #Do we have a persistant cache file (pvrdetails.xml) for this item ?
        addonsArtPath = "special://profile/addon_data/script.skin.helper.service/artworkcache/"
        cachefile = os.path.join(addonsArtPath, normalize_string(dbID) + ".xml")
        if not ignoreCache:
            artwork = getArtworkFromCacheFile(cachefile,artwork)
            if artwork: return artwork
        
        #nothing in our cache, proceed with lookup...
        searchtitle = title
        if manualLookup:
            searchtitle = xbmcgui.Dialog().input(ADDON.getLocalizedString(32147), title, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
                
        #if nothing in persistant cache, perform the internet scraping
        if not cacheFound and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
            logMsg("getAddonArtwork no cache found for %s - starting lookup..."%dbID)    
            #grab artwork from tmdb/fanart.tv
            if "movie" in preftype:
                artwork = getTmdbDetails(searchtitle,artwork,"movie",year,includeCast)
            elif "tv" in preftype or "show" in preftype or "series" in preftype:
                artwork = getTmdbDetails(searchtitle,artwork,"tv",year,includeCast)
            else:
                artwork = getTmdbDetails(searchtitle,artwork,"",year,includeCast)
            
            if downloadLocal == True:
                #download images if we want them local
                for artType in KodiArtTypes:
                    if artwork.has_key(artType[0]): artwork[artType[0]] = downloadImage(artwork[artType[0]],addonsArtPath,artType[1])
            
            #extrafanart images
            if artwork.get("extrafanarts"):
                if downloadLocal:
                    efadir = os.path.join(addonsArtPath,"extrafanart/")
                    count = 1
                    for fanart in eval(artwork.get("extrafanarts")):
                        downloadImage(fanart,efadir,"fanart%s.jpg"%count)
                        count += 1
                    artwork["extrafanart"] = efadir
                else: artwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=%s" %(single_urlencode(try_encode(cachefile)))
            
            #create persistant cache file...
            if title:
                artwork["title"] = title
                if year and not artwork.get("year"): artwork["year"] = year
                if not xbmcvfs.exists(addonsArtPath): xbmcvfs.mkdirs(addonsArtPath)
                createNFO(cachefile,artwork)
                    
        #store in cache for quick access later
        WINDOW.setProperty(try_encode(cacheStr), repr(artwork))
    except Exception as e:
        logMsg("ERROR in getAddonArtwork --> " + str(e), 0)
        
    return artwork
   
def getPvrThumbPath(channel,title):
    pvrThumbPath = ""
    comparetitle = getCompareString(title)
    if not channel: channel = "unknown_channel"
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
    
def getfanartTVimages(type,id,artwork=None,allowoverwrite=True):
    #gets fanart.tv images for given id
    if not artwork: artwork={}
    api_key = "639191cb0774661597f28a47e7e2bad5"
    logMsg("get fanart.tv images for type: %s - id: %s" %(type,id))
    extrafanarts = []
    if artwork.get("extrafanarts"): extrafanarts = eval(artwork.get("extrafanarts"))
    try:
        maxfanarts = WINDOW.getProperty("SkinHelper.maxNumFanArts")
        if maxfanarts: maxfanarts = int(maxfanarts)
    except: maxfanarts = 0
    
    if type == "movie":
        url = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s' %(id,api_key)
    elif type == "artist":
        url = 'http://webservice.fanart.tv/v3/music/%s?api_key=%s' %(id,api_key)
    elif type == "album":
        url = 'http://webservice.fanart.tv/v3/music/albums/%s?api_key=%s' %(id,api_key)
    else:
        url = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s' %(id,api_key)
    try:
        response = requests.get(url, timeout=15)
    except Exception as e:
        logMsg("getfanartTVimages lookup failed--> " + str(e), 0)
        return artwork
    if response and response.content and response.status_code == 200:
        data = json.loads(response.content.decode('utf-8','replace'))
    else:
        logMsg("get fanart.tv images FAILED for type: %s - id: %s  - statuscode: %s" %(type,id,response.status_code))
        return artwork
    if data:
        if type == "album" and data.has_key("albums"):
            for key, value in data["albums"].iteritems():
                if value.has_key("cdart"):
                    for cdart in value.get("cdart"):
                        if xbmcvfs.exists(cdart.get("url")) and (not artwork.get("discart") or (allowoverwrite and not "http:" in artwork.get("discart"))):
                            artwork["discart"] = cdart.get("url")
                if value.has_key("albumcover"):
                    for albumcover in value.get("albumcover"):    
                        if xbmcvfs.exists(albumcover.get("url")) and (not artwork.get("folder") or (allowoverwrite and not "http:" in artwork.get("folder"))):
                            artwork["folder"] = albumcover.get("url")
        else:
            #we need to use a little mapping between fanart.tv arttypes and kodi artttypes
            fanartTVTypes = [ ("logo","clearlogo"),("musiclogo","clearlogo"),("disc","discart"),("clearart","clearart"),("banner","banner"),("clearlogo","clearlogo"),("poster","poster"),("background","fanart"),("showbackground","fanart"),("characterart","characterart")]
            if type != "artist": fanartTVTypes.append( ("thumb","landscape") )
            if type == "artist": fanartTVTypes.append( ("thumb","folder") )
            prefixes = ["",type,"hd","hd"+type]
            for fanarttype in fanartTVTypes:
                for prefix in prefixes:
                    fanarttvimage = prefix+fanarttype[0]
                    if data.has_key(fanarttvimage):
                        for item in data[fanarttvimage]:
                            if item.get("lang","") == KODILANGUAGE:
                                #select image in preferred language
                                if xbmcvfs.exists(item.get("url")):
                                    artwork[fanarttype[1]] = item.get("url")
                                    break
                        if not artwork.get(fanarttype[1]) or (allowoverwrite and not "http:" in artwork.get(fanarttype[1])):
                            #just grab the first english one as fallback
                            for item in data[fanarttvimage]:
                                if item.get("lang","") == "en" or not item.get("lang"):
                                    if xbmcvfs.exists(item.get("url")):
                                        artwork[fanarttype[1]] = item.get("url")
                                        break
                        #grab extrafanarts in list
                        if "background" in fanarttvimage:
                            fanartcount = 0
                            for item in data[fanarttvimage]:
                                if item.get("url") not in extrafanarts and fanartcount < maxfanarts:
                                    if xbmcvfs.exists(item.get("url")):
                                        extrafanarts.append(item.get("url"))
                                        fanartcount += 1               
    #save extrafanarts as string
    if extrafanarts:
        artwork["extrafanarts"] = repr(extrafanarts)
    return artwork

def getTmdbDetails(title,artwork=None,type=None,year="",includeCast=False):
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
            #find year match
            if data and year and data.get("results"):
                for item in data["results"]:
                    if item.get("first_air_date") and year in item.get("first_air_date"):
                        matchFound = item
                        break
                    elif item.get("release_date") and year in item.get("release_date"):
                        matchFound = item
                        break
                        
            #find exact match based on title
            if not matchFound and data and data.get("results",None):
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
            media_type = type
            if media_type == "multi" and matchFound.get("media_type"):
                media_type = matchFound.get("media_type","")
            name = item.get("name")
            if not name: name = item.get("title")
            artwork["tmdb_title"] = name
            artwork["tmdb_type"] = media_type
            logMsg("getTMDBimage - TMDB match found for %s !" %title)
            #lookup external tmdb_id and perform artwork lookup on fanart.tv
            if (WINDOW.getProperty("SkinHelper.useFanArtTv") == "true" or includeCast) and id:
                languages = [KODILANGUAGE,"en"]
                for language in languages:
                    if media_type == "movie":
                        url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=videos' %(id,tmdb_apiKey,language)
                        if includeCast: url += ',credits'
                    elif media_type == "tv":
                        url = 'http://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=external_ids,videos&language=%s' %(id,tmdb_apiKey,language)
                        if includeCast: url = 'http://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=external_ids,credits,videos&language=%s' %(id,tmdb_apiKey,language)
                    response = requests.get(url)
                    data = json.loads(response.content.decode('utf-8','replace'))
                    if data:
                        if not media_id and data.get("imdb_id"):
                            media_id = str(data.get("imdb_id"))
                            artwork["imdb_id"] = media_id
                        if not media_id and data.get("external_ids"): 
                            media_id = str(data["external_ids"].get("tvdb_id"))
                            artwork["tvdb_id"] = media_id
                        if data.get("vote_average"): artwork["rating"] = str(data.get("vote_average"))
                        if data.get("budget"): artwork["budget"] = str(data.get("budget"))
                        if data.get("revenue"): artwork["revenue"] = str(data.get("revenue"))
                        if data.get("tagline"): artwork["tagline"] = data.get("tagline")
                        if data.get("homepage"): artwork["homepage"] = data.get("homepage")
                        if data.get("status"): artwork["status"] = data.get("status")
                        if data.get("networks"):
                            itms = []
                            for itm in data.get("networks"):
                                itms.append(itm.get("name"))
                            artwork["studio"] = " / ".join(itms)
                        if data.get("production_companies"):
                            itms = []
                            for itm in data.get("production_companies"):
                                itms.append(itm.get("name"))
                            artwork["studio"] = " / ".join(itms)
                        if data.get("genres"):
                            itms = []
                            for itm in data.get("genres"):
                                itms.append(itm.get("name"))
                            artwork["genre"] = " / ".join(itms)
                        if data.get("videos") and data["videos"].get("results"):
                            for video in data["videos"].get("results"):
                                if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                                    artwork["trailer"] = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' %video.get("key")
                                    break
                        if data.get("credits") and data["credits"].get("cast"):
                            artwork["cast"] = []
                            artwork["castandrole"] = []
                            for cast in data["credits"].get("cast"):
                                cast_thumb = ""
                                if cast.get("profile_path"): cast_thumb = "http://image.tmdb.org/t/p/original" + cast.get("profile_path")
                                artwork["cast"].append( {"name": cast.get("name"), "role": cast.get("character"), "thumbnail": cast_thumb } )
                                artwork["castandrole"].append( (cast.get("name"), cast.get("character")) )
                        if data.get("credits") and data["credits"].get("crew"):
                            for cast in data["credits"].get("crew"):
                                if not artwork.get("writer") and "Author" in cast.get("job"): artwork["writer"] = cast.get("name")
                                if not artwork.get("writer") and "Writer" in cast.get("job"): artwork["writer"] = cast.get("name")
                                if not artwork.get("director") and "Director" in cast.get("job"): artwork["director"] = cast.get("name")
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
            logMsg("getTmdbDetails - no internet access, disabling internet lookups for now",0)
        else:
            logMsg("getTmdbDetails - Error in getTmdbDetails --> " + str(e),0)
    
    if artwork.get("cast"): 
        artwork["cast"] = repr(artwork.get("cast"))
        artwork["castandrole"] = repr(artwork.get("castandrole"))
    
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
    thumb = getTmdbDetails(actorname,None,"person")
    #save in cache
    cache[actorname] = thumb
    WINDOW.setProperty("SkinHelper.ActorImages",repr(cache))
    return thumb

def searchThumb(searchphrase, searchphrase2=""):
    #general method to perform online image search by querying all providers
    thumb = WINDOW.getProperty("SkinHelper.Thumbcache-" + try_encode(searchphrase)).decode("utf-8")
    if not thumb: thumb = getActorImage(searchphrase).get("thumb","")
    if not thumb: thumb = getTmdbDetails(searchphrase).get("poster","")
    if not thumb: thumb = searchGoogleImage(searchphrase,searchphrase2)
    if not thumb: thumb = searchYoutubeImage(searchphrase,searchphrase2)
    WINDOW.setProperty("SkinHelper.Thumbcache-"+try_encode(searchphrase),thumb)
    return thumb
    
def downloadImage(imageUrl,thumbsPath, filename, allowoverwrite=False):
    try:
        if not xbmcvfs.exists(thumbsPath):
            xbmcvfs.mkdirs(thumbsPath)
        newFile = os.path.join(thumbsPath,filename)
        if xbmcvfs.exists(newFile) and allowoverwrite and imageUrl != newFile:
            retries = 0
            while xbmcvfs.exists(newFile) and retries < 10:
                xbmcvfs.delete(newFile)
                xbmc.sleep(500)
                retries += 1
        if not xbmcvfs.exists(newFile):
            #do not overwrite existing images
            xbmcvfs.copy(imageUrl,newFile)
        return newFile
    except Exception as e:
        logMsg("ERROR in downloadImage --> " + str(e), 0)
        return imageUrl

def createNFO(cachefile, artwork):
    try:
        tree = xmltree.ElementTree( xmltree.Element( "artdetails" ) )
        root = tree.getroot()
        for key, value in artwork.iteritems():
            if value:
                child = xmltree.SubElement( root, key )
                child.text = try_decode(value)
        
        indentXML( tree.getroot() )
        xmlstring = xmltree.tostring(tree.getroot(), encoding="utf-8")
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
            root = xmltree.fromstring(f.read())
            f.close()
            cacheFound = True
            for child in root:
                if not artwork.get(child.tag):
                    value = try_decode(child.text).replace('\n', ' ').replace('\r', '')
                    artwork[child.tag] = value
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
                url = 'http://www.thelogodb.com/api/json/v1/3241/tvchannel.php?s=%s' %try_encode(searchphrase)
                response = requests.get(url)
                if response.content:
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
                url = 'http://www.thelogodb.com/api/json/v1/3241/tvchannel.php?s=%s' %try_encode(search_alt)
                response = requests.get(url)
                if response.content:
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

def searchGoogleImage(searchphrase1, searchphrase2="",manualLookup=False):
    if searchphrase2: searchphrase = "'%s' '%s'" %(searchphrase1, searchphrase2)
    if manualLookup: xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    else: searchphrase = searchphrase1
    imagesList = []
    imagesList2 = []
    image = ""
    try:
        results = getGoogleImages(searchphrase)
        #prefer results with searchphrase in url
        count = 0
        for img in results:
            count += 1
            if not manualLookup and xbmcvfs.exists(img):
                #just return the first image found (assuming that will be the best match)
                return img
            else:
                #manual lookup, list results and let user pick one
                listitem = xbmcgui.ListItem(label=img)
                listitem.setProperty("icon",img)
                imagesList.append(listitem)
        
        if manualLookup and imagesList:
            import Dialogs as dialogs
            w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=imagesList, windowtitle="",multiselect=False )
            w.doModal()
            selectedItem = w.result
            if selectedItem != -1:
                selectedItem = imagesList[selectedItem]
                image = selectedItem.getProperty("icon")
        
    except Exception as e:
        if "getaddrinfo failed" in str(e):
            WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
            logMsg("searchGoogleImage - no internet access, disabling internet lookups for now",0)
        else:
            logMsg("searchGoogleImage - ERROR in searchGoogleImage ! --> " + str(e),0)
    if manualLookup: 
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    return image

def getAnimatedPosters(imdbid):
    #get the item from cache first
    cacheStr = "SkinHelper.AnimatedPosters.%s" %imdbid
    cache = WINDOW.getProperty(cacheStr).decode('utf-8')
    if cache:
        return eval(cache)
    else:
        result = {}
        logMsg("getAnimatedPosters for imdbid: %s " %(imdbid))
        #create local thumbs directory
        if not xbmcvfs.exists("special://thumbnails/animatedgifs/"):
            xbmcvfs.mkdir("special://thumbnails/animatedgifs/")
        
        # retrieve animated poster and fanart
        for img in [("animated_fanart","%s_background_0_original.gif" %imdbid), ("animated_poster","%s_poster_0_original.gif" %imdbid)]:
            if xbmcvfs.exists("special://thumbnails/animatedgifs/%s"%img[1]):
                result[img[0]] = "special://thumbnails/animatedgifs/%s"%img[1]
            elif xbmcvfs.exists("http://www.consiliumb.com/animatedgifs/%s" %img[1]):
                xbmcvfs.copy("http://www.consiliumb.com/animatedgifs/%s"%img[1], "special://thumbnails/animatedgifs/%s"%img[1])
                for i in range(40):
                    if xbmcvfs.exists("special://thumbnails/animatedgifs/%s"%img[1]): break
                    else: xbmc.sleep(250)
                result[img[0]] = "special://thumbnails/animatedgifs/%s"%img[1]
        
        WINDOW.setProperty(cacheStr,repr(result))
        return result
    
def getGoogleImages(terms,**kwargs):
    start = ''
    page = 1
    args = ['q={0}'.format(urllib.quote_plus(try_encode(terms)))]
    for k in kwargs.keys():
        if kwargs[k]: args.append('{0}={1}'.format(k,kwargs[k]))
    query = '&'.join(args)
    start = ''
    baseURL = 'https://www.google.com/search?site=imghp&tbm=isch&tbs=isz:l{start}{query}'
    if page > 1: start = '&start=%s' % ((page - 1) * 1)
    url = baseURL.format(start=start,query='&' + query)
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Safari/535.19')]
    html = opener.open(url).read()
    soup = BeautifulSoup.BeautifulSoup(html)
    results = []
    for div in soup.findAll('div'):
        if div.get("class") == "rg_di rg_el ivg-i":
            a = div.find("a")
            if a:
                page = a.get("href","")
                params = urlparse.parse_qs(page)
                image = params.get("/imgres?imgurl")
                if image:
                    results.append(image[0])
    return results

def getImdbTop250():
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    html = opener.open("http://www.imdb.com/chart/top").read()
    soup = BeautifulSoup.BeautifulSoup(html)
    results = {}
    for table in soup.findAll('table'):
        if table.get("class") == "chart full-width":
            for td in table.findAll('td'):
                if td.get("class") == "titleColumn":
                    a = td.find("a")
                    if a:
                        url = a.get("href","")
                        imdb_id = url.split("/")[2]
                        imdb_rank = url.split("chttp_tt_")[1]
                        results[imdb_id] = imdb_rank
    return results
    
def searchYoutubeImage(searchphrase, searchphrase2=""):
    image = ""
    if searchphrase2:
        searchphrase = searchphrase + " " + searchphrase2
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
 
def getMusicBrainzId(artist, album="", track=""):
    albumid = ""
    artistid = ""
    album = album.replace(" (single)","")
    track = track.split(" (")[0]
    matchartist = getCompareString(artist)
    if artist.startswith("The "): artist = artist.replace("The ","")
    logMsg("getMusicBrainzId -- artist:  -  %s  - album:  %s  - track:  %s" %(artist,album,track))
    
    #use musicbrainz to get ID
    try:
        if not WINDOW.getProperty("SkinHelper.TempDisableMusicBrainz"):
            MBalbum = None
            if not MBalbum and artist and album:
                MBalbums = m.search_release_groups(query=single_urlencode(try_encode(album)),limit=1,offset=None, strict=False, artist=single_urlencode(try_encode(artist)))
                if MBalbums and MBalbums.get("release-group-list"): MBalbum = MBalbums.get("release-group-list")[0]
            if not MBalbum and artist and track:
                MBalbums = m.search_recordings(query=single_urlencode(try_encode(track)),limit=1,offset=None, strict=False, artist=single_urlencode(try_encode(artist)))
                if MBalbums and MBalbums.get("recording-list"): MBalbum = MBalbums.get("recording-list")[0]
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
    except Exception as e:
        logMsg("getMusicArtwork AudioDb lookup failed --> " + str(e), 0)
    
    #try lastfm as fallback
    if (not artistid or not albumid) and artist and album:
        try:
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/'
            params = {'method': 'album.getInfo', 'format': 'json', 'artist' : artist, 'album': album, 'api_key': '1869cecbff11c2715934b45b721e6fb0'}
            response = requests.get(lastfm_url, params=params)
            if response and response.content:
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.get("album"):
                    lfmdetails = data["album"]
                    if lfmdetails.get("mbid") and not albumid: albumid = lfmdetails.get("mbid")
                    if lfmdetails.get("tracks") and not artistid and lfmdetails["tracks"].get("track"):
                        for track in lfmdetails.get("tracks")["track"]:
                            if track["artist"]["name"] == artist and track["artist"]["mbid"]:
                                artistid = track["artist"]["mbid"]
                                break;
        except Exception as e:
            logMsg("getMusicArtwork LastFM lookup failed --> " + str(e), 0)
    
    #get lastFM by artist name as last resort
    if not artistid and artist:
        try:
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/'
            params = {'method': 'artist.getInfo', 'format': 'json', 'artist' : artist, 'api_key': '1869cecbff11c2715934b45b721e6fb0'}
            response = requests.get(lastfm_url, params=params)
            if response and response.content:
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.get("artist"):
                    lfmdetails = data["artist"]
                    if lfmdetails.get("mbid") and not artistid: artistid = lfmdetails.get("mbid")
        except Exception as e:
            logMsg("getMusicArtwork LastFM lookup failed --> " + str(e), 0)
    
    logMsg("getMusicBrainzId results for artist %s  - artistid:  %s  - albumid:  %s" %(artist,artistid,albumid))
    return (artistid, albumid)

def getArtistArtwork(musicbrainzartistid, artwork=None, allowoverwrite=True):
    if not artwork: artwork = {}
    #get fanart.tv artwork for artist
    artwork = getfanartTVimages("artist",musicbrainzartistid,artwork, allowoverwrite)
    extrafanarts = []
    if artwork.get("extrafanarts"): extrafanarts = eval(artwork.get("extrafanarts"))
    
    #get audiodb info for artist  (and use as spare for artwork)
    try:
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/artist-mb.php?i=%s' %musicbrainzartistid
        response = requests.get(audiodb_url)
    except Exception as e:
        logMsg("getMusicArtwork AudioDb lookup failed --> " + str(e), 0)
    if response and response.content:
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("artists") and len(data.get("artists")) > 0:
            adbdetails = data["artists"][0]
            if not artwork.get("banner") and adbdetails.get("strArtistBanner") and xbmcvfs.exists(adbdetails.get("strArtistBanner")): artwork["banner"] = adbdetails.get("strArtistBanner")
            if adbdetails.get("strArtistFanart") and not artwork.get("fanart") and xbmcvfs.exists(adbdetails.get("strArtistFanart")): artwork["fanart"] = adbdetails.get("strArtistFanart")
            if adbdetails.get("strArtistFanart2") and not adbdetails.get("strArtistFanart2") in extrafanarts and xbmcvfs.exists(adbdetails.get("strArtistFanart2")): extrafanarts.append(adbdetails.get("strArtistFanart2"))
            if adbdetails.get("strArtistFanart3") and not adbdetails.get("strArtistFanart3") in extrafanarts and xbmcvfs.exists(adbdetails.get("strArtistFanart3")): extrafanarts.append(adbdetails.get("strArtistFanart3"))
            if extrafanarts and adbdetails.get("strArtistFanart") and not adbdetails.get("strArtistFanart") in extrafanarts and xbmcvfs.exists(adbdetails.get("strArtistFanart")): extrafanarts.append(adbdetails.get("strArtistFanart"))
            if not artwork.get("clearlogo") and adbdetails.get("strArtistLogo") and xbmcvfs.exists(adbdetails.get("strArtistLogo")): artwork["clearlogo"] = adbdetails.get("strArtistLogo")
            if not artwork.get("artistthumb") and adbdetails.get("strArtistThumb") and xbmcvfs.exists(adbdetails.get("strArtistThumb")): artwork["artistthumb"] = adbdetails.get("strArtistThumb")
            if not artwork.get("folder") and adbdetails.get("strArtistThumb") and xbmcvfs.exists(adbdetails.get("strArtistThumb")): artwork["folder"] = adbdetails.get("strArtistThumb")
            if not artwork.get("info") and adbdetails.get("strBiography" + KODILANGUAGE.upper()): artwork["info"] = adbdetails.get("strBiography" + KODILANGUAGE.upper())
            if not artwork.get("info") and adbdetails.get("strBiographyEN"): artwork["info"] = adbdetails.get("strBiographyEN")
            if artwork.get("info"): artwork["info"] = artwork.get("info").replace('\n', ' ').replace('\r', '')
    
    #get lastFM info for artist  (and use as spare for artwork)
    if not artwork.get("info") or not artwork.get("artistthumb"):
        try:
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&format=json&api_key=1869cecbff11c2715934b45b721e6fb0&mbid=%s' %musicbrainzartistid
            response = requests.get(lastfm_url)
        except Exception as e:
            logMsg("getMusicArtwork LastFM lookup failed --> " + str(e), 0)
        if response and response.content:
            data = json.loads(response.content.decode('utf-8','replace'))
            if data and data.get("artist"):
                lfmdetails = data["artist"]
                if lfmdetails.get("image"):
                    for image in lfmdetails["image"]:
                        if not artwork.get("artistthumb") and image["size"]=="extralarge" and image and xbmcvfs.exists(image["#text"]): artwork["artistthumb"] = image["#text"]
                
                if not artwork.get("info") and lfmdetails.get("bio"): artwork["info"] = lfmdetails["bio"].get("content","").replace('\n', ' ').replace('\r', '')  
    
    #save extrafanarts as string
    if extrafanarts:
        artwork["extrafanarts"] = repr(extrafanarts)

    return artwork

def getAlbumArtwork(musicbrainzalbumid, artwork=None, allowoverwrite=True):
    if not artwork: artwork = {}
    #get fanart.tv artwork for album
    artwork = getfanartTVimages("album",musicbrainzalbumid,artwork,allowoverwrite)
    #get album info on theaudiodb (and use as spare for artwork)
    try:
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/193621276b2d731671156g/album-mb.php?i=%s' %musicbrainzalbumid
        response = requests.get(audiodb_url)
    except Exception as e:
        logMsg("getMusicArtwork AudioDB lookup failed --> " + str(e), 0)
        return {}
    if response and response.content:
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("album") and len(data.get("album")) > 0:
            adbdetails = data["album"][0]
            if not artwork.get("folder") and adbdetails.get("strAlbumThumb") and xbmcvfs.exists(adbdetails.get("strAlbumThumb")): artwork["folder"] = adbdetails.get("strAlbumThumb")
            if not artwork.get("discart") and adbdetails.get("strAlbumCDart") and xbmcvfs.exists(adbdetails.get("strAlbumCDart")): artwork["discart"] = adbdetails.get("strAlbumCDart")
            if not artwork.get("info") and adbdetails.get("strDescription" + KODILANGUAGE.upper()): artwork["info"] = adbdetails.get("strDescription" + KODILANGUAGE.upper())
            if not artwork.get("info") and adbdetails.get("strDescriptionEN"): artwork["info"] = adbdetails.get("strDescriptionEN")
            if artwork.get("info"): artwork["info"] = normalize_string(artwork["info"]).replace('\n', ' ').replace('\r', '')
    
    #get lastFM info for artist  (and use as spare for artwork)
    if (not artwork.get("info") or not artwork.get("folder")) and artwork.get("artistname") and artwork.get("albumname"):
        try:
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/?method=album.getInfo&format=json&api_key=1869cecbff11c2715934b45b721e6fb0&artist=%s&album=%s' %(artwork["artistname"],artwork["albumname"])
            response = requests.get(lastfm_url)
        except Exception as e:
            logMsg("getMusicArtwork LastFM lookup failed --> " + str(e), 0)
        if response and response.content:
            data = json.loads(response.content.decode('utf-8','replace'))
            if data and data.get("album"):
                if isinstance(data["album"], list): lfmdetails = data["album"][0]
                else: lfmdetails = data["album"]
                if lfmdetails.get("image"):
                    for image in lfmdetails["image"]:
                        if image and not artwork.get("folder") and image["size"]=="extralarge" and xbmcvfs.exists(image["#text"]): artwork["folder"] = image["#text"]

                if not artwork.get("info") and lfmdetails.get("wiki"): artwork["info"] = lfmdetails["wiki"].get("content","").replace('\n', ' ').replace('\r', '').split(' <a')[0]  
    
    #get album thumb from musicbrainz
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
    
def preCacheAllMusicArt(skipOnCache=False):
    #process all albums and precache the artwork
    progressDialog = xbmcgui.DialogProgressBG()
    try:
        progressDialog.create(ADDON.getLocalizedString(32157))
        progressDialog.update(0, ADDON.getLocalizedString(32157),"Collecting albums...")
        json_response = getJSON('AudioLibrary.GetAlbums', '{ "properties": [ "artist","displayartist" ] }')
        if json_response:
            for count, item in enumerate(json_response):
                artistName = item["displayartist"]
                albumName = item["label"]
                progressDialog.update((count * 100) / len(json_response),ADDON.getLocalizedString(32157), artistName + " - " + albumName)
                getMusicArtwork(artistName,albumName,"",False)
                logMsg("preCacheAllMusicArt -- " + artistName + " - " + albumName, 0)
    except Exception as e:
        logMsg("ERROR in preCacheAllMusicArt --> " + str(e), 0)
    progressDialog.close()
    
def getMusicArtwork(artistName, albumName="", trackName="", ignoreCache=False):
    if not artistName:
        logMsg("getMusicArtwork - No artist given, skipping...")
        return {}
    albumartwork = {}
    path = ""
    artistCacheFound = False
    albumCacheFound = False
    artistpath = ""
    albumpath = ""
    if albumName == trackName: trackName = ""
    if artistName == trackName: trackName = ""
    if not albumName and trackName: albumName = trackName
    artistOnly = False
    if not albumName: artistOnly = True
    if "/" in artistName: artistName = artistName.split("/")[0]
    localArtistMatch = False
    localAlbumMatch = False
    cacheStrAlbum = ""
    albumcache = None

    enableMusicArtScraper = WINDOW.getProperty("SkinHelper.enableMusicArtScraper") == "true"
    downloadMusicArt = WINDOW.getProperty("SkinHelper.downloadMusicArt") == "true"
    allowoverwrite = WINDOW.getProperty("SkinHelper.preferOnlineMusicArt") == "true"
    enableLocalMusicArtLookup = WINDOW.getProperty("SkinHelper.enableLocalMusicArtLookup") == "true"

    ############# ALBUM DETAILS #########################
    if artistName and albumName:
        
        #get the items from window cache first
        cacheStrAlbum = "SkinHelper.Music.Cache-%s-%s" %(artistName.lower(),albumName.lower())
        albumcache = WINDOW.getProperty(try_encode("SkinHelper.Music.Cache-%s-%s" %(artistName.lower(),albumName.lower()))).decode("utf-8")
        if albumcache and not ignoreCache:
            albumartwork = eval(albumcache)
            albumCacheFound = True
        else:
            logMsg("getMusicArtwork artist: %s  - track: %s  -  album: %s" %(artistName,trackName,albumName))
            #get details from persistant cachefile to prevent online lookups
            if not ignoreCache: albumartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicart/%s-%s.xml" %(normalize_string(artistName),normalize_string(albumName)))
            else: albumartwork = {}
            if albumartwork and albumartwork.get("artistname"): 
                albumCacheFound = True
            
            #always grab details from library for trackcounts etc.
            songcount = 0
            tracklist = []
            json_items = getJSON('AudioLibrary.GetAlbums','{ "filter": {"operator":"is", "field":"album", "value":"%s"}, "properties": [ "description","fanart","thumbnail","artistid","artist","displayartist","musicbrainzalbumid","musicbrainzalbumartistid" ] }'%(albumName.replace("\"","\\" + "\"")))
            for json_response in json_items:
                if artistName in json_response["displayartist"]:
                    logMsg("getMusicArtwork found album details --> " + repr(json_response))
                    localAlbumMatch = True
                    if json_response.get("description") and not albumartwork.get("info"): albumartwork["info"] = json_response["description"]
                    if json_response.get("thumbnail") and not (json_response["label"].lower() == "singles" or "Various Artists" in json_response.get("displayartist").lower()) and xbmcvfs.exists(getCleanImage(json_response["thumbnail"])): albumartwork["folder"] = getCleanImage(json_response["thumbnail"])
                    if json_response.get("label") and not albumartwork.get("albumname"): albumartwork["albumname"] = json_response["label"]
                    if json_response.get("displayartist") and not albumartwork.get("artistname"): albumartwork["artistname"] = json_response["displayartist"]
                    if json_response.get("musicbrainzalbumid") and not albumartwork.get("musicbrainzalbumid"): albumartwork["musicbrainzalbumid"] = json_response["musicbrainzalbumid"]
                    albumid = json_response.get("albumid")
                    #get track listing for album
                    json_response2 = getJSON('AudioLibrary.GetSongs', '{ "properties": [ %s ], "sort": {"method":"track"}, "filter": { "albumid": %d}}'%(fields_songs,albumid))
                    for song in json_response2:
                        if not path: path = song["file"]
                        if song.get("track"): tracklist.append(u"%s - %s" %(song["track"], song["title"]))
                        else: tracklist.append(song["title"])
                        songcount += 1
                
                if not albumartwork.get("artistname"): albumartwork["artistname"] = artistName
                
                #make sure that our results are strings
                albumartwork["tracklist"] = u"[CR]".join(tracklist)
                albumartwork["tracklist.formatted"] = ""
                for trackitem in tracklist:
                    albumartwork["tracklist.formatted"] += u"• %s[CR]" %trackitem
                albumartwork["albumcount"] = "1"
                albumartwork["songcount"] = "%s"%songcount
                if isinstance(albumartwork.get("musicbrainzalbumid",""), list):
                    albumartwork["musicbrainzalbumid"] = albumartwork["musicbrainzalbumid"][0]
   
    ############## ARTIST DETAILS #######################################
    
    #get the items from window cache first
    cacheStrArtist = "SkinHelper.Music.Cache-%s" %artistName.lower()
    artistcache = WINDOW.getProperty(try_encode(cacheStrArtist)).decode("utf-8")
    if artistcache and not ignoreCache:
        artistartwork = eval(artistcache)
        artistCacheFound = True
    else:
        #get details from persistant cachefile to prevent online lookups
        if not ignoreCache: artistartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicart/%s.xml" %normalize_string(artistName))
        else: artistartwork = {}
        if artistartwork: artistCacheFound = True
            
        #always grab details from library for trackcounts etc.
        songcount = 0
        albumcount = 0
        albums = []
        tracklist = []
        json_response = None
        json_response = getJSON('AudioLibrary.GetArtists', '{ "filter": {"operator":"is", "field":"artist", "value":"%s"}, "properties": [ "description","fanart","thumbnail","musicbrainzartistid" ] }'%artistName)
        if len(json_response) == 1:
            json_response = json_response[0]
            localArtistMatch = True
            if json_response.get("description") and not artistartwork.get("info"): artistartwork["info"] = json_response["description"]
            if json_response.get("fanart") and xbmcvfs.exists(getCleanImage(json_response["fanart"])): artistartwork["fanart"] = getCleanImage(json_response["fanart"])
            if json_response.get("thumbnail") and xbmcvfs.exists(getCleanImage(json_response["thumbnail"])) : artistartwork["folder"] = getCleanImage(json_response["thumbnail"])
            if json_response.get("label") and not artistartwork.get("artistname",""): artistartwork["artistname"] = json_response["label"]
            if json_response.get("musicbrainzartistid") and not artistartwork.get("musicbrainzartistid"): artistartwork["musicbrainzartistid"] = json_response["musicbrainzartistid"]
            #get track/album listing for artist
            json_response2 = None
            json_response2 = getJSON('AudioLibrary.GetSongs', '{ "filter":{"artistid": %d}, "properties": [ %s ] }'%(json_response.get("artistid"),fields_songs))
            logMsg("getMusicArtwork found songs for artist --> " + repr(json_response2))
            for song in json_response2:
                if not trackName: trackName = song.get("label","")
                if song.get("album"):
                    if not path and song.get("file"):
                        #get path from song - only if artist level matches...
                        if "\\" in song.get("file"): delim = "\\"
                        else: delim = "/"
                        pathartist = song.get("file").split(delim)[-3]
                        match =  SM(None, artistName, pathartist).ratio()
                        if match >= 0.50: path = song.get("file")
                    if not albumName: albumName = song.get("album")
                    if song.get("musicbrainzartistid") and not artistartwork.get("musicbrainzartistid"): artistartwork["musicbrainzartistid"] = song["musicbrainzartistid"]
                    tracklist.append(song["title"])
                    songcount += 1
                    if song.get("album") and song["album"] not in albums:
                        albumcount +=1
                        albums.append(song["album"])
            
            #make sure that our results are strings
            artistartwork["albums"] = u"[CR]".join(albums)
            artistartwork["albums.formatted"] = ""
            for albumitem in albums:
                artistartwork["albums.formatted"] += u"• %s[CR]" %albumitem
            artistartwork["tracklist.formatted"] = ""
            for trackitem in tracklist:
                artistartwork["tracklist.formatted"] += u"• %s[CR]" %trackitem
            artistartwork["tracklist"] = u"[CR]".join(tracklist)
            artistartwork["albumcount"] = "%s"%albumcount
            artistartwork["songcount"] = "%s"%songcount
            if not albumartwork.get("artistname"): albumartwork["artistname"] = artistName
            if not albumartwork.get("albumname"): albumartwork["albumname"] = albumName
            if isinstance(artistartwork.get("musicbrainzartistid",""), list):
                artistartwork["musicbrainzartistid"] = artistartwork["musicbrainzartistid"][0]
        
            #LOOKUP LOCAL ARTWORK PATH PASED ON SONG FILE PATH
            if path and enableLocalMusicArtLookup and (not artistCacheFound or (albumName and not albumCacheFound)) and localArtistMatch:
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
                    match =  SM(None, artistName, artistpath.split(delim)[-2]).ratio()
                    if not match >= 0.50:
                        logMsg("getMusicArtwork - lookup on disk skipped for %s - not correct folder structure (artistname\albumname)" %artistartwork.get("artistname",""))
                        albumpath = ""
                        artistpath = ""
                    else:    
                        #lookup local artist artwork
                        artistartwork["path"] = artistpath
                        for artType in KodiArtTypes:
                            artpath = os.path.join(artistpath,artType[1])
                            if xbmcvfs.exists(artpath) and not artistartwork.get(artType[0]):
                                artistartwork[artType[0]] = artpath
                                logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],artistName))
                        
                        #lookup local album artwork
                        if albumName and xbmcvfs.exists(albumpath):
                            albumartwork["path"] = albumpath
                            #lookup existing artwork in the paths
                            for artType in KodiArtTypes:
                                artpath = os.path.join(albumpath,artType[1])
                                if xbmcvfs.exists(artpath) and not albumartwork.get(artType[0]):
                                    albumartwork[artType[0]] = artpath
                                    logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],albumName))
                        else: albumpath = ""
               
        #online lookup for details
        if enableMusicArtScraper and (not artistCacheFound or (albumName and not albumCacheFound)):
            #lookup details in musicbrainz
            #retrieve album id and artist id with a combined query of album name and artist name to get an accurate result
            if not albumartwork.get("musicbrainzalbumid") or not artistartwork.get("musicbrainzartistid"):
                musicbrainzartistid, musicbrainzalbumid = getMusicBrainzId(artistName,albumName,trackName)
                if not albumartwork.get("musicbrainzalbumid"): 
                    albumartwork["musicbrainzalbumid"] = musicbrainzalbumid
                if not artistartwork.get("musicbrainzartistid"): 
                    artistartwork["musicbrainzartistid"] = musicbrainzartistid

            ########################################################## ARTIST LEVEL #########################################################
            if artistartwork.get("musicbrainzartistid") and not artistCacheFound:
                artistartwork = getArtistArtwork(artistartwork.get("musicbrainzartistid"), artistartwork, allowoverwrite)

                #download images if we want them local
                if downloadMusicArt and artistpath:
                    for artType in KodiArtTypes:
                        if artistartwork.has_key(artType[0]): artistartwork[artType[0]] = downloadImage(artistartwork[artType[0]],artistpath,artType[1],allowoverwrite)
                
                #extrafanart images
                if artistartwork.get("extrafanarts"):
                    if downloadMusicArt and artistpath:
                        efadir = os.path.join(artistpath,"extrafanart/")
                        xbmcvfs.mkdir(efadir)
                        count = 1
                        for fanart in eval(artistartwork.get("extrafanarts")):
                            downloadImage(fanart,efadir,"fanart%s.jpg"%count)
                            count += 1
                        artistartwork["extrafanart"] = efadir
                    elif not artistartwork.get("extrafanart"): artistartwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=special://profile/addon_data/script.skin.helper.service/musicart/%s.xml" %normalize_string(artistName)
                
            ######################################################### ALBUM LEVEL #########################################################    
            if albumName and albumartwork.get("musicbrainzalbumid") and not albumCacheFound:
                albumartwork = getAlbumArtwork(albumartwork.get("musicbrainzalbumid"), albumartwork, allowoverwrite)
                
                #download images if we want them local
                if downloadMusicArt and albumpath and localAlbumMatch:
                    for artType in KodiArtTypes:
                        if albumartwork.has_key(artType[0]): albumartwork[artType[0]] = downloadImage(albumartwork[artType[0]],albumpath,artType[1],allowoverwrite)
        
        #write to persistant cache
        if artistartwork and not artistCacheFound:
            if artistartwork.get("landscape"): del artistartwork["landscape"]
            if artistartwork.get("folder") and not artistartwork.get("thumb"): artistartwork["thumb"] = artistartwork.get("folder")
            createNFO("special://profile/addon_data/script.skin.helper.service/musicart/%s.xml" %normalize_string(artistName),artistartwork)
        if albumartwork and albumName and not artistOnly and not albumCacheFound:
            if albumartwork.get("landscape"): del albumartwork["landscape"]
            if albumartwork.get("folder") and not albumartwork.get("thumb"): albumartwork["thumb"] = albumartwork.get("folder")
            if not cacheStrAlbum: cacheStrAlbum = "SkinHelper.Music.Cache-%s-%s" %(artistName.lower(),albumName.lower())
            createNFO("special://profile/addon_data/script.skin.helper.service/musicart/%s-%s.xml" %(normalize_string(artistName),normalize_string(albumName)),albumartwork)
        
    #save to window cache
    if not albumcache:
        WINDOW.setProperty(try_encode(cacheStrAlbum), repr(albumartwork))
    if not artistcache:
        WINDOW.setProperty(try_encode(cacheStrArtist), repr(artistartwork))
    
    #return the results...    
    artwork = artistartwork
    #combine album info with artist info
    if artistartwork.get("info") and albumartwork.get("info") and not artistOnly:
        artwork["info"] = albumartwork["info"] + "  ---  " + artistartwork["info"]
    #return artwork combined
    if albumartwork and not artistOnly:
        for key, value in albumartwork.iteritems():
            if value and key != "info": artwork[key] = value

    return artwork
