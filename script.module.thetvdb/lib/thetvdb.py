# -*- coding: utf-8 -*-
import requests
import xbmc, xbmcgui, xbmcaddon
import time, re, os
from datetime import date, timedelta, datetime

try:
    import simplejson as json
except:
    import json

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id').decode("utf-8")
ADDON_ICON = ADDON.getAddonInfo('icon').decode("utf-8")
ADDON_NAME = ADDON.getAddonInfo('name').decode("utf-8")
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version').decode("utf-8")
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)
SETTING = ADDON.getSetting
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
USE_CACHE = True
DAYS_AHEAD = 60

def logMsg(msg):
	xbmc.log('{0} - thetvdb: {1}'.format(ADDON_ID, try_encode(msg)))

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
    
def getToken(refresh=False):
    #get token from memory cache first
    token = WINDOW.getProperty("script.module.thetvdb.token").decode('utf-8')
    if token and not refresh:
        return token
    
    #refresh previous token
    prev_token = ADDON.getSetting("token")
    if prev_token:
        url = 'https://api.thetvdb.com/refresh_token'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-agent': 'Mozilla/5.0', 'Authorization': 'Bearer %s' % prev_token}
        response = requests.get(url, headers=headers)
        if response and response.content and response.status_code == 200:
            data = json.loads(response.content.decode('utf-8','replace'))
            token = data["token"]
        if token:
            WINDOW.setProperty("script.module.thetvdb.token",token)
            return token
    
    #do first login to get initial token
    url = 'https://api.thetvdb.com/login'
    payload = {'apikey': 'A7613F5C1482A540'}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-agent': 'Mozilla/5.0'}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response and response.content and response.status_code == 200:
        data = json.loads(response.content.decode('utf-8','replace'))
        token = data["token"]
        ADDON.setSetting("token",token)
        WINDOW.setProperty("script.module.thetvdb.token",token)
        return token
    else:
        logMsg("Error getting JWT token!")
        return None

def getKodiJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, try_encode(params)))
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        jsonobject = jsonobject['result']
    return jsonobject
        
def getData(endpoint):
    
    #use memory cache first
    cachestr = "thetvdb--%s--%s" %(endpoint,date.today().strftime("%m%d%Y"))
    cache = WINDOW.getProperty(cachestr)
    if cache and USE_CACHE:
        data = eval(cache)
    else:
        #grab the results from the api
        url = 'https://api.thetvdb.com/' + endpoint
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-agent': 'Mozilla/5.0', 'Authorization': 'Bearer %s' % getToken()}
        response = requests.get(url, headers=headers, timeout=5)
        data = {}
        if response and response.content and response.status_code == 200:
            data = json.loads(response.content.decode('utf-8','replace'))
        elif response.status_code == 401:
            #token expired, refresh it and repeat our request
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-agent': 'Mozilla/5.0', 'Authorization': 'Bearer %s' % getToken(True)}
            response = requests.get(url, headers=headers, timeout=5)
            if response and response.content and response.status_code == 200:
                data = json.loads(response.content.decode('utf-8','replace'))

        if data.get("data"): 
            data = data["data"]
            
        #store results in window cache
        WINDOW.setProperty(cachestr,repr(data).decode("utf-8"))
    
    #return our data
    return data

def getSeriesPoster(seriesid,season=None):
    #retrieves the URL for the series poster, prefer season poster if season number provided
    
    score = 0
    posterurl = ""
    if season:
        images = getData("series/%s/images/query?keyType=season&subKey=%s" %(seriesid,season))
        for image in images:
            image_score = image["ratingsInfo"]["average"] * image["ratingsInfo"]["count"]
            if image_score > score:
                posterurl = "http://thetvdb.com/banners/" + image["fileName"]
                score = image_score
                
    if not posterurl:
        images = getData("series/%s/images/query?keyType=poster" %(seriesid))
        for image in images:
            image_score = image["ratingsInfo"]["average"] * image["ratingsInfo"]["count"]
            if image_score > score:
                posterurl = "http://thetvdb.com/banners/" + image["fileName"]
                score = image_score
                
    return posterurl
    
def getSeriesFanart(seriesid,Landscape=False):
    #retrieves the URL for the series fanart image
    
    score = 0
    fanarturl = ""
    images = getData("series/%s/images/query?keyType=fanart" %(seriesid))
    for image in images:
        if (image["subKey"] == "text" and Landscape) or (not Landscape and image["subKey"] == "graphical"):
            image_score = image["ratingsInfo"]["average"] * image["ratingsInfo"]["count"]
            if image_score > score:
                fanarturl = "http://thetvdb.com/banners/" + image["fileName"]
                score = image_score
                
    return fanarturl
       
def getEpisode(episodeid):
    '''
        Returns the full information for a given episode id. 
        Deprecation Warning: The director key will be deprecated in favor of the new directors key in a future release.
        Usage: specify the episode ID: getEpisode(episodeid)
    '''
    episode = getData("episodes/%s" %episodeid)
    if episode["filename"]:
        episode["thumbnail"] = "http://thetvdb.com/banners/" + episode["filename"]
    episode["poster"] = getSeriesPoster(episode["seriesId"],episode["airedSeason"])
    return episode
        
