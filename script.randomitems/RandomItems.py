import xbmc
from xbmcgui import Window
from urllib import quote_plus, unquote_plus
import re
import sys
import os
import random


class Main:
    # grab the home window
    WINDOW = Window( 10000 )

    def _clear_properties( self ):
        # we enumerate thru and clear individual properties in case other scripts set window properties
        for count in range( self.LIMIT ):
            # we clear title for visible condition
            self.WINDOW.clearProperty( "RandomMovie.%d.Title" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomEpisode.%d.ShowTitle" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomSong.%d.Title" % ( count + 1, ) )

    def _get_media( self, path, file ):
        # set default values
        play_path = fanart_path = thumb_path = path + file
        # we handle stack:// media special
        if ( file.startswith( "stack://" ) ):
            play_path = fanart_path = file
            thumb_path = file[ 8 : ].split( " , " )[ 0 ]
        # we handle rar:// and zip:// media special
        if ( file.startswith( "rar://" ) or file.startswith( "zip://" ) ):
            play_path = fanart_path = thumb_path = file
        # return media info
        return xbmc.getCacheThumbName( thumb_path ), xbmc.getCacheThumbName( fanart_path ), play_path

    def _parse_argv( self ):
        try:
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            # no params passed
            params = {}
        # set our preferences
        self.LIMIT = int( params.get( "limit", "5" ) )
        self.ALBUMS = params.get( "albums", "" ) == "True"
        self.UNPLAYED = params.get( "unplayed", "" ) == "True"
        self.PLAY_TRAILER = params.get( "trailer", "" ) == "True"
        self.ALARM = int( params.get( "alarm", "0" ) )
        self.RANDOM_ORDER = "True"

    def _set_alarm( self ):
        # only run if user/skinner preference
        if ( not self.ALARM ): return
        # set the alarms command
        command = "XBMC.RunScript(%s,limit=%d&albums=%s&unplayed=%s&trailer=%s&alarm=%d)" % ( os.path.join( os.getcwd(), __file__ ), self.LIMIT, str( self.ALBUMS ), str( self.UNPLAYED ), str( self.PLAY_TRAILER ), self.ALARM, )
        xbmc.executebuiltin( "AlarmClock(RandomItems,%s,%d,true)" % ( command, self.ALARM, ) )

    def __init__( self ):
        # parse argv for any preferences
        self._parse_argv()
        # clear properties
        self._clear_properties()
        # set any alarm
        self._set_alarm()
        # format our records start and end
        xbmc.executehttpapi( "SetResponseFormat()" )
        xbmc.executehttpapi( "SetResponseFormat(OpenRecord,%s)" % ( "<record>", ) )
        xbmc.executehttpapi( "SetResponseFormat(CloseRecord,%s)" % ( "</record>", ) )
        # fetch media info
        self._fetch_movie_info()
        self._fetch_tvshow_info()
        self._fetch_music_info()
    
    def _fetch_movie_info( self ):
        # set our unplayed query
        unplayed = ( "", "where playCount is null ", )[ self.UNPLAYED ]
        # sql statement
        if ( self.RANDOM_ORDER ):
            # random order
            sql_movies = "select * from movieview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
        else:
            # movies not finished
            sql_movies = "select movieview.*, bookmark.timeInSeconds from movieview join bookmark on (movieview.idFile = bookmark.idFile) %sorder by movieview.c00 limit %d" % ( unplayed, self.LIMIT, )
        # query the database
        movies_xml = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % quote_plus( sql_movies ), )
        # separate the records
        movies = re.findall( "<record>(.+?)</record>", movies_xml, re.DOTALL )
        # enumerate thru our records and set our properties
        for count, movie in enumerate( movies ):
            # separate individual fields
            fields = re.findall( "<field>(.*?)</field>", movie, re.DOTALL )
            # set properties

            self.WINDOW.setProperty( "RandomMovie.%d.Title" % ( count + 1, ), fields[ 2 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Rating" % ( count + 1, ), fields[ 7 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Year" % ( count + 1, ), fields[ 9 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Plot" % ( count + 1, ), fields[ 3 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.RunningTime" % ( count + 1, ), fields[ 13 ] )
            # get cache names of path to use for thumbnail/fanart and play path
            thumb_cache, fanart_cache, play_path = self._get_media( fields[ 25 ], fields[ 24 ] )
            if os.path.isfile("%s.dds" % (xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", os.path.splitext(fanart_cache)[0],) ) )):
                fanart_cache = "%s.dds" % (os.path.splitext(fanart_cache)[0],)
            self.WINDOW.setProperty( "RandomMovie.%d.Path" % ( count + 1, ), ( play_path, fields[ 21 ], )[ fields[ 21 ] != "" and self.PLAY_TRAILER ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Trailer" % ( count + 1, ), fields[ 21 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) )
            # initial thumb path
            thumb = "special://profile/Thumbnails/Video/%s/%s" % ( thumb_cache[ 0 ], thumb_cache, )
            # if thumb does not exist use an auto generated thumb path
            if ( not os.path.isfile( xbmc.translatePath( thumb ) ) ):
                thumb = "special://profile/Thumbnails/Video/%s/auto-%s" % ( thumb_cache[ 0 ], thumb_cache, )
            self.WINDOW.setProperty( "RandomMovie.%d.Thumb" % ( count + 1, ), thumb )

    def _fetch_tvshow_info( self ):
        # set our unplayed query
        unplayed = ( "", "where playCount is null ", )[ self.UNPLAYED ]
        # sql statement
        if ( self.RANDOM_ORDER ):
            # random order
            sql_episodes = "select * from episodeview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
        else:
            # tv shows not finished
            sql_episodes = "select episodeview.*, bookmark.timeInSeconds from episodeview join bookmark on (episodeview.idFile = bookmark.idFile) %sorder by episodeview.strTitle limit %d" % ( unplayed, self.LIMIT, )
        # query the database
        episodes_xml = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % quote_plus( sql_episodes ), )
        # separate the records
        episodes = re.findall( "<record>(.+?)</record>", episodes_xml, re.DOTALL )
        # enumerate thru our records and set our properties
        for count, episode in enumerate( episodes ):
            # separate individual fields
            fields = re.findall( "<field>(.*?)</field>", episode, re.DOTALL )
            # set properties        
            self.WINDOW.setProperty( "RandomEpisode.%d.ShowTitle" % ( count + 1, ), fields[ 28 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeTitle" % ( count + 1, ), fields[ 2 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNo" % ( count + 1, ), "s%02de%02d" % ( int( fields[ 14 ] ), int( fields[ 15 ] ), ) )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeSeason" % ( count + 1, ), fields[ 14 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNumber" % ( count + 1, ), fields[ 15 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.Rating" % ( count + 1, ), fields[ 5 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.Plot" % ( count + 1, ), fields[ 3 ] )
            # get cache names of path to use for thumbnail/fanart and play path
            thumb_cache, fanart_cache, play_path = self._get_media( fields[ 25 ], fields[ 24 ] )
            if ( not os.path.isfile( xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) ) ) ):
                fanart_cache = xbmc.getCacheThumbName(os.path.join(os.path.split(os.path.split(fields[ 25 ])[0])[0], ""))
            if os.path.isfile("%s.dds" % (xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", os.path.splitext(fanart_cache)[0],) ) )):
                fanart_cache = "%s.dds" % (os.path.splitext(fanart_cache)[0],)
            self.WINDOW.setProperty( "RandomEpisode.%d.Path" % ( count + 1, ), play_path )
            self.WINDOW.setProperty( "RandomEpisode.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) )
            # initial thumb path
            thumb = "special://profile/Thumbnails/Video/%s/%s" % ( thumb_cache[ 0 ], thumb_cache, )
            # if thumb does not exist use an auto generated thumb path
            if ( not os.path.isfile( xbmc.translatePath( thumb ) ) ):
                thumb = "special://profile/Thumbnails/Video/%s/auto-%s" % ( thumb_cache[ 0 ], thumb_cache, )
            self.WINDOW.setProperty( "RandomEpisode.%d.Thumb" % ( count + 1, ), thumb )

    def _fetch_music_info( self ):
        # sql statement
        if ( self.ALBUMS ):
            sql_music = "select idAlbum from albumview order by idAlbum desc limit %d" % ( self.LIMIT, )
            # query the database for recently added albums
            music_xml = xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_music ), )
            # separate the records
            albums = re.findall( "<record>(.+?)</record>", music_xml, re.DOTALL )
            # set our unplayed query
            unplayed = ( "(idAlbum = %s)", "(idAlbum = %s and lastplayed is null)", )[ self.UNPLAYED ]
            # sql statement
            sql_music = "select songview.* from songview where %s limit 1" % ( unplayed, )
            # clear our xml data
            music_xml = ""
            # enumerate thru albums and fetch info
            for album in albums:
                # query the database and add result to our string
                music_xml += xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_music % ( album.replace( "<field>", "" ).replace( "</field>", "" ), ) ), )
        else:
            # set our unplayed query
            unplayed = ( "", "where lastplayed is null ", )[ self.UNPLAYED ]
            # sql statement
            sql_music = "select * from songview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
            # query the database
            music_xml = xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_music ), )
        # separate the records
        items = re.findall( "<record>(.+?)</record>", music_xml, re.DOTALL )
        # enumerate thru our records and set our properties
        for count, item in enumerate( items ):
            # separate individual fields
            fields = re.findall( "<field>(.*?)</field>", item, re.DOTALL )
            # set properties
            self.WINDOW.setProperty( "RandomSong.%d.Title" % ( count + 1, ), fields[ 3 ] )
            self.WINDOW.setProperty( "RandomSong.%d.Year" % ( count + 1, ), fields[ 6 ] )
            self.WINDOW.setProperty( "RandomSong.%d.Artist" % ( count + 1, ), fields[ 24 ] )
            self.WINDOW.setProperty( "RandomSong.%d.Album" % ( count + 1, ), fields[ 21 ] )
            self.WINDOW.setProperty( "RandomSong.%d.Rating" % ( count + 1, ), fields[ 18 ] )
            path = fields[ 22 ]
            # don't add song for albums list TODO: figure out how toplay albums
            ##if ( not self.ALBUMS ):
            path += fields[ 8 ]
            self.WINDOW.setProperty( "RandomSong.%d.Path" % ( count + 1, ), path )
            # get cache name of path to use for fanart
            cache_name = xbmc.getCacheThumbName( fields[ 24 ] )
            self.WINDOW.setProperty( "RandomSong.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Music/%s/%s" % ( "Fanart", cache_name, ) )
            self.WINDOW.setProperty( "RandomSong.%d.Thumb" % ( count + 1, ), fields[ 27 ] )

if ( __name__ == "__main__" ):
    Main()