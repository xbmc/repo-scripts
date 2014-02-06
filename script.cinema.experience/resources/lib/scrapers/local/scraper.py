# -*- coding: utf-8 -*-
"""
Local trailer scraper
"""
# TODO: add watched.xml to skip watched trailers

import os, sys, time, re, urllib, traceback
from random import shuffle, random

import xbmc, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from folder import absolute_listdir
from ce_playlist import _set_trailer_info
import utils

class Main:
    utils.log( "Local Folder Trailer Scraper Started", xbmc.LOGNOTICE )
    
    mpaa_ratings = [ 'G', 'PG', 'PG-13', 'R', 'NC-17', 'NR', 'Unrated', 'Not yet rated' ]
    
    def __init__( self, equivalent_mpaa=None, mpaa=None, genre=None, settings=None, movie=None ):
        self.mpaa = self.mpaa_ratings.index( equivalent_mpaa )
        genre = genre.split( " / " )
        self.genre = []
        if isinstance( genre, list ):
            self.genre = genre
        else:
            self.genre.append( genre )
        for item in self.genre:
            if item == "Action and Adventure":
                self.genre.insert( self.genre.index( "Action and Adventure" ) + 1, "Adventure" )
                self.genre[ self.genre.index( "Action and Adventure" ) ] = "Action"
        genre_test = ["Sci-Fi", "Action", "Adventure", "Science Fiction" ]
        genre_match = ["Science Fiction", "Action and Adventure", "Action and Adventure", "Sci-Fi" ]
        # check to see if the movie genre has matching genres to those contained in genre_test, if there are, add equivalent genres
        genre_append = []
        if len( set( genre_test ).intersection( self.genre ) ) > 0:
            for item in self.genre:
                try:
                    genre_append.append( genre_match[ genre_test.index( item ) ] )
                except ValueError:
                    pass
                except:
                    traceback.print_exc()
                    pass
        self.genre.extend( genre_append )
        self.settings = settings
        self.movie = movie
        self.trailers = []
        self.tmp_trailers = []
        if int( self.settings[ "trailer_play_mode" ] )== 1:
            self.watched_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloader" + "_watched.txt" )
        else:
            self.watched_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )

    def fetch_trailers( self ):
        utils.log( "Fetching Trailers", xbmc.LOGNOTICE )
        # get watched list
        self._get_watched()
        # fetch all trailers recursively
        self.tmp_trailers = absolute_listdir( self.settings[ "trailer_folder" ], media_type = "video", recursive = True, contains = "-trailer" )
        # get a random number of trailers
        self._shuffle_trailers()
        # save watched list
        self._save_watched()
        # return results
        return self.trailers

    def _shuffle_trailers( self ):
        # randomize the groups and create our play list
        utils.log( "Shuffling Trailers", xbmc.LOGNOTICE )
        shuffle( self.tmp_trailers )
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
            if self.settings[ "trailer_limit_genre" ]:
                if len( set( trailer_genre ).intersection( self.genre ) ) < 1:
                    utils.log("Genre Not Matched - Skipping Trailer: %s != %s" % (trailer_genre, self.genre) )
                    continue
            if self.settings[ "trailer_limit_mpaa" ]:
                trailer_mpaa = self.mpaa_ratings.index( trailer_rating )
                if trailer_mpaa > self.mpaa:
                    utils.log("MPAA too high - Skipping Trailer: %s > %s" % ( trailer_rating, self.mpaa_ratings[ self.mpaa ] ) )
                    continue 
            self.trailers += [ trailer_info ]
            # add id to watched file TODO: maybe don't add if not user preference
            self.watched += [ xbmc.getCacheThumbName( trailer ) ]
            # increment counter
            count += 1
            # if we have enough exit
            if ( count == self.settings[ "trailer_count" ] ):
                break
        if ( len( self.trailers ) == 0 and self.settings[ "trailer_unwatched_only" ] and len( self.watched ) > 0 ):
            self._reset_watched()
            #attempt to load our playlist again
            self._shuffle_trailers()

    def _get_watched( self ):
        self.watched = utils.load_saved_list( self.watched_path, "Trailer Watched List" )

    def _reset_watched( self ):
        utils.log( "Resetting Watched List", xbmc.LOGNOTICE )
        if xbmcvfs.exists( self.watched_path ):
            xbmcvfs.delete( self.watched_path )
            self.watched = []

    def _save_watched( self ):
        utils.save_list( self.watched_path, self.watched, "Watched Trailers" )
