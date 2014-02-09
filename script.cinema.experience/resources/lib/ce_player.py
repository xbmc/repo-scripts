import xbmcgui, xbmc, xbmcaddon, xbmcvfs
import os, re, sys, socket, traceback, time, __builtin__
from urllib import quote_plus
from threading import Thread
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

true = True
false = False
null = None

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
triggers                 = sys.modules[ "__main__" ].triggers
trivia_settings          = sys.modules[ "__main__" ].trivia_settings
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
video_settings           = sys.modules[ "__main__" ].video_settings
ha_settings              = sys.modules[ "__main__" ].ha_settings
extra_settings           = sys.modules[ "__main__" ].extra_settings
_3d_settings             = sys.modules[ "__main__" ]._3d_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
__addon__                = xbmcaddon.Addon( __scriptID__ )
# language method
__language__             = __addon__.getLocalizedString

number_of_features = extra_settings[ "number_of_features" ] + 1
playback = ""
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
header = "Cinema Experience"
time_delay = 200
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") ).decode('utf-8')
playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
is_paused = False
prev_trigger = ""
script_header = "[ %s ]" % __scriptID__

from ce_playlist import _get_special_items, build_music_playlist, _rebuild_playlist, _store_playlist, _get_queued_video_info, _clear_playlists
from slides import _fetch_slides
from trailer_downloader import downloader
from launch_automation import Launch_automation
import utils

