#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmcplugin, xbmcgui, xbmc, xbmcaddon, xbmcvfs
import os,sys
import urllib
from traceback import print_exc
from datetime import datetime
import _strptime
import time
import datetime as dt
import unicodedata
import urlparse
import xml.etree.ElementTree as xmltree

try:
    import simplejson as json
except:
    import json

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)
SETTING = ADDON.getSetting
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)

fields_base = '"dateadded", "file", "lastplayed","plot", "title", "art", "playcount",'
fields_file = fields_base + '"streamdetails", "director", "resume", "runtime",'
fields_movies = fields_file + '"plotoutline", "sorttitle", "cast", "votes", "showlink", "top250", "trailer", "year", "country", "studio", "set", "genre", "mpaa", "setid", "rating", "tag", "tagline", "writer", "originaltitle", "imdbnumber"'
fields_tvshows = fields_base + '"sorttitle", "mpaa", "premiered", "year", "episode", "watchedepisodes", "votes", "rating", "studio", "season", "genre", "cast", "episodeguide", "tag", "originaltitle", "imdbnumber"'
fields_episodes = fields_file + '"cast", "productioncode", "rating", "votes", "episode", "showtitle", "tvshowid", "season", "firstaired", "writer", "originaltitle"'
fields_musicvideos = fields_file + '"genre", "artist", "tag", "album", "track", "studio", "year"'
fields_files = fields_file + fields_movies + ", " + fields_tvshows + ", " + fields_episodes
fields_songs = '"artist", "title", "rating", "fanart", "thumbnail", "duration", "playcount", "comment", "file", "album", "lastplayed", "genre"'
fields_albums = '"title", "fanart", "thumbnail", "genre", "displayartist", "artist", "genreid", "musicbrainzalbumartistid", "year", "rating", "artistid", "musicbrainzalbumid", "theme", "description", "type", "style", "playcount", "albumlabel", "mood"'
fields_pvrrecordings = '"art", "channel", "directory", "endtime", "file", "genre", "icon", "playcount", "plot", "plotoutline", "resume", "runtime", "starttime", "streamurl", "title"'
KodiArtTypes = [ ("thumb","thumb.jpg"),("poster","poster.jpg"),("fanart","fanart.jpg"),("banner","banner.jpg"),("landscape","landscape.jpg"),("clearlogo","logo.png"),("clearart","clearart.png"),("channellogo","channellogo.png"),("discart","disc.png"),("discart","cdart.png"),("extrafanart","extrafanart/"),("characterart","characterart.png"),("folder","folder.jpg") ]

def logMsg(msg, level = 1):
    if WINDOW.getProperty("SkinHelper.enableDebugLog") == "true" or level == 0:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        if "exception" in msg.lower() or "error" in msg.lower():
            xbmc.log("Skin Helper Service --> " + msg, level=xbmc.LOGERROR)
            print_exc()
        else: 
            xbmc.log("Skin Helper Service --> " + msg, level=xbmc.LOGNOTICE)
                   
def getContentPath(libPath):
    if "$INFO" in libPath and not "reload=" in libPath:
        libPath = libPath.replace("$INFO[Window(Home).Property(", "")
        libPath = libPath.replace(")]", "")
        libPath = WINDOW.getProperty(libPath)    
    if "Activate" in libPath:
        if "ActivateWindow(MusicLibrary," in libPath:
            libPath = libPath.replace("ActivateWindow(MusicLibrary," ,"musicdb://").lower()
            libPath = libPath.replace(",return","/")
            libPath = libPath.replace(", return","/")
        else:
            libPath = libPath.split(",",1)[1]
            libPath = libPath.replace(",return","")
            libPath = libPath.replace(", return","")
        
        libPath = libPath.replace(")","")
        libPath = libPath.replace("\"","")
        libPath = libPath.replace("musicdb://special://","special://")
        libPath = libPath.replace("videodb://special://","special://")
    if "&reload=" in libPath:
        libPath = libPath.split("&reload=")[0]
    return libPath

