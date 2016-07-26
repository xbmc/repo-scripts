#!/usr/bin/python
# -*- coding: utf-8 -*-

from Utils import *
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import base64
import musicbrainzngs as m
import BeautifulSoup
import htmlentitydefs
import urllib2, re
from difflib import SequenceMatcher as SM

requests.packages.urllib3.disable_warnings()
s = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
s.mount('http://', HTTPAdapter(max_retries=retries))
s.mount('https://', HTTPAdapter(max_retries=retries))

m.set_useragent("script.skin.helper.service", "1.0.0", "https://github.com/marcelveldt/script.skin.helper.service")
tmdb_apiKey = "ae06df54334aa653354e9a010f4b81cb"

def getPVRThumbs(title,channel,type="channels",path="",genre="",year="",ignoreCache=False, manualLookup=False, override=None):
    cacheFound = False
    ignore = False
    artwork = {}
    pvrThumbPath = None
    if WINDOW.getProperty("SkinHelper.IgnoreCache"): ignoreCache = True
    
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
        for splitchar in splittitlechar.split(";"):
            if splitchar in title:
                title = title.split(splitchar)[0]
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
    if cache and ignoreCache==False and not override:
        cache = eval(cache)
        if cache.has_key(dbID): 
            artwork = cache[dbID]
            cacheFound = True
    else: cache = {}
    
    if not cacheFound:
        
        pvrThumbPath = getPvrThumbPath(channel,title)
        #Do we have a persistant cache file (pvrdetails.xml) for this item ?
        cachefile = os.path.join(pvrThumbPath, "pvrdetails.xml")
        if not ignoreCache and not override:
            artwork = getArtworkFromCacheFile(cachefile,artwork)
        if artwork:
            cacheFound = True
                
        if not cacheFound:
            logMsg("getPVRThumb for dbID: %s" %dbID)
            searchtitle = title
            if manualLookup:
                searchtitle = xbmcgui.Dialog().input(ADDON.getLocalizedString(32147), title, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
            
            if not override:
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
            
                #delete existing files on disk (only at default location)
                if manualLookup and pvrThumbPath.startswith(WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")):
                    recursiveDelete(pvrThumbPath)
                
                #lookup existing artwork in pvrthumbs paths
                if xbmcvfs.exists(pvrThumbPath) and not ("special" in pvrThumbPath and manualLookup):
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
            else:
                artwork = override
            
            #if nothing in library or persistant cache, perform the internet scraping
            if not cacheFound and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
                    
                if not override:
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
                        if manualLookup:
                            artwork["thumb"] = searchYoutubeImage("'%s'" %searchtitle )
                        else:
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
        #not found
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
                if not artwork.get(child.tag) and child.text:
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
            if xbmc.getCondVisibility("PVR.HasTVChannels"):
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
    if searchphrase2 and not manualLookup: searchphrase = "'%s' '%s'" %(searchphrase1, searchphrase2)
    else: searchphrase = searchphrase1
    if manualLookup: xbmc.executebuiltin( "ActivateWindow(busydialog)" )
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

def preCacheAllAnimatedArt():
    #issued after database update: collect all animated artwork
    if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAnimatedPosters)"):
        logMsg("Precache all animated artwork STARTED")
        movies = getJSON('VideoLibrary.GetMovies','{ "properties": [ "imdbnumber" ] }')
        for movie in movies:
            getAnimatedArtwork(movie["imdbnumber"],"poster",movie["movieid"])
            getAnimatedArtwork(movie["imdbnumber"],"fanart",movie["movieid"])
        logMsg("Precache all animated artwork FINISHED")
    
def getAnimatedPostersDb():
    allItems = {}
    
    #try window cache first
    cacheStr = "SkinHelper.AnimatedArtwork"
    cache = WINDOW.getProperty(cacheStr).decode("utf-8")
    if cache: return eval(cache)

    #get all animated posters from the online json file
    
    #create local thumbs directory
    if not xbmcvfs.exists("special://thumbnails/animatedgifs/"):
        xbmcvfs.mkdir("special://thumbnails/animatedgifs/")
        
    response = requests.get('http://www.consiliumb.com/animatedgifs/movies.json')
    if response.content:
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.has_key('movies'):
            for item in data['movies']:
                imdbid = item['imdbid']
                posters = []
                fanarts = []
                for img in item['entries']:
                    if img['type'] == 'poster':
                        posters.append(img['image'])
                    elif img['type'] == 'background':
                        fanarts.append(img['image'])
                allItems[imdbid + 'poster'] = posters
                allItems[imdbid + 'fanart'] = fanarts
    #store in cache
    WINDOW.setProperty(cacheStr, repr(allItems))
    return allItems
              
def getAnimatedArtwork(imdbid,arttype="poster",dbid=None,manualHeader=""):
    if manualHeader: 
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    
    #get the item from cache first
    cacheStr = "SkinHelper.AnimatedArtwork.%s.%s" %(imdbid,arttype)
    cache = WINDOW.getProperty(cacheStr).decode('utf-8')
    if cache and not manualHeader:
        image = cache
    else:
        image = ""
        logMsg("Get Animated %s for imdbid: %s " %(arttype,imdbid))
        
        #check local first
        localfilename = "special://thumbnails/animatedgifs/%s_%s.gif" %(imdbid,arttype)
        localfilenamenone = "special://thumbnails/animatedgifs/%s_%s.none" %(imdbid,arttype)
        if xbmcvfs.exists(localfilename) and not manualHeader:
            image = localfilename
        elif xbmcvfs.exists(localfilenamenone) and not manualHeader:
            image = "None"
        else:    
            #lookup in database
            all_artwork = getAnimatedPostersDb()
            
            if manualHeader:
                #present selectbox to let the user choose the artwork
                imagesList = []
                #add none entry
                listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32013))
                listitem.setProperty("icon","DefaultAddonNone.png")
                imagesList.append(listitem)
                #add browse entry
                listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32176))
                listitem.setProperty("icon","DefaultFolder.png")
                imagesList.append(listitem)
                #append online images
                if all_artwork.get(imdbid + arttype):
                    for img in all_artwork[imdbid + arttype]:
                        listitem = xbmcgui.ListItem(label=img)
                        listitem.setProperty("icon","http://www.consiliumb.com/animatedgifs/%s"%img)
                        imagesList.append(listitem)
                import Dialogs as dialogs
                w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=imagesList, windowtitle=manualHeader, multiselect=False )
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                w.doModal()
                selectedItem = w.result
                xbmc.executebuiltin( "ActivateWindow(busydialog)" )
                if selectedItem == 0:
                    image = "None"
                elif selectedItem == 1:
                    image = xbmcgui.Dialog().browse( 2 , ADDON.getLocalizedString(32176), 'files', mask='.gif').decode("utf-8")
                elif selectedItem != -1:
                    selectedItem = imagesList[selectedItem]
                    image = selectedItem.getProperty("icon").decode("utf-8")
                        
            elif all_artwork.get(imdbid + arttype):
                #just select the first image...
                image = "http://www.consiliumb.com/animatedgifs/%s" %all_artwork[imdbid + arttype][0]
                
            #save to file
            xbmcvfs.delete(localfilename)
            xbmcvfs.delete(localfilenamenone)
            if image == "None":
                #write empty file to prevent recurring lookups
                file =  xbmcvfs.File(localfilenamenone,"w")
                file.write("")
                file.close()
            elif image:
                try:
                    urllib.URLopener().retrieve(image.replace(".gif","_original.gif"), xbmc.translatePath(localfilename).decode("utf-8"))
                except:
                    if "consiliumb" in image:
                        image = image.replace(".gif","_original.gif")
                    xbmcvfs.copy(image,localfilename)
                    xbmc.sleep(150)
                image = localfilename
            
            #save in kodi db
            if dbid and image and image != "None":
                setJSON('VideoLibrary.SetMovieDetails','{ "movieid": %i, "art": { "animated%s": "%s" } }'%(int(dbid),arttype,image))
            elif dbid and image == "None":
                setJSON('VideoLibrary.SetMovieDetails','{ "movieid": %i, "art": { "animated%s": null } }'%(int(dbid),arttype))
            
            #set image to none if empty to prevent further lookups untill next restart
            if not image: image = "None"
            
            #save in window cache
            WINDOW.setProperty(cacheStr,image)
            
            if manualHeader: 
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    return image
    
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
    html = requests.get(url, headers={'User-agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows Phone OS 7.0; Trident/3.1; IEMobile/7.0; LG; GW910)'}, timeout=5).text
    soup = BeautifulSoup.BeautifulSoup(html)
    results = []
    for div in soup.findAll('div'):
        if div.get("id") == "images":
            for a in div.findAll("a"):
                page = a.get("href")
                try:
                    img = page.split("imgurl=")[-1]
                    img = img.split("&imgrefurl=")[0]
                    results.append( img )
                except: pass

    return results

