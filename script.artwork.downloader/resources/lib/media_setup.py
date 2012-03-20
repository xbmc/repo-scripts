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
from resources.lib.utils import *
from elementtree import ElementTree as ET
# Commoncache plugin import
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

cacheMedia = StorageServer.StorageServer("ArtworkDownloader",1)
#cacheMedia.timeout = 600 # In seconds

# Retrieve JSON data from cache function
def _media_listing(media_type):
    result = cacheMedia.cacheFunction( _media_listing_new, media_type )
    if len(result) == 0 or result == 'Empty':
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
                    Media = {}
                    Media['name']       = item['label']
                    Media['path']       = media_path(item['file'])
                    Media['id']         = item['imdbnumber']
                    Media['tvshowid']   = item['tvshowid']
                    # Search for season information
                    json_response_season = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season"], "sort": { "method": "label" }, "tvshowid":%s }, "id": 1}' %Media['tvshowid'])
                    jsonobject_season = simplejson.loads(json_response_season)
                    # Get start/end and total seasons
                    if jsonobject_season['result'].has_key('limits'):
                        limits = jsonobject_season['result']['limits']
                        Media['seasontotal'] = limits['total']
                        Media['seasonstart'] = limits['start']
                        Media['seasonend'] = limits['end']
                    # Get the season numbers
                    if jsonobject_season['result'].has_key('seasons'):
                        seasons = jsonobject_season['result']['seasons']
                        Media['seasons'] =[]
                        for season in seasons:
                            Media['seasons'].append(season['season'])            
                    '''
                    # Retrieve season folder path
                    i = Media['seasonstart']
                    Media['seasonpaths'] = []
                    while( i <= Media['seasonend'] and not xbmc.abortRequested ):
                        json_response_episode = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid":%s, "season":%s, "properties": ["file"] }, "id": 1}' %(Media['tvshowid'],i) )
                        jsonobject_episode = simplejson.loads(json_response_episode)
                        itempath = ''
                        Seasonitem = {}
                        if jsonobject_episode['result'].has_key('episodes'):
                            for item in jsonobject_episode['result']['episodes']:
                                itempath = ( media_path(item['file']) )
                                if itempath:
                                    break
                        Seasonitem['seasonpath'] = itempath
                        Seasonitem['seasonnumber'] = str( i )
                        #log('Path: %s' %Seasonitem['seasonpath'] )
                        #log('Number: %s'%Seasonitem['seasonnumber'] )
                        if Seasonitem['seasonpath']:
                            Media['seasonpaths'].append(Seasonitem)
                        i += 1
                    '''
                    #log(Media)
                    Medialist.append(Media)
        
        elif media_type == 'movie':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "imdbnumber", "year", "trailer", "streamdetails"], "sort": { "method": "label" } }, "id": 1}')
            json_response = unicode(json_response, 'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            
            if jsonobject['result'].has_key('movies'):
                for item in jsonobject['result']['movies']:
                    Media = {}
                    Media['movieid']    = item['movieid']
                    Media['name']       = item['label']
                    Media['year']       = item['year']
                    Media['path']       = media_path(item['file'])
                    Media['file']       = item['file']
                    Media['trailer']    = item['trailer']
                    Media['id']         = item['imdbnumber']
                    # Get streamdetails
                    file = Media['file'].encode('utf-8').lower()
                    if ( ('dvd') in file and not ('hddvd' or 'hd-dvd') in file ) or ( file.endswith('.vob' or '.ifo') ):
                        Media['disctype'] = 'dvd'
                        #log('Match on filename: %s' %Media['disctype'] )
                    elif '3d' in file:
                        Media['disctype'] = '3d'
                        #log('Match on filename: %s' %Media['disctype'] )
                    elif ( ('bluray' or 'blu-ray' or 'brrip' or 'bdrip') in file ):
                        Media['disctype'] = 'bluray'
                        #log('Match on filename: %s' %Media['disctype'] )
                    elif item['streamdetails'] != None and item['streamdetails'].has_key('video'):
                        videowidth = item['streamdetails']['video'][0]['width']
                        videoheight = item['streamdetails']['video'][0]['height']
                        if videowidth <= 720 and videoheight <= 480:
                            Media['disctype'] = 'dvd'
                        else:
                            Media['disctype'] = 'bluray'
                        #log('Match on streamdetails: %s' %Media['disctype'] )
                    else:
                        Media['disctype'] = 'n/a'
                    Medialist.append(Media)

        elif media_type == 'musicvideo':
            json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["file", "artist", "album", "track", "runtime", "year", "genre"], "sort": { "method": "album" } }, "id": 1}')
            json_response = unicode(json_response, 'utf-8', errors='ignore')
            jsonobject = simplejson.loads(json_response)
            if jsonobject['result'].has_key('musicvideos'):
                for item in jsonobject['result']['musicvideos']:
                    Media = {}
                    Media['id']         = ''
                    Media['movieid']    = item['musicvideoid']
                    Media['name']       = item['label']
                    Media['artist']     = item['artist']
                    Media['album']      = item['album']
                    Media['track']      = item['track']
                    Media['runtime']    = item['runtime']
                    Media['year']       = item['year']
                    Media['path']       = media_path(item['file'])
                    Medialist.append(Media)
        else:
            log('No JSON results found')
    except Exception, NoneType:
        Medialist = 'Empty'
        log('No %s found in your library' %media_type)
    except Exception, e:
        Medialist = 'Empty'
        log( str( e ), xbmc.LOGERROR )
    return Medialist


def media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies
    if path.startswith("rar"):
        path = os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]
    return path