def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, try_encode(params)))
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        jsonobject = jsonobject['result']
        if isinstance(jsonobject, list):
            return jsonobject
        if jsonobject.has_key('files'):
            return jsonobject['files']
        elif jsonobject.has_key('movies'):
            return jsonobject['movies']
        elif jsonobject.has_key('tvshows'):
            return jsonobject['tvshows']
        elif jsonobject.has_key('episodes'):
            return jsonobject['episodes']
        elif jsonobject.has_key('musicvideos'):
            return jsonobject['musicvideos']
        elif jsonobject.has_key('channels'):
            return jsonobject['channels']
        elif jsonobject.has_key('recordings'):
            return jsonobject['recordings']
        elif jsonobject.has_key('timers'):
            return jsonobject['timers']
        elif jsonobject.has_key('channeldetails'):
            return jsonobject['channeldetails']    
        elif jsonobject.has_key('songs'):
            return jsonobject['songs']
        elif jsonobject.has_key('albums'):
            return jsonobject['albums']
        elif jsonobject.has_key('songdetails'):
            return jsonobject['songdetails']
        elif jsonobject.has_key('albumdetails'):
            return jsonobject['albumdetails']
        elif jsonobject.has_key('artistdetails'):
            return jsonobject['artistdetails']
        elif jsonobject.has_key('favourites'):
            if jsonobject['favourites']:
                return jsonobject['favourites']
            else:
                return {}
        elif jsonobject.has_key('tvshowdetails'):
            return jsonobject['tvshowdetails']
        elif jsonobject.has_key('episodedetails'):
            return jsonobject['episodedetails']
        elif jsonobject.has_key('moviedetails'):
            return jsonobject['moviedetails']
        elif jsonobject.has_key('setdetails'):
            return jsonobject['setdetails']
        elif jsonobject.has_key('sets'):
            return jsonobject['sets']
        elif jsonobject.has_key('video'):
            return jsonobject['video']
        elif jsonobject.has_key('artists'):
            return jsonobject['artists']
        elif jsonobject.has_key('channelgroups'):
            return jsonobject['channelgroups']
        elif jsonobject.has_key('sources'):
            if jsonobject['sources']:
                return jsonobject['sources']
            else:
                return {}
        elif jsonobject.has_key('addons'):
            return jsonobject['addons']
        elif jsonobject.has_key('item'):
            return jsonobject['item']
        elif jsonobject.has_key('genres'):
            return jsonobject['genres']
        else:
            logMsg("getJson - invalid result for Method %s - params: %s - response: %s" %(method,params, str(jsonobject))) 
            return {}
    else:
        logMsg("getJson - empty result for Method %s - params: %s - response: %s" %(method,params, str(jsonobject))) 
        return {}

def setAddonsettings():
    if not xbmcvfs.exists(SETTING("pvrthumbspath")):
        xbmcvfs.mkdirs(SETTING("pvrthumbspath"))
    if not xbmcvfs.exists("special://profile/addon_data/script.skin.helper.service/musicart/"):
        xbmcvfs.mkdirs("special://profile/addon_data/script.skin.helper.service/musicart/")
    #get the addonsettings and store them in memory
    WINDOW.setProperty("SkinHelper.pvrthumbspath",SETTING("pvrthumbspath"))
    WINDOW.setProperty("SkinHelper.cacheRecordings",SETTING("cacheRecordings"))
    WINDOW.setProperty("SkinHelper.cacheGuideEntries",SETTING("cacheGuideEntries"))
    WINDOW.setProperty("SkinHelper.customRecordingsPath",SETTING("customRecordingsPath"))
    WINDOW.setProperty("SkinHelper.useTMDBLookups",SETTING("useTMDBLookups"))
    WINDOW.setProperty("SkinHelper.useGoogleLookups",SETTING("useGoogleLookups"))
    WINDOW.setProperty("SkinHelper.useYoutubeLookups",SETTING("useYoutubeLookups"))
    WINDOW.setProperty("SkinHelper.useLocalLibraryLookups",SETTING("useLocalLibraryLookups"))
    WINDOW.setProperty("SkinHelper.customlookuppath",SETTING("customlookuppath"))
    WINDOW.setProperty("SkinHelper.useFanArtTv",SETTING("useFanArtTv"))
    WINDOW.setProperty("SkinHelper.ignorechannels",SETTING("ignorechannels"))
    WINDOW.setProperty("SkinHelper.ignoretitles",SETTING("ignoretitles"))
    WINDOW.setProperty("SkinHelper.stripwords",SETTING("stripwords"))
    WINDOW.setProperty("SkinHelper.directory_structure",SETTING("directory_structure"))
    WINDOW.setProperty("SkinHelper.lastUpdate","%s" %datetime.now())    
    WINDOW.setProperty("SkinHelper.enablewallbackgrounds",SETTING("enablewallbackgrounds"))
    WINDOW.setProperty("SkinHelper.preferBWwallbackgrounds",SETTING("preferBWwallbackgrounds"))
    WINDOW.setProperty("SkinHelper.enableMusicArtScraper",SETTING("enableMusicArtScraper"))
    WINDOW.setProperty("SkinHelper.downloadMusicArt",SETTING("downloadMusicArt"))
    WINDOW.setProperty("SkinHelper.enableLocalMusicArtLookup",SETTING("enableLocalMusicArtLookup"))
    WINDOW.setProperty("SkinHelper.enableDebugLog",SETTING("enableDebugLog"))
    WINDOW.setProperty("SkinHelper.maxNumFanArts",SETTING("maxNumFanArts"))
    WINDOW.setProperty("SkinHelper.splittitlechar",SETTING("splittitlechar"))
    WINDOW.setProperty("SkinHelper.enablePVRThumbsRecordingsOnly",SETTING("enablePVRThumbsRecordingsOnly"))
    
