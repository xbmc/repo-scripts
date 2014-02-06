# -*- coding: utf-8 -*-

__script__ = "Cinema Experience"
__scriptID__ = "script.cinema.experience"

# main imports
import os, sys, traceback, threading, re, time
from random import shuffle, random
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
triggers                 = sys.modules[ "__main__" ].triggers
trivia_settings          = sys.modules[ "__main__" ].trivia_settings
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
video_settings           = sys.modules[ "__main__" ].video_settings
ha_settings              = sys.modules[ "__main__" ].ha_settings
extra_settings           = sys.modules[ "__main__" ].extra_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from ce_playlist import build_music_playlist, _rebuild_playlist
import utils

CEPlayer           = xbmc.Player
volume_query = '{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}'

class Trivia( xbmcgui.WindowXML ):
    # special action codes
    ACTION_NEXT_SLIDE = ( 2, 3, 7, )
    ACTION_PREV_SLIDE = ( 1, 4, )
    ACTION_EXIT_SCRIPT = ( 9, 10, 92)

    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXML.__init__( self, *args, **kwargs )
        # update dialog
        self.settings = trivia_settings
        self.mpaa = movie_mpaa
        self.genre = movie_genre
        # initialize our class variable
        self.plist = plist
        self.slide_playlist = slide_playlist
        if self.settings[ "trivia_music" ] > 0:
            self.music_playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
        self._init_variables()
        self._get_global_timer( (self.settings[ "trivia_total_time" ] * 60 ) , self._exit_trivia )
        #display slideshow
        #self.doModal()

    def onInit( self ):
        self._load_watched_trivia_file()
        # start music
        self._start_slideshow_music()
        # Build Video Playlist
        _rebuild_playlist( self.plist )
        # start slideshow
        self._next_slide( 0 )

    def _init_variables( self ):
        self.global_timer = None
        self.slide_timer = None
        self.exiting = False
        self.xbmc_volume = self._get_current_volume()
        self.image_count = 0
        self.watched = []

    def _get_current_volume( self ):
        # get the current volume
        result = xbmc.executeJSONRPC( volume_query )
        match = re.search( '"volume" ?: ?([0-9]{1,3})', result )
        volume = int( match.group(1) )
        utils.log( "Current Volume: %d" % volume )
        return volume

    def _start_slideshow_music( self ):
        if self.settings[ "trivia_music" ] > 0:
            utils.log( "Starting Tivia Music", xbmc.LOGNOTICE )
            # did user set this preference
            # check to see if script is to adjust the volume
            if self.settings[ "trivia_adjust_volume" ]:
                utils.log( "Adjusting Volume to %s" % self.settings[ "trivia_music_volume" ], xbmc.LOGNOTICE )
                # calculate the new volume
                volume = self.settings[ "trivia_music_volume" ]
                # set the volume percent of current volume
                xbmc.executebuiltin( "XBMC.SetVolume(%d)" % ( volume, ) )
            # play music
            xbmc.sleep( 200 )
            CEPlayer().play( self.music_playlist )

    def _next_slide( self, slide=1, final_slide=False ):
        # cancel timer if it's running
        if self.slide_timer is not None:
            self.slide_timer.cancel()
        # increment/decrement count
        self.image_count += slide
        # check to see if music playlist has come to an end
        if self.settings[ "trivia_music" ] > 0:
            if ( not CEPlayer().isPlayingAudio() ):
                utils.log( "Restarting Music Playback", xbmc.LOGNOTICE )
                CEPlayer().play( self.music_playlist )
        if self.image_count < 0:
            self.image_count = 0
        # if no more slides, exit
        if self.image_count > len( self.slide_playlist ) -1:
            self._exit_trivia()
        else:     
            # set the property the image control uses
            myslide = self.slide_playlist[ self.image_count ]
            slide_type = "still"
            if (re.search("__question__", myslide)) :
                slide_type = "question"
                myslide = myslide.replace("__question__", "")
            elif (re.search("__answer__", myslide)) :
                slide_type = "answer"
                myslide = myslide.replace("__answer__", "")
            elif (re.search("__clue__", myslide)) :
                slide_type = "clue"
                myslide = myslide.replace("__clue__", "")
            elif (re.search("__still__", myslide)) :
                slide_type = "still"
                myslide = myslide.replace("__still__", "")
            utils.log( "Slide #%s Type %s - %s" % (self.image_count, slide_type, myslide), xbmc.LOGNOTICE )
            xbmcgui.Window( xbmcgui.getCurrentWindowId() ).setProperty( "Slide", myslide )
            # add id to watched file TODO: maybe don't add if not user preference
            self.watched.append( xbmc.getCacheThumbName( self.slide_playlist[ self.image_count ] ) )
            # start slide timer
            self._get_slide_timer( slide_type )
        

    def _load_watched_trivia_file( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" )
        self.watched = utils.load_saved_list( base_path, "Watched Trivia" )
        #print self.watched
        
    def _save_watched_trivia_file( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" )
        #print self.watched
        utils.save_list( base_path, self.watched, "Watched Trivia" )

    def _reset_watched( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" )
        if xbmcvfs.exists( base_path ):
            xbmcvfs.delete( base_path )
            self.watched = []

    def _get_slide_timer( self, slide_type="still" ):
        if slide_type == "question": 
            timer = self.settings[ "trivia_slide_time_q" ]
        elif slide_type == "answer": 
            timer = self.settings[ "trivia_slide_time_a" ]
        elif slide_type == "clue":
            timer = self.settings[ "trivia_slide_time_c" ]
        elif slide_type == "still":
            timer = self.settings[ "trivia_slide_time_s" ]
        utils.log( "Slide delay %s seconds type is %s" % ( timer, slide_type ), xbmc.LOGNOTICE )
        self.slide_timer = threading.Timer( timer, self._next_slide,() )
        self.slide_timer.start() 

    def _get_global_timer( self, time, function ):
        self.global_timer = threading.Timer( time, function,() )
        self.global_timer.start()

    def _exit_trivia( self ):
        import xbmcscript_player as script
        script.Main()
        # notify we are exiting
        self.exiting = True
        # cancel timers
        self._cancel_timers()
        # save watched slides
        self._save_watched_trivia_file()
        # set the volume back to original
        # show an end image
        self._show_intro_outro( "outro" )

    def _show_intro_outro( self, type="intro" ):
        is_playing = True
        if type == "outro":
            utils.log( "## Outro ##", xbmc.LOGNOTICE )
            if self.settings[ "trivia_fade_volume" ] and self.settings[ "trivia_adjust_volume"]:
                self._fade_volume()
            self._play_video_playlist()
        else:
            pass

    def _play_video_playlist( self ):
        # set this to -1 as True and False are taken
        self.exiting = -1
        # cancel timers
        self._cancel_timers()
        CEPlayer().stop()
        xbmc.sleep( 500 )
        if ( self.settings[ "trivia_fade_volume" ] and self.settings[ "trivia_adjust_volume"] ):
            self._fade_volume( False )
        elif ( not self.settings[ "trivia_fade_volume" ] and self.settings[ "trivia_adjust_volume"] ):
            xbmc.executebuiltin( "XBMC.SetVolume(%d)" % ( self.xbmc_volume ) )
        # close trivia slide show
        self.close()

    def _cancel_timers( self ):
        utils.log( "[script.cinema.experience] Canceling timers...", xbmc.LOGNOTICE )
        # cancel all timers
        if self.slide_timer is not None:
            self.slide_timer.cancel()
            self.slide_timer = None
        if self.global_timer is not None:
            self.global_timer.cancel()
            self.global_timer = None

    def _fade_volume( self, out=True ):
        # set initial start/end values
        volumes = range( 1, self.xbmc_volume + 1 )
        # calc sleep time, 0.5 second for rise time
        sleep_time = 0.5 / len( volumes )
        # if fading out reverse order
        if out:
            utils.log( "Fading Volume", xbmc.LOGNOTICE )
            volumes = range( 1, self.settings[ "trivia_music_volume" ] )
            volumes.reverse()
            # calc sleep time, for fade time
            sleep_time = ( self.settings[ "trivia_fade_time" ] * 1.0 ) / len( volumes )
        else:
            utils.log( "Raising Volume", xbmc.LOGNOTICE )
        # loop thru and set volume
        utils.log( "Start Volume: %d " % ( self._get_current_volume() ), xbmc.LOGNOTICE )
        for volume in volumes:
            xbmc.executebuiltin( "XBMC.SetVolume(%d)" % volume  )
            # sleep
            xbmc.sleep( int( sleep_time * 1000 ) )
        utils.log( "Finish Volume: %d " % ( self._get_current_volume() ), xbmc.LOGNOTICE )

    def onClick( self, controlId ):
        pass

    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if action in self.ACTION_EXIT_SCRIPT and self.exiting is False:
            self._exit_trivia()
        elif action in self.ACTION_EXIT_SCRIPT and self.exiting is True:
            self._play_video_playlist()
        elif action in self.ACTION_NEXT_SLIDE and not self.exiting:
            self._next_slide()
        elif action in self.ACTION_PREV_SLIDE and not self.exiting:
            self._next_slide( -1 )