def getSeries(seriesid,ContinuingOnly=False):
    '''
        Returns a series record that contains all information known about a particular series id.
        Usage: specify the serie ID: getSeries(seriesid)
    '''
    seriesinfo = getData("series/%s" %seriesid)
    if ContinuingOnly and seriesinfo.get("status","") != "Continuing":
        return None
    seriesinfo["poster"] = getSeriesPoster(seriesid)
    if seriesinfo.get("banner"):
        seriesinfo["banner"] = "http://thetvdb.com/banners/" + seriesinfo["banner"]
    seriesinfo["fanart"] = getSeriesFanart(seriesid)
    seriesinfo["landscape"] = getSeriesFanart(seriesid,True)
    return seriesinfo
    
def getContinuingSeries():
    '''
        only gets the continuing series, based on which series were recently updated as there is no other api call to get that information
    '''
    recent_series = getRecentlyUpdatedSeries()
    continuing_series = []
    for recent_serie in recent_series:
        seriesinfo = getSeries(recent_serie["id"],True)
        if seriesinfo:
            continuing_series.append(seriesinfo)
    return continuing_series
        
def getSeriesActors(seriesid):
    '''
        Returns actors for the given series id.
        Usage: specify the series ID: getSeriesActors(seriesid)
    '''
    return getData("series/%s/actors" %seriesid)
       
def getSeriesEpisodes(seriesid):
    '''
        Returns all episodes for a given series.
        Usage: specify the series ID: getSeriesEpisodes(seriesid)
    '''
    allepisodes = []
    page = 1
    while True:
        #get all episodes by iterating over the pages
        data = getData("series/%s/episodes?page=%s" %(seriesid,page) )
        if not data:
            break
        else:
            allepisodes += data
            page += 1
    return allepisodes
    
def getSeriesEpisodesByQuery(seriesid,absoluteNumber="",airedSeason="",airedEpisode="",dvdSeason="",dvdEpisode="",imdbId=""):
    '''
        This route allows the user to query against episodes for the given series. The response is an array of episode records that have been filtered down to basic information.
        Usage: specify the series ID: getSeriesEpisodesByQuery(seriesid)
        optionally you can specify one or more fields for the query:
        absoluteNumber --> Absolute number of the episode
        airedSeason --> Aired season number
        airedEpisode --> Aired episode number
        dvdSeason --> DVD season number
        dvdEpisode --> DVD episode number
        imdbId --> IMDB id of the series
    '''
    allepisodes = []
    page = 1
    while True:
        #get all episodes by iterating over the pages
        data = getData("series/%s/episodes/query?page=%s&absoluteNumber=%s&airedSeason=%s&airedEpisode=%s&dvdSeason=%s&dvdEpisode=%s&imdbId=%s" 
            %(seriesid,page,absoluteNumber,airedSeason,airedEpisode,dvdSeason,dvdEpisode,imdbId) )
        if not data:
            break
        else:
            allepisodes += data
            page += 1
    return allepisodes
    
def getSeriesEpisodesSummary(seriesid):
    '''
        Returns a summary of the episodes and seasons available for the series.
        Note: Season 0 is for all episodes that are considered to be specials.

        Usage: specify the series ID: getSeriesEpisodesSummary(seriesid)
    '''
    return getData("series/%s/episodes/summary" %(seriesid))

def searchSeries(name="",imdbId="",zap2itId=""):
    '''
        Allows the user to search for a series based on one or more parameters. Returns an array of results that match the query.
        Usage: specify the series ID: searchSeries(parameters)
        
        Available parameters:
        name --> Name of the series to search for.
        imdbId --> IMDB id of the series
        zap2itId -->  Zap2it ID of the series to search for.
    '''
    return getData("search/series?name=%s,imdbId=%s,zap2itId=%s" 
        %(seriesid,page,absoluteNumber,airedSeason,airedEpisode,dvdSeason,dvdEpisode,imdbId) )
            
def getRecentlyUpdatedSeries():
    '''
        Returns all series that have been updated in the last week
    '''
    DAY = 24*60*60
    utc_date = date.today() - timedelta(days=7)
    cur_epoch = (utc_date.toordinal() - date(1970, 1, 1).toordinal()) * DAY
    return getData("updated/query?fromTime=%s" %cur_epoch)
    
def getUnAiredEpisodes(seriesid):
    '''
        Returns the unaired episodes for the specified seriesid
        Usage: specify the series ID: getUnAiredEpisodes(seriesid)
    '''
    next_episodes = []
    seriesinfo = getSeries(seriesid, True)
    if seriesinfo:
        episodes = getSeriesEpisodes(seriesid)
        for episode in episodes:
            if episode["firstAired"] and episode["episodeName"]:
                airdate = datetime.strptime(episode["firstAired"],"%Y-%m-%d").date()
                if airdate == date.today() or (airdate > date.today() and airdate < (date.today() + timedelta(days=DAYS_AHEAD)) ):
                    #if airdate is today or (max X days) in the future add to our list
                    episode = getEpisode(episode["id"])
                    episode["seriesinfo"] = seriesinfo
                    next_episodes.append(episode)
                
    #return our list sorted by date
    return sorted(next_episodes, key=lambda k: k.get('firstAired', ""))
    