def indentXML( elem, level=0 ):
    i = "\n" + level*"\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indentXML(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding,"ignore")
    except:
        return text       

def try_decode(text, encoding="utf-8"):
    try:
        return text.decode(encoding,"ignore")
    except:
        return text       
         
def setSkinVersion():
    try:
        skin = xbmc.getSkinDir()
        skinLabel = xbmcaddon.Addon(id=skin).getAddonInfo('name')
        skinVersion = xbmcaddon.Addon(id=skin).getAddonInfo('version')
        WINDOW.setProperty("SkinHelper.skinTitle",skinLabel + " - " + xbmc.getLocalizedString(19114) + ": " + skinVersion)
        WINDOW.setProperty("SkinHelper.skinVersion",xbmc.getLocalizedString(19114) + ": " + skinVersion)
        WINDOW.setProperty("SkinHelper.Version",ADDON_VERSION.replace(".",""))
    except Exception as e:
        logMsg("Error in setSkinVersion --> " + str(e), 0)
    
def createListItem(item):

    itemtype = "Video"
    if "type" in item:
        if "artist" in item["type"] or "song" in item["type"] or "album" in item["type"]:
            itemtype = "Music"

    liz = xbmcgui.ListItem(item['title'])
    liz.setInfo( type=itemtype, infoLabels={ "Title": item['title'] })
    liz.setProperty('IsPlayable', 'true')
    season = None
    episode = None
    
    if "duration" in item:
        liz.setInfo( type=itemtype, infoLabels={ "duration": item['duration'] })
    
    if "runtime" in item:
        liz.setInfo( type=itemtype, infoLabels={ "duration": item['runtime'] })
    
    if "file" in item:
        liz.setPath(item['file'])
        liz.setProperty("path", item['file'])
    
    if "episode" in item:
        episode = "%.2d" % float(item['episode'])
        liz.setInfo( type=itemtype, infoLabels={ "Episode": item['episode'] })
    
    if "season" in item:
        season = "%.2d" % float(item['season'])
        liz.setInfo( type=itemtype, infoLabels={ "Season": item['season'] })
        
    if season and episode:
        episodeno = "s%se%s" %(season,episode)
        liz.setProperty("episodeno", episodeno)
    
    if "episodeid" in item:
        liz.setProperty("DBID", str(item['episodeid']))
        if not item.get("type"): item["type"] = "episode"
        liz.setIconImage('DefaultTVShows.png')
        
    if "tvshowid" in item and not "episodeid" in item:
        liz.setProperty("DBID", str(item['tvshowid']))
        if not item.get("type"): item["type"] = "tvshow"
        liz.setInfo( type=itemtype, infoLabels={ "TvShowTitle": item['label'] })
        liz.setIconImage('DefaultTVShows.png')
        
    if "songid" in item:
        liz.setProperty("DBID", str(item['songid']))
        if not item.get("type"): item["type"] = "song"
        liz.setIconImage('DefaultAudio.png')
        
    if "movieid" in item:
        liz.setProperty("DBID", str(item['movieid']))
        if not item.get("type"): item["type"] = "movie"
        liz.setIconImage('DefaultMovies.png')
    
    if "musicvideoid" in item:
        liz.setProperty("DBID", str(item['musicvideoid']))
        if not item.get("type"): item["type"] = "musicvideo"
        liz.setIconImage('DefaultMusicVideos.png')
    
    if "type" in item:
        liz.setProperty("type", item['type'])
        liz.setProperty("dbtype", item['type'])
        
    if "extraproperties" in item:
        if isinstance(item["extraproperties"],dict):
            for key,value in item["extraproperties"].iteritems():
                liz.setProperty(key, value)
    if "plot" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Plot": item['plot'] })
        
    if "imdbnumber" in item:
        liz.setInfo( type=itemtype, infoLabels={ "imdbnumber": item['imdbnumber'] })
        liz.setProperty("imdbnumber", str(item['imdbnumber']))
    
    if "album_description" in item:
        liz.setProperty("Album_Description",item['album_description'])
    
    if "artist" in item:
        if itemtype == "Music":
            liz.setInfo( type=itemtype, infoLabels={ "Artist": " / ".join(item['artist']) })
        else:
            liz.setInfo( type=itemtype, infoLabels={ "Artist": item['artist'] })
        
    if "votes" in item:
        liz.setInfo( type=itemtype, infoLabels={ "votes": item['votes'] })
    
    if "trailer" in item:
        liz.setInfo( type=itemtype, infoLabels={ "trailer": item['trailer'] })
        liz.setProperty("trailer", item['trailer'])
        
    if "dateadded" in item:
        liz.setInfo( type=itemtype, infoLabels={ "dateadded": item['dateadded'] })
        
    if "album" in item:
        liz.setInfo( type=itemtype, infoLabels={ "album": item['album'] })
        
    if "plotoutline" in item:
        liz.setInfo( type=itemtype, infoLabels={ "plotoutline ": item['plotoutline'] })
        
    if "studio" in item:
        liz.setInfo( type=itemtype, infoLabels={ "studio": " / ".join(item['studio']) })
        
    if "playcount" in item:
        liz.setInfo( type=itemtype, infoLabels={ "playcount": item['playcount'] })
        
    if "mpaa" in item:
        liz.setInfo( type=itemtype, infoLabels={ "mpaa": item['mpaa'] })
        
    if "tagline" in item:
        liz.setInfo( type=itemtype, infoLabels={ "tagline": item['tagline'] })
    
    if "showtitle" in item:
        liz.setInfo( type=itemtype, infoLabels={ "TVshowTitle": item['showtitle'] })
    
    if "rating" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Rating": str(round(float(item['rating']),1)) })
    
    if "playcount" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Playcount": item['playcount'] })
    
    if "director" in item:
        director = item['director']
        if isinstance(director, list): director = " / ".join(director)
        liz.setInfo( type=itemtype, infoLabels={ "Director": director })
    
    if "writer" in item:
        writer = item['writer']
        if isinstance(writer, list): writer = " / ".join(writer)
        liz.setInfo( type=itemtype, infoLabels={ "Writer": writer })
    
    if "genre" in item:
        genre = item['genre']
        if isinstance(genre, list): genre = " / ".join(genre)
        liz.setInfo( type=itemtype, infoLabels={ "genre": genre })
        
    if "year" in item:
        liz.setInfo( type=itemtype, infoLabels={ "year": item['year'] })
    
    if "firstaired" in item:
        liz.setInfo( type=itemtype, infoLabels={ "premiered": item['firstaired'] })

    if "premiered" in item:
        liz.setInfo( type=itemtype, infoLabels={ "premiered": item['premiered'] })
        
    if "cast" in item:
        if item["cast"]:
            listCast = []
            listCastAndRole = []
            for castmember in item["cast"]:
                listCast.append( castmember["name"] )
                listCastAndRole.append( (castmember["name"], castmember["role"]) ) 
            cast = [listCast, listCastAndRole]
            liz.setInfo( type=itemtype, infoLabels={ "Cast": cast[0] })
            liz.setInfo( type=itemtype, infoLabels={ "CastAndRole": cast[1] })
    
    if "resume" in item:
        liz.setProperty("resumetime", str(item['resume']['position']))
        liz.setProperty("totaltime", str(item['resume']['total']))
    
    if "art" in item:
        art = item['art']
        if art and not art.get("fanart") and art.get("tvshow.fanart"):
            art["fanart"] = art.get("tvshow.fanart")
        if art and not art.get("poster") and art.get("tvshow.poster"):
            art["poster"] = art.get("tvshow.poster")
        if art and not art.get("clearlogo") and art.get("tvshow.clearlogo"):
            art["clearlogo"] = art.get("tvshow.clearlogo")
        if art and not art.get("landscape") and art.get("tvshow.landscape"):
            art["landscape"] = art.get("tvshow.landscape")
        thumb = None
        if item['art'].get('thumb',''): thumb = item['art'].get('thumb','')
        elif item.get('icon',''): thumb = item.get('icon','')
        elif item['art'].get('poster',''): thumb = item['art'].get('poster','')
        liz.setThumbnailImage(thumb)
    else:
        art = []
        if "fanart" in item:
            art.append(("fanart",item["fanart"]))
        if "thumbnail" in item:
            art.append(("thumb",item["thumbnail"]))
            liz.setThumbnailImage(item["thumbnail"])
        elif "icon" in item:
            art.append(("thumb",item["icon"]))
            liz.setIconImage(item["icon"])
    liz.setArt(art)
    
    hasVideoStream = False
    if "streamdetails" in item:
        for key, value in item['streamdetails'].iteritems():
            for stream in value:
                if 'video' in key: hasVideoStream = True
                liz.addStreamInfo(key, stream)
    
    if item.get('streamdetails2',''):
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
                liz.setProperty("VideoResolution", resolution)
            if stream.get("codec",""):
                liz.setProperty("VideoCodec", str(stream["codec"]))    
            if stream.get("aspect",""):
                liz.setProperty("VideoAspect", str(round(stream["aspect"], 2))) 
        if len(audiostreams) > 0:
            #grab details of first audio stream
            stream = audiostreams[0]
            liz.setProperty("AudioCodec", stream.get('codec',''))
            liz.setProperty("AudioChannels", str(stream.get('channels','')))
            liz.setProperty("AudioLanguage", stream.get('language',''))
        if len(subtitles) > 0:
            #grab details of first subtitle
            liz.setProperty("SubtitleLanguage", subtitles[0].get('language',''))
    
    
    if not hasVideoStream and "runtime" in item:
        stream = {'duration': item['runtime']}
        liz.addStreamInfo("video", stream)
    
    #pvr properties
    if "progresspercentage" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Progress": item['progresspercentage'] })
    if "starttime" in item:
        starttime = getLocalDateTimeFromUtc(item['starttime'])
        liz.setProperty("StartTime", starttime[1])
        liz.setProperty("StartDate", starttime[0])
        endtime = getLocalDateTimeFromUtc(item['endtime'])
        liz.setProperty("EndTime", endtime[1])
        liz.setProperty("EndDate", endtime[0])
        fulldate = starttime[0] + " " + starttime[1] + "-" + endtime[1]
        liz.setProperty("Date",fulldate )
    if "channellogo" in item:
        liz.setProperty("ChannelIcon", item['channellogo'])
        liz.setProperty("ChannelLogo", item['channellogo'])
    if "episodename" in item:
        liz.setProperty("EpisodeName", item['episodename'])
        liz.setInfo( type=itemtype, infoLabels={ "EpisodeName": item['episodename'] })
    if "channel" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Channel": item['channel'] })
        liz.setInfo( type=itemtype, infoLabels={ "ChannelName": item['channel'] })
        liz.setProperty("ChannelName", item['channel'])
        liz.setProperty("Channel", item['channel'])
        liz.setLabel2(item['channel'])
        
    return liz
    
