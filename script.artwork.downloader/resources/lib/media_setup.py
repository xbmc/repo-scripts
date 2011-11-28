import re
import xbmc
import urllib
import simplejson
import unicodedata
from resources.lib.utils import _log as log

### get list of all tvshows and movies with their imdbnumber from library

# Fixes unicode problems
def _unicode( text, encoding='utf-8' ):
    try: text = unicode( text, encoding )
    except: pass
    return text

def _normalize_string( text ):
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text
# Retrieve JSON list
def _media_listing(media_type):
        log('Using JSON for retrieving %s info' %media_type)
        Medialist = []
        if media_type == 'tvshow':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('tvshows'):
                for item in jsonobject['result']['tvshows']:
                    Media = {}
                    Media['name'] = _normalize_string(item['label'])
                    Media['path'] = item['file']
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
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('movies'):
                for item in jsonobject['result']['movies']:
                    Media = {}
                    Media['name'] = _normalize_string(item['label'])
                    Media['path'] = item['file']
                    Media['id'] = item['imdbnumber']
                    Media['movieid'] = item['movieid']
                    Medialist.append(Media)
        else:
            log('No JSON results found')
        return Medialist