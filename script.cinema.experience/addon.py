# -*- coding: utf-8 -*-

import xbmcgui, xbmc, xbmcaddon, xbmcvfs
import os, re, sys, socket, traceback, time, __builtin__
from urllib import quote_plus
from threading import Thread
#from multiprocessing import Process as Thread

__addon__         = xbmcaddon.Addon()
__version__       = __addon__.getAddonInfo('version')
__scriptID__      = __addon__.getAddonInfo('id')
__script__        = __addon__.getAddonInfo('name')
__addonname__     = __script__
# language method
__language__ = __addon__.getLocalizedString
# settings method
__setting__ = __addon__.getSetting

true = True
false = False
null = None

triggers                    = ( "Script Start", "Trivia Intro", "Trivia", "Trivia Outro", "Coming Attractions Intro", "Movie Trailer", 
                                "Coming Attractions Outro", "Movie Theater Intro", "Countdown", "Feature Presentation Intro", "Audio Format", 
                                "MPAA Rating", "Movie", "Feature Presentation Outro", "Movie Theatre Outro", "Intermission", "Script End", "Pause", "Resume" )

trivia_settings             = {        "trivia_mode": int( __setting__( "trivia_mode" ) ),
                                 "trivia_total_time": int( float( __setting__( "trivia_total_time" ) ) ),
                               "trivia_slide_time_s": int( float( __setting__( "trivia_slide_time_s" ) ) ),
                               "trivia_slide_time_q": int( float( __setting__( "trivia_slide_time_q" ) ) ),
                               "trivia_slide_time_c": int( float( __setting__( "trivia_slide_time_c" ) ) ),
                               "trivia_slide_time_a": int( float( __setting__( "trivia_slide_time_a" ) ) ),
                                      "trivia_music": int( __setting__( "trivia_music" ) ),
                                     "trivia_folder": xbmc.translatePath( __setting__( "trivia_folder" ) ).decode('utf-8'),
                              "trivia_adjust_volume": eval( __setting__( "trivia_adjust_volume" ) ),
                                "trivia_fade_volume": eval( __setting__( "trivia_fade_volume" ) ),
                                  "trivia_fade_time": int( float( __setting__( "trivia_fade_time" ) ) ),
                                 "trivia_music_file": xbmc.translatePath( __setting__( "trivia_music_file" ) ).decode('utf-8'),
                               "trivia_music_folder": xbmc.translatePath( __setting__( "trivia_music_folder" ) ).decode('utf-8'),
                               "trivia_music_volume": int( float( __setting__( "trivia_music_volume" ) ) ),
                             "trivia_unwatched_only": eval( __setting__( "trivia_unwatched_only" ) ), 
                                "trivia_limit_query": eval( __setting__( "trivia_limit_query" ) ),
                             "trivia_moviequiz_mode": int( __setting__( "trivia_moviequiz_mode" ) ),
                           "trivia_moviequiz_qlimit": int( float( __setting__( "trivia_moviequiz_qlimit" ) ) ),
                                     "trivia_rating": __setting__( "trivia_rating" )
                              }
                              
trailer_settings             = { "trailer_count": ( 0, 1, 2, 3, 4, 5, 10, )[int( float( __setting__( "trailer_count" ) ) ) ],
                               "trailer_scraper": ( "amt_database", "amt_current", "local", "xbmc_library", )[int( float( __setting__( "trailer_scraper" ) ) ) ],
                             "trailer_play_mode": int( float( __setting__( "trailer_play_mode" ) ) ),
                       "trailer_download_folder": xbmc.translatePath( __setting__( "trailer_download_folder" ) ).decode('utf-8'),
                                "trailer_folder": xbmc.translatePath( __setting__( "trailer_folder" ) ).decode('utf-8'),
                           "trailer_amt_db_file": xbmc.translatePath( __setting__( "trailer_amt_db_file" ) ).decode('utf-8'),
                           "trailer_newest_only": eval( __setting__( "trailer_newest_only" ) ),
                               "trailer_quality": ( "Standard", "480p", "720p", "1080p" )[ int( float( __setting__( "trailer_quality" ) ) ) ],
                           "trailer_quality_url": ( "", "_480p", "_720p", "_720p", )[ int( float( __setting__( "trailer_quality" ) ) ) ],
                               "trailer_hd_only": eval( __setting__( "trailer_hd_only" ) ),
                            "trailer_limit_mpaa": eval( __setting__( "trailer_limit_mpaa" ) ),
                           "trailer_limit_genre": eval( __setting__( "trailer_limit_genre" ) ),
                                "trailer_rating": __setting__( "trailer_rating" ),
                  "trailer_unwatched_movie_only": eval( __setting__( "trailer_unwatched_movie_only" ) ),
                        "trailer_unwatched_only": eval( __setting__( "trailer_unwatched_only" ) ),
                          "trailer_skip_youtube": eval( __setting__( "trailer_skip_youtube" ) )
                               }