def detectPluginContent(plugin,skipscan=False):
    #based on the properties in the listitem we try to detect the content
    logMsg("detectPluginContent processing: " + plugin)
    image = None
    contentType = None
    #load from cache first
    cache = WINDOW.getProperty("skinhelper-widgetcontenttype").decode("utf-8")
    if cache:
        cache = eval(cache)
        if cache and cache.get(plugin):
            contentType = cache[plugin][0]
            image = cache[plugin][1]
            logMsg("detectPluginContent cache found for: " + plugin)
            return (contentType, image)
    else: cache = {}
        
    #probe path to determine content
    if not contentType:
        logMsg("detectPluginContent cache NOT found for: " + plugin)
        #safety check: check if no library windows are active to prevent any addons setting the view
        curWindow = xbmc.getInfoLabel("$INFO[Window.Property(xmlfile)]")
        if curWindow.endswith("Nav.xml") or curWindow == "AddonBrowser.xml" or curWindow.startswith("MyPVR"):
            skipScan = True
        
        if not skipscan:
            media_array = getJSON('Files.GetDirectory','{ "directory": "%s", "media": "files", "properties": ["title", "file", "thumbnail", "episode", "showtitle", "season", "album", "artist", "imdbnumber", "firstaired", "mpaa", "trailer", "studio", "art"], "limits": {"end":1} }' %plugin)
            if not media_array: contentType="empty"
            for item in media_array:
                if item.has_key("art") and not image:
                    if item["art"].has_key("fanart") and not image:
                        image = item["art"]["fanart"]
                    elif item["art"].has_key("tvshow.fanart") and not image:
                        image = item["art"]["tvshow.fanart"]
                    elif item["art"].has_key("thumb") and not image:
                        image = item["art"]["thumb"]
                    elif item.has_key("fanart_image") and not image:
                        image = item["fanart_image"]
                    elif item.has_key("thumbnail") and not image:
                        image = item["thumbnail"]
                if not item.has_key("showtitle") and not item.has_key("artist"):
                    #these properties are only returned in the json response if we're looking at actual file content...
                    # if it's missing it means this is a main directory listing and no need to scan the underlying listitems.
                    contentType = "files"
                    break
                if not item.has_key("showtitle") and item.has_key("artist"):
                    ##### AUDIO ITEMS ####
                    if item["type"] == "artist":
                        contentType = "artists"
                        break
                    elif isinstance(item["artist"], list) and len(item["artist"]) > 0 and item["artist"][0] == item["title"]:
                        contentType = "artists"
                        break
                    elif item["type"] == "album" or item["album"] == item["title"]:
                        contentType = "albums"
                        break
                    elif (item["type"] == "song" and not "play_album" in item["file"]) or (item["artist"] and item["album"]):
                        contentType = "songs"
                        break
                else:    
                    ##### VIDEO ITEMS ####
                    if (item["showtitle"] and not item["artist"]):
                        #this is a tvshow, episode or season...
                        if item["type"] == "season" or (item["season"] > -1 and item["episode"] == -1):
                            contentType = "seasons"
                            break
                        elif item["type"] == "episode" or item["season"] > -1 and item["episode"] > -1:
                            contentType = "episodes"
                            break
                        else:
                            contentType = "tvshows"
                            break
                    elif (item["artist"]):
                        #this is a musicvideo!
                        contentType = "musicvideos"
                        break
                    elif item["type"] == "movie" or item["imdbnumber"] or item["mpaa"] or item["trailer"] or item["studio"]:
                        contentType = "movies"
                        break
    
        #last resort or skipscan chosen - detect content based on the path
        if not contentType:
            if "movie" in plugin or "box" in plugin or "dvd" in plugin or "rentals" in plugin:
                contentType = "movies"
            elif "album" in plugin:
                contentType = "albums"
            elif "show" in plugin:
                contentType = "tvshows"
            elif "song" in plugin:
                contentType = "songs"
            elif "musicvideo" in plugin:
                contentType = "musicvideos"
            else:
                contentType = "unknown"
            
        #save to cache
        logMsg("detectPluginContent detected type for: %s is: %s " %(plugin,contentType))
        cache[plugin] = (contentType,image)
        cache = repr(cache)
        if contentType != "empty": 
            WINDOW.setProperty("skinhelper-widgetcontenttype",cache)
    
    #return the values
    return (contentType, getCleanImage(image))

