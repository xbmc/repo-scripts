#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
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
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import random
import urllib
import datetime
from traceback import print_exc
from time import gmtime, strftime

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
    
__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString
PLOT_ENABLE = True

import library
LIBRARY = library.LibraryFunctions()

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()
        self.WINDOW = xbmcgui.Window(10000)
        
        if self.TYPE == "randommovies":
            self.parse_movies( 'randommovies', 32004 )
        elif self.TYPE == "recentmovies":
            self.parse_movies( 'recentmovies', 32005 )
        elif self.TYPE == "recommendedmovies":
            self.parse_movies( 'recommendedmovies', 32006 )
        elif self.TYPE == "recommendedepisodes":
            self.parse_tvshows_recommended( 'recommendedepisodes', 32010 )
        elif self.TYPE == "recentepisodes":
            self.parse_tvshows( 'recentepisodes', 32008 )
        elif self.TYPE == "randomepisodes":
            self.parse_tvshows( 'randomepisodes', 32007 )
        elif self.TYPE == "randomalbums":
            self.parse_albums( 'randomalbums', 32016 )
        elif self.TYPE == "recentalbums":
            self.parse_albums( 'recentalbums', 32017 )
        elif self.TYPE == "recommendedalbums":
            self.parse_albums( 'recommendedalbums', 32018 )
        elif self.TYPE == "randomsongs":
            self.parse_song( 'randomsongs', 32015 )
            
        # Play an albums
        elif self.TYPE == "play_album":
            self.play_album( self.ALBUM )
            
        if not self.TYPE:
            # Show a root menu
            full_liz = list()
            items = [[32004, "randommovies"], [32005, "recentmovies"], [32006, "recommendedmovies"], [32007, "randomepisodes"], [32008, "recentepisodes"], [32010, "recommendedepisodes"], [32016, "randomalbums"], [32017, "recentalbums"], [32018, "recommendedalbums"], [32015, "randomsongs"]]
            for item in items:
                liz = xbmcgui.ListItem( __localize__( item[0] ) )
                liz.setIconImage( "DefaultFolder.png" )
                full_liz.append( ( "plugin://service.library.data.provider?type=" + item[1], liz, True ) )

            xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
            xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
                
            
    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)
        
    def parse_movies(self, request, list_type):
        json_query = self._get_data( request )
        if json_query:
            json_query = simplejson.loads(json_query)
            if json_query.has_key('result') and json_query['result'].has_key('movies'):
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                full_liz = list()
                for item in json_query['result']['movies']:
                    watched = False
                    if item['playcount'] >= 1:
                        watched = True
                    if not PLOT_ENABLE and not watched:
                        plot = __localize__(32014)
                    else:
                        plot = item['plot']
                    if len(item['studio']) > 0:
                        studio = item['studio'][0]
                    else:
                        studio = ""
                    if len(item['country']) > 0:
                        country = item['country'][0]
                    else:
                        country = ""
                    # create a list item
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo( type="Video", infoLabels={ "Title": item['title'] })
                    liz.setInfo( type="Video", infoLabels={ "OriginalTitle": item['originaltitle'] })
                    liz.setInfo( type="Video", infoLabels={ "Year": item['year'] })
                    liz.setInfo( type="Video", infoLabels={ "Genre": " / ".join(item['genre']) })
                    liz.setInfo( type="Video", infoLabels={ "Studio": studio })
                    liz.setInfo( type="Video", infoLabels={ "Country": country })
                    liz.setInfo( type="Video", infoLabels={ "Plot": plot })
                    liz.setInfo( type="Video", infoLabels={ "PlotOutline": item['plotoutline'] })
                    liz.setInfo( type="Video", infoLabels={ "Tagline": item['tagline'] })
                    liz.setInfo( type="Video", infoLabels={ "Rating": str(float(item['rating'])) })
                    liz.setInfo( type="Video", infoLabels={ "Votes": item['votes'] })
                    liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa'] })
                    liz.setInfo( type="Video", infoLabels={ "Director": " / ".join(item['director']) })
                    liz.setInfo( type="Video", infoLabels={ "Trailer": item['trailer'] })
                    liz.setInfo( type="Video", infoLabels={ "Playcount": item['playcount'] })
                    liz.setProperty("resumetime", str(item['resume']['position']))
                    liz.setProperty("totaltime", str(item['resume']['total']))
                    liz.setProperty("type", __localize__(list_type))

                    liz.setArt(item['art'])
                    liz.setThumbnailImage(item['art'].get('poster', ''))
                    liz.setIconImage('DefaultVideoCover.png')
                    liz.setProperty("fanart_image", item['art'].get('fanart', ''))
                    for key, value in item['streamdetails'].iteritems():
                        for stream in value:
                            liz.addStreamInfo( key, stream ) 
                    full_liz.append((item['file'], liz, False))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
                xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            del json_query
        
    def parse_tvshows_recommended(self, request, list_type):
        json_query = self._get_data( request )
        if json_query:
            # First unplayed episode of recent played tvshows
            json_query = simplejson.loads(json_query)
            if json_query.has_key('result') and json_query['result'].has_key('tvshows'):
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                full_liz = list()
                count = 0
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    count += 1
                    #json_query2 = self.load_file( str( item['tvshowid'] ) )
                    json_query2 = self.WINDOW.getProperty( "recommendedepisodes-data-" + str( item['tvshowid'] ) )
                    if json_query:
                        json_query2 = simplejson.loads(json_query2)
                        if json_query2.has_key('result') and json_query2['result'] != None and json_query2['result'].has_key('episodes'):
                            for item2 in json_query2['result']['episodes']:
                                episode = "%.2d" % float(item2['episode'])
                                season = "%.2d" % float(item2['season'])
                                episodeno = "s%se%s" %(season,episode)
                                break
                        watched = False
                        if item2['playcount'] >= 1:
                            watched = True
                        if not PLOT_ENABLE and not watched:
                            plot = __localize__(32014)
                        else:
                            plot = item2['plot']
                        if len(item['studio']) > 0:
                            studio = item['studio'][0]
                        else:
                            studio = ""
                        liz = xbmcgui.ListItem(item2['title'])
                        liz.setInfo( type="Video", infoLabels={ "Title": item2['title'] })
                        liz.setInfo( type="Video", infoLabels={ "Episode": item2['episode'] })
                        liz.setInfo( type="Video", infoLabels={ "Season": item2['season'] })
                        liz.setInfo( type="Video", infoLabels={ "Studio": studio })
                        liz.setInfo( type="Video", infoLabels={ "Premiered": item2['firstaired'] })
                        liz.setInfo( type="Video", infoLabels={ "Plot": plot })
                        liz.setInfo( type="Video", infoLabels={ "TVshowTitle": item2['showtitle'] })
                        liz.setInfo( type="Video", infoLabels={ "Rating": str(round(float(item2['rating']),1)) })
                        liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa'] })
                        liz.setInfo( type="Video", infoLabels={ "Playcount": item2['playcount'] })
                        liz.setProperty("episodeno", episodeno)
                        liz.setProperty("resumetime", str(item2['resume']['position']))
                        liz.setProperty("totaltime", str(item2['resume']['total']))
                        liz.setProperty("type", __localize__(list_type))
                        liz.setArt(item2['art'])
                        liz.setThumbnailImage(item2['art'].get('thumb',''))
                        liz.setIconImage('DefaultTVShows.png')
                        liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart',''))
                        for key, value in item2['streamdetails'].iteritems():
                            for stream in value:
                                liz.addStreamInfo( key, stream ) 
                        
                        full_liz.append((item2['file'], liz, False))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
                xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            del json_query

    def parse_tvshows(self, request, list_type):
        #json_query = unicode(self.WINDOW.getProperty( request + '-data' ) , 'utf-8', errors='ignore')
        json_query = self._get_data( request )
        if json_query:
            json_query = simplejson.loads(json_query)
            if json_query.has_key('result') and json_query['result'].has_key('episodes'):
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                full_liz = list()
                for item in json_query['result']['episodes']:
                    episode = "%.2d" % float(item['episode'])
                    season = "%.2d" % float(item['season'])
                    episodeno = "s%se%s" %(season,episode)
                    watched = False
                    if item['playcount'] >= 1:
                        watched = True
                    if not PLOT_ENABLE and not watched:
                        plot = __localize__(32014)
                    else:
                        plot = item['plot']
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo( type="Video", infoLabels={ "Title": item['title'] })
                    liz.setInfo( type="Video", infoLabels={ "Episode": item['episode'] })
                    liz.setInfo( type="Video", infoLabels={ "Season": item['season'] })
                    #liz.setInfo( type="Video", infoLabels={ "Studio": item['studio'][0] })
                    liz.setInfo( type="Video", infoLabels={ "Premiered": item['firstaired'] })
                    liz.setInfo( type="Video", infoLabels={ "Plot": plot })
                    liz.setInfo( type="Video", infoLabels={ "TVshowTitle": item['showtitle'] })
                    liz.setInfo( type="Video", infoLabels={ "Rating": str(round(float(item['rating']),1)) })
                    #liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa'] })
                    liz.setInfo( type="Video", infoLabels={ "Playcount": item['playcount'] })
                    liz.setProperty("episodeno", episodeno)
                    liz.setProperty("resumetime", str(item['resume']['position']))
                    liz.setProperty("totaltime", str(item['resume']['total']))
                    liz.setProperty("type", __localize__(list_type))
                    liz.setArt(item['art'])
                    liz.setThumbnailImage(item['art'].get('thumb',''))
                    liz.setIconImage('DefaultTVShows.png')
                    liz.setProperty("fanart_image", item['art'].get('tvshow.fanart',''))
                    for key, value in item['streamdetails'].iteritems():
                        for stream in value:
                            liz.addStreamInfo( key, stream ) 
                    full_liz.append((item['file'], liz, False))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
                xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            del json_query
        
    def parse_song(self, request, list_type):
        json_query = self._get_data( request )
        if json_query:
            json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "playcount", "genre", "artist", "album", "year", "file", "thumbnail", "fanart", "rating"], "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}, "limits": {"end": %d},' %self.LIMIT
            json_query = simplejson.loads(json_query)
            if json_query.has_key('result') and json_query['result'].has_key('songs'):
                xbmcplugin.setContent(int(sys.argv[1]), 'songs')
                full_liz = list()
                for item in json_query['result']['songs']:
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo( type="Music", infoLabels={ "Title": item['title'] })
                    liz.setInfo( type="Music", infoLabels={ "Artist": item['artist'][0] })
                    liz.setInfo( type="Music", infoLabels={ "Genre": " / ".join(item['genre']) })
                    liz.setInfo( type="Music", infoLabels={ "Year": item['year'] })
                    liz.setInfo( type="Music", infoLabels={ "Rating": str(float(item['rating'])) })
                    liz.setInfo( type="Music", infoLabels={ "Album": item['album'] })
                    liz.setProperty("type", __localize__(list_type))

                    liz.setThumbnailImage(item['thumbnail'])
                    liz.setIconImage('DefaultMusicSongs.png')
                    liz.setProperty("fanart_image", item['fanart'])

                    full_liz.append((item['file'], liz, False))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
                xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            del json_query
        
    def parse_albums (self, request, list_type):
        json_query = self._get_data( request )
        if json_query:
            json_query = simplejson.loads(json_query)
            if json_query.has_key('result') and json_query['result'].has_key('albums'):
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                full_liz = list()
                for item in json_query['result']['albums']:
                    rating = str(item['rating'])
                    if rating == '48':
                        rating = ''
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo( type="Music", infoLabels={ "Title": item['title'] })
                    liz.setInfo( type="Music", infoLabels={ "Artist": item['artist'][0] })
                    liz.setInfo( type="Music", infoLabels={ "Genre": " / ".join(item['genre']) })
                    liz.setInfo( type="Music", infoLabels={ "Year": item['year'] })
                    liz.setInfo( type="Music", infoLabels={ "Rating": rating })
                    liz.setProperty("Album_Mood", " / ".join(item['mood']) )
                    liz.setProperty("Album_Style", " / ".join(item['style']) )
                    liz.setProperty("Album_Theme", " / ".join(item['theme']) )
                    liz.setProperty("Album_Type", " / ".join(item['type']) )
                    liz.setProperty("Album_Label", item['albumlabel'])
                    liz.setProperty("Album_Description", item['description'])
                    liz.setProperty("type", __localize__(list_type))

                    liz.setThumbnailImage(item['thumbnail'])
                    liz.setIconImage('DefaultAlbumCover.png')
                    liz.setProperty("fanart_image", item['fanart'])
                    
                    # Path will call plugin again, with the album id
                    path = sys.argv[0] + "?type=play_album&album=" + str(item['albumid'])
                    
                    full_liz.append((path, liz, False))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
                xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            del json_query
        
    def play_album( self, album ):
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(album) )
        # Return ResolvedUrl as failed, as we've taken care of what to play
        xbmcplugin.setResolvedUrl( handle=int( sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem() )
        
    def _get_data( self, request ):
        if request == "randommovies":
            return LIBRARY._fetch_random_movies( self.USECACHE )
        elif request == "recentmovies":
            return LIBRARY._fetch_recent_movies( self.USECACHE )
        elif request == "recommendedmovies":
            return LIBRARY._fetch_recommended_movies( self.USECACHE )

        elif request == "randomepisodes":
            return LIBRARY._fetch_random_episodes( self.USECACHE )
        elif request == "recentepisodes":
            return LIBRARY._fetch_recent_episodes( self.USECACHE )
        elif request == "recommendedepisodes":
            return LIBRARY._fetch_recommended_episodes( self.USECACHE )

        elif request == "randomalbums":
            return LIBRARY._fetch_random_albums( self.USECACHE )
        elif request == "recentalbums":
            return LIBRARY._fetch_recent_albums( self.USECACHE )
        elif request == "recommendedalbums":
            return LIBRARY._fetch_recommended_albums( self.USECACHE )
        
        elif request == "randomsongs":
            return LIBRARY._fetch_random_songs( self.USECACHE )        
            
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
        except:
            params = {}
        self.TYPE = params.get( "?type", "" )
        self.ALBUM = params.get( "album", "" )
        self.USECACHE = params.get( "reload", False )
        if self.USECACHE is not False:
            self.USECACHE == True
        global PLOT_ENABLE 
        PLOT_ENABLE = __addon__.getSetting("plot_enable")  == 'true'
        self.RANDOMITEMS_UNPLAYED = __addon__.getSetting("randomitems_unplayed")  == 'true'
    
log('script version %s started' % __addonversion__)
Main()
log('script version %s stopped' % __addonversion__)