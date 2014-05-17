# -*- coding: utf-8 -*-

import os
import re
import sys
import xbmc
import xbmcvfs
import shutil
import unicodedata
import urllib2

try: import simplejson as json
except: import json

try:
    __scriptname__ = sys.modules[ "__main__" ].__scriptname__
except:
    __scriptname__ = ""

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def log(msg):
  xbmc.log((u"### [%s] - %s" % (__scriptname__,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def cleanDirectory(directory):
    try:
        if xbmcvfs.exists(directory):
            for root, dirs, files in os.walk(directory):
                for f in files:
                    file = os.path.join(root, f)
                    xbmcvfs.delete(file)
                for d in dirs:
                    dir = os.path.join(root, d)
                    xbmcvfs.rmdir(dir)
    except:
        pass
    
    if not xbmcvfs.exists(directory):
        os.makedirs(directory)

def getShowId():
    try:
      playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
      playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
      tvshowid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
      tvshowid = json.loads(xbmc.executeJSONRPC (tvshowid_query))['result']['item']['tvshowid']
      tvdbid_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
      return json.loads(xbmc.executeJSONRPC (tvdbid_query))['result']['tvshowdetails']['imdbnumber']
    except:
      log("Failed to find TVDBid in database")
      
def xbmcOriginalTitle(OriginalTitle):
    MovieName =  xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
    if MovieName:
        OriginalTitle = MovieName
    else:
        ShowID = getShowId()
        if ShowID:
            HTTPResponse = urllib2.urlopen("http://www.thetvdb.com//data/series/%s/" % str(ShowID)).read()
            if re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL):
                OriginalTitle = re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL)[0]
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