def getLocalDateTimeFromUtc(timestring):
    try:
        systemtime = xbmc.getInfoLabel("System.Time")
        utc = datetime.fromtimestamp(time.mktime(time.strptime(timestring, '%Y-%m-%d %H:%M:%S')))
        epoch = time.mktime(utc.timetuple())
        offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp(epoch)
        correcttime = utc + offset
        if "AM" in systemtime or "PM" in systemtime:
            return (correcttime.strftime("%Y-%m-%d"),correcttime.strftime("%I:%M %p"))
        else:
            return (correcttime.strftime("%d-%m-%Y"),correcttime.strftime("%H:%M"))
    except:
        logMsg("ERROR in getLocalDateTimeFromUtc --> " + timestring, 0)
        
        return (timestring,timestring)

def double_urlencode(text):
   """double URL-encode a given 'text'.  Do not return the 'variablename=' portion."""

   text = single_urlencode(text)
   text = single_urlencode(text)

   return text

def single_urlencode(text):
   """single URL-encode a given 'text'.  Do not return the 'variablename=' portion."""

   blah = urllib.urlencode({'blahblahblah':text})

   #we know the length of the 'blahblahblah=' is equal to 13.  This lets us avoid any messy string matches
   blah = blah[13:]

   return blah

def createSmartShortcutSubmenu(windowProp,iconimage):
    try:
        if xbmcvfs.exists("special://skin/shortcuts/"):
            shortcutFile = xbmc.translatePath("special://home/addons/script.skinshortcuts/resources/shortcuts/info-window-home-property-%s-title.DATA.xml" %windowProp.replace(".","-")).decode("utf-8")
            templatefile = os.path.join(ADDON_PATH,"resources","smartshortcuts","smartshortcuts-submenu-template.xml")
            if not xbmcvfs.exists(shortcutFile):
                with open(templatefile, 'r') as f:
                    data = f.read()
                data = data.replace("WINDOWPROP",windowProp)
                data = data.replace("ICONIMAGE",iconimage)
                with open(shortcutFile, 'w') as f:
                    f.write(data)
    except Exception as e:
        logMsg("ERROR in createSmartShortcutSubmenu ! --> " + str(e), 0)