video_settings             = { "mte_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "mte_intro" ) ) ) ],
                          "mte_intro_type": ( "file", "folder" )[ int( float( __setting__( "mte_intro" ) ) ) > 1 ],
                          "mte_intro_file": xbmc.translatePath( __setting__( "mte_intro_file" ) ).decode('utf-8'),
                        "mte_intro_folder": xbmc.translatePath( __setting__( "mte_intro_folder" ) ).decode('utf-8'),
                               "mte_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "mte_outro" ) ) ) ],
                          "mte_outro_type": ( "file", "folder" )[ int( float( __setting__( "mte_outro" ) ) ) > 1 ],
                          "mte_outro_file": xbmc.translatePath( __setting__( "mte_outro_file" ) ).decode('utf-8'),
                        "mte_outro_folder": xbmc.translatePath( __setting__( "mte_outro_folder" ) ).decode('utf-8'),
                               "fpv_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "fpv_intro" ) ) ) ],
                          "fpv_intro_type": ( "file", "folder" )[ int( float( __setting__( "fpv_intro" ) ) ) > 1 ],
                          "fpv_intro_file": xbmc.translatePath( __setting__( "fpv_intro_file" ) ).decode('utf-8'),
                        "fpv_intro_folder": xbmc.translatePath( __setting__( "fpv_intro_folder" ) ).decode('utf-8'),
                               "fpv_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "fpv_outro" ) ) ) ],
                          "fpv_outro_type": ( "file", "folder" )[ int( float( __setting__( "fpv_outro" ) ) ) > 1 ],
                          "fpv_outro_file": xbmc.translatePath( __setting__( "fpv_outro_file" ) ).decode('utf-8'),
                        "fpv_outro_folder": xbmc.translatePath( __setting__( "fpv_outro_folder" ) ).decode('utf-8'),
                          "enable_ratings": eval( __setting__( "enable_ratings" ) ),
                    "rating_videos_folder": xbmc.translatePath( __setting__( "rating_videos_folder" ) ).decode('utf-8'),
                            "enable_audio": eval( __setting__( "enable_audio" ) ),
                     "audio_videos_folder": xbmc.translatePath( __setting__( "audio_videos_folder" ) ).decode('utf-8'),
                         "countdown_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "countdown_video" ) ) ) ],
                    "countdown_video_type": ( "file", "folder" )[ int( float( __setting__( "countdown_video" ) ) ) > 1 ],
                    "countdown_video_file": xbmc.translatePath( __setting__( "countdown_video_file" ) ).decode('utf-8'),
                  "countdown_video_folder": xbmc.translatePath( __setting__( "countdown_video_folder" ) ).decode('utf-8'),
                               "cav_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "cav_intro" ) ) ) ],
                          "cav_intro_type": ( "file", "folder" )[ int( float( __setting__( "cav_intro" ) ) ) > 1 ],
                          "cav_intro_file": xbmc.translatePath( __setting__( "cav_intro_file" ) ).decode('utf-8'),
                        "cav_intro_folder": xbmc.translatePath( __setting__( "cav_intro_folder" ) ).decode('utf-8'),
                               "cav_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "cav_outro" ) ) ) ],
                          "cav_outro_type": ( "file", "folder" )[ int( float( __setting__( "cav_outro" ) ) ) > 1 ],
                          "cav_outro_file": xbmc.translatePath( __setting__( "cav_outro_file" ) ).decode('utf-8'),
                        "cav_outro_folder": xbmc.translatePath( __setting__( "cav_outro_folder" ) ).decode('utf-8'),
                            "trivia_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "trivia_intro" ) ) ) ],
                       "trivia_intro_type": ( "file", "folder" )[ int( float( __setting__( "trivia_intro" ) ) ) > 1 ],
                       "trivia_intro_file": xbmc.translatePath( __setting__( "trivia_intro_file" ) ).decode('utf-8'),
                     "trivia_intro_folder": xbmc.translatePath( __setting__( "trivia_intro_folder" ) ).decode('utf-8'),
                            "trivia_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "trivia_outro" ) ) ) ],
                       "trivia_outro_type": ( "file", "folder" )[ int( float( __setting__( "trivia_outro" ) ) ) > 1 ],
                       "trivia_outro_file": xbmc.translatePath( __setting__( "trivia_outro_file" ) ).decode('utf-8'),
                     "trivia_outro_folder": xbmc.translatePath( __setting__( "trivia_outro_folder" ) ).decode('utf-8')
                               }

