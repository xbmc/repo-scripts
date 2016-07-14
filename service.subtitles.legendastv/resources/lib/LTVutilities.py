# -*- coding: utf-8 -*-

import os
import re
import sys
import xbmc
import xbmcvfs
import shutil
import unicodedata
import urllib, urllib2

try: import simplejson as json
except: import json

try:
    __scriptname__ = sys.modules[ "__main__" ].__scriptname__
except:
    __scriptname__ = ""

TheTVDBApi = "A1738606AC58C23D"
TMDBApi    = "96e0692265de9b2019b16f0c144efa56"

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def log(msg):
  xbmc.log((u"### [%s] - %s" % (__scriptname__,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def getTheTVDBToken():
    HTTPRequest = urllib2.Request("https://api.thetvdb.com/login", data=json.dumps({"apikey" : TheTVDBApi}), headers={'Content-Type' : 'application/json'})
    try:
        HTTPResponse = urllib2.urlopen(HTTPRequest).read()
        return json.loads(HTTPResponse)['token']
    except:
        return None

def cleanDirectory(directory):
  try:
    if xbmcvfs.exists(directory + "/"):
      for root, dirs, files in os.walk(directory):
        for f in files:
          file = os.path.join(root, f)
          log(file)
          xbmcvfs.delete(file)
      for d in dirs:
        dir = os.path.join(root, d)
        xbmcvfs.rmdir(dir)
  except:
    pass
    
  if not xbmcvfs.exists(directory):
    xbmcvfs.mkdirs(directory)

def getShowId():
    try:
      playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
      playerid       = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
      tvshowid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
      tvshowid       = json.loads(xbmc.executeJSONRPC (tvshowid_query))['result']['item']['tvshowid']
      tvdbid_query   = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
      tvdbid         =  json.loads(xbmc.executeJSONRPC (tvdbid_query))['result']['tvshowdetails']['imdbnumber']
      log("getShowId: " + tvdbid)
      return tvdbid
    except:
      log("Failed to find TVDBid in database")
      return None

def getShowIMDB():
    ShowID = getShowId()
    if ShowID:
        try:
            TheTVDBToken = getTheTVDBToken()
            HTTPRequest  = urllib2.Request("https://api.thetvdb.com/series/%s" % ShowID, headers={'Authorization' : 'Bearer %s' % TheTVDBToken})
            HTTPResponse =  urllib2.urlopen(HTTPRequest).read()
            JSONContent  = json.loads(HTTPResponse)
            if JSONContent.has_key("data"):
                return JSONContent['data']['imdbId']
        except:
            return None
    else:
        return None


def getMovieId():
    try:
        playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        playerid       = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
        movieid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["imdbnumber", "title", "year"]}, "id": 1}'
        movieid       = json.loads(xbmc.executeJSONRPC (movieid_query))
        # print json.dumps(movieid, sort_keys=True, indent=4, separators=(',', ': '))
  
        if movieid['result']['item'].has_key("imdbnumber") and len(movieid['result']['item']["imdbnumber"]):
            return movieid['result']['item']["imdbnumber"]
        elif movieid['result']['item'].has_key("title") and len(movieid['result']['item']["title"]):
            title = movieid['result']['item']["title"].encode("utf-8");
            Query = urllib.urlencode({"api_key" : TMDBApi, "page" : "1", "query" : title, "year" : movieid['result']['item']["year"]})
            HTTPRequest = urllib2.Request("https://api.themoviedb.org/3/search/movie", data=Query)
            HTTPRequest.get_method = lambda: "GET"
            HTTPResponse = urllib2.urlopen(HTTPRequest).read()
            JSONContent  = json.loads(HTTPResponse);
            if len(JSONContent['results']):
                TMDBId = JSONContent['results'][0]['id']
                HTTPRequest  = urllib2.Request("https://api.themoviedb.org/3/movie/%s?api_key=%s" % (TMDBId, TMDBApi))
                HTTPResponse = urllib2.urlopen(HTTPRequest).read()
                JSONContent  = json.loads(HTTPResponse);
                if JSONContent.has_key("imdb_id"):
                    log("getMovieID: "+JSONContent["imdb_id"])
                    return JSONContent["imdb_id"]
            return None
    except:
        return None
      
def xbmcOriginalTitle(OriginalTitle):
  if not len(OriginalTitle):
    return OriginalTitle

  TVName = xbmc.getInfoLabel("VideoPlayer.TVShowTitle")

  if TVName:
    ShowID = getShowId()
    if ShowID:
      try:
        TheTVDBToken = getTheTVDBToken()
      except:
        return normalizeString(OriginalTitle)

      HTTPRequest  = urllib2.Request("https://api.thetvdb.com/series/%s" % ShowID, headers={'Authorization' : 'Bearer %s' % TheTVDBToken})
      HTTPResponse = urllib2.urlopen(HTTPRequest).read()

      try:
        JSONContent = json.loads(HTTPResponse)
      except Exception as e:
        return normalizeString(OriginalTitle)

      if JSONContent.has_key("data"):
        return JSONContent['data']['seriesName']
  else:
    MovieID = getMovieId()
    if MovieID:
      HTTPRequest  = urllib2.Request("https://api.themoviedb.org/3/find/%s?external_source=imdb_id&api_key=%s" % (MovieID, TMDBApi))
      HTTPResponse = urllib2.urlopen(HTTPRequest).read()
      JSONContent  = json.loads(HTTPResponse);
      if len(JSONContent["movie_results"]):
        return normalizeString(JSONContent["movie_results"][0]['original_title'].encode('utf-8'))
  
  return normalizeString(OriginalTitle)

def isStacked(subA, subB):
    subA, subB = re.escape(subA), re.escape(subB)
    regexesStacked = ["(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[0-9]+)(.*?)(\.[^.]+)$", 
                      "(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[a-d])(.*?)(\.[^.]+)$",
                      "(.*?)([ ._-]*[a-d])(.*?)(\.[^.]+)$"]
    for regex in regexesStacked:
        if re.search(subA, regex):
            fnA, diskA, otherA, extA = re.findall(regex, subA)[0]
            if re.search(subB, regex):
                fnB, diskB, otherB, extB = re.findall(regex, subB)[0]
                if fnA == fnB and otherA == otherB:
                    return True
    return False