def getImdbTop250():
    results = {}
    #movie top250
    html = requests.get("http://www.imdb.com/chart/top", headers={'User-agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup.BeautifulSoup(html.text)
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
                        
    #tvshows top250
    html = requests.get("http://www.imdb.com/chart/toptv", headers={'User-agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup.BeautifulSoup(html.text)
    for table in soup.findAll('table'):
        if table.get("class") == "chart full-width":
            for td in table.findAll('td'):
                if td.get("class") == "titleColumn":
                    a = td.find("a")
                    if a:
                        url = a.get("href","")
                        imdb_id = url.split("/")[2]
                        imdb_rank = url.split("chttvtp_tt_")[1]
                        results[imdb_id] = imdb_rank
    return results
    
def searchYoutubeImage(searchphrase, searchphrase2=""):
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.youtube)"):
        return ""
        
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
    response = None
    album = album.split(" (")[0]
    artist = artist.split(" (")[0]
    track = track.split(" (")[0]
    matchartist = getCompareString(artist)
    if artist.startswith("The "): artist = artist.replace("The ","")
    logMsg("getMusicBrainzId -- artist:  -  %s  - album:  %s  - track:  %s" %(artist,album,track))
    
    #use musicbrainz to get ID - prefer because it's the most accurate
    if (not artistid or not albumid):
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
        if (not artistid or not albumid) and album:
            audiodb_url = 'http://www.theaudiodb.com/api/v1/json/32176f5352254d85853778/searchalbum.php'
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
        if (not artistid or not albumid) and artist and track:
            audiodb_url = 'http://www.theaudiodb.com/api/v1/json/32176f5352254d85853778/searchtrack.php'
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
    
    #try lastfm by asrtist and album
    if (not artistid or not albumid) and artist and album:
        try:
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/'
            params = {'method': 'album.getInfo', 'format': 'json', 'artist' : artist, 'album': album, 'api_key': '822eb03d95f45fbab2137d646aaf798'}
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
            params = {'method': 'artist.getInfo', 'format': 'json', 'artist' : artist, 'api_key': '822eb03d95f45fbab2137d646aaf798'}
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
    skipOnlineMusicArtOnLocal = WINDOW.getProperty("SkinHelper.skipOnlineMusicArtOnLocal") == "true"
    #get fanart.tv artwork for artist
    if not (skipOnlineMusicArtOnLocal and artwork.get("extrafanart") and artwork.get("clearlogo") and artwork.get("banner") and (artwork.get("artistthumb") or artwork.get("folder"))):
        artwork = getfanartTVimages("artist",musicbrainzartistid,artwork, allowoverwrite)
    else:
        logMsg("SKIP online FANART.TV lookups for artist %s - local artwork found" %musicbrainzartistid)
    
    extrafanarts = []
    if artwork.get("extrafanarts"): extrafanarts = eval(artwork.get("extrafanarts"))
    
    if (skipOnlineMusicArtOnLocal and artwork.get("extrafanart") and artwork.get("clearlogo") and artwork.get("banner") and (artwork.get("artistthumb") or artwork.get("folder")) and artwork.get("info")):
        return artwork
        logMsg("SKIP online AUDIODB/LASTFM lookups for artist %s - local artwork found" %musicbrainzartistid)
    else:
        logMsg("performing audiodb/lastfm lookups for artist " + musicbrainzartistid)
    
    #get audiodb info for artist  (and use as spare for artwork)
    try:
        response = None
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/32176f5352254d85853778/artist-mb.php?i=%s' %musicbrainzartistid
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
            if not artwork.get("folder") and adbdetails.get("strArtistThumb") and xbmcvfs.exists(adbdetails.get("strArtistThumb")): artwork["folder"] = adbdetails.get("strArtistThumb")
            if not artwork.get("info") and adbdetails.get("strBiography" + KODILANGUAGE.upper()): artwork["info"] = adbdetails.get("strBiography" + KODILANGUAGE.upper())
            if not artwork.get("info") and adbdetails.get("strBiographyEN"): artwork["info"] = adbdetails.get("strBiographyEN")
            if artwork.get("info"): artwork["info"] = artwork.get("info").replace('\n', ' ').replace('\r', '')
    
    #get lastFM info for artist  (and use as spare for artwork)
    if not artwork.get("info") or not artwork.get("artistthumb"):
        try:
            response = None
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&format=json&api_key=822eb03d95f45fbab2137d646aaf798&mbid=%s' %musicbrainzartistid
            response = requests.get(lastfm_url)
        except Exception as e:
            logMsg("getMusicArtwork LastFM lookup failed --> " + str(e), 0)
        if response and response.content:
            data = json.loads(response.content.decode('utf-8','replace'))
            if data and data.get("artist"):
                lfmdetails = data["artist"]
                if lfmdetails.get("image"):
                    for image in lfmdetails["image"]:
                        if not artwork.get("folder") and image["size"]=="extralarge" and image and xbmcvfs.exists(image["#text"]): artwork["folder"] = image["#text"]
                
                if not artwork.get("info") and lfmdetails.get("bio"): artwork["info"] = lfmdetails["bio"].get("content","").split(' <a href')[0]
    
    #save extrafanarts as string
    if extrafanarts:
        artwork["extrafanarts"] = repr(extrafanarts)

    return artwork

def getAlbumArtwork(musicbrainzalbumid, artwork=None, allowoverwrite=True):
    if not artwork: artwork = {}
    skipOnlineMusicArtOnLocal = WINDOW.getProperty("SkinHelper.skipOnlineMusicArtOnLocal") == "true"
    
    #get fanart.tv artwork for album
    if not (skipOnlineMusicArtOnLocal and artwork.get("folder") and artwork.get("discart")):
        artwork = getfanartTVimages("album",musicbrainzalbumid,artwork,allowoverwrite)
    else:
        logMsg("SKIP online FANART.TV lookup for album %s - local artwork found" %musicbrainzalbumid)
    
    if (skipOnlineMusicArtOnLocal and artwork.get("folder") and artwork.get("discart") and artwork.get("info")):
        return artwork
        logMsg("SKIP online AUDIODB/LASTFM lookups for album %s - local artwork found" %musicbrainzalbumid)
    else:
        logMsg("performing audiodb/lastfm lookups for album " + musicbrainzalbumid)
    
    #get album info on theaudiodb (and use as spare for artwork)
    try:
        response = None
        audiodb_url = 'http://www.theaudiodb.com/api/v1/json/32176f5352254d85853778/album-mb.php?i=%s' %musicbrainzalbumid
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
            lastfm_url = 'http://ws.audioscrobbler.com/2.0/?method=album.getInfo&format=json&api_key=822eb03d95f45fbab2137d646aaf798&artist=%s&album=%s' %(artwork["artistname"],artwork["albumname"])
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

                if not artwork.get("info") and lfmdetails.get("wiki"): artwork["info"] = lfmdetails["wiki"].get("content","").split(' <a')[0]
    
    #get album thumb from musicbrainz
    if not artwork.get("thumb") and not artwork.get("folder") and not WINDOW.getProperty("SkinHelper.TempDisableMusicBrainz"): 
        try: 
            new_file = "special://profile/addon_data/script.skin.helper.service/musicartcache/%s.jpg" %musicbrainzalbumid
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

def getCustomFolderPath(path, foldername):
    if "\\" in path: delim = "\\"
    else: delim = "/"
    dirs, files = xbmcvfs.listdir(path)
    pathfound = ""
    for strictness in [1, 0.95, 0.9, 0.8, 0.7]:
        for dir in dirs:
            dir = dir.decode("utf-8")
            curpath = os.path.join(path,dir) + delim
            match =  SM(None, foldername, dir).ratio()
            if match >= strictness: 
                return curpath
            elif not pathfound:
                pathfound = getCustomFolderPath(curpath,foldername)
            if pathfound: break
    return pathfound

def getSongDurationString(seconds):
    sec = timedelta(seconds=int(seconds))
    d = datetime(1,1,1) + sec
    if d.second < 10:
        secstr = "0%d" %d.second
    else:
        secstr = str(d.second)
    return "%d:%s" %(d.minute, secstr)
    
def getMusicArtwork(artistName, albumName="", trackName="", ignoreCache=False):
    if not artistName:
        return {}
    if albumName == trackName: trackName = ""
    if artistName == trackName: trackName = ""
    if not albumName and trackName: albumName = trackName
    if "/" in artistName and artistName.lower() != "ac/dc": artistName = artistName.split("/")[0]
    
    #GET FROM WINDOW CACHE FIRST
    cacheStr = try_encode(u"SkinHelper.Music.Cache-%s-%s-%s" %(artistName,albumName,trackName))
    cache = WINDOW.getProperty(cacheStr).decode("utf-8")
    if cache and not ignoreCache:
        logMsg("getMusicArtwork - return data from cache - artist: %s  - track: %s  -  album: %s" %(artistName,trackName,albumName))
        return eval(cache)
    else:
        logMsg("getMusicArtwork artist: %s  - track: %s  -  album: %s" %(artistName,trackName,albumName))
    
    albumartwork = {}
    path = ""
    path2 = ""
    artistCacheFound = False
    albumCacheFound = False
    artistpath = ""
    albumpath = ""
    artistOnly = False
    if not albumName: artistOnly = True
    localArtistMatch = False
    localAlbumMatch = False
    cacheStrAlbum = ""
    albumcache = None
    isCompilation = False
    if WINDOW.getProperty("SkinHelper.IgnoreCache"): ignoreCache = True

    enableMusicArtScraper = WINDOW.getProperty("SkinHelper.enableMusicArtScraper") == "true"
    downloadMusicArt = WINDOW.getProperty("SkinHelper.downloadMusicArt") == "true"
    allowoverwrite = WINDOW.getProperty("SkinHelper.preferOnlineMusicArt") == "true"
    enableLocalMusicArtLookup = WINDOW.getProperty("SkinHelper.enableLocalMusicArtLookup") == "true"
    custommusiclookuppath = WINDOW.getProperty("SkinHelper.custommusiclookuppath").decode("utf-8")

    ############# ALBUM DETAILS #########################
    if artistName and albumName:
        #get details from persistant cachefile to prevent online lookups
        albumartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicartcache/%s-%s.xml" %(normalize_string(artistName),normalize_string(albumName)))
        if albumartwork and not ignoreCache: 
            albumCacheFound = True
            logMsg("getMusicArtwork - return data from from persistant cache for album: %s" %albumName)
        else:
            #grab details from library for trackcounts etc.
            logMsg("getMusicArtwork - NO data in persistant cache for album: %s - starting lookup" %albumName)
            albumartwork = {}
            songcount = 0
            tracklist = []
            tracklistwithduration = []
            json_items = getJSON('AudioLibrary.GetAlbums','{ "filter": {"operator":"is", "field":"album", "value":"%s"}, "properties": [ "description","fanart","thumbnail","artistid","artist","musicbrainzalbumid","musicbrainzalbumartistid" ] }'%(albumName.replace("\"","\\" + "\"")))
            for strictmatch in [True, False]:
                for json_response in json_items:
                    if localAlbumMatch: break
                    if (strictmatch and artistName in json_response["artist"]) or not strictmatch or not artistName:
                        logMsg("getMusicArtwork found album details in Kodi DB for album %s - %s" %(albumName,json_response))
                        localAlbumMatch = True
                        if json_response.get("description") and not albumartwork.get("info"): albumartwork["info"] = json_response["description"]
                        if json_response.get("label") and not albumartwork.get("albumname"): albumartwork["albumname"] = json_response["label"]
                        if json_response.get("artist") and not albumartwork.get("artistname"): albumartwork["artistname"] = json_response["artist"][0]
                        if json_response.get("musicbrainzalbumid") and not albumartwork.get("musicbrainzalbumid"): albumartwork["musicbrainzalbumid"] = json_response["musicbrainzalbumid"]
                        albumid = json_response.get("albumid")
                        #get track listing for album
                        json_response2 = getJSON('AudioLibrary.GetSongs', '{ "properties": [ "file","track","title","duration" ], "sort": {"method":"track"}, "filter": { "albumid": %d}}'%(albumid))
                        for song in json_response2:
                            if not path: path = song["file"]
                            if song.get("track"): tracklist.append(u"[B]%s[/B] - %s" %(song["track"], song["title"]))
                            else: tracklist.append(song["title"])
                            if song.get("track"): tracklistwithduration.append(u"[B]%s[/B] - %s - %s" %(song["track"], song["title"], getSongDurationString(song["duration"])))
                            else: tracklistwithduration.append(u"%s - %s" %(song["title"], getSongDurationString(song["duration"])))
                            songcount += 1
                
            if not albumartwork.get("artistname"): albumartwork["artistname"] = artistName
            
            #make sure that our results are strings
            albumartwork["tracklist"] = u"[CR]".join(tracklist)
            albumartwork["tracklist.formatted"] = ""
            for trackitem in tracklist:
                albumartwork["tracklist.formatted"] += u"• %s[CR]" %trackitem
            albumartwork["tracklistwithduration"] = u"[CR]".join(tracklistwithduration)
            albumartwork["albumcount"] = "1"
            albumartwork["songcount"] = "%s"%songcount
            if isinstance(albumartwork.get("musicbrainzalbumid",""), list):
                albumartwork["musicbrainzalbumid"] = albumartwork["musicbrainzalbumid"][0]
   
    ############## ARTIST DETAILS #######################################
    
    #get details from persistant cachefile to prevent online lookups
    artistartwork = getArtworkFromCacheFile("special://profile/addon_data/script.skin.helper.service/musicartcache/%s.xml" %normalize_string(artistName))
    if artistartwork and not ignoreCache: 
        artistCacheFound = True
        logMsg("getMusicArtwork - return data from from persistant cache for artist: %s" %artistName)
    else:
        #grab details from library for trackcounts etc.
        logMsg("getMusicArtwork - NO data in persistant cache for artist: %s - starting lookup" %artistName)
        artistartwork = {}
        songcount = 0
        albumcount = 0
        albums = []
        albumsartist = []
        albumscompilations = []
        tracklist = []
        tracklistwithduration = []
        json_response = None
        json_response = getJSON('AudioLibrary.GetArtists', '{ "filter": {"operator":"is", "field":"artist", "value":"%s"}, "properties": [ "description","fanart","thumbnail","musicbrainzartistid" ] }'%artistName)
        if len(json_response) == 1:
            json_response = json_response[0]
            localArtistMatch = True
            logMsg("getMusicArtwork found artist details in Kodi DB for artist %s ---> %s" %(artistName,json_response))
            if json_response.get("description") and not artistartwork.get("info"): artistartwork["info"] = json_response["description"]
            if json_response.get("fanart") and xbmcvfs.exists(getCleanImage(json_response["fanart"])): artistartwork["fanart"] = getCleanImage(json_response["fanart"])
            if json_response.get("thumbnail") and xbmcvfs.exists(getCleanImage(json_response["thumbnail"])) : artistartwork["folder"] = getCleanImage(json_response["thumbnail"])
            if json_response.get("label") and not artistartwork.get("artistname",""): artistartwork["artistname"] = json_response["label"]
            if json_response.get("musicbrainzartistid") and not artistartwork.get("musicbrainzartistid"): artistartwork["musicbrainzartistid"] = json_response["musicbrainzartistid"]
            #get track/album listing for artist
            json_response2 = None
            json_response2 = getJSON('AudioLibrary.GetSongs', '{ "filter":{"artistid": %d}, "properties": [ "file","track","title","duration","musicbrainzartistid","album","artist","albumartistid" ] }'%(json_response.get("artistid")))
            for song in json_response2:
                tracklist.append(song["title"])
                tracklistwithduration.append(u"%s - %s" %(song["title"], getSongDurationString(song["duration"])))
                songcount += 1
                if len(song.get("artist")) > 1 and not albumName and not trackName:
                    # skip multi artist song in artist listing
                    continue
                if not trackName: trackName = song.get("label","")
                if song.get("albumartistid") and song.get("file") and json_response["artistid"] in song["albumartistid"] and not path2:
                    #set additional path to prevent artist lookups in compilations
                    path2 = song.get("file")
                if song.get("album"):
                    if not path and song.get("file"):
                        path = song.get("file")
                    if not albumName: albumName = song.get("album")
                    if song.get("musicbrainzartistid") and not artistartwork.get("musicbrainzartistid"): artistartwork["musicbrainzartistid"] = song["musicbrainzartistid"]
                    if song["album"] not in albums:
                        albumcount +=1
                        albums.append(song["album"])
                        if song.get("albumartistid") and json_response["artistid"] in song["albumartistid"]:
                            albumsartist.append(song["album"])
                        else:
                            albumscompilations.append(song["album"])
            
            #make sure that our results are strings
            artistartwork["albums"] = u"[CR]".join(albums)
            artistartwork["albumsartist"] = u"[CR]".join(albumsartist)
            artistartwork["albumscompilations"] = u"[CR]".join(albumscompilations)
            artistartwork["albums.formatted"] = ""
            for albumitem in albums:
                artistartwork["albums.formatted"] += u"• %s[CR]" %albumitem
            artistartwork["tracklist.formatted"] = ""
            for trackitem in tracklist:
                artistartwork["tracklist.formatted"] += u"• %s[CR]" %trackitem
            artistartwork["tracklist"] = u"[CR]".join(tracklist)
            artistartwork["tracklistwithduration"] = u"[CR]".join(tracklistwithduration)
            artistartwork["albumcount"] = "%s"%albumcount
            artistartwork["songcount"] = "%s"%songcount
            artistartwork["AlbumsArtistCount"] = str(len(albumsartist))
            artistartwork["AlbumsCompilationsCount"] = str(len(albumscompilations))
            if not albumartwork.get("artistname"): albumartwork["artistname"] = artistName
            if not albumartwork.get("albumname"): albumartwork["albumname"] = albumName
            if isinstance(artistartwork.get("musicbrainzartistid",""), list):
                artistartwork["musicbrainzartistid"] = artistartwork["musicbrainzartistid"][0]
            
    #LOOKUP ART IN CUSTOM FOLDER
    if custommusiclookuppath and (not artistCacheFound or (albumName and not albumCacheFound)):
        if "\\" in custommusiclookuppath: delim = "\\"
        else: delim = "/"
        
        #try to locate the artist folder recursively...
        artist_path = getCustomFolderPath(custommusiclookuppath, artistName)
        if artist_path:
            #lookup local artist artwork
            logMsg("getMusicArtwork - lookup artwork in custom folder for artist: %s - using path: %s" %(artistName,artist_path))
            artistartwork["custompath"] = artist_path
            for artType in KodiArtTypes:
                artpath = os.path.join(artist_path,artType[1])
                if xbmcvfs.exists(artpath) and not artistartwork.get(artType[0]):
                    artistartwork[artType[0]] = artpath
                    logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],artistName))
            #lookup local album artwork
            if albumName:
                album_path = getCustomFolderPath(artist_path, albumName)
                if xbmcvfs.exists(album_path):
                    #get sublevels (if disclevel in use)...
                    dirs, files = xbmcvfs.listdir(album_path)
                    albumpaths = [album_path]
                    for dir in dirs:
                        albumpaths.append(os.path.join(album_path,dir.decode("utf-8")) + delim)
                    for album_path in albumpaths:
                        logMsg("getMusicArtwork - lookup artwork in custom folder for album: %s - using path: %s" %(albumName,album_path))
                        albumartwork["custompath"] = album_path
                        #lookup existing artwork in the paths
                        for artType in KodiArtTypes:
                            artpath = os.path.join(album_path,artType[1])
                            if xbmcvfs.exists(artpath) and not albumartwork.get(artType[0]):
                                albumartwork[artType[0]] = artpath
                                logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],albumName))
                else:
                    logMsg("getMusicArtwork - lookup artwork in custom folder SKIPPED for album: %s - using path: %s -- path not found!" %(albumName,album_path))
        else:
            logMsg("getMusicArtwork - lookup artwork in custom folder SKIPPED for artist: %s -- path not found in custom music artwork folder!" %(artistName))
            
    #LOOKUP LOCAL ARTWORK PATH PASED ON SONG FILE PATH
    if (path or path2) and enableLocalMusicArtLookup and (not artistCacheFound or (albumName and not albumCacheFound)):
        if "\\" in path: delim = "\\"
        else: delim = "/"
        
        #determine ARTIST folder structure (there might be a disclevel too...)
        #just move up the directory tree (max 3 levels) untill we find artist artwork
        if localArtistMatch and path2:
            if "\\" in path2: delim = "\\"
            else: delim = "/"
            for trypath in [path2.rsplit(delim, 2)[0] + delim, path2.rsplit(delim, 3)[0] + delim, path2.rsplit(delim, 1)[0] + delim]:
                logMsg("getMusicArtwork - lookup path %s" %trypath)
                for item in ["artist.nfo","banner.jpg","fanart.jpg","logo.png","extrafanart/"]:
                    artpath = os.path.join(trypath,item)
                    if xbmcvfs.exists(artpath):
                        artistpath = trypath
                        break
                if artistpath: break
            
        #lookup local artist artwork
        if artistpath:
            logMsg("getMusicArtwork - lookup artwork on disk for artist: %s - using path: %s" %(artistName,artistpath))
            artistartwork["path"] = artistpath
            for artType in KodiArtTypes:
                artpath = os.path.join(artistpath,artType[1])
                if xbmcvfs.exists(artpath) and not artistartwork.get(artType[0]):
                    artistartwork[artType[0]] = artpath
                    logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],artistName))
        else:
            logMsg("getMusicArtwork - lookup artist artwork on disk skipped for %s - not correct folder structure or no artwork found" %artistartwork.get("artistname",""))
        
        #determine ALBUM folder structure (there might be a disclevel too...)
        #just move up the directory tree (max 2 levels) untill we find album artwork
        if albumName:
            if "\\" in path: delim = "\\"
            else: delim = "/"
            for trypath in [path.rsplit(delim, 1)[0] + delim, path.rsplit(delim, 2)[0] + delim]:
                logMsg("getMusicArtwork - lookup path %s" %trypath)
                for item in ["album.nfo","disc.png","cdart.png"]:
                    artpath = os.path.join(trypath,item)
                    if xbmcvfs.exists(artpath):
                        albumpath = trypath
                        break
                if albumpath: break
            
            #lookup local album artwork
            if albumpath:
                logMsg("getMusicArtwork - lookup artwork on disk for album: %s - found path: %s" %(albumName,albumpath))
                albumartwork["path"] = albumpath
                for artType in KodiArtTypes:
                    artpath = os.path.join(albumpath,artType[1])
                    if xbmcvfs.exists(artpath) and not albumartwork.get(artType[0]):
                        albumartwork[artType[0]] = artpath
                        logMsg("getMusicArtwork - %s found on disk for %s" %(artType[0],albumName))
            else:
                logMsg("getMusicArtwork - lookup album artwork on disk skipped for %s - not correct folder structure or no artwork found" %albumName)
                  
    #online lookup for details
    if enableMusicArtScraper and (not artistCacheFound or (albumName and not albumCacheFound)):
        
        if WINDOW.getProperty("SkinHelperShutdownRequested"):
            return {}
        
        #lookup details in musicbrainz
        #retrieve album id and artist id with a combined query of album name, track name and artist name to get an accurate result
        if not albumartwork.get("musicbrainzalbumid") or not artistartwork.get("musicbrainzartistid") or ignoreCache:
            musicbrainzartistid, musicbrainzalbumid = getMusicBrainzId(artistName,albumName,trackName)
            if not albumartwork.get("musicbrainzalbumid") or ignoreCache: 
                albumartwork["musicbrainzalbumid"] = musicbrainzalbumid
            if not artistartwork.get("musicbrainzartistid") or ignoreCache: 
                artistartwork["musicbrainzartistid"] = musicbrainzartistid

        ########################################################## ARTIST LEVEL #########################################################
        if artistartwork.get("musicbrainzartistid") and not artistCacheFound:
            artistartwork = getArtistArtwork(artistartwork.get("musicbrainzartistid"), artistartwork, allowoverwrite)
            #download images if we want them local
            if artistartwork.get("custompath"):
                artistpath = artistartwork["custompath"]
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
                elif not artistartwork.get("extrafanart"): artistartwork["extrafanart"] = "plugin://script.skin.helper.service/?action=EXTRAFANART&path=special://profile/addon_data/script.skin.helper.service/musicartcache/%s.xml" %normalize_string(artistName)
            
        ######################################################### ALBUM LEVEL #########################################################    
        if albumName and albumartwork.get("musicbrainzalbumid") and not albumCacheFound:
            albumartwork = getAlbumArtwork(albumartwork.get("musicbrainzalbumid"), albumartwork, allowoverwrite)
            
            #download images if we want them local
            if downloadMusicArt and albumpath and localAlbumMatch:
                for artType in KodiArtTypes:
                    if albumartwork.has_key(artType[0]): albumartwork[artType[0]] = downloadImage(albumartwork[artType[0]],albumpath,artType[1],allowoverwrite)
        
    #write to persistant cache
    if artistartwork and not artistCacheFound:
        if artistartwork.get("folder") and not artistartwork.get("thumb"): artistartwork["thumb"] = artistartwork.get("folder")
        if artistartwork.get("info"): artistartwork["info"] = artistartwork["info"].replace('\n', ' ').replace('\r', '')
        artistartwork["artistthumb"] = artistartwork.get("thumb","")
        createNFO("special://profile/addon_data/script.skin.helper.service/musicartcache/%s.xml" %normalize_string(artistName),artistartwork)
    if albumartwork and albumName and not artistOnly and not albumCacheFound:
        if albumartwork.get("folder") and not albumartwork.get("thumb"): albumartwork["thumb"] = albumartwork.get("folder")
        if albumartwork.get("info"): albumartwork["info"] = albumartwork["info"].replace('\n', ' ').replace('\r', '')
        if not cacheStrAlbum: cacheStrAlbum = "SkinHelper.Music.Cache-%s-%s" %(artistName.lower(),albumName.lower())
        albumartwork["albumthumb"] = albumartwork.get("thumb","")
        createNFO("special://profile/addon_data/script.skin.helper.service/musicartcache/%s-%s.xml" %(normalize_string(artistName),normalize_string(albumName)),albumartwork)
            
    #return the results...    
    artwork = artistartwork
    #combine album info with artist info
    if artistartwork.get("info") and albumartwork.get("info") and not artistOnly:
        artwork["info"] = albumartwork["info"] + "  ---  " + artistartwork["info"]
    #return artwork combined
    if albumartwork and not artistOnly:
        for key, value in albumartwork.iteritems():
            if value and key != "info": artwork[key] = value
            
    #save to cache
    WINDOW.setProperty(cacheStr,repr(artwork))
    
    return artwork
    