feature_settings             = { "enable_notification": eval( __setting__( "enable_notification" ) ),
                                  "number_of_features": int( float( __setting__( "number_of_features" ) ) ),
                                  "intermission_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __setting__( "intermission_video" ) ) ) ],
                             "intermission_video_type": ( "file", "folder" )[ int( __setting__( "intermission_video" ) ) > 1 ],
                             "intermission_video_file": xbmc.translatePath( __setting__( "intermission_video_file" ) ).decode('utf-8'),
                           "intermission_video_folder": xbmc.translatePath( __setting__( "intermission_video_folder" ) ).decode('utf-8'),
                                  "intermission_audio": eval( __setting__( "intermission_audio" ) ),
                                "intermission_ratings": eval( __setting__( "intermission_ratings" ) )
                               }

ha_settings             = {       "ha_enable": eval( __setting__( "ha_enable" ) ),
                           "ha_multi_trigger": eval( __setting__( "ha_multi_trigger" ) ),
                            "ha_script_start": eval( __setting__( "ha_script_start" ) ),
                            "ha_trivia_intro": eval( __setting__( "ha_trivia_intro" ) ),
                            "ha_trivia_start": eval( __setting__( "ha_trivia_start" ) ),
                            "ha_trivia_outro": eval( __setting__( "ha_trivia_outro" ) ),
                               "ha_mte_intro": eval( __setting__( "ha_mte_intro" ) ),
                               "ha_cav_intro": eval( __setting__( "ha_cav_intro" ) ),
                           "ha_trailer_start": eval( __setting__( "ha_trailer_start" ) ),
                               "ha_cav_outro": eval( __setting__( "ha_cav_outro" ) ),
                               "ha_fpv_intro": eval( __setting__( "ha_fpv_intro" ) ),
                             "ha_mpaa_rating": eval( __setting__( "ha_mpaa_rating" ) ),
                         "ha_countdown_video": eval( __setting__( "ha_countdown_video" ) ),
                            "ha_audio_format": eval( __setting__( "ha_audio_format" ) ),
                                   "ha_movie": eval( __setting__( "ha_movie" ) ),
                               "ha_fpv_outro": eval( __setting__( "ha_fpv_outro" ) ),
                               "ha_mte_outro": eval( __setting__( "ha_mte_outro" ) ),
                            "ha_intermission": eval( __setting__( "ha_intermission" ) ),
                              "ha_script_end": eval( __setting__( "ha_script_end" ) ),
                                  "ha_paused": eval( __setting__( "ha_paused" ) ),
                                 "ha_resumed": eval( __setting__( "ha_resumed" ) )
                          }

extra_settings          = {     "voxcommando": eval( __setting__( "voxcommando" ) ) }

audio_formats           = {             "dts": "DTS",
                                        "dca": "DTS",
                                      "dtsma": "DTS-MA",
                                   "dtshd_ma": "DTSHD-MA",
                                  "dtshd_hra": "DTS-HR",
                                      "dtshr": "DTS-HR",
                                        "ac3": "Dolby",
                                   "a_truehd": "Dolby TrueHD",
                                     "truehd": "Dolby TrueHD"
                          }

