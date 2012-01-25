import sys
import os
import re
import thread
import xbmc
import xbmcgui
from threading import Timer
from utilities import *

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__
__settings__   = sys.modules[ "__main__" ].__settings__
__language__   = sys.modules[ "__main__" ].__language__
__cwd__        = sys.modules[ "__main__" ].__cwd__

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )

    def onInit( self ):
        self.setup_all()

    def setup_all( self ):
        self.setup_variables()
        self.settings = get_settings()
        self.get_scraper()
        self.getMyPlayer()

    def get_scraper( self ):
        exec "import scrapers.%s.lyricsScraper as lyricsScraper" % ( self.settings[ "scraper" ], )
        self.LyricsScraper = lyricsScraper.LyricsFetcher()
        self.scraper_title = lyricsScraper.__title__

    def setup_variables( self ):
        self.lock = thread.allocate_lock()
        self.timer = None
        self.allowtimer = True
        self.artist = None
        self.song = None
        self.controlId = -1
        self.pOverlay = []

    def refresh(self):
        self.lock.acquire()
        try:
            #May be XBMC is not playing any media file
            cur_time = xbmc.Player().getTime()
            nums = self.getControl( 110 ).size()
            pos = self.getControl( 110 ).getSelectedPosition()
            if (cur_time < self.pOverlay[pos][0]):
                while (pos > 0 and self.pOverlay[pos - 1][0] > cur_time):
                    pos = pos -1
            else:
                while (pos < nums - 1 and self.pOverlay[pos + 1][0] < cur_time):
                    pos = pos +1
                if (pos + 5 > nums - 1):
                    self.getControl( 110 ).selectItem( nums - 1 )
                else:
                    self.getControl( 110 ).selectItem( pos + 5 )
            self.getControl( 110 ).selectItem( pos )
            self.setFocus( self.getControl( 110 ) )
            if (self.allowtimer and cur_time < self.pOverlay[nums - 1][0]):
                waittime = self.pOverlay[pos + 1][0] - cur_time
                self.timer = Timer(waittime, self.refresh)
                self.timer.start()
            self.lock.release()
        except:
            self.lock.release()

    def show_control( self, controlId ):
        self.getControl( 100 ).setVisible( controlId == 100 )
        self.getControl( 110 ).setVisible( controlId == 110 )
        self.getControl( 120 ).setVisible( controlId == 120 )
        page_control = ( controlId == 100 )

        xbmc.sleep( 5 )
        try:
            self.setFocus( self.getControl( controlId + page_control ) )
        except:
            self.setFocus( self.getControl( controlId ) )

    def get_lyrics(self, artist, song):
        self.reset_controls()
        self.getControl( 200 ).setLabel( "" )
        self.menu_items = []

        lyrics = self.get_lyrics_from_file2()
        if ( lyrics == "" ):
            lyrics = self.get_lyrics_from_file( artist, song )
        if ( lyrics != "" ):
            self.show_lyrics( lyrics )
            self.getControl( 200 ).setEnabled( False )
            self.getControl( 200 ).setLabel( __language__( 30000 ) )
        else:
            self.getControl( 200 ).setEnabled( True )
            self.getControl( 200 ).setLabel( self.scraper_title )
            lyrics = self.LyricsScraper.get_lyrics( artist, song )

            if ( isinstance( lyrics, basestring ) ):
                self.show_lyrics( lyrics, True )
            elif ( isinstance( lyrics, list ) and lyrics ):
                self.show_choices( lyrics )

    def get_lyrics_from_list( self, item ):
        lyrics = self.LyricsScraper.get_lyrics_from_list( self.menu_items[ item ] )
        self.show_lyrics( lyrics, True )

    def get_lyrics_from_file( self, artist, song ):
        try:
            xbmc.sleep( 60 )
            if ( self.settings[ "artist_folder" ] ):
                self.song_path = unicode( os.path.join( self.settings[ "lyrics_path" ], artist.replace( "\\", "_" ).replace( "/", "_" ), song.replace( "\\", "_" ).replace( "/", "_" ) + ".lrc" ), "utf-8" )
            else:
                self.song_path = unicode( os.path.join( self.settings[ "lyrics_path" ], artist.replace( "\\", "_" ).replace( "/", "_" ) + " - " + song.replace( "\\", "_" ).replace( "/", "_" ) + ".lrc" ), "utf-8" )
            lyrics_file = open( self.song_path, "r" )
            lyrics = lyrics_file.read()
            lyrics_file.close()
            return lyrics
        except IOError:
            return ""

    def get_lyrics_from_file2( self ):
        try:
            xbmc.sleep( 60 )
            path = xbmc.Player().getPlayingFile()
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            filename = basename.rsplit( ".", 1 )[ 0 ]
            if ( self.settings[ "subfolder" ] ):
                self.song_path = unicode( os.path.join( dirname, self.settings[ "subfolder_name" ], filename + ".lrc" ), "utf-8" )
            else:
                self.song_path = unicode( os.path.join( dirname, filename + ".lrc" ), "utf-8" )
            lyrics_file = open( self.song_path, "r" )
            lyrics = lyrics_file.read()
            lyrics_file.close()
            return lyrics
        except IOError:
            return ""

    def save_lyrics_to_file( self, lyrics ):
        try:
            if ( not os.path.isdir( os.path.dirname( self.song_path ) ) ):
                os.makedirs( os.path.dirname( self.song_path ) )
            lyrics_file = open( self.song_path, "w" )
            lyrics_file.write( lyrics )
            lyrics_file.close()
            return True
        except IOError:
            LOG( LOG_ERROR, "%s %s::%s (%d) [%s]", __scriptname__, self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            return False

    def show_lyrics( self, lyrics, save=False ):
        if ( lyrics == "" ):
            self.getControl( 100 ).setText( __language__( 30001 ) )
            self.getControl( 110 ).addItem( __language__( 30001 ) )
        else:
            self.parser_lyrics( lyrics )
            lyrics1 = ""
            for time, line in self.pOverlay:
                self.getControl( 110 ).addItem( line )
                lyrics1 += line + '\n'
            self.getControl( 110 ).selectItem( 0 )
            self.getControl( 100 ).setText( lyrics1 )
            if ( self.settings[ "save_lyrics" ] and save ): success = self.save_lyrics_to_file( lyrics )
        self.show_control( 100 + ( self.settings[ "smooth_scrolling" ] * 10 ) )
        if (self.allowtimer and self.settings[ "smooth_scrolling" ] and self.getControl( 110 ).size() > 1):
            self.refresh()

    def parser_lyrics( self, lyrics):
        self.pOverlay = []
        tag = re.compile('\[(\d+):(\d\d)(\.\d+|)\]')
        lyrics = lyrics.replace( "\r\n" , "\n" )
        sep = "\n"
        for x in lyrics.split( sep ):
            match1 = tag.match( x )
            times = []
            if ( match1 ):
                while ( match1 ):
                    times.append( float(match1.group(1)) * 60 + float(match1.group(2)) )
                    y = 5 + len(match1.group(1)) + len(match1.group(3))
                    x = x[y:]
                    match1 = tag.match( x )
                for time in times:
                    self.pOverlay.append( (time, x) )
        self.pOverlay.sort( cmp=lambda x,y: cmp(x[0], y[0]) )

    def show_choices( self, choices ):
        for song in choices:
            self.getControl( 120 ).addItem( song[ 0 ] )
        self.getControl( 120 ).selectItem( 0 )
        self.menu_items = choices
        self.show_control( 120 )
    
    def reset_controls( self ):
        self.getControl( 100 ).reset()
        self.getControl( 110 ).reset()
        self.getControl( 120 ).reset()

    def exit_script( self, restart=False ):
        self.lock.acquire()
        try:
            self.timer.cancel()
        except:
            pass
        self.allowtimer = False
        self.lock.release()
        self.close()

    def onClick( self, controlId ):
        if ( controlId == 120 ):
            self.get_lyrics_from_list( self.getControl( 120 ).getSelectedPosition() )

    def onFocus( self, controlId ):
        self.controlId = controlId

    def onAction( self, action ):
        actionId = action.getId()
        if ( actionId in CANCEL_DIALOG ):
            self.exit_script()

    def get_artist_from_filename( self, filename ):
        try:
            artist = filename
            song = filename
            basename = os.path.basename( filename )
            # Artist - Song.ext
            if ( self.settings[ "filename_format" ] == "0" ):
                artist = basename.split( "-", 1 )[ 0 ].strip()
                song = os.path.splitext( basename.split( "-", 1 )[ 1 ].strip() )[ 0 ]
            # Artist/Album/Song.ext or Artist/Album/Track Song.ext
            elif ( self.settings[ "filename_format" ] in ( "1", "2", ) ):
                artist = os.path.basename( os.path.split( os.path.split( filename )[ 0 ] )[ 0 ] )
                # Artist/Album/Song.ext
                if ( self.settings[ "filename_format" ] == "1" ):
                    song = os.path.splitext( basename )[ 0 ]
                # Artist/Album/Track Song.ext
                elif ( self.settings[ "filename_format" ] == "2" ):
                    song = os.path.splitext( basename )[ 0 ].split( " ", 1 )[ 1 ]
        except:
            # invalid format selected
            LOG( LOG_ERROR, "%s %s::%s (%d) [%s]", __scriptname__, self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
        return artist, song

    def getMyPlayer( self ):
        self.MyPlayer = MyPlayer( xbmc.PLAYER_CORE_PAPLAYER, function=self.myPlayerChanged )
        self.myPlayerChanged( 2 )

    def myPlayerChanged( self, event, force_update=False ):
        #LOG( LOG_DEBUG, "%s GUI::myPlayerChanged [%s]", __scriptname__, [ "stopped","ended","started" ][ event ] )
        if ( event < 2 ): 
            self.exit_script()
        else:
            for cnt in range( 5 ):
                song = ''
                artist = ''
                songfile = ''
                try:
                    song = xbmc.Player().getMusicInfoTag().getTitle()
                    artist = xbmc.Player().getMusicInfoTag().getArtist()
                    print "Song: " + song + " /Artist: " + artist

                    songfile = xbmc.Player().getPlayingFile()
                except:
                    pass
                if ( song and ( not artist or self.settings[ "use_filename" ] ) ):
                    artist, song = self.get_artist_from_filename( songfile )
                if ( song and ( self.song != song or self.artist != artist or force_update ) ):
                    self.artist = artist
                    self.song = song
                    self.lock.acquire()
                    try:
                        self.timer.cancel()
                    except:
                        pass
                    self.lock.release()
                    self.get_lyrics( artist, song )
                    break
                xbmc.sleep( 50 )
            if (self.allowtimer and self.settings[ "smooth_scrolling" ] and self.getControl( 110 ).size() > 1):
                self.lock.acquire()
                try:
                    self.timer.cancel()
                except:
                    pass
                self.lock.release()
                self.refresh()


## Thanks Thor918 for this class ##
class MyPlayer( xbmc.Player ):
    """ Player Class: calls function when song changes or playback ends """
    def __init__( self, *args, **kwargs ):
        xbmc.Player.__init__( self )
        self.function = kwargs[ "function" ]

    def onPlayBackStopped( self ):
        xbmc.sleep( 300 )
        if ( not xbmc.Player().isPlayingAudio() ):
            self.function( 0 )
    
    def onPlayBackEnded( self ):
        xbmc.sleep( 300 )
        if ( not xbmc.Player().isPlayingAudio() ):
            self.function( 1 )
    
    def onPlayBackStarted( self ):
        self.function( 2 )
