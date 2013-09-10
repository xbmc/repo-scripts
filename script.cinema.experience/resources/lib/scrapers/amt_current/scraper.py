# -*- coding: utf-8 -*-

"""
Apple Movie Trailers current trailers scraper
"""

import os, sys, time, re, urllib, traceback
from random import shuffle, random
from xml.sax.saxutils import unescape

import xbmc

#__useragent__ = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
__useragent__ = "QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
#__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

class _urlopener( urllib.FancyURLopener ):
    version = __useragent__
# set for user agent
urllib._urlopener = _urlopener()

BASE_CACHE_PATH          = sys.modules["__main__"].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules["__main__"].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules["__main__"].BASE_CURRENT_SOURCE_PATH

class _Parser:
    """
        Parses an xml document for videos
    """

    def __init__( self, xmlSource, mpaa, genre, settings, watched ):
        self.mpaa = mpaa
        self.genre = genre.replace( "Sci-Fi", "Science Fiction" ).replace( "Action", "Action and ADV" ).replace( "Adventure", "ACT and Adventure" ).replace( "ACT",  "Action" ).replace( "ADV",  "Adventure" ).split( " / " )
        self.settings = settings
        self.watched = watched
        self.trailers = []
        # get our regions format
        self.date_format = xbmc.getRegion( "datelong" ).replace( "DDDD,", "" ).replace( "MMMM", "%B" ).replace( "D", "%d" ).replace( "YYYY", "%Y" ).strip()
        # get the list
        self._parse_source( xmlSource )

    def _parse_source( self, xmlSource ):
        try:
            # counter to limit results
            count = 0
            # mpaa ratings
            mpaa_ratings = { "G": 0, "PG": 1, "PG-13": 2, "R": 3, "NC-17": 4, "--": 5, "Not yet rated": -1 }
            # set the proper mpaa rating user preference
            self.mpaa = ( self.settings[ "trailer_rating" ], self.mpaa, )[ self.settings[ "trailer_limit_mpaa" ] ]
            # encoding
            encoding = re.findall( "<\?xml version=\"[^\"]*\" encoding=\"([^\"]*)\"\?>", xmlSource )[ 0 ]
            # gather all video records <movieinfo>
            movies = re.findall( "<movieinfo id=\"(.+?)\">(.*?)</movieinfo>", xmlSource )
            # randomize the trailers and create our play list
            shuffle( movies )
            # enumerate thru the movies list and gather info
            print movies
            for id, movie in movies:
                # user preference to skip watch trailers
                if ( self.settings[ "trailer_unwatched_only" ] and id in self.watched ):
                    continue
                # find info
                info = re.findall( "<info>(.*?)</info>", movie )
                # check if rating is ok
                mpaa = re.findall( "<rating>(.*?)</rating>", info[ 0 ] )[ 0 ]
                if ( mpaa_ratings.get( self.mpaa, -1 ) < mpaa_ratings.get( mpaa, -1 ) ):
                    continue
                # check if genre is ok
                genre = re.findall( "<genre>(.*?)</genre>", movie )
                genres = []
                if ( genre ):
                    genres = [ genre for genre in re.findall( "<name>(.*?)</name>", genre[ 0 ] ) ]
                genre = " / ".join( genres )
                if ( not set( genres ).intersection( set( self.genre ) ) and self.settings[ "trailer_limit_genre" ] ):
                    continue
                # add id to watched file TODO: maybe don't add if not user preference
                self.watched += [ id ]
                #cast = re.findall( "<cast>(.*?)</cast>", movie )
                poster = re.findall( "<poster>(.*?)</poster>", movie )
                preview = re.findall( "<preview>(.*?)</preview>", movie )
                # set our info
                try:
                    title = unicode( unescape( re.findall( "<title>(.*?)</title>", info[ 0 ] )[ 0 ] ), encoding, "replace" )
                except:
                    traceback.print_exc()
                    title = ""
                    print info[ 0 ]
                try:
                    runtime = re.findall( "<runtime>(.*?)</runtime>", info[ 0 ] )[ 0 ]
                except:
                    traceback.print_exc()
                    runtime = ""
                    print info[ 0 ]
                try:
                    studio = unicode( unescape( re.findall( "<studio>(.*?)</studio>", info[ 0 ] )[ 0 ] ), encoding, "replace" )
                except:
                    traceback.print_exc()
                    studio = ""
                    print info[ 0 ]
                #postdate = ""
                #tmp_postdate = re.findall( "<postdate>(.*?)</postdate>", info[ 0 ] )[ 0 ]
                #if ( tmp_postdate ):
                #    postdate = "%s-%s-%s" % ( tmp_postdate[ 8 : ], tmp_postdate[ 5 : 7 ], tmp_postdate[ : 4 ], )
                try:
                    releasedate = re.findall( "<releasedate>(.*?)</releasedate>", info[ 0 ] )[ 0 ]
                    if ( not releasedate ):
                        releasedate = ""
                except:
                    traceback.print_exc()
                    print info[ 0 ]
                    releasedate = ""
                #copyright = unicode( unescape( re.findall( "<copyright>(.*?)</copyright>", info[ 0 ] )[ 0 ] ), encoding, "replace" )
                director = unicode( unescape( re.findall( "<director>(.*?)</director>", info[ 0 ] )[ 0 ] ), encoding, "replace" )
                plot = unicode( unescape( re.findall( "<description>(.*?)</description>", info[ 0 ] )[ 0 ] ), encoding, "replace" )
                # actors
                #actors = []
                #if ( cast ):
                #    actor_list = re.findall( "<name>(.*?)</name>", cast[ 0 ] )
                #    for actor in actor_list:
                #        actors += [ unicode( unescape( actor ), encoding, "replace" ) ]
                # poster
                xlarge = re.findall( "<xlarge>(.*?)</xlarge>", poster[ 0 ] )
                location = re.findall( "<location>(.*?)</location>", poster[ 0 ] )
                poster = xlarge[ 0 ] or location[ 0 ]
                # add user agent to url
                poster += "|User-Agent=%s" % ( urllib.quote_plus( __useragent__ ), )
                # trailer
                trailer = re.findall( "<large[^>]*>(.*?)</large>", preview[ 0 ] )[ 0 ]
                # replace with 1080p if quality == 1080p
                if ( self.settings[ "trailer_quality" ] == "1080p" ):
                    trailer = trailer.replace( "a720p.m4v", "h1080p.mov" )
                # add user agent to url
                trailer += "|User-Agent=%s" % ( urllib.quote_plus( __useragent__ ), )
                # size
                #size = long( re.findall( "filesize=\"([0-9]*)", preview[ 0 ] )[ 0 ] )
                # add the item to our media list
                self.trailers += [ ( id, title, trailer, poster, plot, runtime, mpaa, releasedate, studio, genre, "Movie Trailer", director, ) ]
                # increment counter
                count += 1
                # if we have enough exit
                if ( count == self.settings[ "trailer_count" ] ):
                    break
        except:
            # oops print error message
            traceback.print_exc()