def getCurrentContentType():
    contenttype=""
    if xbmc.getCondVisibility("Container.Content(episodes)"):
        contenttype = "episodes"
    elif xbmc.getCondVisibility("Container.Content(movies) + !substring(Container.FolderPath,setid=)"):
        contenttype = "movies"  
    elif xbmc.getCondVisibility("[Container.Content(sets) | StringCompare(Container.Folderpath,videodb://movies/sets/)] + !substring(Container.FolderPath,setid=)"):
        contenttype = "sets"
    elif xbmc.getCondVisibility("substring(Container.FolderPath,?setid=)"):
        contenttype = "setmovies" 
    elif xbmc.getCondVisibility("Container.Content(tvshows)"):
        contenttype = "tvshows"
    elif xbmc.getCondVisibility("Container.Content(seasons)"):
        contenttype = "seasons"
    elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
        contenttype = "musicvideos"
    elif xbmc.getCondVisibility("Container.Content(songs) | StringCompare(Container.FolderPath,musicdb://singles/)"):
        contenttype = "songs"
    elif xbmc.getCondVisibility("Container.Content(artists)"):
        contenttype = "artists"
    elif xbmc.getCondVisibility("Container.Content(albums)"):
        contenttype = "albums"
    elif xbmc.getCondVisibility("Window.IsActive(MyPVRChannels.xml) | Window.IsActive(MyPVRGuide.xml) | Window.IsActive(MyPVRSearch.xml)"):
        contenttype = "tvchannels"
    elif xbmc.getCondVisibility("Window.IsActive(MyPVRRecordings.xml) | Window.IsActive(MyPVRTimers.xml)"):
        contenttype = "tvrecordings"
    elif xbmc.getCondVisibility("Window.IsActive(programs) | Window.IsActive(addonbrowser)"):
        contenttype = "programs"
    elif xbmc.getCondVisibility("Window.IsActive(pictures)"):
        contenttype = "pictures"
    elif xbmc.getCondVisibility("Container.Content(genres)"):
        contenttype = "genres"
    elif xbmc.getCondVisibility("Container.Content(files)"):
        contenttype = "files"
    WINDOW.setProperty("contenttype",contenttype)
    return contenttype
         
