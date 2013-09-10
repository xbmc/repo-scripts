# -*- coding: utf-8 -*-

__scriptID__ = "script.cinema.experience"
__modname__ = "local folder scraper"
"""
Local trailer scraper
"""
# TODO: add watched.xml to skip watched trailers

import os, sys, time, re, urllib
from random import shuffle, random
from xml.sax.saxutils import unescape

import xbmc

logmessage = "[ " + __scriptID__ + " ] - [ " + __modname__ + " ]"
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from folder import dirEntries
from ce_playlist import _set_trailer_info

class Main:
    xbmc.log("%s - Local Folder Trailer Scraper Started" % logmessage, level=xbmc.LOGNOTICE )
    
    def __init__( self, equivalent_mpaa=None, mpaa=None, genre=None, settings=None, movie=None ):
        self.mpaa = equivalent_mpaa
        self.genre = genre.replace( "Sci-Fi", "Science Fiction" ).replace( "Action", "Action and ADV" ).replace( "Adventure", "ACT and Adventure" ).replace( "ACT",  "Action" ).replace( "ADV",  "Adventure" ).split( " / " )
        self.settings = settings
        self.movie = movie
        self.trailers = []
        self.tmp_trailers = []

    def fetch_trailers( self ):
        xbmc.log("%s - Fetching Trailers" % logmessage, level=xbmc.LOGNOTICE )
        # get watched list
        self._get_watched()
        # fetch all trailers recursively
        self.tmp_trailers = dirEntries( self.settings[ "trailer_folder" ], "video", "TRUE", "-trailer" )
        # get a random number of trailers
        self._shuffle_trailers()
        # save watched list
        self._save_watched()
        # return results
        return self.trailers

    def _shuffle_trailers( self ):
        # randomize the groups and create our play list
        xbmc.log("%s - Shuffling Trailers" % logmessage, level=xbmc.LOGNOTICE )
        shuffle( self.tmp_trailers )
        # reset counter
        count = 0
        # now create our final playlist
        for trailer in self.tmp_trailers:
            # user preference to skip watch trailers
            if ( self.settings[ "trailer_unwatched_only" ] and xbmc.getCacheThumbName( trailer ) in self.watched ):
                continue
            # add trailer to our final list
            trailer_info = _set_trailer_info( trailer )
            trailer_genre = trailer_info[ 9 ].split(" / ")
            trailer_rating = trailer_info[ 6 ].replace("Rated ", "")
            if self.settings[ "trailer_limit_genre" ] and ( not list(set(trailer_genre) & set(self.genre) ) ):
                xbmc.log("%s - Genre Not Matched - Skipping Trailer" % logmessage, level=xbmc.LOGDEBUG )
                continue
            if self.settings[ "trailer_limit_mpaa" ] and ( not trailer_rating or not trailer_rating == self.mpaa ):
                xbmc.log("%s - MPAA Not Matched - Skipping Trailer" % logmessage, level=xbmc.LOGDEBUG )
                continue
            self.trailers += [ trailer_info ]
            # add id to watched file TODO: maybe don't add if not user preference
            self.watched += [ xbmc.getCacheThumbName( trailer ) ]
            # increment counter
            count += 1
            # if we have enough exit
            if ( count == self.settings[ "trailer_count" ] ):
                break
        if ( len(self.trailers) == 0 and self.settings[ "trailer_unwatched_only" ] and len( self.watched ) > 0 ):
            self._reset_watched()
            #attempt to load our playlist again
            self._shuffle_trailers()

    def _get_watched( self ):
        xbmc.log("%s - Getting Watched List" % logmessage, level=xbmc.LOGNOTICE )
        try:
            # base path to watched file
            if int( self.settings[ "trailer_play_mode" ] )== 1:
                base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloader" + "_watched.txt" )
            else:
                base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
            # open path
            usock = open( base_path, "r" )
            # read source
            self.watched = eval( usock.read() )
            # close socket
            usock.close()
        except:
            self.watched = []

    def _reset_watched( self ):
        xbmc.log("%s - Resetting Watched List" % logmessage, level=xbmc.LOGNOTICE )
        if int( self.settings[ "trailer_play_mode" ] )== 1:
            base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloader" + "_watched.txt" )
        else:
            base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
        if ( os.path.isfile( base_path ) ):
            os.remove( base_path )
            self.watched = []

    def _save_watched( self ):
        xbmc.log("%s - Saving Watched List" % logmessage, level=xbmc.LOGNOTICE )
        try:
            # base path to watched file
            if int( self.settings[ "trailer_play_mode" ] )== 1:
                base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloader" + "_watched.txt" )
            else:
                base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
            # if the path to the source file does not exist create it
            if ( not os.path.isdir( os.path.dirname( base_path ) ) ):
                os.makedirs( os.path.dirname( base_path ) )
            # open source path for writing
            file_object = open( base_path, "w" )
            # write xmlSource
            file_object.write( repr( self.watched ) )
            # close file object
            file_object.close()
        except:
            pass
