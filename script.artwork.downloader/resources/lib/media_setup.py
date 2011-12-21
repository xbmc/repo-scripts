import os
import re
import xbmc
import urllib
import simplejson
from resources.lib.utils import _normalize_string as normalize_string
from resources.lib.utils import _log as log

### get list of all tvshows and movies with their imdbnumber from library


# Retrieve JSON list
def _media_listing(media_type):
        log('Using JSON for retrieving %s info' %media_type)
        Medialist = []
        if media_type == 'tvshow':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
            json_response = unicode(json_response,'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('tvshows'):
                for item in jsonobject['result']['tvshows']:
                    Media = {}
                    Media['name'] = item['label']
                    Media['path'] = _media_path(item['file'])
                    Media['id'] = item['imdbnumber']
                    Media['tvshowid'] = item['tvshowid']
                    ### Search for season numbers
                    json_response_season = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"tvshowid":%s }, "id": 1}' %Media['tvshowid'])
                    jsonobject_season = simplejson.loads(json_response_season)
                    if jsonobject_season['result'].has_key('limits'):
                        limits = jsonobject_season['result']['limits']
                        Media['seasontotal'] = limits['total']
                        Media['seasonstart'] = limits['start']
                        Media['seasonend'] = limits['end']
                    Medialist.append(Media)
        elif media_type == 'movie':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
            json_response = unicode(json_response,'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('movies'):
                for item in jsonobject['result']['movies']:
                    Media = {}
                    Media['name'] = item['label']
                    Media['path'] = _media_path(item['file'])
                    Media['id'] = item['imdbnumber']
                    Media['movieid'] = item['movieid']
                    Medialist.append(Media)
        else:
            log('No JSON results found')
        return Medialist


def _media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1]
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies
    if path.startswith("rar"):
        path = os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]
    return path