def getCleanImage(image):
    if image and "image://" in image:
        image = image.replace("image://","")
        image=urllib.unquote(image.encode("utf-8"))
        if image.endswith("/"):
            image = image[:-1]
    return try_decode(image)

def normalize_string(text):
    text = text.replace(":", "")
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = text.replace("<", "")
    text = text.replace(">", "")
    text = text.replace("*", "")
    text = text.replace("?", "")
    text = text.replace('|', "")
    text = text.replace('(', "")
    text = text.replace(')', "")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', try_decode(text))
    return text
    
def recursiveDelete(path):
    success = True
    path = try_encode(path)
    dirs, files = xbmcvfs.listdir(path)
    for file in files:
        success = xbmcvfs.delete(os.path.join(path,file))
    for dir in dirs:
        success = recursiveDelete(os.path.join(path,dir))
    success = xbmcvfs.rmdir(path)
    return success 

def addToZip(src, zf, abs_src):
    dirs, files = xbmcvfs.listdir(src)
    for file in files:
        file = file.decode("utf-8")
        logMsg("zipping " + file)
        file = xbmc.translatePath( os.path.join(src, file) ).decode("utf-8")
        absname = os.path.abspath(file)
        arcname = absname[len(abs_src) + 1:]
        try:
            #newer python can use unicode for the files in the zip
            zf.write(absname, arcname)
        except:
            #older python version uses utf-8 for filenames in the zip
            zf.write(absname.encode("utf-8"), arcname.encode("utf-8"))
    for dir in dirs:
        addToZip(os.path.join(src,dir),zf,abs_src)
    return zf
        
def zip(src, dst):
    import zipfile
    src = try_decode(src)
    dst = try_decode(dst)
    zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(xbmc.translatePath(src).decode("utf-8"))
    zf = addToZip(src,zf,abs_src)
    zf.close()
    
def unzip(zip_file,path):
    import shutil
    import zipfile
    zip_file = try_decode(zip_file)
    path = try_decode(path)
    logMsg("START UNZIP of file %s  to path %s " %(zipfile,path))
    f = zipfile.ZipFile(zip_file, 'r')
    for fileinfo in f.infolist():
        filename = fileinfo.filename
        filename = try_decode(filename)
        logMsg("unzipping " + filename)
        if "\\" in filename: xbmcvfs.mkdirs(os.path.join(path,filename.rsplit("\\", 1)[0]))
        elif "/" in filename: xbmcvfs.mkdirs(os.path.join(path,filename.rsplit("/", 1)[0]))
        filename = os.path.join(path,filename)
        logMsg("unzipping " + filename)
        try:
            #newer python uses unicode
            outputfile = open(filename, "wb")
        except:
            #older python uses utf-8
            outputfile = open(filename.encode("utf-8"), "wb")
        #use shutil to support non-ascii formatted files in the zip
        shutil.copyfileobj(f.open(fileinfo.filename), outputfile)
        outputfile.close()
    f.close()
    logMsg("UNZIP DONE of file %s  to path %s " %(zipfile,path))
    
def matchStudioLogo(studiostr,studiologos):
    #try to find a matching studio logo
    studiologo = ""
    studios = []
    if "/" in studiostr:
        studios = studiostr.split(" / ")
    else:
        studios.append(studiostr)
    
    for studio in studios:
        studio = studio.lower()
        #find logo normal
        if studiologos.has_key(studio):
            studiologo = studiologos[studio]
        
        if not studiologo:
            #find logo by substituting characters
            if " (" in studio:
                studio = studio.split(" (")[0]
                if studiologos.has_key(studio):
                    studiologo = studiologos[studio]
        
        if not studiologo:
            #find logo by substituting characters for pvr channels
            if " HD" in studio:
                studio = studio.replace(" HD","")
            elif " " in studio:
                studio = studio.replace(" ","")
            if studiologos.has_key(studio):
                studiologo = studiologos[studio]
                
    return studiologo