class Script():
    def __init__(self, *args, **kwargs):
        self. init_var()
        
    def init_var( self ):
        self.player = xbmc.Player()
        
    def start_script( self, library_view = "oldway" ):
        messy_exit = False
        utils.log( "Library_view: %s" % library_view, xbmc.LOGNOTICE )
        early_exit = False
        movie_next = False
        prev_trigger = None
        if library_view != "oldway":
            xbmc.executebuiltin( "ActivateWindow(videolibrary,%s,return)" % library_view )
            # wait until Video Library shows
            while not xbmc.getCondVisibility( "Container.Content(movies)" ):
                pass
            if extra_settings[ "enable_notification" ]:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % (header, __language__( 32546 ), 300000, image) )
            # wait until playlist is full to the required number of features
            utils.log( "Waiting for queue to be filled with %s Feature films" % number_of_features, xbmc.LOGNOTICE )
            count = 0
            while playlist.size() < number_of_features:
                if playlist.size() > count:
                    utils.log( "User queued %s of %s Feature films" % (playlist.size(), number_of_features), xbmc.LOGNOTICE )
                    header1 = header + " - Feature " + "%d" % playlist.size()
                    message = __language__( 32543 ) + playlist[playlist.size() -1].getdescription()
                    if extra_settings[ "enable_notification" ]:
                        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % (header1, message, time_delay, image) )
                    count = playlist.size()
                    xbmc.sleep(time_delay*2)
                if not xbmc.getCondVisibility( "Container.Content(movies)" ):
                    early_exit = True
                    break
            utils.log( "User queued %s Feature films" % playlist.size(), xbmc.LOGNOTICE )
            if not early_exit:
                header1 = header + " - Feature " + "%d" % playlist.size()
                message = __language__( 32543 ) + playlist[playlist.size() -1].getdescription()
                if extra_settings[ "enable_notification" ]:
                    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % (header1, message, time_delay, image) )
                early_exit = False
        # If for some reason the limit does not get reached and the window changed, cancel script
        if playlist.size() < number_of_features and library_view != "oldway":
            if extra_settings[ "enable_notification" ]:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % (header, __language__( 32544 ), time_delay, image) )
            _clear_playlists()
        else:
            mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie = _get_queued_video_info( feature = 0 )
            plist = _store_playlist() # need to store movie playlist
            self._play_trivia( mpaa, genre, plist, equivalent_mpaa )
            mplaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
            mplaylist.clear()
            trigger_list = self.load_trigger_list()
            self.player.play( playlist )
            count = -1
            stop_check = 0
            paused = False
            # wait until fullscreen video is shown
            while not xbmc.getCondVisibility( "Window.IsActive(fullscreenvideo)" ):
                pass
            while not playlist.getposition() == ( playlist.size() - 1 ):
                if playlist.getposition() > count:
                    try:
                        utils.log( "Item From Trigger List: %s" % trigger_list[ playlist.getposition() ], xbmc.LOGNOTICE )
                    except:
                        utils.log( "Problem With Trigger List", xbmc.LOGNOTICE )
                    utils.log( "Playlist Position: %s  Playlist Size: %s " % ( ( playlist.getposition() + 1 ), ( playlist.size() ) ), xbmc.LOGNOTICE )
                    if not playlist.getposition() == ( playlist.size() - 1 ):
                        prev_trigger = Launch_automation().launch_automation( trigger_list[ playlist.getposition() ], prev_trigger )
                        count = playlist.getposition()
                    else: 
                        break  # Reached the last item in the playlist
                try:
                    #if not self.player.isPlayingVideo() and not is_paused:
                    if not xbmc.getCondVisibility( "Window.IsActive(fullscreenvideo)" ):
                        utils.log( "Video may have stopped", xbmc.LOGNOTICE )
                        xbmc.sleep( 5000 )  # wait 5 seconds for fullscreen video to show up(during playback)
                        if not xbmc.getCondVisibility( "Window.IsActive(fullscreenvideo)" ): # if fullscreen video does not show up, break and exit script
                            messy_exit = True
                            break
                except:
                    if xbmc.getCondVisibility( "Container.Content(movies)" ):
                        utils.log( "Video Definitely Stopped", xbmc.LOGNOTICE )
                        messy_exit = True
                        break
            if not playlist.size() < 1 and not messy_exit: # To catch an already running script when a new instance started
                utils.log( "Playlist Position: %s  Playlist Size: %s " % ( playlist.getposition() + 1, ( playlist.size() ) ), xbmc.LOGNOTICE )
                prev_trigger = Launch_automation().launch_automation( trigger_list[ playlist.getposition() ], prev_trigger )
                if trigger_list[ playlist.getposition() ] == "Movie":
                    utils.log( "Item From Trigger List: %s" % trigger_list[ playlist.getposition() ], xbmc.LOGNOTICE )
                else:
                    utils.log( "Item From Trigger List: %s" % trigger_list[ playlist.getposition() ], xbmc.LOGNOTICE )
                messy_exit = False
                xbmc.sleep(1000)
                self._wait_until_end()
            else:
                utils.log( "User might have pressed stop", xbmc.LOGNOTICE )
                utils.log( "Stopping Script", xbmc.LOGNOTICE )
                messy_exit = False
        return messy_exit
        
    def load_trigger_list( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trigger_list.txt" )
        trigger_list = utils.load_saved_list( base_path, "Trigger List" )
        return trigger_list

    def voxcommando():
        playlistsize = playlist.size()
        if playlistsize > 1:
            movie_titles = ""
            #for feature_count in range (1, playlistsize + 1):
            for feature_count in range (1, playlistsize):
                movie_title = playlist[ feature_count - 1 ].getdescription()
                utils.log( "Feature #%-2d - %s" % ( feature_count, movie_title ), xbmc.LOGNOTICE )
                movie_titles = movie_titles + movie_title + "<li>"
            movie_titles = movie_titles.rstrip("<li>")
            if extra_settings[ "voxcommando" ]:
                utils.broadcastUDP( "<b>CElaunch." + str( playlistsize ) + "<li>" + movie_titles + "</b>", port = 33000 )
        else:
            # get the queued video info
            movie_title = playlist[ 0 ].getdescription()
            utils.log( "Feature - %s" % movie_title, xbmc.LOGNOTICE )
            if extra_settings[ "voxcommando" ]:
                utils.broadcastUDP( "<b>CElaunch<li>" + movie_title + "</b>", port = 33000 )

    def _jsonrpc_query( self, jsonquery ):
        movie_ids = []        
        jsonresponse = xbmc.executeJSONRPC( jsonquery )
        data = simplejson.loads( jsonresponse )
        if data.has_key('result'):
            if data['result'].has_key('movies'):
                movie_list = data['result']['movies']
                for movie in movie_list:
                    movie_ids.append( movie[ "movieid" ] )
        return movie_ids

    def trivia_intro( self ):
        utils.log( "## Intro ##", xbmc.LOGNOTICE )
        _clear_playlists( "video" )
        play_list = playlist
        # initialize intro lists
        playlist_intro = []
        # get trivia intro videos
        _get_special_items( playlist=play_list,
                               items=video_settings[ "trivia_intro" ],
                                path=( video_settings[ "trivia_intro_file" ], video_settings[ "trivia_intro_folder" ], )[ video_settings[ "trivia_intro_type" ] == "folder" ],
                               genre= "Trivia Intro",
                               index=0,
                          media_type="video"
                          )
        if not video_settings[ "trivia_intro" ] == 0:
            self.player.play( play_list )
            
    def start_downloader( self, mpaa, genre, equivalent_mpaa ):
        # start the downloader if Play Mode is set to stream and if scraper is not Local or XBMC_library
        if trailer_settings[ "trailer_play_mode" ] == 1 and  ( trailer_settings[ "trailer_scraper" ] in ( "amt_database", "amt_current" ) ):
            utils.log( "Starting Downloader Thread", xbmc.LOGNOTICE )
            thread = Thread( target=downloader, args=( mpaa, genre, equivalent_mpaa ) )
            thread.start()
        else:
            pass
            
    def _wait_until_end( self ): # wait until the end of the playlist(for Trivia Intro)
        utils.log( "Waiting Until End Of Video", xbmc.LOGNOTICE )
        try:
            self.psize = int( xbmc.PlayList( xbmc.PLAYLIST_VIDEO ).size() ) - 1
            utils.log( "Playlist Size: %s" % ( self.psize + 1 ) )
            while xbmc.PlayList( xbmc.PLAYLIST_VIDEO ).getposition() < self.psize:
                pass
            utils.log( "Video TotalTime: %s" % self.player.getTotalTime() )
            while self.player.getTime() < ( self.player.getTotalTime() - 1 ):
                pass
            utils.log( "Video getTime: %s"  % self.player.getTime() )
            #xbmc.sleep(400)
        except:
            traceback.print_exc()
            utils.log( "Video either stopped or skipped, Continuing on..." )

    def _play_trivia( self, mpaa, genre, plist, equivalent_mpaa ):
        Launch_automation().launch_automation( triggers[0] ) # Script Start - Or where it seems to be
        if trivia_settings[ "trivia_mode" ] == 2: # Start Movie Quiz Script
            utils.log( "Starting script.moviequiz", xbmc.LOGNOTICE )
            self.start_downloader( mpaa, genre, equivalent_mpaa )
            try:
                _MA_= xbmcaddon.Addon( "script.moviequiz" )
                BASE_MOVIEQUIZ_PATH = xbmc.translatePath( _MA_.getAddonInfo('path') )
                sys.path.append( BASE_MOVIEQUIZ_PATH )
                try:
                    import quizlib.question as question
                    utils.log( "Loaded question module", xbmc.LOGNOTICE )
                except ImportError:
                    traceback.print_exc()
                    utils.log( "Failed to Load question module", xbmc.LOGNOTICE )
                except:
                    traceback.print_exc()
                try:
                    import quizlib.mq_ce_play as moviequiz
                    utils.log( "Loaded mq_ce_play module", xbmc.LOGNOTICE )
                except ImportError:
                    traceback.print_exc()
                    utils.log( "Failed to Load mq_ce_play module", xbmc.LOGNOTICE )
                except:
                    traceback.print_exc()
    #            pDialog.close()
                self.trivia_intro()        
                if playlist.size() > 0:
                    self._wait_until_end()
                xbmc.sleep( 500 ) # wait .5 seconds 
                xbmc.Player().stop()
                path = _MA_.getAddonInfo('path')
                question_type = 1
                mode = ( True, False )[ trivia_settings[ "trivia_moviequiz_mode" ] ]
                mpaa = ( trivia_settings[ "trivia_rating" ], equivalent_mpaa, )[ trivia_settings[ "trivia_limit_query" ] ]
                question_limit = trivia_settings[ "trivia_moviequiz_qlimit" ]
                completion = moviequiz.runCinemaExperience( question_type, mode, mpaa, genre, question_limit )
                if completion:
                    utils.log( "Completed script.moviequiz", xbmc.LOGNOTICE )
                else:
                    utils.log( "Failed in script.moviequiz", xbmc.LOGNOTICE )
            except:
                traceback.print_exc()
                utils.log( "Failed to start script.moviequiz", xbmc.LOGNOTICE )
            _rebuild_playlist( plist )
            import xbmcscript_player as script
            script.Main()
            xbmc.executebuiltin( "XBMC.ActivateWindow(fullscreenvideo)" )
            #xbmc.sleep(500) # wait .5 seconds
            #xbmc.Player().play( playlist )
        elif trivia_settings[ "trivia_folder" ] and trivia_settings[ "trivia_mode" ] == 1:  # Start Slide Show
            self.start_downloader( mpaa, genre, equivalent_mpaa )
            if not trivia_settings[ "trivia_music" ] == 0:
                build_music_playlist()
            # set the proper mpaa rating user preference
            mpaa = ( trivia_settings[ "trivia_rating" ], equivalent_mpaa, )[ trivia_settings[ "trivia_limit_query" ] ]
            utils.log( "Slide MPAA Rating: %s" % equivalent_mpaa, xbmc.LOGNOTICE )
            # import trivia module and execute the gui
            slide_playlist = _fetch_slides( equivalent_mpaa )
            self.trivia_intro()
            if playlist.size() > 0:
                Launch_automation().launch_automation( triggers[1] ) # Trivia Intro
                xbmc.sleep( 500 ) # wait .5 seconds 
                self._wait_until_end()
            #xbmc.sleep(500) # wait .5 seconds 
            xbmc.Player().stop()
            __builtin__.plist = plist
            __builtin__.slide_playlist = slide_playlist
            __builtin__.movie_mpaa = mpaa
            __builtin__.movie_genre = genre
            from xbmcscript_trivia import Trivia
            utils.log( "Starting Trivia script", xbmc.LOGNOTICE )
            Launch_automation().launch_automation( triggers[2] ) # Trivia Start
            ui = Trivia( "script-CExperience-trivia.xml", __addon__.getAddonInfo('path'), "Default", "720p" )
            ui.doModal()
            del ui
            # we need to activate the video window
            #xbmc.sleep(5) # wait .005 seconds
            xbmc.executebuiltin( "XBMC.ActivateWindow(fullscreenvideo)" )
            #xbmc.Player().play( playlist )
        elif trivia_settings[ "trivia_mode" ] == 0: # No Trivia
            # no trivia slide show so play the video
            self.start_downloader( mpaa, genre, equivalent_mpaa )
            _rebuild_playlist( plist )
            # play the video playlist
            import xbmcscript_player as script
            script.Main()
            xbmc.executebuiltin( "XBMC.ActivateWindow(fullscreenvideo)" )
            xbmc.sleep( 500 ) # wait .5 seconds
            #xbmc.Player().play( playlist )