def getNextUnAiredEpisode(seriesid):
    '''
        Returns the first next airing episode for the specified seriesid
        Usage: specify the series ID: getNextUnAiredEpisode(seriesid)
    '''
    next_episodes = getUnAiredEpisodes(seriesid)
    if next_episodes:
        return next_episodes[0]
    else:
        return None

def getUnAiredEpisodeList(seriesids):
    '''
        Returns the next airing episode for each specified seriesid
        Usage: specify the series ID: getNextUnAiredEpisode(list of seriesids)
    '''
    next_episodes = []
    for seriesid in seriesids:
        episodes = getUnAiredEpisodes(seriesid)
        if episodes:
            next_episodes.append(episodes[0])
                
    #return our list sorted by date
    return sorted(next_episodes, key=lambda k: k.get('firstAired', ""))
    
def getKodiSeriesUnairedEpisodesList(singleEpisodePerShow=True):
    '''
        Returns the next unaired episode for all continuing tv shows in the Kodi library
        Defaults to a single episode (next unaired) for each show, to disable have False as argument.
    '''
    kodi_series = getKodiJSON('VideoLibrary.GetTvShows','{"properties": [ "title","imdbnumber","art", "genre", "cast", "studio" ] }')
    
    #use primitive cache by using kodi window prop
    cachestr = "tvdb-KodiUnairedEpisodes-%s-%s-%s-%s" %(date.today().strftime("%m%d%Y"),len(kodi_series),singleEpisodePerShow,DAYS_AHEAD)
    cache = WINDOW.getProperty(cachestr)
    if cache and USE_CACHE:
        return eval(cache)
    
    next_episodes = []
    if kodi_series and kodi_series.get("tvshows"):
        for kodi_serie in kodi_series["tvshows"]:
            if kodi_serie["imdbnumber"] and kodi_serie["imdbnumber"].startswith("tt"):
                #lookup serie by imdbid
                search_serie = searchSeries(imdbid=kodi_serie["imdbnumber"])
                serieid = search_serie[0]["id"]
            elif kodi_serie["imdbnumber"]:
                #imdbid in kodidb is already tvdb id
                serieid = kodi_serie["imdbnumber"]
            else:
                #lookup series id by name
                search_serie = searchSeries(title=kodi_serie["title"])
                serieid = search_serie[0]["id"]
            
            episodes = []
            if singleEpisodePerShow:
                episodes.append( getNextUnAiredEpisode(serieid) )
            else:
                episodes = getUnAiredEpisodes(serieid)
            for next_episode in episodes:
                if next_episode:
                    #make the json output kodi compatible
                    next_episode["art"] = {}
                    next_episode["art"]["thumb"] = next_episode.get("thumbnail","")
                    next_episode["art"]["poster"] = next_episode.get("poster","")
                    next_episode["art"]["landscape"] = kodi_serie["art"].get("landscape",next_episode["seriesinfo"].get("landscape",""))
                    next_episode["art"]["fanart"] = kodi_serie["art"].get("fanart",next_episode["seriesinfo"].get("fanart",""))
                    next_episode["art"]["banner"] = kodi_serie["art"].get("banner",next_episode["seriesinfo"].get("banner",""))
                    next_episode["art"]["clearlogo"] = kodi_serie["art"].get("clearlogo","")
                    next_episode["art"]["clearart"] = kodi_serie["art"].get("clearart","")
                        
                    next_episode["title"] = next_episode["episodeName"]
                    next_episode["tvshowtitle"] = kodi_serie["title"]
                    next_episode["studio"] = kodi_serie["studio"]
                    next_episode["genre"] = kodi_serie["genre"]
                    next_episode["cast"] = kodi_serie["cast"]
                    next_episode["tvshowid"] = kodi_serie["tvshowid"]
                    next_episode["season"] = next_episode["airedSeason"]
                    next_episode["episode"] = next_episode["airedEpisodeNumber"]
                    next_episode["episodeid"] = -1
                    next_episode["file"] = "plugin://script.skin.helper.service?action=LAUNCH&path=ActivateWindow(Videos,videodb://tvshows/titles/%s/,return)" %kodi_serie["tvshowid"]
                    next_episode["type"] = "episode"
                    next_episode["firstaired"] = next_episode["firstAired"]
                    next_episode["writer"] = next_episode["writers"]
                    next_episode["director"] = [ next_episode["director"] ]
                    next_episode["rating"] = next_episode["siteRating"]
                    next_episode["plot"] = next_episode["overview"]
                    next_episode["runtime"] = int(next_episode["seriesinfo"]["runtime"]) * 60
                    next_episodes.append(next_episode)
             
    #return our list sorted by date
    next_episodes = sorted(next_episodes, key=lambda k: k.get('firstAired', ""))
    WINDOW.setProperty(cachestr,repr(next_episodes).decode("utf-8"))
    return next_episodes
        