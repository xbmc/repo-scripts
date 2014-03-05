#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

#import modules
import os
import xbmc
import urllib
import sys

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

### import libraries
from lib.utils import log

### get datalist from the unique media item
# Retrieve JSON list
def _media_unique(media_type, dbid):
    log('Using JSON for retrieving %s info' %media_type)
    Medialist = []
    if media_type == 'tvshow':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"properties": ["file", "imdbnumber", "art"], "tvshowid":%s}, "id": 1}' %dbid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('tvshowdetails'):
            item = jsonobject['result']['tvshowdetails']
            # Search for season information
            json_query_season = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "art"], "sort": { "method": "label" }, "tvshowid":%s }, "id": 1}' %item.get('tvshowid',''))
            json_query_season = unicode(json_query_season, 'utf-8', errors='ignore')
            jsonobject_season = simplejson.loads(json_query_season)
            # Get start/end and total seasons
            if jsonobject_season['result'].has_key('limits'):
                season_limit = jsonobject_season['result']['limits']
            # Get the season numbers
            seasons_list =[]
            if jsonobject_season['result'].has_key('seasons'):
                seasons = jsonobject_season['result']['seasons']
                for season in seasons:
                    seasons_list.append(season.get('season')) 
            Medialist.append({'id': item.get('imdbnumber',''),
                              'dbid': item.get('tvshowid',''),
                              'name': item.get('label',''),
                              'path': media_path(item.get('file','')),
                              'seasontotal': season_limit.get('total',''),
                              'seasonstart': season_limit.get('start',''),
                              'seasonend': season_limit.get('end',''),
                              'seasons': seasons_list,
                              'art' : item.get('art',''),
                              'mediatype': media_type})

    elif media_type == 'movie':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["file", "imdbnumber", "year", "trailer", "streamdetails", "art"], "movieid":%s }, "id": 1}' %dbid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('moviedetails'):
            item = jsonobject['result']['moviedetails']
            disctype = media_disctype(item.get('file','').encode('utf-8').lower(),
                                      item['streamdetails']['video'])
            streamdetails = item['streamdetails']['video']
            Medialist.append({'dbid': item.get('movieid',''),
                              'id': item.get('imdbnumber',''),
                              'name': item.get('label',''),
                              'year': item.get('year',''),
                              'file': item.get('file',''),
                              'path': media_path(item.get('file','')),
                              'trailer': item.get('trailer',''),
                              'disctype': disctype,
                              'art' : item.get('art',''),
                              'mediatype': media_type})

    elif media_type == 'musicvideo':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideoDetails", "params": {"properties": ["file", "artist", "album", "track", "runtime", "year", "genre", "art"], "movieid":%s }, "id": 1}' %dbid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('musicvideodetails'):
            item = jsonobject['result']['musicvideodetails']
            Medialist.append({'dbid': item.get('musicvideoid',''),
                              'id': '',
                              'name': item.get('label',''),
                              'artist': item.get('artist',''),
                              'album': item.get('album',''),
                              'track': item.get('track',''),
                              'runtime': item.get('runtime',''),
                              'year': item.get('year',''),
                              'path': media_path(item.get('file','')),
                              'art' : item.get('art',''),
                              'mediatype': media_type})
    else:
            log('No JSON results found')
    return Medialist

def _media_listing(media_type):
    log('Using JSON for retrieving %s info' %media_type)
    Medialist = []
    if media_type == 'tvshow':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber", "art"], "sort": { "method": "label" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('tvshows'):
            for item in jsonobject['result']['tvshows']:
                # Search for season information
                json_query_season = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "art"], "sort": { "method": "label" }, "tvshowid":%s }, "id": 1}' %item.get('tvshowid',''))
                jsonobject_season = simplejson.loads(json_query_season)
                # Get start/end and total seasons
                if jsonobject_season['result'].has_key('limits'):
                    season_limit = jsonobject_season['result']['limits']
                # Get the season numbers
                seasons_list =[]
                if jsonobject_season['result'].has_key('seasons'):
                    seasons = jsonobject_season['result']['seasons']
                    for season in seasons:
                        seasons_list.append(season.get('season')) 
                Medialist.append({'id': item.get('imdbnumber',''),
                                  'dbid': item.get('tvshowid',''),
                                  'name': item.get('label',''),
                                  'path': media_path(item.get('file','')),
                                  'seasontotal': season_limit.get('total',''),
                                  'seasonstart': season_limit.get('start',''),
                                  'seasonend': season_limit.get('end',''),
                                  'seasons': seasons_list,
                                  'art' : item.get('art',''),
                                  'mediatype': media_type})

    elif media_type == 'movie':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "imdbnumber", "year", "trailer", "streamdetails", "art"], "sort": { "method": "label" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('movies'):
            for item in jsonobject['result']['movies']:
                disctype = media_disctype(item.get('file','').encode('utf-8').lower(),
                                          item['streamdetails']['video'])
                Medialist.append({'dbid': item.get('movieid',''),
                                  'id': item.get('imdbnumber',''),
                                  'name': item.get('label',''),
                                  'year': item.get('year',''),
                                  'file': item.get('file',''),
                                  'path': media_path(item.get('file','')),
                                  'trailer': item.get('trailer',''),
                                  'disctype': disctype,
                                  'art' : item.get('art',''),
                                  'mediatype': media_type})

    elif media_type == 'musicvideo':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["file", "artist", "album", "track", "runtime", "year", "genre", "art"], "sort": { "method": "album" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        jsonobject = simplejson.loads(json_query)
        if jsonobject.has_key('result') and jsonobject['result'].has_key('musicvideos'):
            for item in jsonobject['result']['musicvideos']:
                Medialist.append({'dbid': item.get('musicvideoid',''),
                                  'id': '',
                                  'name': item.get('label',''),
                                  'artist': item.get('artist',''),
                                  'album': item.get('album',''),
                                  'track': item.get('track',''),
                                  'runtime': item.get('runtime',''),
                                  'year': item.get('year',''),
                                  'path': media_path(item.get('file','')),
                                  'art' : item.get('art',''),
                                  'mediatype': media_type})
    else:
            log('No JSON results found')
    return Medialist

def media_disctype(filename, streamdetails):
    if (('dvd') in filename and not any(x in filename for x in ['hddvd', 'hd-dvd']) or (filename.endswith('.vob') or filename.endswith('.ifo'))):
        disctype = 'dvd'
    elif ('3d' in filename and not 'ac3d' in filename):
        disctype = '3d'
    elif any(x in filename for x in ['bluray', 'blu-ray', 'brrip', 'bdrip']):
        disctype = 'bluray'
    elif streamdetails:
        videowidth = streamdetails[0]['width']
        videoheight = streamdetails[0]['height']
        if videowidth <= 720 and videoheight <= 480:
            disctype = 'dvd'
        else:
            disctype = 'bluray'
    else:
        disctype = 'n/a'
    return disctype

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
    else:
        path = [path]
    return path
