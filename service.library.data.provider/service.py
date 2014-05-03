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
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
PLOT_ENABLE = True

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()
        self.WINDOW = xbmcgui.Window(10000)
        
        # Create datapath if not exists
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)

        # clear our property, if another instance is already running it should stop now
        self._init_vars()
        self.WINDOW.clearProperty('LibraryDataProvider_Running')
        a_total = datetime.datetime.now()
        self._fetch_random()
        self._fetch_recent()
        self._fetch_recommended()
        b_total = datetime.datetime.now()
        c_total = b_total - a_total
        log('Total time needed for all queries: %s' % c_total)
        # give a possible other instance some time to notice the empty property
        self.WINDOW.setProperty('LibraryDataProvider_Running', 'true')
        self._daemon()
            
            
    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.Player = Widgets_Player(action = self._update)
        self.Monitor = Widgets_Monitor(update_listitems = self._update)

            
    def _fetch_random( self ):
        self._fetch_random_movies()
        self._fetch_random_episodes()
        self._fetch_random_songs()
        self._fetch_random_albums()
        
    def _fetch_random_movies( self ):
        file = self.open_file( 'randommovies' )
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director"], "limits": {"end": %d},' % self.LIMIT
        if self.RANDOMITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" } }}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "randommovies",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
    def _fetch_random_episodes( self ):
        file = self.open_file( 'randomepisodes' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "streamdetails", "firstaired", "runtime"], "limits": {"end": %d},' %self.LIMIT
        if self.RANDOMITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "randomepisodes",strftime( "%Y%m%d%H%M%S",gmtime() ) )

    def _fetch_random_songs( self ):
        file = self.open_file( 'randomsongs' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "playcount", "genre", "artist", "album", "year", "file", "thumbnail", "fanart", "rating"], "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}, "limits": {"end": %d},' %self.LIMIT
        if self.RANDOMITEMS_UNPLAYED == "True":
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}'  %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s  "sort": {"method": "random"}}}'  %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "randomsongs",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
    def _fetch_random_albums( self ):
        file = self.open_file( 'randomalbums' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "theme", "mood", "style", "type", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount"], "limits": {"end": %d},' %self.LIMIT
        json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "randomalbums",strftime( "%Y%m%d%H%M%S",gmtime() ) )

        
    def _fetch_recent( self ):
        self._fetch_recent_movies()
        self._fetch_recent_episodes()
        self._fetch_recent_albums()
        
    def _fetch_recent_movies( self ):
        file = self.open_file( 'recentmovies' )
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director"], "limits": {"end": %d},' % self.LIMIT
        if self.RECENTITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}, "filter": {"field": "playcount", "operator": "is", "value": "0"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "recentmovies",strftime( "%Y%m%d%H%M%S",gmtime() ) )

    def _fetch_recent_episodes( self ):
        file = self.open_file( 'recentepisodes' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "streamdetails", "firstaired", "runtime"], "limits": {"end": %d},' %self.LIMIT
        if self.RECENTITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "recentepisodes",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
    def _fetch_recent_albums( self ):
        file = self.open_file( 'recentalbums' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "theme", "mood", "style", "type", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount"], "limits": {"end": %d},' %self.LIMIT
        json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded" }}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "recentalbums",strftime( "%Y%m%d%H%M%S",gmtime() ) )
    
    
    def _fetch_recommended( self ):
        self._fetch_recommended_movies()
        self._fetch_recommended_episodes()
        self._fetch_recommended_albums()

    def _fetch_recommended_movies( self ):
        file = self.open_file( 'recommendedmovies' )
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director"], "limits": {"end": %d},' % self.LIMIT
        json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "recommendedmovies",strftime( "%Y%m%d%H%M%S",gmtime() ) )
    
    def _fetch_recommended_episodes( self ):
        file = self.open_file( 'recommendedepisodes' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "streamdetails", "firstaired", "runtime"], "limits": {"end": %d},' %self.LIMIT
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "mpaa", "file", "art"], "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %self.LIMIT)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query1 = simplejson.loads(json_query)
        if json_query1.has_key('result') and json_query1['result'].has_key('tvshows'):
            for item in json_query1['result']['tvshows']:
                file2 = self.open_file( str( item['tvshowid'] ) )
                if xbmc.abortRequested:
                    break
                json_query2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": ["title", "playcount", "plot", "season", "episode", "showtitle", "file", "lastplayed", "rating", "resume", "art", "streamdetails", "firstaired", "runtime"], "sort": {"method": "episode"}, "filter": {"field": "playcount", "operator": "is", "value": "0"}, "limits": {"end": 1}}, "id": 1}' %item['tvshowid'])
                json_query2 = unicode(json_query2, 'utf-8', errors='ignore')
                self.save_data( file2, json_query2 )
                self.WINDOW.setProperty(str(item['tvshowid']), json_query2)
        
        self.save_data( file, json_query )
        xbmcgui.Window( 10000 ).setProperty( "recommendedepisodes",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
    def _fetch_recommended_albums( self ):
        file = self.open_file( 'recommendedalbums' )
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "theme", "mood", "style", "type", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount"], "limits": {"end": %d},' %self.LIMIT
        json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "playcount" }}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        self.save_data( file, json_query)
        xbmcgui.Window( 10000 ).setProperty( "recommendedalbums",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
        
    def open_file(self, request):
        path = os.path.join( __datapath__, request + ".json" )
        log( "Opening file - " + path )
        
        # Keep trying to open file until succeeded (avoids race condition)
        fileOpened = False
        tries = 0
        
        while fileOpened == False:
            try:
                file = xbmcvfs.File( path, 'w' )
                fileOpened = True
            except:
                print_exc()
                tries = tries + 1
                wait = 1
                
        return( file )
        
    def save_data(self, file, data):
        log( "Saving file" )
        file.write( data.encode("utf-8") )
        file.close()
        
        
    def _daemon(self):
        # deamon is meant to keep script running at all time
        count = 0
        home_update = False
        while (not xbmc.abortRequested) and self.WINDOW.getProperty('LibraryDataProvider_Running') == 'true':
            xbmc.sleep(1000)
            if not xbmc.Player().isPlayingVideo():
                # Update random items
                count += 1
                if count == 1200: # 10 minutes
                    self._fetch_random()
                    count = 0    # reset counter
                    
    def _update(self, type):
        xbmc.sleep(1000)
        if type == 'movie':
            self._fetch_recommended_movies()
            self._fetch_recent_movies()
        elif type == 'episode':
            self._fetch_recommended_episodes()
            self._fetch_recent_episodes()
        elif type == 'video':
            #only on db update
            self._fetch_recommended_movies()
            self._fetch_recommended_episodes()
            self._fetch_recent_movies()
            self._fetch_recent_episodes()
        elif type == 'music':
            self._fetch_recommended_albums()
            self._fetch_recent_albums()
            
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
        except:
            params = {}
        self.LIMIT = int(__addon__.getSetting("limit"))
        self.TYPE = params.get( "?type", "" )
        self.ALBUM = params.get( "album", "" )
        self.RECENTITEMS_UNPLAYED = __addon__.getSetting("recentitems_unplayed")  == 'true'
        global PLOT_ENABLE 
        PLOT_ENABLE = __addon__.getSetting("plot_enable")  == 'true'
        self.RANDOMITEMS_UNPLAYED = __addon__.getSetting("randomitems_unplayed")  == 'true'
    
class Widgets_Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.update_listitems = kwargs['update_listitems']

    def onDatabaseUpdated(self, database):
        self.update_listitems(database)
        

class Widgets_Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.type = ""
        self.action = kwargs[ "action" ]
        self.substrings = [ '-trailer', 'http://' ]

    def onPlayBackStarted(self):
        xbmc.sleep(1000)
        # Set values based on the file content
        if (self.isPlayingAudio()):
            self.type = "music"  
        else:
            if xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
                filename = ''
                isMovie = True
                try:
                    filename = self.getPlayingFile()
                except:
                    pass
                if filename != '':
                    for string in self.substrings:
                        if string in filename:
                            isMovie = False
                            break
                if isMovie:
                    self.type = "movie"
            elif xbmc.getCondVisibility('VideoPlayer.Content(episodes)'):
                # Check for tv show title and season to make sure it's really an episode
                if xbmc.getInfoLabel('VideoPlayer.Season') != "" and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != "":
                    self.type = "episode"

    def onPlayBackEnded(self):
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        if self.type == 'movie':
            self.action('movie')
        elif self.type == 'episode':
            self.action('episode')
        elif self.type == 'music':
            self.action('music')
        self.type = ""
    
log('service version %s started' % __addonversion__)
Main()
log('service version %s stopped' % __addonversion__)