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
import thread
import socket
import cPickle as pickle
from datetime import datetime
from traceback import print_exc
from time import gmtime, strftime
import _strptime

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")

__resource__     = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")


sys.path.append(__resource__)
import library, sql, tmdb


def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        log('script (service) version %s started' % __addonversion__)
        self.running = True
        try:

            #json_query = simplejson.loads( xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "JSONRPC.Introspect", "id": 1}') )
            #print(simplejson.dumps(json_query, sort_keys=True, indent=4 * ' '))

            self._init_vars()

            self.QUIT = False

            # Before we load any threads, we need to use strftime, to ensure it is imported (potential threading issue)
            strftime( "%Y%m%d%H%M%S",gmtime() )

            # Start threads
            thread.start_new_thread( self._player_daemon, () )
            thread.start_new_thread( self._socket_daemon, () )

            # If we're a client, tell the server we're live
            if __addon__.getSetting( "role" ) == "Client":
                self.pingServer( True )

            self._daemon()

            # Clear xbmcgui items
            self.movieWidget = []
            self.episodeWidget = []
            self.albumWidget = []
            self.pvrWidget = []
            self.nextupWidget = []
        except:
            log( "script (service) fatal error" )
            print_exc()
        self.running = False
        log( "(-> localhost) 'quit'" )
        clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        clientsocket.connect( ( "localhost", int( __addon__.getSetting( "port" ) ) ) )
        clientsocket.send( "QUIT||||EOD" )
        clientsocket.send( "QUIT||||EOD" )
        clientsocket.close()
        log('script (service) version %s stopped' % __addonversion__)
        self.WINDOW = xbmcgui.Window(10000)

    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.playingLiveTV = False

        self.movieWidget = []
        self.episodeWidget = []
        self.albumWidget = []
        self.pvrWidget = []

        self.nextupWidget = []

        self.movieLastUpdated = 0
        self.episodeLastUpdated = 0
        self.albumLastUpdated = 0
        self.pvrLastUpdated = 0

        self.lastMovieHabits = None
        self.lastEpisodeHabits = None
        self.lastAlbumHabits = None
        self.lastPVRHabits = None

        self.movieWeighting = None
        self.episodeWeighting = None
        self.albumWeighting = None
        self.pvrWeighting = None

        # Create empty client list
        self.clients = []

        # Create a socket
        self.serversocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

    def _player_daemon( self ):
        # This is the daemon which will add information about played media to the database

        # Create a connection to the database
        self.connectionWrite = sql.connect()

        # Create a player and monitor object
        self.Player = Widgets_Player( action = self.mediaStarted, ended = self.mediaEnded )
        self.Monitor = Widgets_Monitor( action = self.libraryUpdated )

        # Loop
        while not xbmc.abortRequested and self.running == True:
            xbmc.sleep( 1000 )

        del self.Player
        del self.Monitor

    def _socket_daemon( self ):
        # This is the daemon which will send back any requested widget (server) or update local skin strings (client)
        log( "Widget listener started on port %s" %( __addon__.getSetting( "port" ) ) )

        # Get the port, and convert it to an int
        port = int( __addon__.getSetting( "port" ) )

        # Bind the server
        self.serversocket.bind( ( "", port ) )
        self.serversocket.listen( 5 )

        # Set all last updated strings to -1, so the skin refreshes all
        # widgets now we're listening (Probably not needed, except for debug purposes)
        self.WINDOW.setProperty( "smartish.movies", "-1" )
        self.WINDOW.setProperty( "smartish.episodes", "-1" )
        self.WINDOW.setProperty( "smartish.pvr", "-1" )
        self.WINDOW.setProperty( "smartish.albums", "-1" )

        # Loop
        while not xbmc.abortRequested and self.running == True:
            try:
                connection, address = self.serversocket.accept()
            except socket.timeout:
                continue
            except:
                print_exc()
                continue
            thread.start_new_thread( self._socket_thread, (connection, address ) )
        log( "Widget listener stopped" )

    def _socket_thread( self, connection, address ):
        totalData = []
        while True:
            data = connection.recv( 1028 )
            if not data:
                break
            totalData.append( data )
            if "|EOD" in data:
                break

        data = "".join( totalData ).split( "||||" )

        if len( totalData ) > 0:
            if data[ 0 ] != "ping":
                log( "(%s -> *) '%s'" %( str( address[ 0 ] ), data[ 0 ] ) )
            if data[ 0 ] == "QUIT":
                connection.send( "QUITTING||||EOD" )
            else:
                # Messages from widget:

                # Display Widget
                returnlimit = int( __addon__.getSetting( "returnLimit" ) )
                if data[ 0 ] == "movies":
                    xbmcplugin.setContent( int( data[ 1 ] ), "movies" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.movieWidget[:returnlimit] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "episodes":
                    xbmcplugin.setContent( int( data[ 1 ] ), "episodes" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.episodeWidget[:returnlimit] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "albums":
                    xbmcplugin.setContent( int( data[ 1 ] ), "albums" )
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.albumWidget[:returnlimit] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )
                if data[ 0 ] == "pvr":
                    xbmcplugin.addDirectoryItems( int( data[1] ),self.pvrWidget[:returnlimit] )
                    xbmcplugin.endOfDirectory( handle=int( data[1] ) )

                # Play media
                if data[ 0 ] == "playpvr":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"channelid": ' + data[ 1 ] + '} } }' )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )
                if data[ 0 ] == "playrec":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"recordingid": ' + data[ 1 ] + '} } }' )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )
                if data[ 0 ] == "playalb":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": { "albumid": ' + data[ 1 ] + ' } } }' )
                    xbmcplugin.setResolvedUrl( handle=int( data[ 2 ] ), succeeded=False, listitem=xbmcgui.ListItem() )

                # Messages from server:

                # Build widgets with data from server
                if data[ 0 ] == "widget":
                    log( "(%s > *) Received data to build %s widget" %( str( address[ 0 ] ), data[ 1 ] ) )
                    thread.start_new_thread( self.gotWidgetFromServer, ( data[ 1 ], pickle.loads( data[ 2 ] ), pickle.loads( data[ 3 ] ) ) )


                # Messages from client:

                # Save last played information
                if data[ 0 ] == "lastplayed":
                    library.nowPlaying[ str( address[ 0 ] ) ] = ( data[ 1 ], data[ 2 ] )
                    library.lastplayedType = data[ 1 ]
                    library.lastplayedID = data[ 2 ]

                    if data[ 1 ] == "movie":
                        self.movieLastUpdated = 0
                        self.lastMovieHabits = None
                    if data[ 1 ] == "episode":
                        self.episodeLastUpdated = 0
                        self.lastEpisodeHabits = None
                        library.tvshowInformation.pop( int( data[ 3 ] ), None )
                        library.tvshowNextUnwatched.pop( int( data[ 3 ] ), None )
                        library.tvshowNewest.pop( int( data[ 3 ] ), None )
                    if data[ 1 ] == "recorded":
                        self.pvrLastUpdated = 0
                    if data[ 1 ] == "album":
                        self.albumLastUpdated = 0
                        self.lastAlbumHabits = None

                # Clear last played information
                if data[ 0 ] == "playbackended":
                    library.lastplayedType = None
                    library.lastplayedID = None
                    library.lastplayedID.pop( str( address[ 0 ] ), None )

                # Update the database with program information
                if data[ 0 ] == "mediainfo":
                    thread.start_new_thread( self.addClientDataToDatabase, ( pickle.loads( data[ 1 ] ), pickle.loads( data[ 2 ] ), pickle.loads( data[ 3 ] ) ) )

                # Update underlying widget data (e.g. after library update)
                if data[ 0 ] == "updatewidget":
                    if data[ 1 ] == "movie":
                        self.lastMovieHabits = None
                        self.movieLastUpdated = 0
                    if data[ 1 ] == "episode":
                        self.lastEpisodeHabits = None
                        self.episodeLastUpdated = 0
                    if data[ 1 ] == "album":
                        self.lastAlbumHabits = None
                        self.albumLastUpdated = 0

                # Client pinging us
                if data[ 0 ] == "ping":
                    # If client isn't registered, add it
                    if not str( address[ 0 ] ) in self.clients:
                        log( "New client has registered at address %s" %( str( address[ 0 ] ) ) )
                        self.clients.append( str( address[ 0 ] ) )

                        # Send widgets
                        thread.start_new_thread( self._send_widgets, ( str( address[ 0 ] ), None ) )

                # Client started up
                if data[ 0 ] == "clientstart":
                    # If client isn't registered, add it
                    if not str( address[ 0 ] ) in self.clients:
                        log( "New client has registered at address %s" %( str( address[ 0 ] ) ) )
                        self.clients.append( str( address[ 0 ] ) )

                    # Send widgets
                    thread.start_new_thread( self._send_widgets, ( str( address[ 0 ] ), None ) )

                if data[ 0 ] != "ping":
                    log( "(* -> %s) 'OK' '%s'" %( str( address[ 0 ] ), data[ 0 ] ) )
                connection.send( "OK||||%s||||EOD" %( data[ 0 ] ) )
        else:
            log( "(* -> %s) 'NODATA' '%s'" %( str( address[ 0 ] ), data[ 0 ] ) )
            connection.send( "NODATA||||EOD" )

    def _send_widgets( self, address, unused ):
        # Send any widgets to client
        if self.movieWeighting is not None:
            self.sendWidgetToClient( "movie", self.movieWeighting, self.movieItems, address )
        if self.episodeWeighting is not None:
            self.sendWidgetToClient( "episode", self.episodeWeighting, self.episodeItems, address )
        if self.pvrWeighting is not None:
            self.sendWidgetToClient( "pvr", self.pvrWeighting, self.pvrItems, address )
        if self.albumWeighting is not None:
            self.sendWidgetToClient( "album", self.albumWeighting, self.albumItems, address )

    def _remove_client( self, address ):
        # Remove client from list
        self.clients.remove( address )
        library.nowPlaying.pop( address, None )

    def _daemon( self ):
        # This is a daemon which will update the widget with latest suggestions
        self.connectionRead = sql.connect( True )
        count = 0
        while not xbmc.abortRequested:
            if __addon__.getSetting( "role" ) == "Client":
                count += 1
                if count >= 60:
                    # Tell the server we're still alive
                    self.pingServer()
                    count = 0
            if __addon__.getSetting( "role" ) == "Server" and ( len( self.clients ) != 0 or xbmc.getCondVisibility( "Skin.HasSetting(enable.smartish.widgets)" ) ):
                count += 1
                if count >= 60 or self.lastMovieHabits is None or self.lastEpisodeHabits is None or self.lastAlbumHabits is None or self.lastPVRHabits is None:
                    nextWidget = self._getNextWidget()

                    if nextWidget is not None:
                        # If live tv is playing, call the mediaStarted function in case channel has changed
                        if self.playingLiveTV:
                            self.mediaStarted( self.connectionRead )

                        # Get the users habits out of the database
                        habits, freshness = sql.getFromDatabase( self.connectionRead, nextWidget )

                        if nextWidget == "movie" and habits == self.lastMovieHabits:
                            self.movieLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            count = 0
                            continue
                        if nextWidget == "episode" and habits == self.lastEpisodeHabits:
                            self.episodeLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            count = 0
                            continue
                        if nextWidget == "album" and habits == self.lastAlbumHabits:
                            self.albumLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            count = 0
                            continue

                        # Pause briefly, and again check that abortRequested hasn't been called
                        xbmc.sleep( 100 )
                        if xbmc.abortRequested:
                            return

                        log( "Updating %s widget" %( nextWidget ) )

                        # Get all the media items that match the users habits
                        weighted, items = library.getMedia( nextWidget, habits, freshness )

                        # Pause briefly, and again check that abortRequested hasn't been called
                        xbmc.sleep( 100 )
                        if xbmc.abortRequested:
                            return

                        # Generate the widgets
                        if weighted is not None:
                            listitems = library.buildWidget( nextWidget, weighted, items )
                        else:
                            listitems = []

                        # Save the widget
                        if nextWidget == "movie":
                            self.movieWidget = listitems
                            self.movieLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            self.lastMovieHabits = habits
                            self.movieWeighting = weighted
                            self.movieItems = items
                            self.WINDOW.setProperty( "smartish.movies", self.movieLastUpdated )
                            log( "Movie widget updated" )
                        elif nextWidget == "episode":
                            self.episodeWidget = listitems
                            self.episodeLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            self.lastEpisodeHabits = habits
                            self.episodeWeighting = weighted
                            self.episodeItems = items
                            self.WINDOW.setProperty( "smartish.episodes", self.episodeLastUpdated )
                            log( "Episode widget updated" )
                        elif nextWidget == "pvr":
                            self.pvrWidget = listitems
                            self.pvrWeighting = weighted
                            self.pvrItems = items
                            self.lastPVRHabits = habits
                            self.pvrLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            self.WINDOW.setProperty( "smartish.pvr", self.pvrLastUpdated )
                            log( "PVR widget updated" )
                        elif nextWidget == "album":
                            self.albumWidget = listitems
                            self.albumLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
                            self.lastAlbumHabits = habits
                            self.albumWeighting = weighted
                            self.albumItems = items
                            self.WINDOW.setProperty( "smartish.albums", self.albumLastUpdated )
                            log( "Album widget updated" )

                        # Send widget data to clients so they can build their own widgets
                        thread.start_new_thread( self.sendWidgetToClient, ( nextWidget, weighted, library.shrinkJson( nextWidget, weighted, items ) ) )

                    # Reset counter and update widget type
                    count = 0

            xbmc.sleep( 1000 )

    def gotWidgetFromServer( self, type, data1, data2 ):
        listitems = library.buildWidget( type, data1, data2 )

        if type == "movie":
            log( "Movie widget updated" )
            self.movieWidget = listitems
            self.movieLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
            self.WINDOW.setProperty( "smartish.movies", self.movieLastUpdated )
        elif type == "episode":
            log( "Episode widget updated" )
            self.episodeWidget = listitems
            self.episodeLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
            self.WINDOW.setProperty( "smartish.episodes", self.episodeLastUpdated )
        elif type == "pvr":
            log( "PVR widget updated" )
            self.pvrWidget = listitems
            self.pvrLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
            self.WINDOW.setProperty( "smartish.pvr", self.pvrLastUpdated )
        elif type == "album":
            log( "Album widget updated" )
            self.albumWidget = listitems
            self.albumLastUpdated = strftime( "%Y%m%d%H%M%S",gmtime() )
            self.WINDOW.setProperty( "smartish.albums", self.albumLastUpdated )
        else:
            log( "Unknown widget type %s" %( type ) )


    def sendWidgetToClient( self, widget, weighted, items, client = None ):
        pickledWeighted = pickle.dumps( weighted, protocol = pickle.HIGHEST_PROTOCOL )
        pickledItems = pickle.dumps( items, protocol = pickle.HIGHEST_PROTOCOL )

        # If we're the client, nothing to do here
        if __addon__.getSetting( "role" ) == "Client":
            return

        # Get list of clients
        if client is not None:
            clients = [ client ]
        else :
            clients = self.clients

        if len( clients ) == 0:
            # No clients set up, nothing to do
            return

        port = int( __addon__.getSetting( "port" ) )
        for client in clients:
            if client is not None and client in self.clients:
                try:
                    clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                    clientsocket.connect( ( client, port ) )
                    log( "(* -> %s) 'widget' (%s)" %( client, widget ) )
                    clientsocket.send( "widget||||%s||||%s||||%s||||EOD" %( widget, pickledWeighted, pickledItems ) )
                    message = clientsocket.recv( 128 ).split( "||||" )
                    log( "(%s -> *) '%s' '%s'" %( client, message[ 0 ], message[ 1 ] ) )
                    clientsocket.close()

                except socket.error, msg:
                    log( repr( msg ) )
                    log( "Removing client %s" %( client ) )
                    self.clients.remove( client )
                except:
                    print_exc()
                    log( "Removing client %s" %( client ) )
                    # Remove client from list
                    self.clients.remove( client )

    def _getNextWidget( self ):
        # This function finds the widget which was the last to be udpated
        update = { self.pvrLastUpdated: "pvr", self.albumLastUpdated: "album", self.episodeLastUpdated: "episode", self.movieLastUpdated: "movie" }

        for key in sorted( update.keys() ):
            return update[ key ]

    def mediaEnded( self ):
        # Media has finished playing, clear our saved values of what was playing
        library.lastplayedID = None
        library.lastplayedType = None
        library.nowPlaying.pop( "localhost", None )

        self.nextupWidget = []

        self.playingLiveTV = False

        # If we're a client, tell the server we've finished playing
        if __addon__.getSetting( "role" ) == "Client":
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                log( "(* -> %s) 'playbackended'" %( host ) )
                clientsocket.send( "playbackended||||EOD" )
                message = clientsocket.recv( 128 ).split( "||||" )
                log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                print_exc()
                log( "Unable to establish connection to server at address %s" %( host ) )


    def mediaStarted( self, connection = None ):
        # Get the active player
        json_query = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
        json_query = unicode(json_query, 'utf-8', errors='ignore')

        json_query = simplejson.loads(json_query)

        if json_query.has_key('result') and json_query[ "result" ]:
            playerid = json_query[ "result" ][ 0 ][ "playerid" ]

            # Get details of the playing media
            json_query = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str( playerid ) + ', "properties": [ "title", "artist", "albumartist", "genre", "year", "rating", "album", "track", "duration", "comment", "lyrics", "playcount", "fanart", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "writer", "studio", "mpaa", "cast", "country", "imdbnumber", "premiered", "productioncode", "runtime", "set", "showlink", "streamdetails", "top250", "votes", "firstaired", "season", "episode", "showtitle", "file", "resume", "artistid", "albumid", "tvshowid", "setid", "watchedepisodes", "disc", "tag", "art", "genreid", "displayartist", "albumartistid", "description", "theme", "mood", "style", "albumlabel", "sorttitle", "episodeguide", "uniqueid", "dateadded", "channel", "channeltype", "hidden", "locked", "channelnumber", "starttime", "endtime" ] } }' )
            json_query = unicode(json_query, 'utf-8', errors='ignore')

            json_query = simplejson.loads(json_query)

            if json_query.has_key( 'result' ):
                type = json_query[ "result" ][ "item" ][ "type" ]
                if type == "episode":
                    self.episode( json_query[ "result" ][ "item" ] )
                elif type == "movie":
                    self.movie( json_query[ "result" ][ "item" ] )
                elif type == "song":
                    self.song( json_query[ "result" ][ "item" ] )
                elif type == "channel":
                    # Get details of the current show
                    live_query = xbmc.executeJSONRPC( '{ "jsonrpc": "2.0",  "id": 1, "method": "PVR.GetBroadcasts", "params": {"channelid": %d, "properties": [ "title", "plot", "plotoutline", "starttime", "endtime", "runtime", "progress", "progresspercentage", "genre", "episodename", "episodenum", "episodepart", "firstaired", "hastimer", "isactive", "parentalrating", "wasactive", "thumbnail" ], "limits": {"end": 1} } }' %( json_query[ "result" ][ "item" ][ "id" ] ) )
                    #live_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannelDetails", "params": {"channelid": %d, "properties": [ "broadcastnow" ]}}' %( json_query[ "result" ][ "item" ][ "id" ] ) )
                    live_query = unicode(live_query, 'utf-8', errors='ignore')
                    live_query = simplejson.loads(live_query)

                    # Check the details we need are actually included:
                    if live_query.has_key( "result" ) and live_query[ "result" ].has_key( "broadcasts" ):
                        if self.playingLiveTV:
                            # Only update if the current show has changed
                            if not self.lastLiveTVChannel == str( json_query[ "result" ][ "item" ][ "id" ] ) + "|" + live_query[ "result" ][ "broadcasts" ][ 0 ][ "starttime" ]:
                                self.livetv( json_query[ "result" ][ "item" ], live_query[ "result" ][ "broadcasts" ][ 0 ], connection )
                        else:
                            self.livetv( json_query[ "result" ][ "item" ], live_query[ "result" ][ "broadcasts" ][ 0 ], connection )

                        # Save the current channel, so we can only update on channel change
                        self.playingLiveTV = True
                        self.lastLiveTVChannel = str( json_query[ "result" ][ "item" ][ "id" ] ) + "|" + live_query[ "result" ][ "broadcasts" ][ 0 ][ "starttime" ]

                elif type == "unknown" and "channel" in json_query[ "result" ][ "item"] and json_query[ "result" ][ "item" ][ "channel" ] != "":
                    self.recordedtv( json_query[ "result" ][ "item" ] )

    def movie( self, json_query ):
        # This function extracts the details we want to save from a movie, and sends them to the addToDatabase function

        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        daytimeStrings = { "dateandtime": dateandtime, "time": time, "day": day }

        # Save this is lastplayed, so the widgets won't display it
        self.lastPlayed( "movie", json_query[ "id" ] )
        self.movieLastUpdated = 0
        self.lastMovieHabits = None

        dbaseInfo = []
        additionalInfo = {}

        # MPAA
        if json_query[ "mpaa" ] != "":
            dbaseInfo.append( ( "movie", "mpaa", json_query[ "mpaa" ] ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "mpaa", json_query[ "mpaa" ] )

        # Tag
        for tag in json_query[ "tag" ]:
            dbaseInfo.append( ( "movie", "tag", tag ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "tag", tag )

        # Director(s)
        for director in json_query[ "director" ]:
            dbaseInfo.append( ( "movie", "director", director ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "director", director )

        # Writer(s)
        for writer in json_query[ "writer" ]:
            dbaseInfo.append( ( "movie", "writer", writer ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "writer", writer )

        # Studio(s)
        for studio in json_query[ "studio" ]:
            dbaseInfo.append( ( "movie", "studio", studio ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "studio", studio )

        # Genre(s)
        for genre in json_query[ "genre" ]:
            dbaseInfo.append( ( "movie", "genre", genre ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "genre", genre )

        # Actor(s)
        for actor in json_query[ "cast" ]:
            dbaseInfo.append( ( "movie", "actor", actor[ "name" ] ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "actor", actor[ "name" ] )

        # Is it watched
        if json_query[ "playcount" ] == 0:
            # This is a new movie
            dbaseInfo.append( ( "movie", "special", "unwatched" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "unwatched" )

        # Get additional info from TMDB
        if __addon__.getSetting( "role" ) == "Server":
            keywords, related = sql.getTMDBExtras( "movie", json_query[ "id" ], json_query[ "imdbnumber" ], json_query[ "year" ] )
            for keyword in keywords:
                dbaseInfo.append( ( "movie", "keyword", keyword ) )
                #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "keyword", keyword )
            for show in related:
                dbaseInfo.append( ( "movie", "related", show ) )
                #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "related", show )
        else:
            # We're a client, so we'll let the server get the additional info
            additionalInfo[ "type" ] = "movie"
            additionalInfo[ "id" ] = json_query[ "id" ]
            additionalInfo[ "imdbnumber" ] = json_query[ "imdbnumber" ]
            additionalInfo[ "year" ] = json_query[ "year" ]


        # Convert dateadded to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )

        # How new is it
        if dateadded.days <= 2:
            dbaseInfo.append( ( "movie", "special", "fresh" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "fresh" )
        if dateadded.days <= 7:
            dbaseInfo.append( ( "movie", "special", "recentlyadded" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "recentlyadded" )

        # Mark played, so we can get percentage unwatched/recent
        dbaseInfo.append( ( "movie", "special", "playedmedia" ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "movie", "special", "playedmedia" )

        # Add all the info to the dbase
        self.newaddToDatabase( daytimeStrings, dbaseInfo, additionalInfo )

    def episode( self, json_query ):
        # This function extracts the details we want to save from a tv show episode, and sends them to the addToDatabase function

        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        daytimeStrings = { "dateandtime": dateandtime, "time": time, "day": day }

        # Save this as last played, so the widgets won't display it
        self.lastPlayed( "episode", json_query[ "id" ], json_query[ "tvshowid" ] )
        library.tvshowInformation.pop( json_query[ "tvshowid" ], None )
        library.tvshowNextUnwatched.pop( json_query[ "tvshowid" ], None )
        library.tvshowNewest.pop( json_query[ "tvshowid" ], None )
        self.episodeLastUpdated = 0
        self.lastEpisodeHabits = None

        dbaseInfo = []
        additionalInfo = {}

        # TV Show ID
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "tvshowid", json_query[ "tvshowid" ] )
        dbaseInfo.append( ( "episode", "tvshowid", json_query[ "tvshowid" ] ) )

        # Now get details of the tv show
        show_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": %s, "properties": ["sorttitle", "mpaa", "premiered", "episode", "watchedepisodes", "studio", "genre", "cast", "tag", "imdbnumber" ]}, "id": 1}' % json_query[ "tvshowid" ] )
        show_query = unicode(show_query, 'utf-8', errors='ignore')
        show_query = simplejson.loads(show_query)
        show_query = show_query[ "result" ][ "tvshowdetails" ]

        # MPAA
        dbaseInfo.append( ( "episode", "mpaa", show_query[ "mpaa" ] ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "mpaa", show_query[ "mpaa" ] )

        # Studio(s)
        for studio in show_query[ "studio" ]:
            dbaseInfo.append( ( "episode", "studio", studio ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "studio", studio )

        # Genre(s)
        for genre in show_query[ "genre" ]:
            dbaseInfo.append( ( "episode", "genre", genre ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "genre", genre )

        # Tag(s)
        for genre in show_query[ "tag" ]:
            dbaseInfo.append( ( "episode", "tag", tag ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "tag", tag )

        # Actor(s)
        for actor in show_query[ "cast" ]:
            dbaseInfo.append( ( "episode", "actor", actor[ "name" ] ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "actor", actor[ "name" ] )

        # Is it watched
        if json_query[ "playcount" ] == 0:
            # This is a new episode
            dbaseInfo.append( ( "episode", "special", "unwatched" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "unwatched" )

        # Get additional info from TMDB
        if __addon__.getSetting( "role" ) == "Server":
            keywords, related = sql.getTMDBExtras( "episode", json_query[ "imdbnumber" ], show_query[ "label" ], show_query[ "premiered" ][:-6] )
            for keyword in keywords:
                dbaseInfo.append( ( "episode", "keyword", keyword ) )
                #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "keyword", keyword )
            for show in related:
                dbaseInfo.append( ( "episode", "related", show ) )
                #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "related", show )
        else:
            # We're a client, so we'll let the server get the additional info
            additionalInfo[ "type" ] = "episode"
            additionalInfo[ "id" ] = json_query[ "imdbnumber" ]
            additionalInfo[ "imdbnumber" ] = show_query[ "label" ]
            additionalInfo[ "year" ] = show_query[ "premiered" ][:-6]

        # Convert dateadded to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )

        # How new is it
        if dateadded.days <= 2:
            dbaseInfo.append( ( "episode", "special", "fresh" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "fresh" )
        if dateadded.days <= 7:
            dbaseInfo.append( ( "episode", "special", "recentlyadded" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "recentlyadded" )

        # Mark played, so we can get percentage unwatched/recent
        dbaseInfo.append( ( "episode", "special", "playedmedia" ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "episode", "special", "playedmedia" )

        # Add all the info to the dbase
        self.newaddToDatabase( daytimeStrings, dbaseInfo, additionalInfo )

    def recordedtv( self, json_query ):
        # This function extracts the details we want to save from a tv show episode, and sends them to the addToDatabase function

        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        daytimeStrings = { "dateandtime": dateandtime, "time": time, "day": day }

        # Save this as last played, so the widget won't display it
        self.lastPlayed( "recorded", json_query[ "id" ] )
        self.pvrLastUpdated = 0

        dbaseInfo = []
        additionalInfo = {}

        # Channel
        dbaseInfo.append( ( "recorded", "channel", json_query[ "channel" ] ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "channel", json_query[ "channel" ] )

        # Genre(s)
        for genre in json_query[ "genre" ]:
            for splitGenre in genre.split( "/" ):
                dbaseInfo.append( ( "recorded", "genre", splitGenre ) )
                #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "genre", splitGenre )

        # Is it watched
        if json_query[ "lastplayed" ] == "":
            # This is a new episode
            dbaseInfo.append( ( "recorded", "special", "unwatched" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "unwatched" )

        # Convert startime to datetime object
        dateadded = datetime.now() - datetime.strptime( json_query[ "starttime" ], "%Y-%m-%d %H:%M:%S" )

        # How new is it
        if dateadded.days <= 2:
            dbaseInfo.append( ( "recorded", "special", "fresh" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "fresh" )
        if dateadded.days <= 7:
            dbaseInfo.append( ( "recorded", "special", "recentlyadded" ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "recentlyadded" )

        # Mark played, so we can get percentage unwatched/recent
        dbaseInfo.append( ( "recorded", "special", "playedmedia" ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "recorded", "special", "playedmedia" )

        # Add all the info to the dbase
        self.newaddToDatabase( daytimeStrings, dbaseInfo, additionalInfo )

    def livetv( self, json_query, live_query, connection = None ):
        # This function extracts the details we want to save from live tv, and sends them to the addToDatabase function

        if connection is None:
            connection = self.connectionWrite

        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        daytimeStrings = { "dateandtime": dateandtime, "time": time, "day": day }

        # Trigger PVR to be next widget to be updated
        self.pvrLastUpdated = 0

        dbaseInfo = []
        additionalInfo = {}

        # ChannelType
        dbaseInfo.append( ( "live", "channeltype", json_query[ "channeltype" ] ) )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "channeltype", json_query[ "channeltype" ] )

        # Channel
        dbaseInfo.append( ( "live", "channel", json_query[ "channel" ] ) )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "channel", json_query[ "channel" ] )

        # ChannelNumber
        dbaseInfo.append( ( "live", "channelnumber", json_query[ "channelnumber" ] ) )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "channelnumber", json_query[ "channelnumber" ] )

        # ChannelID
        dbaseInfo.append( ( "live", "channelid", json_query[ "id" ] ) )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "channelid", json_query[ "id" ] )

        # Genre
        for genre in live_query[ "genre" ]:
            for splitGenre in genre.split( "/" ):
                dbaseInfo.append( ( "live", "genre", splitGenre ) )
                #self.addToDatabase( connection, dateandtime, time, day, "live", "genre", splitGenre )

        # Mark played, so we can get percentage unwatched/recent
        dbaseInfo.append( ( "live", "special", "playedmedia" ) )
        dbaseInfo.append( ( "live", "special", "playedlive" ) )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "special", "playedmedia" )
        #self.addToDatabase( connection, dateandtime, time, day, "live", "special", "playedlive" )

        # Add all the info to the dbase
        self.newaddToDatabase( daytimeStrings, dbaseInfo, additionalInfo )

    def song( self, json_query ):
        # This function extracts the details we want to save from a song, and sends them to the addToDatabase function

        # First, time stamps (so all items have identical time stamp)
        dateandtime = str( datetime.now() )
        time = str( "%02d:%02d" %( datetime.now().hour, datetime.now().minute ) )
        day = datetime.today().weekday()
        daytimeStrings = { "dateandtime": dateandtime, "time": time, "day": day }

        dbaseInfo = []
        additionalInfo = {}

        # Now get details of the album
        album_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"albumid": %s, "properties": [ "title", "description", "artist", "genre", "theme", "mood", "style", "type", "albumlabel", "rating", "year", "musicbrainzalbumid", "musicbrainzalbumartistid", "fanart", "thumbnail", "playcount", "genreid", "artistid", "displayartist" ]}, "id": 1}' % json_query[ "albumid" ] )
        album_query = unicode(album_query, 'utf-8', errors='ignore')
        album_query = simplejson.loads(album_query)
        album_query = album_query[ "result" ][ "albumdetails" ]

        # Check album has changed
        if library.lastplayedType == "album" and library.lastplayedID == album_query[ "albumid" ]:
            return

        # Save album, so we only update data on album change
        self.lastPlayed( "album", album_query[ "albumid" ] )
        self.albumLastUpdated = 0
        self.lastAlbumHabits = None

        for artist in album_query[ "artist" ]:
            dbaseInfo.append( ( "album", "artist", artist ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "artist", artist )

        for style in album_query[ "style" ]:
            dbaseInfo.append( ( "album", "style", style ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "style", style )

        for theme in album_query[ "theme" ]:
            dbaseInfo.append( ( "album", "theme", theme ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "theme", theme )

        dbaseInfo.append( ( "album", "label", album_query[ "label" ] ) )
        #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "label", album_query[ "label" ] )

        for genre in album_query[ "genre" ]:
            dbaseInfo.append( ( "album", "genre", genre ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "genre", genre )

        for mood in album_query[ "mood" ]:
            dbaseInfo.append( ( "album", "mood", mood ) )
            #self.addToDatabase( self.connectionWrite, dateandtime, time, day, "album", "mood", mood )

        # Add all the info to the dbase
        self.newaddToDatabase( daytimeStrings, dbaseInfo, additionalInfo )

    def libraryUpdated( self, database ):
        if database == "video":
            # Clear movie and episode habits, and set them both to be updated
            self.lastMovieHabits = None
            self.lastEpisodeHabits = None
            self.movieLastUpdated = 0
            self.episodeLastUpdated = 0
            self.updateWidgetServer( "movie" )
            self.updateWidgetServer( "episode" )
        if database == "music":
            # Clear album habits, and set to be updated
            self.lastAlbumHabits = None
            self.albumLastUpdated = 0
            self.updateWidgetServer( "album" )

    def newaddToDatabase( self, daytime, dbaseInfo, additionalInfo ):
        if __addon__.getSetting( "role" ) == "Server":
            # We're the server, add the habits into the database
            connection = sql.connect()
            nextupHabits = {}
            type = None

            for habit in dbaseInfo:
                sql.addToDatabase( connection, daytime[ "dateandtime" ], daytime[ "time" ], daytime[ "day" ], habit[ 0 ], habit[ 1 ], habit[ 2 ] )
                nextupHabits = sql.nextupHabits( nextupHabits, habit[ 1 ], habit[ 2 ] )
                if type is None:
                    type = habit[ 0 ]

            connection.close()

            thread.start_new_thread( self.buildNextUpWidget, ( type, nextupHabits ) )
            self.buildNextUpWidget( type, nextupHabits )
        else:
            # We're the client, send the data to the server to add
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                log( "(* -> %s) 'mediainfo'" %( host ) )
                clientsocket.send( "mediainfo||||%s||||%s||||%s||||EOD" %( pickle.dumps( daytime, protocol = pickle.HIGHEST_PROTOCOL ), pickle.dumps( dbaseInfo, protocol = pickle.HIGHEST_PROTOCOL ), pickle.dumps( additionalInfo, protocol = pickle.HIGHEST_PROTOCOL ) ) )
                message = clientsocket.recv( 128 ).split( "||||" )
                log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                print_exc()
                log( "Unable to establish connection to server at address %s" %( host ) )

    def addClientDataToDatabase( self, daytime, dbaseInfo, additionalInfo ):
        # We've received habits from client we need to add to the database
        connection = sql.connect()
        nextupHabits = {}

        type = None

        for habit in dbaseInfo:
            sql.addToDatabase( connection, daytime[ "dateandtime" ], daytime[ "time" ], daytime[ "day" ], habit[ 0 ], habit[ 1 ], habit[ 2 ] )
            nextupHabits = sql.nextupHabits( nextupHabits, habit[ 1 ], habit[ 2 ] )

            if type is None:
                type = habit[ 0 ]

        # If this is a movie or episode, try to get additional info from TMDB
        if "type" in additionalInfo:
            keywords, related = sql.getTMDBExtras( additionalInfo[ "type" ], additionalInfo[ "id" ], additionalInfo[ "imdbnumber" ], additionalInfo[ "year" ] )
            for keyword in keywords:
                self.addToDatabase( connection, daytime[ "dateandtime" ], daytime[ "time" ], daytime[ "day" ], additionalInfo[ "type" ], "keyword", keyword )
                nextupHabits = sql.nextupHabits( nextupHabits, "keyword", keyword )
            for show in related:
                self.addToDatabase( connection, daytime[ "dateandtime" ], daytime[ "time" ], daytime[ "day" ], additionalInfo[ "type" ], "related", show )
                nextupHabits = sql.nextupHabits( nextupHabits, "related", show )

        connection.close()

        self.buildNextUpWidget( type, nextupHabits )


    def buildNextUpWidget( self, type, habits ):
        if type is None: return []
        if type != "movie" and type != "episode": return []

        log( "Updating %s nextup" %( type ) )
        weighted, items = library.getMedia( type, habits, ( 10, 10, 0 ) )

        # Pause briefly, and again check that abortRequested hasn't been called
        xbmc.sleep( 100 )
        if xbmc.abortRequested:
            return

        # Generate the widgets
        if weighted is not None:
            self.nextupWidget = library.buildWidget( type, weighted, items )
        else:
            self.nextupWidget = []

        log( "Updated %s nextup" %( type ) )

    def addToDatabase( self, connection, dateandtime, time, day, media, type, data ):
        log( "### DEPRECATED FUNCTION CALLED!" )
        if __addon__.getSetting( "role" ) == "Server":
            # If we're acting as a server, add the data into the database
            sql.addToDatabase( connection, dateandtime, time, day, media, type, data )
        else:
            # We're acting as the client, so tell the server to add the data into the database
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                log( "(* -> %s) 'mediainfo'" %( host ) )
                clientsocket.send( "mediainfo||||%s||||%s||||%s||||%s||||%s||||%s||||EOD" %( dateandtime, time, day, media, type, data ) )
                message = clientsocket.recv( 128 ).split( "||||" )
                log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                print_exc()
                log( "Unable to establish connection to server at address %s" %( host ) )

    def lastPlayed( self, type, id, episodeID = "" ):
        library.lastplayedType = type
        library.lastplayedID = id
        library.nowPlaying[ "localhost" ] = ( type, id )

        if __addon__.getSetting( "role" ) == "Client":
            # We're acting as the client, so tell the server to add the data into the database
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                log( "(* -> %s) 'lastplayed'" %( host ) )
                clientsocket.send( "lastplayed||||%s||||%s||||%s||||EOD" %( type, id, episodeID ) )
                message = clientsocket.recv( 128 ).split( "||||" )
                log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                print_exc()
                log( "(playing) Unable to establish connection to server at address %s:%s" %( host, port ) )

    def updateWidgetServer( self, type ):
        if __addon__.getSetting( "role" ) == "Client":
            # We're acting as the client, so tell the server to update a particular widget (e.g. after media
            # played or library updated)
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                log( "(* -> %s) 'updatewidget' (%s)" %( host, type ) )
                clientsocket.send( "updatewidget||||%s||||EOD" %( type ) )
                message = clientsocket.recv( 128 ).split( "||||" )
                log( "(%s -> *) '%s' 's'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                log( "Unable to establish connection to server at address %s" %( host ) )

    def pingServer( self, firstConnect = False ):
        if __addon__.getSetting( "role" ) == "Client":
            # Ping the server
            host = __addon__.getSetting( "serverip" )
            port = int( __addon__.getSetting( "port" ) )

            if firstConnect:
                message = "clientstart"
            else:
                message = "ping"

            try:
                clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                clientsocket.connect( ( host, port ) )
                if firstConnect:
                    log( "(* -> %s) '%s'" %( host, message ) )
                clientsocket.send( "%s||||EOD" %( message ) )
                message = clientsocket.recv( 128 ).split( "||||" )
                if firstConnect:
                    log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
                clientsocket.close()

            except:
                log( "Unable to establish connection to server at address %s" %( host ) )



class Widgets_Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.action = kwargs[ "action" ]

    def onDatabaseUpdated(self, database):
        self.action( database )

class Widgets_Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.action = kwargs[ "action" ]
        self.ended = kwargs[ "ended" ]

    def onPlayBackStarted(self):
        log( "Playback started" )
        xbmc.sleep(1000)
        self.action()

    def onPlayBackEnded(self):
        self.ended()

    def onPlayBackStopped(self):
        self.ended()
