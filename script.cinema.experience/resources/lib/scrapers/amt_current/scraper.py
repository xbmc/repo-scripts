# -*- coding: utf-8 -*-

"""
Apple Movie Trailers current trailers scraper
"""

import os, sys, time, re, urllib, traceback, time
from random import shuffle, random
import xml.etree.ElementTree as ET
from datetime import datetime

import xbmc, xbmcvfs

#__useragent__ = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
__useragent__ = "QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
#__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

class _urlopener( urllib.FancyURLopener ):
    version = __useragent__
# set for user agent
urllib._urlopener = _urlopener()

BASE_CACHE_PATH = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
import utils

class _Parser:
    """
    Parses an xml document for videos
    """

    mpaa_ratings = [ 'G', 'PG', 'PG-13', 'R', 'NC-17', 'NR', 'Not yet rated' ]

    def __init__( self, path, mpaa, genre, settings, scraper ):
        self.mpaa = self.mpaa_ratings.index(mpaa)
        self.genre = genre.replace( "Sci-Fi", "Science Fiction" ).replace( "Action", "Action and ADV" ).replace( "Adventure", "ACT and Adventure" ).replace( "ACT", "Action" ).replace( "ADV", "Adventure" ).split( " / " )
        self.settings = settings
        self.trailers = []
        # get our regions format
        self.date_format = xbmc.getRegion( "datelong" ).replace( "DDDD,", "" ).replace( "MMMM", "%B" ).replace( "D", "%d" ).replace( "YYYY", "%Y" ).strip()
        # override the requested mpaa rating per user preference
        if not self.settings[ 'trailer_limit_mpaa' ]:
            self.mpaa = len( self.mpaa_ratings )
        if self.settings[ 'trailer_rating' ] != '--':
            self.mpaa = self.mpaa_ratings.index( self.settings[ 'trailer_rating' ] )
        # get the list
        self._parse_source( path, scraper )

    def _parse_source( self, path, scraper ):
        try:
            tree = ET.parse( path )
            root = tree.getroot()

            utils.log( "Parsing %d trailers" % len( root ) )

            moviedata = []

            for movieinfo in root.findall( 'movieinfo' ):
                title = movieinfo.findtext( 'info/title' )

                # filter old releases date
                # TODO: add preference
                # Datetime bug workaround: http://forum.xbmc.org/showthread.php?tid=112916
                # test to see if release date is present, if it is, test to see if it is a future release, otherwise assume that it is a future release.
                if movieinfo.findtext( 'info/releasedate' ):
                    releasedate = datetime(*(time.strptime( movieinfo.findtext( 'info/releasedate' ), '%Y-%m-%d' )[0:6]))
                    if releasedate <= datetime.now():
                        root.remove( movieinfo )
                        continue
                    

                # filter watched
                if ( self.settings[ 'trailer_unwatched_only' ] and movieinfo.get( 'id' ) in scraper.watched ):
                    root.remove( movieinfo )
                    continue

                # filter by rating
                mpaa = self.mpaa_ratings.index( movieinfo.find( 'info/rating' ).text )
                if mpaa > self.mpaa:
                    root.remove( movieinfo )
                    continue

                # filter by genre
                genres = [ elem.text for elem in movieinfo.findall( 'genre/name' ) ]
                sr_genres = abs( len( set( genres ).intersection( self.genre ) ) - len( self.genre ) )
                if self.settings[ 'trailer_limit_genre' ]:
                    if sr_genres == len( self.genre ):
                        root.remove( movieinfo )
                        continue
                # append to sort
                moviedata.append( ( mpaa, sr_genres, releasedate, movieinfo ) )

            # sort
            moviedata.sort()
            root[:] = [item[-1] for item in moviedata]

            agent = '|User-Agent=%s' % urllib.quote_plus( __useragent__ )

            for movieinfo in root.findall('movieinfo'):
                trailer = movieinfo.findtext( 'preview/*' )
                if self.settings[ 'trailer_quality' ] == '1080p':
                    trailer = trailer.replace( 'a720p.m4v', 'h1080p.mov' )
                trailer += agent

                self.trailers += [(
                    movieinfo.get( 'id' ),
                    movieinfo.findtext( 'info/title' ),
                    trailer,
                    movieinfo.findtext( 'poster/xlarge' ) + agent,
                    movieinfo.findtext( 'info/description' ),
                    movieinfo.findtext( 'info/runtime' ),
                    movieinfo.findtext( 'info/rating' ),
                    movieinfo.findtext( 'info/releasedate' ),
                    movieinfo.findtext( 'info/studio' ),
                    ' / '.join( [ elem.text for elem in movieinfo.findall( 'genre/name' ) ] ),
                    'Movie Trailer',
                    movieinfo.findtext( 'info/director' )
                )]

            utils.log( "scraper added %d trailers" % len( self.trailers ) )
            
            tree = None

        except:
            # oops print error message
            traceback.print_exc()