def updateMusicArt(type,id):
    #called when music library changed
    while WINDOW.getProperty("updateMusicArt.busy"):
        #only allow 1 update at a time to prevent hitting the API's to fast or run into buffer overruns
        xbmc.sleep(150)
        
    WINDOW.setProperty("updateMusicArt.busy","busy")
    if type == "song" and id:
        item = getJSON('AudioLibrary.GetSongDetails','{ "songid": %s, "properties": [ "title","album","artist" ] }' %id)
        if item and item.get("title"):
            logMsg("updateMusicArt - update detected for song " + item["title"])
            for artist in item["artist"]:
                getMusicArtwork(artist,item["album"],item["title"],True)
    elif type == "artist" and id:
        item = getJSON('AudioLibrary.GetArtistDetails','{ "artistid": %s }' %id)
        logMsg("updateMusicArt - update detected for artist " + item["label"])
        getMusicArtwork(item["label"],"","",True)
    elif type == "album" and id:
        item = getJSON('AudioLibrary.GetAlbumDetails','{ "albumid": %s, "properties": [ "title","artist" ] }' %id)
        logMsg("updateMusicArt - update detected for album " + item["title"])
        for artist in item["artist"]:
            getMusicArtwork(artist,item["title"],"",True)
    WINDOW.clearProperty("updateMusicArt.busy")
        
    
