#import modules
import os
import xbmc
import urllib
import sys

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import json as simplejson
else:
    import simplejson

### import libraries
from resources.lib.utils import log
# Commoncache plugin import
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

cacheMedia = StorageServer.StorageServer("ArtworkDownloader",1)
#cacheMedia.timeout = 600 # In seconds

# Retrieve JSON data from cache function
def _media_listing(media_type):
    #result = cacheMedia.cacheFunction( _media_listing_new, media_type )
    result = _media_listing_new(media_type)
    if len(result) == 0:
        result = []
        return result
    else:
        return result

### get list of all tvshows and movies with their imdbnumber from library
# Retrieve JSON list

def _media_listing_new(media_type):
    log('Using JSON for retrieving %s info' %media_type)
    Medialist = []
    try:
        if media_type == 'tvshow':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
            json_response = unicode(json_response, 'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('tvshows'):
                for item in jsonobject['result']['tvshows']:
                    # Search for season information
                    json_response_season = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season"], "sort": { "method": "label" }, "tvshowid":%s }, "id": 1}' %item.get('tvshowid',''))
                    jsonobject_season = simplejson.loads(json_response_season)
                    # Get start/end and total seasons
                    if jsonobject_season['result'].has_key('limits'):
                        season_limit = jsonobject_season['result']['limits']
                    # Get the season numbers
                    if jsonobject_season['result'].has_key('seasons'):
                        seasons = jsonobject_season['result']['seasons']
                        seasons_list =[]
                        for season in seasons:
                            seasons_list.append(season.get('season')) 
                    Medialist.append({'id': item.get('imdbnumber',''),
                                      'tvshowid': item.get('tvshowid',''),
                                      'name': item.get('label',''),
                                      'path': media_path(item.get('file','')),
                                      'seasontotal': season_limit.get('total',''),
                                      'seasonstart': season_limit.get('start',''),
                                      'seasonend': season_limit.get('end',''),
                                      'seasons': seasons_list})

        elif media_type == 'movie':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "imdbnumber", "year", "trailer", "streamdetails"], "sort": { "method": "label" } }, "id": 1}')
            json_response = unicode(json_response, 'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('movies'):
                for item in jsonobject['result']['movies']:
                    filename = item.get('file','').encode('utf-8').lower()
                    if (('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename) or (filename.endswith('.vob' or '.ifo')):
                        disctype = 'dvd'
                    elif '3d' in filename:
                        disctype = '3d'
                    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip') in filename):
                        disctype = 'bluray'
                    elif item['streamdetails'] != None and item['streamdetails'].has_key('video'):
                        videowidth = item['streamdetails']['video'][0]['width']
                        videoheight = item['streamdetails']['video'][0]['height']
                        if videowidth <= 720 and videoheight <= 480:
                            disctype = 'dvd'
                        else:
                            disctype = 'bluray'
                    else:
                        disctype = 'n/a'
                    Medialist.append({'movieid': item.get('movieid',''),
                                      'id': item.get('imdbnumber',''),
                                      'name': item.get('label',''),
                                      'year': item.get('year',''),
                                      'file': item.get('file',''),
                                      'path': media_path(item.get('file','')),
                                      'trailer': item.get('trailer',''),
                                      'disctype': disctype})

        elif media_type == 'musicvideo':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["file", "artist", "album", "track", "runtime", "year", "genre"], "sort": { "method": "album" } }, "id": 1}')
            json_response = unicode(json_response, 'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('musicvideos'):
                for item in jsonobject['result']['musicvideos']:
                    Medialist.append({'id': '',
                                      'movieid': item.get('musicvideoid',''),
                                      'name': item.get('label',''),
                                      'artist': item.get('artist',''),
                                      'album': item.get('album',''),
                                      'track': item.get('track',''),
                                      'runtime': item.get('runtime',''),
                                      'year': item.get('year',''),
                                      'path': media_path(item.get('file',''))})
        else:
                log('No JSON results found')
    except Exception, NoneType:
        Medialist = []
        log('No %s found in your library' %media_type)
    except Exception, e:
        Medialist = []
        log( str( e ), xbmc.LOGERROR )
    return Medialist


def media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        path = [os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://","").split('%2f/')
        path = []
        for item in temp_path:
            path.append(urllib.url2pathname(item))
        print path
    else:
        path = [path]
    return path