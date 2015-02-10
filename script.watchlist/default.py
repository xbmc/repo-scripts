#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
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
            
        if self.TYPE == "movies":
            self.movies()
        elif self.TYPE == "episodes":
            self.episodes()
            
        elif not self.TYPE:
            # Show a root menu
            full_liz = list()
            items = [[32001, "movies"], [32002, "episodes"]]
            for item in items:
                liz = xbmcgui.ListItem( __localize__( item[0] ) )
                liz.setIconImage( "DefaultFolder.png" )
                full_liz.append( ( "plugin://script.watchlist?type=" + item[1], liz, True ) )

            xbmcplugin.addDirectoryItems(int(sys.argv[1]),full_liz)
            xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))
            
        else:
            # Unsupported type variable
            log( "Unsupported media type" )
            pass
                        
    def movies( self ):
        xbmcplugin.setContent( int( sys.argv[1] ), "movies" )

        # Get movies watchlist
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director"], "limits": {"end": %d},' % self.LIMIT
        json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}}}' %json_string)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads( json_query )
        
        # Check whether results have been returned
        if json_query.has_key( "result" ) and json_query[ "result" ].has_key( "movies" ):
            for item in json_query[ "result" ][ "movies" ]:
                liz = xbmcgui.ListItem( item[ "title" ] )
                
                # Check watched status, and set plot (if plot enabled)
                watched = False
                if item[ "playcount" ] >= 1:
                    watched = True
                if not PLOT_ENABLE and not watched:
                    plot = __localize__( 32003 )
                else:
                    plot = item[ "plot" ]
                    
                if len( item[ 'studio' ] ) > 0:
                    studio = item[ 'studio' ][ 0 ]
                else:
                    studio = ""
                if len( item[ 'country' ] ) > 0:
                    country = item[ 'country' ][ 0 ]
                else:
                    country = ""

                    
                # Item details
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
                #liz.setProperty("type", __localize__(list_type))
                
                # Art
                liz.setArt(item['art'])
                liz.setThumbnailImage(item['art'].get('poster', ''))
                liz.setIconImage('DefaultVideoCover.png')
                liz.setProperty("fanart_image", item['art'].get('fanart', ''))
                
                # Stream details
                for key, value in item['streamdetails'].iteritems():
                    for stream in value:
                        liz.addStreamInfo( key, stream ) 
                # Add item to list
                xbmcplugin.addDirectoryItem( int( sys.argv[ 1 ] ), item[ "file" ], liz, False, self.LIMIT )
                
        # End list
        xbmcplugin.endOfDirectory( int( sys.argv[ 1 ] ), cacheToDisc = False )
            
    
    def episodes( self ):
        xbmcplugin.setContent( int( sys.argv[1] ), "episodes" )
        
        # Get episodes watchlist
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "streamdetails", "firstaired", "runtime"], "limits": {"end": %d},' %self.LIMIT
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "mpaa", "file", "art"], "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %self.LIMIT)
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('tvshows'):
            for item in json_query['result']['tvshows']:
                # If we've been told to abort, do so
                if xbmc.abortRequested:
                    break
                    
                # Get details of this particular episode
                json_query2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": ["title", "playcount", "plot", "season", "episode", "showtitle", "file", "lastplayed", "rating", "resume", "art", "streamdetails", "firstaired", "runtime"], "sort": {"method": "episode"}, "filter": {"field": "playcount", "operator": "is", "value": "0"}, "limits": {"end": 1}}, "id": 1}' %item['tvshowid'])
                json_query2 = simplejson.loads( json_query2 )
                
                if json_query2.has_key( "result" ) and json_query2[ "result" ] is not None and json_query2[ "result" ].has_key( "episodes" ):
                    for item2 in json_query2[ "result" ][ "episodes" ]:
                        liz = xbmcgui.ListItem( item2[ "title" ] )
                        
                        # Episode/season details
                        episode = "%.2d" % float(item2['episode'])
                        season = "%.2d" % float(item2['season'])
                        episodeno = "s%se%s" %(season,episode)
                        
                        if len( item[ 'studio' ] ) > 0:
                            studio = item[ 'studio' ][ 0 ]
                        else:
                            studio = ""
                        
                        # Check watched status and set plot (if plot enabled)
                        watched = False
                        if item2[ "playcount" ] >= 1:
                            watched = True
                        if not PLOT_ENABLE and not watched:
                            plot = __localize__( 32003 )
                        else:
                            plot = item2[ "plot" ]
                            
                        # Item details
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
                        
                        # Art
                        liz.setArt(item2['art'])
                        liz.setThumbnailImage(item2['art'].get('thumb',''))
                        liz.setIconImage('DefaultTVShows.png')
                        liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart',''))
                        
                        # Stream details
                        for key, value in item2['streamdetails'].iteritems():
                            for stream in value:
                                liz.addStreamInfo( key, stream ) 
                        
                        # Add item to list
                        xbmcplugin.addDirectoryItem( int( sys.argv[ 1 ] ), item2[ "file" ], liz, False, self.LIMIT )
                        
                        break
                
        # End list
        xbmcplugin.endOfDirectory( int( sys.argv[ 1 ] ), cacheToDisc = False )
            
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
        except:
            params = {}
        self.LIMIT = int(__addon__.getSetting("limit"))
        self.TYPE = params.get( "?type", "" )
        global PLOT_ENABLE 
        PLOT_ENABLE = __addon__.getSetting("plot_enable")  == 'true'
    
log('script version %s started' % __addonversion__)
Main()
log('script version %s stopped' % __addonversion__)