def resetGlobalWidgetWindowProps():
    WINDOW.setProperty("widgetreload2", time.strftime("%Y%m%d%H%M%S", time.gmtime()))
    
def resetPlayerWindowProps():
    #reset all window props provided by the script...
    WINDOW.setProperty("SkinHelper.Player.Music.Banner","") 
    WINDOW.setProperty("SkinHelper.Player.Music.ClearLogo","") 
    WINDOW.setProperty("SkinHelper.Player.Music.DiscArt","") 
    WINDOW.setProperty("SkinHelper.Player.Music.FanArt","") 
    WINDOW.setProperty("SkinHelper.Player.Music.Thumb","") 
    WINDOW.setProperty("SkinHelper.Player.Music.Info","") 
    WINDOW.setProperty("SkinHelper.Player.Music.TrackList","") 
    WINDOW.setProperty("SkinHelper.Player.Music.SongCount","") 
    WINDOW.setProperty("SkinHelper.Player.Music.albumCount","") 
    WINDOW.setProperty("SkinHelper.Player.Music.AlbumList","")
    WINDOW.setProperty("SkinHelper.Player.Music.ExtraFanArt","")
    
def resetMusicWidgetWindowProps():
    #clear the cache for the music widgets
    logMsg("Music database changed, refreshing widgets....",0)
    WINDOW.setProperty("widgetreloadmusic", time.strftime("%Y%m%d%H%M%S", time.gmtime()))

def resetVideoWidgetWindowProps():
    #clear the cache for the video widgets
    logMsg("Video database changed, refreshing widgets....",0)
    WINDOW.setProperty("widgetreload", time.strftime("%Y%m%d%H%M%S", time.gmtime()))

def getResourceAddonFiles(addonName,allFilesList=None):
    # get listing of all files (eg studio logos) inside a resource image addonName
    # listing is delivered by the addon and not read live because of some issues with listdir and resourceaddons.
    # http://forum.kodi.tv/showthread.php?tid=246245
    if not allFilesList: 
        allFilesList = {}
        
    # read data from our permanent cache file to prevent that we have to query the resource addon
    cachefile = os.path.join(ADDON_PATH, 'resources', addonName + '.json' ).decode("utf-8")
    data = getDataFromCacheFile(cachefile)
    if not data:
        # safe data to our permanent cache file, only to be written if the resource addon changes.
        data = listFilesInPath("resource://%s/"%addonName)
        saveDataToCacheFile(cachefile,data)
    
    #return the data
    if data:
        for key, value in data.iteritems():
            if not allFilesList.get(key):
                allFilesList[key] = value
    return allFilesList
     
def listFilesInPath(path, allFilesList=None):
    #used for easy matching of studio logos
    if not allFilesList: 
        allFilesList = {}
    dirs, files = xbmcvfs.listdir(path)
    for file in files:
        file = file.decode("utf-8")
        name = file.split(".png")[0].lower()
        if not allFilesList.has_key(name):
            allFilesList[name] = path + file
    for dir in dirs:
        dirs2, files2 = xbmcvfs.listdir(os.path.join(path,dir)+os.sep)
        for file in files2:
            file = file.decode("utf-8")
            dir = dir.decode("utf-8")
            name = dir + "/" + file.split(".png")[0].lower()
            if not allFilesList.has_key(name):
                if "/" in path:
                    sep = "/"
                else:
                    sep = "\\"
                allFilesList[name] = path + dir + sep + file
    
    #return the list
    return allFilesList
   
def getDataFromCacheFile(file):
    data = {}
    try:
        if xbmcvfs.exists(file):
            f = xbmcvfs.File(file, 'r')
            text =  f.read().decode("utf-8")
            f.close()
            if text: data = eval(text)   
    except Exception as e:
        logMsg("ERROR in getDataFromCacheFile for file %s --> %s" %(file,str(e)), 0)
    return data
      
def saveDataToCacheFile(file,data):
    #safety check: does the config directory exist?
    if not xbmcvfs.exists(ADDON_DATA_PATH + os.sep):
        xbmcvfs.mkdirs(ADDON_DATA_PATH)
    try:            
        str_data = repr(data).encode("utf-8")
        f = xbmcvfs.File(file, 'w')
        f.write(str_data)
        f.close()
    except Exception as e:
        logMsg("ERROR in saveDataToCacheFile for file %s --> %s" %(file,str(e)), 0)

def getCompareString(string,optionalreplacestring=""):
    #strip all kinds of chars from a string to be used in compare actions
    string = try_encode(string)
    string = string.lower().replace(".","").replace(" ","").replace("-","").replace("_","").replace("'","").replace("`","").replace("’","").replace("_new","").replace("new_","")
    if optionalreplacestring: string = string.replace(optionalreplacestring.lower(),"")
    string = try_decode(string)
    string = normalize_string(string)
    return string
    