class Main:
    utils.log( "Apple Movie Trailers Scraper" )

    # base url
    BASE_CURRENT_URL = "http://www.apple.com/trailers/home/xml/current%s.xml"
    
    def __init__( self, equivalent_mpaa=None, mpaa=None, genre=None, settings=None, movie=None ):
        self.mpaa = equivalent_mpaa
        self.genre = genre
        self.settings = settings
        self.watched_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
            
    def fetch_trailers( self ):
        # initialize trailers list
        trailers = []
        selected_trailers = []
        # fetch source
        path = os.path.join( BASE_CURRENT_SOURCE_PATH, "current%s.xml" % self.settings[ "trailer_quality_url" ] )
        url = self.BASE_CURRENT_URL % ( self.settings[ "trailer_quality_url" ], )

        # parse source and add our items
        if self._update_xml_source( path, url ):
            trailers = self._parse_xml_source( path )
        shuffle( trailers  )
        
        # grab enough trailers
        count = 0
        for trailer in trailers:
            selected_trailers.append( trailer )
            self.watched.append( trailer[ 0 ] )
            count += 1
            if count == int( self.settings[ "trailer_count" ] ):
                break
            
        if ( len( selected_trailers ) < self.settings[ "trailer_count" ] and self.settings[ "trailer_unwatched_only" ] ):
            self._reset_watched()
            #attempt to load our playlist again
            self.fetch_trailers()
        self._save_watched()
        # return results
        return selected_trailers

    def _update_xml_source( self, base_path, base_url=None ):
        try:
            ok = True
            # get the source files date if it exists
            try: date = os.path.getmtime( base_path )
            except: date = 0
            # we only refresh if it's been more than a day, 24hr * 60min * 60sec
            refresh = ( ( time.time() - ( 24 * 60 * 60 ) ) >= date )
            # only fetch source if it's been more than a day
            if ( refresh and base_url is not None ):
                urllib.urlretrieve( base_url, base_path )
        except:
            traceback.print_exc()
            ok = False
        return ok

    def _parse_xml_source( self, base_path ):
        self._get_watched()

        # Parse xml for videos
        parser = _Parser( base_path, self.mpaa, self.genre, self.settings, self )

        # saved watched file
        if int( self.settings[ "trailer_play_mode" ] ) != 1:
            self._save_watched()

        # return result
        trailers = parser.trailers
        parser = None
        return trailers

    def _get_watched( self ):
        self.watched = utils.load_saved_list( self.watched_path, "Trailer Watched List" )

    def _reset_watched( self ):
        utils.log("Resetting Watched List" )
        if xbmcvfs.exists( self.watched_path ):
            xbmcvfs.delete( self.watched_path )
            self.watched = []

    def _save_watched( self ):
        utils.save_list( self.watched_path, self.watched, "Watched Trailers" )