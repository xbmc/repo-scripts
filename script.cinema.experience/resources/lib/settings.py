# -*- coding: utf-8 -*- 
import sys, os, traceback, re
import xbmcgui, xbmc, xbmcaddon, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
__addon__                = xbmcaddon.Addon( __scriptID__ )
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
settings_path            = os.path.join( BASE_CURRENT_SOURCE_PATH, "settings.xml" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils

true = True
false = False
null = None

class settings():
    def __init__( self, *args, **kwargs ):
        utils.log( 'settings() - __init__' )
        self.start()
      
    def start( self ):
        utils.log('settings() - start')
        self.setting_values = self.read_settings_xml()
        self.trivia_settings            = {         "trivia_mode": int( __addon__.getSetting( "trivia_mode" ) ),
                                              "trivia_total_time": int( float( __addon__.getSetting( "trivia_total_time" ) ) ),
                                            "trivia_slide_time_s": int( float( __addon__.getSetting( "trivia_slide_time_s" ) ) ),
                                            "trivia_slide_time_q": int( float( __addon__.getSetting( "trivia_slide_time_q" ) ) ),
                                            "trivia_slide_time_c": int( float( __addon__.getSetting( "trivia_slide_time_c" ) ) ),
                                            "trivia_slide_time_a": int( float( __addon__.getSetting( "trivia_slide_time_a" ) ) ),
                                                   "trivia_music": int( __addon__.getSetting( "trivia_music" ) ),
                                                  "trivia_folder": xbmc.translatePath( __addon__.getSetting( "trivia_folder" ) ).decode('utf-8'),
                                           "trivia_adjust_volume": eval( __addon__.getSetting( "trivia_adjust_volume" ) ),
                                             "trivia_fade_volume": eval( __addon__.getSetting( "trivia_fade_volume" ) ),
                                               "trivia_fade_time": int( float( __addon__.getSetting( "trivia_fade_time" ) ) ),
                                              "trivia_music_file": xbmc.translatePath( __addon__.getSetting( "trivia_music_file" ) ).decode('utf-8'),
                                            "trivia_music_folder": xbmc.translatePath( __addon__.getSetting( "trivia_music_folder" ) ).decode('utf-8'),
                                            "trivia_music_volume": int( float( __addon__.getSetting( "trivia_music_volume" ) ) ),
                                          "trivia_unwatched_only": eval( __addon__.getSetting( "trivia_unwatched_only" ) ), 
                                             "trivia_limit_query": eval( __addon__.getSetting( "trivia_limit_query" ) ),
                                          "trivia_moviequiz_mode": int( __addon__.getSetting( "trivia_moviequiz_mode" ) ),
                                        "trivia_moviequiz_qlimit": int( float( __addon__.getSetting( "trivia_moviequiz_qlimit" ) ) ),
                                                  "trivia_rating": __addon__.getSetting( "trivia_rating" )
                                          }
                                  
        self.trailer_settings           = {       "trailer_count": ( 0, 1, 2, 3, 4, 5, 10, )[int( float( __addon__.getSetting( "trailer_count" ) ) ) ],
                                                "trailer_scraper": ( "amt_database", "amt_current", "local", "xbmc_library", )[int( float( __addon__.getSetting( "trailer_scraper" ) ) ) ],
                                              "trailer_play_mode": int( float( __addon__.getSetting( "trailer_play_mode" ) ) ),
                                        "trailer_download_folder": xbmc.translatePath( __addon__.getSetting( "trailer_download_folder" ) ).decode('utf-8'),
                                                 "trailer_folder": xbmc.translatePath( __addon__.getSetting( "trailer_folder" ) ).decode('utf-8'),
                                            "trailer_amt_db_file": xbmc.translatePath( __addon__.getSetting( "trailer_amt_db_file" ) ).decode('utf-8'),
                                            "trailer_newest_only": eval( __addon__.getSetting( "trailer_newest_only" ) ),
                                                "trailer_quality": ( "Standard", "480p", "720p", "1080p" )[ int( float( __addon__.getSetting( "trailer_quality" ) ) ) ],
                                            "trailer_quality_url": ( "", "_480p", "_720p", "_720p", )[ int( float( __addon__.getSetting( "trailer_quality" ) ) ) ],
                                                "trailer_hd_only": eval( __addon__.getSetting( "trailer_hd_only" ) ),
                                             "trailer_limit_mpaa": eval( __addon__.getSetting( "trailer_limit_mpaa" ) ),
                                            "trailer_limit_genre": eval( __addon__.getSetting( "trailer_limit_genre" ) ),
                                                 "trailer_rating": __addon__.getSetting( "trailer_rating" ),
                                   "trailer_unwatched_movie_only": eval( __addon__.getSetting( "trailer_unwatched_movie_only" ) ),
                                         "trailer_unwatched_only": eval( __addon__.getSetting( "trailer_unwatched_only" ) ),
                                           "trailer_skip_youtube": eval( __addon__.getSetting( "trailer_skip_youtube" ) )
                                          }

        self.video_settings             = {           "mte_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "mte_intro" ) ) ) ],
                                                 "mte_intro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "mte_intro" ) ) ) > 1 ],
                                                 "mte_intro_file": xbmc.translatePath( __addon__.getSetting( "mte_intro_file" ) ).decode('utf-8'),
                                               "mte_intro_folder": xbmc.translatePath( __addon__.getSetting( "mte_intro_folder" ) ).decode('utf-8'),
                                                      "mte_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "mte_outro" ) ) ) ],
                                                 "mte_outro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "mte_outro" ) ) ) > 1 ],
                                                 "mte_outro_file": xbmc.translatePath( __addon__.getSetting( "mte_outro_file" ) ).decode('utf-8'),
                                               "mte_outro_folder": xbmc.translatePath( __addon__.getSetting( "mte_outro_folder" ) ).decode('utf-8'),
                                                      "fpv_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "fpv_intro" ) ) ) ],
                                                 "fpv_intro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "fpv_intro" ) ) ) > 1 ],
                                                 "fpv_intro_file": xbmc.translatePath( __addon__.getSetting( "fpv_intro_file" ) ).decode('utf-8'),
                                               "fpv_intro_folder": xbmc.translatePath( __addon__.getSetting( "fpv_intro_folder" ) ).decode('utf-8'),
                                                      "fpv_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "fpv_outro" ) ) ) ],
                                                 "fpv_outro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "fpv_outro" ) ) ) > 1 ],
                                                 "fpv_outro_file": xbmc.translatePath( __addon__.getSetting( "fpv_outro_file" ) ).decode('utf-8'),
                                               "fpv_outro_folder": xbmc.translatePath( __addon__.getSetting( "fpv_outro_folder" ) ).decode('utf-8'),
                                                 "enable_ratings": eval( __addon__.getSetting( "enable_ratings" ) ),
                                           "rating_videos_folder": xbmc.translatePath( __addon__.getSetting( "rating_videos_folder" ) ).decode('utf-8'),
                                                   "enable_audio": eval( __addon__.getSetting( "enable_audio" ) ),
                                            "audio_videos_folder": xbmc.translatePath( __addon__.getSetting( "audio_videos_folder" ) ).decode('utf-8'),
                                                "countdown_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "countdown_video" ) ) ) ],
                                           "countdown_video_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "countdown_video" ) ) ) > 1 ],
                                           "countdown_video_file": xbmc.translatePath( __addon__.getSetting( "countdown_video_file" ) ).decode('utf-8'),
                                         "countdown_video_folder": xbmc.translatePath( __addon__.getSetting( "countdown_video_folder" ) ).decode('utf-8'),
                                                      "cav_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "cav_intro" ) ) ) ],
                                                 "cav_intro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "cav_intro" ) ) ) > 1 ],
                                                 "cav_intro_file": xbmc.translatePath( __addon__.getSetting( "cav_intro_file" ) ).decode('utf-8'),
                                               "cav_intro_folder": xbmc.translatePath( __addon__.getSetting( "cav_intro_folder" ) ).decode('utf-8'),
                                                      "cav_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "cav_outro" ) ) ) ],
                                                 "cav_outro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "cav_outro" ) ) ) > 1 ],
                                                 "cav_outro_file": xbmc.translatePath( __addon__.getSetting( "cav_outro_file" ) ).decode('utf-8'),
                                               "cav_outro_folder": xbmc.translatePath( __addon__.getSetting( "cav_outro_folder" ) ).decode('utf-8'),
                                                   "trivia_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "trivia_intro" ) ) ) ],
                                              "trivia_intro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "trivia_intro" ) ) ) > 1 ],
                                              "trivia_intro_file": xbmc.translatePath( __addon__.getSetting( "trivia_intro_file" ) ).decode('utf-8'),
                                            "trivia_intro_folder": xbmc.translatePath( __addon__.getSetting( "trivia_intro_folder" ) ).decode('utf-8'),
                                                   "trivia_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "trivia_outro" ) ) ) ],
                                              "trivia_outro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "trivia_outro" ) ) ) > 1 ],
                                              "trivia_outro_file": xbmc.translatePath( __addon__.getSetting( "trivia_outro_file" ) ).decode('utf-8'),
                                            "trivia_outro_folder": xbmc.translatePath( __addon__.getSetting( "trivia_outro_folder" ) ).decode('utf-8')
                                               }

        self.ha_settings            = {               "ha_enable": eval( __addon__.getSetting( "ha_enable" ) ),
                                               "ha_multi_trigger": eval( __addon__.getSetting( "ha_multi_trigger" ) ),
                                                "ha_script_start": eval( __addon__.getSetting( "ha_script_start" ) ),
                                                "ha_trivia_intro": eval( __addon__.getSetting( "ha_trivia_intro" ) ),
                                                "ha_trivia_start": eval( __addon__.getSetting( "ha_trivia_start" ) ),
                                                "ha_trivia_outro": eval( __addon__.getSetting( "ha_trivia_outro" ) ),
                                                   "ha_mte_intro": eval( __addon__.getSetting( "ha_mte_intro" ) ),
                                                   "ha_cav_intro": eval( __addon__.getSetting( "ha_cav_intro" ) ),
                                               "ha_trailer_start": eval( __addon__.getSetting( "ha_trailer_start" ) ),
                                                   "ha_cav_outro": eval( __addon__.getSetting( "ha_cav_outro" ) ),
                                                   "ha_fpv_intro": eval( __addon__.getSetting( "ha_fpv_intro" ) ),
                                                 "ha_mpaa_rating": eval( __addon__.getSetting( "ha_mpaa_rating" ) ),
                                             "ha_countdown_video": eval( __addon__.getSetting( "ha_countdown_video" ) ),
                                                "ha_audio_format": eval( __addon__.getSetting( "ha_audio_format" ) ),
                                                       "ha_movie": eval( __addon__.getSetting( "ha_movie" ) ),
                                                   "ha_fpv_outro": eval( __addon__.getSetting( "ha_fpv_outro" ) ),
                                                   "ha_mte_outro": eval( __addon__.getSetting( "ha_mte_outro" ) ),
                                                "ha_intermission": eval( __addon__.getSetting( "ha_intermission" ) ),
                                                    "ha_3d_intro": eval( __addon__.getSetting( "ha_3d_intro" ) ),
                                                  "ha_3d_trailer": eval( __addon__.getSetting( "ha_3d_trailer" ) ),
                                                    "ha_3d_outro": eval( __addon__.getSetting( "ha_3d_outro" ) ),
                                                  "ha_script_end": eval( __addon__.getSetting( "ha_script_end" ) ),
                                                      "ha_paused": eval( __addon__.getSetting( "ha_paused" ) ),
                                                     "ha_resumed": eval( __addon__.getSetting( "ha_resumed" ) )
                                      }

        self.extra_settings         = {     "enable_notification": eval( __addon__.getSetting( "enable_notification" ) ),
                                             "number_of_features": int( float( __addon__.getSetting( "number_of_features" ) ) ),
                                             "intermission_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "intermission_video" ) ) ) ],
                                        "intermission_video_type": ( "file", "folder" )[ int( __addon__.getSetting( "intermission_video" ) ) > 1 ],
                                        "intermission_video_file": xbmc.translatePath( __addon__.getSetting( "intermission_video_file" ) ).decode('utf-8'),
                                      "intermission_video_folder": xbmc.translatePath( __addon__.getSetting( "intermission_video_folder" ) ).decode('utf-8'),
                                             "intermission_audio": eval( __addon__.getSetting( "intermission_audio" ) ),
                                           "intermission_ratings": eval( __addon__.getSetting( "intermission_ratings" ) ),
                                                    "voxcommando": eval( __addon__.getSetting( "voxcommando" ) ),
                                                  "override_play": eval( __addon__.getSetting( "override_play" ) )
                                      }
        
        self._3d_settings           = {         "enable_3d_intro": eval( __addon__.getSetting( "enable_3d_intro" ) ),
                                                  "3d_movie_tags": __addon__.getSetting( "3d_movie_tags" ),
                                                    "3d_override": eval( __addon__.getSetting( "3d_override" ) ),
                                                       "3d_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_intro" ) ) ) ],
                                                  "3d_intro_type": ( "file", "folder" )[ int( __addon__.getSetting( "3d_intro" ) ) > 1 ],
                                                  "3d_intro_file": xbmc.translatePath( __addon__.getSetting( "3d_intro_file" ) ).decode('utf-8'),
                                                "3d_intro_folder": xbmc.translatePath( __addon__.getSetting( "3d_intro_folder" ) ).decode('utf-8'),
                                                   "3d_fpv_intro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_fpv_intro" ) ) ) ],
                                              "3d_fpv_intro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "3d_fpv_intro" ) ) ) > 1 ],
                                              "3d_fpv_intro_file": xbmc.translatePath( __addon__.getSetting( "3d_fpv_intro_file" ) ).decode('utf-8'),
                                            "3d_fpv_intro_folder": xbmc.translatePath( __addon__.getSetting( "3d_fpv_intro_folder" ) ).decode('utf-8'),
                                                   "3d_fpv_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_fpv_outro" ) ) ) ],
                                              "3d_fpv_outro_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "3d_fpv_outro" ) ) ) > 1 ],
                                              "3d_fpv_outro_file": xbmc.translatePath( __addon__.getSetting( "3d_fpv_outro_file" ) ).decode('utf-8'),
                                            "3d_fpv_outro_folder": xbmc.translatePath( __addon__.getSetting( "3d_fpv_outro_folder" ) ).decode('utf-8'),
                                                       "3d_outro": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_outro" ) ) ) ],
                                                  "3d_outro_type": ( "file", "folder" )[ int( __addon__.getSetting( "3d_outro" ) ) > 1 ],
                                                  "3d_outro_file": xbmc.translatePath( __addon__.getSetting( "3d_outro_file" ) ).decode('utf-8'),
                                                "3d_outro_folder": xbmc.translatePath( __addon__.getSetting( "3d_outro_folder" ) ).decode('utf-8'),
                                             "3d_countdown_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_countdown_video" ) ) ) ],
                                        "3d_countdown_video_type": ( "file", "folder" )[ int( float( __addon__.getSetting( "3d_countdown_video" ) ) ) > 1 ],
                                        "3d_countdown_video_file": xbmc.translatePath( __addon__.getSetting( "3d_countdown_video_file" ) ).decode('utf-8'),
                                      "3d_countdown_video_folder": xbmc.translatePath( __addon__.getSetting( "3d_countdown_video_folder" ) ).decode('utf-8'),
                                              "3d_enable_ratings": eval( __addon__.getSetting( "3d_enable_ratings" ) ),
                                        "3d_rating_videos_folder": xbmc.translatePath( __addon__.getSetting( "3d_rating_videos_folder" ) ).decode('utf-8'),
                                                "3d_enable_audio": eval( __addon__.getSetting( "3d_enable_audio" ) ),
                                         "3d_audio_videos_folder": xbmc.translatePath( __addon__.getSetting( "3d_audio_videos_folder" ) ).decode('utf-8'),
                                                    "3d_trailers": eval( __addon__.getSetting( "3d_trailers" ) ),
                                               "3d_trailer_count": ( 0, 1, 2, 3, 4, 5, 10, )[int( float( __addon__.getSetting( "3d_trailer_count" ) ) ) ],
                                              "3d_trailer_folder": xbmc.translatePath( __addon__.getSetting( "3d_trailer_folder" ) ).decode('utf-8'),
                                          "3d_trailer_limit_mpaa": eval( __addon__.getSetting( "3d_trailer_limit_mpaa" ) ),
                                         "3d_trailer_limit_genre": eval( __addon__.getSetting( "3d_trailer_limit_genre" ) ),
                                              "3d_trailer_rating": __addon__.getSetting( "3d_trailer_rating" ),
                                      "3d_trailer_unwatched_only":  eval( __addon__.getSetting( "3d_trailer_unwatched_only" ) ),
                                          "3d_intermission_video": ( 0, 1, 1, 2, 3, 4, 5, )[ int( float( __addon__.getSetting( "3d_intermission_video" ) ) ) ],
                                     "3d_intermission_video_type": ( "file", "folder" )[ int( __addon__.getSetting( "3d_intermission_video" ) ) > 1 ],
                                     "3d_intermission_video_file": xbmc.translatePath( __addon__.getSetting( "3d_intermission_video_file" ) ).decode('utf-8'),
                                   "3d_intermission_video_folder": xbmc.translatePath( __addon__.getSetting( "3d_intermission_video_folder" ) ).decode('utf-8')
                                      }

        self.audio_formats          = {                     "dts": "DTS",
                                                            "dca": "DTS",
                                                          "dtsma": "DTS-MA",
                                                       "dtshd_ma": "DTSHD-MA",
                                                      "dtshd_hra": "DTS-HR",
                                                          "dtshr": "DTS-HR",
                                                            "ac3": "Dolby",
                                                       "a_truehd": "Dolby TrueHD",
                                                         "truehd": "Dolby TrueHD"
                                       }
        self.triggers               = ( "Script Start", "Trivia Intro", "Trivia", "Trivia Outro", "Coming Attractions Intro", "Movie Trailer", 
                                    "Coming Attractions Outro", "Movie Theater Intro", "Countdown", "3D Movie Trailer", "Feature Presentation Intro", "Audio Format", 
                                    "MPAA Rating", "Movie", "Feature Presentation Outro", "Movie Theatre Outro", "Intermission", "Script End", "Pause", "Resume" )

    def read_settings_xml( self ):
        setting_values = {}
        try:
            utils.log( "Reading settings.xml" )
            settings_file = xbmcvfs.File( settings_path ).read()
            settings_list = settings_file.replace("<settings>\n","").replace("</settings>\n","").split("/>\n")
            for setting in settings_list:
                match = re.search('    <setting id="(.*?)" value="(.*?)"', setting)
                if match:
                    setting_values[ match.group( 1 ) ] =  match.group( 2 ) 
                else:
                    match = re.search("""    <setting id="(.*?)" value='(.*?)'""", setting)
                    if match:
                        setting_values[ match.group( 1 ) ] =  match.group( 2 )
        except:
            traceback.print_exc()
        return setting_values
        
    def settings_to_log( self ):
        try:
            utils.log( "Settings" )
            setting_values = self.read_settings_xml()
            for k, v in sorted( setting_values.items() ):
                utils.log( "%30s: %s" % ( k, str( utils.unescape( v.decode('utf-8', 'ignore') ) ) ) )
        except:
            traceback.print_exc()
            
    def store_settings( self ):
        try:
            utils.log( "Storing Settings" )
            setting_values = self.read_settings_xml()
            for k, v in sorted( setting_values.items() ):
                __addon__.setSetting( id=k, value=v )
        except:
            traceback.print_exc()
        return True
            
        