class Main:
    print "Apple Movie Trailers Newest trailers scraper"
    # base url
    BASE_CURRENT_URL = "http://www.apple.com/trailers/home/xml/newest%s.xml"
    
    def __init__( self, equivalent_mpaa=None, mpaa=None, genre=None, settings=None, movie=None ):
        self.mpaa = equivalent_mpaa
        self.genre = genre
        self.settings = settings

    def fetch_trailers( self ):
        # initialize trailers list
        trailers = []
        # fetch source
        path = os.path.join( BASE_CURRENT_SOURCE_PATH, "newest%s.xml" % self.settings[ "trailer_quality_url" ] )
        url = self.BASE_CURRENT_URL % ( self.settings[ "trailer_quality_url" ], )
        xmlSource = self._get_xml_source( path, url )
        # parse source and add our items
        if ( xmlSource ):
            trailers = self._parse_xml_source( xmlSource )
        # return results
        return trailers

    def _get_xml_source( self, base_path, base_url=None ):
        try:
            ok = True
            # get the source files date if it exists
            try: date = os.path.getmtime( base_path )
            except: date = 0
            # we only refresh if it's been more than a day, 24hr * 60min * 60sec
            refresh = ( ( time.time() - ( 24 * 60 * 60 ) ) >= date )
            # only fetch source if it's been more than a day
            if ( refresh and base_url is not None ):
                # open url
                usock = urllib.urlopen( base_url )
            else:
                # open path
                usock = open( base_path, "r" )
            # read source
            xmlSource = usock.read()
            # close socket
            usock.close()
            # save the xmlSource for future parsing
            if ( refresh and base_url is not None ):
                ok = self._save_xml_source( xmlSource, base_path )
        except:
            # oops print error message
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            ok = False
        if ( ok ):
            return xmlSource
        else:
            return ""

    def _save_xml_source( self, xmlSource, base_path ):
        try:
            # if the path to the source file does not exist create it
            if ( not os.path.isdir( os.path.dirname( base_path ) ) ):
                os.makedirs( os.path.dirname( base_path ) )
            # open source path for writing
            file_object = open( base_path, "w" )
            # write xmlSource
            file_object.write( xmlSource )
            # close file object
            file_object.close()
            # return successful
            return True
        except:
            # oops print error message
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            return False

    def _parse_xml_source( self, xmlSource ):
        # base path to watched file
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
        # get watched file
        try:
            watched = eval( self._get_xml_source( base_path ) )
        except:
            watched = []
        # Parse xmlSource for videos
        parser = _Parser( xmlSource, self.mpaa, self.genre, self.settings, watched )
        # saved watched file
        ok = self._save_xml_source( repr( parser.watched ), base_path )
        # return result
        return parser.trailers