number_of_features = feature_settings[ "number_of_features" ] + 1
playback = ""
BASE_CACHE_PATH          = os.path.join( xbmc.translatePath( "special://profile" ).decode('utf-8'), "Thumbnails", "Video" )
BASE_CURRENT_SOURCE_PATH = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), os.path.basename( __addon__.getAddonInfo('path') ) )
BASE_RESOURCE_PATH       = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path').decode('utf-8'), 'resources' ) )
home_automation_folder   = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" )
home_automation_module   = os.path.join( home_automation_folder, "home_automation.py" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
headings = ( __language__(32600), __language__(32601), __language__(32602), __language__(32603), __language__(32604), __language__(32605), __language__(32606), __language__(32607), __language__(32608), __language__(32609), __language__(32610), __language__(32611), __language__(32612) )
header = "Cinema Experience"
time_delay = 200
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") ).decode('utf-8')
playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
is_paused = False
prev_trigger = ""
script_header = "[ %s ]" % __scriptID__

from ce_playlist import _get_special_items, build_music_playlist, _rebuild_playlist, _store_playlist, _get_queued_video_info, _clear_playlists
from slides import _fetch_slides
from new_trailer_downloader import downloader
from utils import settings_to_log
from launch_automation import Launch_automation

#Check to see if module is moved to /userdata/addon_data/script.cinema.experience
if not xbmcvfs.exists( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" ) ):
    source = os.path.join( BASE_RESOURCE_PATH, "ha_scripts", "home_automation.py" )
    destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" )
    xbmcvfs.mkdir( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" ) )        
    xbmcvfs.copy( source, destination )
    xbmc.log( "[ script.cinema.experience ] - home_automation.py copied", level=xbmc.LOGNOTICE )

def footprints():
    xbmc.log( "[ script.cinema.experience ] - Script Name: %s" % __script__, level=xbmc.LOGNOTICE )
    xbmc.log( "[ script.cinema.experience ] - Script ID: %s" % __scriptID__, level=xbmc.LOGNOTICE )
    xbmc.log( "[ script.cinema.experience ] - Script Version: %s" % __version__, level=xbmc.LOGNOTICE )
    xbmc.log( "[ script.cinema.experience ] - Starting Window ID: %s" % xbmcgui.getCurrentWindowId(), level=xbmc.LOGNOTICE )

def _clear_watched_items( clear_type ):
    xbmc.log( "[ script.cinema.experience ] - _clear_watched_items( %s )" % ( clear_type ), level=xbmc.LOGNOTICE )
    # initialize base_path
    base_paths = []
    # clear trivia or trailers
    if ( clear_type == "ClearWatchedTrailers" ):
        # handle AMT db special
        sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "scrapers") )
        from amt_database import scraper as scraper
        Scraper = scraper.Main()
        # update trailers
        Scraper.clear_watched()
        # set base watched file path
        base_paths += [ os.path.join( BASE_CURRENT_SOURCE_PATH, "amt_current_watched.txt" ) ]
        base_paths += [ os.path.join( BASE_CURRENT_SOURCE_PATH, "local_watched.txt" ) ]
    else:
        # set base watched file path
        base_paths = [ os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" ) ]
    try:
        # set proper message
        message = ( 32531, 32541, )[ sys.argv[ 1 ] == "ClearWatchedTrailers" ]
        # remove watched status file(s)
        for base_path in base_paths:
            # remove file if it exists
            if ( xbmcvfs.exists( base_path ) ):
                xbmcvfs.delete( base_path )
    except:
        # set proper message
        message = ( 32532, 32542, )[ sys.argv[ 1 ] == "ClearWatchedTrailers" ]
    # inform user of result
    ok = xbmcgui.Dialog().ok( __language__( 32000 ), __language__( message ) )

def _build_playlist( movies, mode = "movie_titles" ):
    if mode == "movie_titles":
        xbmc.log( "[script.cinema.experience] - Movie Title Mode", level=xbmc.LOGNOTICE )
        for movie in movies:
            xbmc.log( "[script.cinema.experience] - Movie Title: %s" % movie, level=xbmc.LOGNOTICE )
            xbmc.executehttpapi( "SetResponseFormat()" )
            xbmc.executehttpapi( "SetResponseFormat(OpenField,)" )
            # select Movie path from movieview Limit 1
            sql = "SELECT movieview.idMovie, movieview.c00, movieview.strPath, movieview.strFileName, movieview.c08, movieview.c14 FROM movieview WHERE c00 LIKE '%s' LIMIT 1" % ( movie.replace( "'", "''", ), )
            xbmc.log( "[script.cinema.experience]  - SQL: %s" % ( sql, ), level=xbmc.LOGDEBUG )
            # query database for info dummy is needed as there are two </field> formatters
            try:
                movie_id, movie_title, movie_path, movie_filename, thumb, genre, dummy = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % quote_plus( sql ), ).split( "</field>" )
                movie_id = int( movie_id )
            except:
                traceback.print_exc()
                xbmc.log( "[script.cinema.experience] - Unable to match movie", level=xbmc.LOGERROR )
                movie_id = 0
                movie_title = movie_path = movie_filename = thumb = genre = dummy = ""
            movie_full_path = os.path.join(movie_path, movie_filename).replace("\\\\" , "\\")
            xbmc.log( "[script.cinema.experience] - Movie Title: %s" % movie_title, level=xbmc.LOGNOTICE )
            xbmc.log( "[script.cinema.experience] - Movie Path: %s" % movie_path, level=xbmc.LOGNOTICE )
            xbmc.log( "[script.cinema.experience] - Movie Filename: %s" % movie_filename, level=xbmc.LOGNOTICE )
            xbmc.log( "[script.cinema.experience] - Full Movie Path: %s" % movie_full_path, level=xbmc.LOGNOTICE )
            if not movie_id == 0:
                json_command = '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 1, "item": {"movieid": %d} }, "id": 1}' % int( movie_id )
                json_response = xbmc.executeJSONRPC(json_command)
                xbmc.log( "[script.cinema.experience] - JSONRPC Response: \n%s" % json_response, level=xbmc.LOGDEBUG )
                xbmc.sleep( 50 )
    elif mode == "movie_ids":
        xbmc.log( "[script.cinema.experience] - Movie ID Mode", level=xbmc.LOGNOTICE )
        for movie_id in movies:
            xbmc.log( "[script.cinema.experience] - Movie ID: %s" % movie_id, level=xbmc.LOGNOTICE )
            json_command = '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 1, "item": {"movieid": %d} }, "id": 1}' % int( movie_id )
            json_response = xbmc.executeJSONRPC( json_command )
            xbmc.log( "[script.cinema.experience] - JSONRPC Response: \n%s" % json_response, level=xbmc.LOGDEBUG )
            xbmc.sleep( 50 )

if __name__ == "__main__" :
    #xbmc.sleep( 2000 )
    footprints()
    prev_trigger = ""
    settings_to_log( BASE_CURRENT_SOURCE_PATH, script_header )
    # check to see if an argv has been passed to script
    xbmcgui.Window(10025).setProperty( "CinemaExperienceRunning", "True" )
    from ce_player import Script
    try:
        try:
            if sys.argv[ 1 ]:
                xbmc.log( "[ script.cinema.experience ] - Script Started With: %s" % sys.argv[ 1 ], level=xbmc.LOGNOTICE )
                try:
                    _command = ""
                    titles = ""
                    if sys.argv[ 1 ] == "ClearWatchedTrivia" or sys.argv[ 1 ] == "ClearWatchedTrailers":
                        _clear_watched_items( sys.argv[ 1 ] )
                        exit = True
                    elif sys.argv[ 1 ] == "oldway":
                        __addon__.setSetting( id='number_of_features', value='0' ) # set number of features to 1
                        _clear_playlists()
                        xbmc.sleep( 250 )
                        xbmc.executebuiltin( "Action(Queue,%d)" % ( xbmcgui.getCurrentWindowId() - 10000, ) )
                        xbmc.log( "[ script.cinema.experience ] - Action(Queue,%d)" % ( xbmcgui.getCurrentWindowId() - 10000, ), level=xbmc.LOGNOTICE )
                        # we need to sleep so the video gets queued properly
                        xbmc.sleep( 250 )
                        exit = Script().start_script( "oldway" )
                    elif sys.argv[ 1 ] == "fromplay":
                        xbmc.sleep( 250 )
                        exit = Script().start_script( "oldway" )
                    elif sys.argv[ 1 ].startswith( "command" ):   # Command Arguments
                        _sys_arg = sys.argv[ 1 ].replace("<li>",";")
                        _command = re.split(";", _sys_arg, maxsplit=1)[1]
                        xbmc.log( "[ script.cinema.experience ] - Command Call: %s" % _command, level=xbmc.LOGNOTICE )
                        if _command.startswith( "movie_title" ):   # Movie Title
                            _clear_playlists()
                            if _command.startswith( "movie_title;" ):
                                titles = re.split(";", _command, maxsplit=1)[1]
                            elif _command.startswith( "movie_title=" ):
                                titles = re.split("=", _command, maxsplit=1)[1]
                            movie_titles = titles.split( ";" )
                            if not movie_titles == "":
                                _build_playlist( movie_titles )
                                exit = Script().start_script( "oldway" )
                            else:
                                exit = False
                        elif _command.startswith( "sqlquery" ):    # SQL Query
                            _clear_playlists()
                            sqlquery = re.split(";", _command, maxsplit=1)[1]
                            movie_titles = _sqlquery( sqlquery )
                            if not movie_titles == "":
                                _build_playlist( movie_titles )
                                exit = Script().start_script( "oldway" )
                            else:
                                exit = False
                        elif _command.startswith( "open_settings" ):    # Open Settings
                            __addon__.openSettings()
                            exit = False
                    elif sys.argv[ 1 ].startswith( "movieid=" ):
                        _clear_playlists()
                        movie_id = sys.argv[ 1 ].split("=")[ 1 ]
                        movie_ids = movie_id.split( ";" )
                        if movie_ids:
                            _build_playlist( movie_ids, mode="movie_ids" )
                            exit = Script().start_script( "oldway" )
                        else:
                            exit = False
                    else:
                        _clear_playlists()
                        exit = Script().start_script( sys.argv[ 1 ].lower() )
                except:
                    traceback.print_exc()
        except:
            if not int( xbmcgui.getCurrentWindowId() ) == 10001: # Not Started from Addon/Programs window
                #start script in 'Old Way' if the script is called with out argv... queue the movie the old way
                __addon__.setSetting( id='number_of_features', value='0' ) # set number of features to 1
                _clear_playlists()
                xbmc.executebuiltin( "Action(Queue,%d)" % ( xbmcgui.getCurrentWindowId() - 10000, ) )
                xbmc.log( "[ script.cinema.experience ] - Action(Queue,%d)" % ( xbmcgui.getCurrentWindowId() - 10000, ), level=xbmc.LOGNOTICE )
                # we need to sleep so the video gets queued properly
                xbmc.sleep( 500 )
                exit = Script().start_script( "oldway" )
            else:
                __addon__.openSettings()
                exit = True
        #xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % (header, __language__( 32545 ), time_delay, image) )
        xbmc.log( "[ script.cinema.experience ] - messy_exit: %s" % exit, level=xbmc.LOGNOTICE )
        if exit:
            pass
        else:
            _clear_playlists()
            prev_trigger = Launch_automation().launch_automation( triggers[16], None ) # Script End
            __addon__.setSetting( id='number_of_features', value='%d' % (number_of_features - 1) )
            xbmcgui.Window(10025).setProperty( "CinemaExperienceRunning", "False" )
    except:
        traceback.print_exc()
        # if script fails, changes settings back
        __addon__.setSetting( id='number_of_features', value='%d' % (number_of_features - 1) )
        prev_trigger = Launch_automation().launch_automation( triggers[16], None ) # Script End
        xbmcgui.Window(10025).setProperty( "CinemaExperienceRunning", "False" )
