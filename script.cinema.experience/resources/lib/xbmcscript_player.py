# -*- coding: utf-8 -*-

__script__ = "Cinema Experience"
__scriptID__ = "script.cinema.experience"
###########################################################
"""
    Video Playlist Module:
    - Assembles Video Playlist based on user settings
"""
############################################################
# main imports
import sys, os, traceback, threading, re
from urllib import quote_plus
from random import shuffle, random

import xbmcgui, xbmc, xbmcaddon, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
triggers                 = sys.modules[ "__main__" ].triggers
trivia_settings          = sys.modules[ "__main__" ].trivia_settings
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
video_settings           = sys.modules[ "__main__" ].video_settings
ha_settings              = sys.modules[ "__main__" ].ha_settings
extra_settings           = sys.modules[ "__main__" ].extra_settings
_3d_settings             = sys.modules[ "__main__" ]._3d_settings
audio_formats            = sys.modules[ "__main__" ].audio_formats
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
__addon__                = xbmcaddon.Addon( __scriptID__ )
# language method
__language__             = __addon__.getLocalizedString

from ce_playlist import _get_special_items, _get_trailers, _set_trailer_info, _get_queued_video_info
import utils

class Main:
    def __init__( self ):
        self.trigger_list = []
        self.downloaded_trailers = []
        self._play_mode = trailer_settings[ "trailer_play_mode" ]
        self.number_of_features = extra_settings[ "number_of_features" ] + 1
        self.playlistsize = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
        self._build_trigger_list()
        self._start()
        self._save_trigger_list()
        # Set play mode back to the original setting
        __addon__.setSetting( id='trailer_play_mode', value='%d' % int( self._play_mode ) )        

    def _save_trigger_list( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trigger_list.txt" )
        utils.save_list( base_path, self.trigger_list, "Trigger List" )
        
    def _build_trigger_list( self ):
        if self.playlistsize == 1:
            self.trigger_list.append( "Movie" )
        else:
            for count in range( 0, self.playlistsize - 1 ):
                self.trigger_list.append( "Movie" )
            self.trigger_list.append( "Movie" )
    
    def _check_trailers( self ):
        if trailer_settings[ "trailer_play_mode" ] == 1:
            path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloaded_trailers.txt" )
            if xbmcvfs.exists( path ):
                utils.log( "File Exists: downloaded_trailers.txt" )
                trailer_list = self._load_trailer_list()
                if trailer_list:
                    for trailer in trailer_list:
                        trailer_detail = _set_trailer_info( trailer )
                        self.downloaded_trailers += trailer_detail
                else:
                    # Change trailer play mode to stream if no download 
                    utils.log( "Empty File: downloaded_trailers.txt" )
                    __addon__.setSetting( id='trailer_play_mode', value='%d' % 0 )
            else:
                # Change trailer play mode to stream if no download 
                utils.log( "File Does Not Exists: downloaded_trailers.txt" )
                __addon__.setSetting( id='trailer_play_mode', value='%d' % 0 )
        else:
            pass
                    
    def _load_trailer_list( self ):
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloaded_trailers.txt" )
        trailer_list = load_saved_list( base_path, "Downloaded Trailers" )
        
    def _start( self ):
        mpaa = audio = genre = movie = equivalent_mpaa = is_3d_movie = ""
        try:
            # create the playlist
            self.playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
            # Check to see if multiple features have been set in settings
            # if multiple features is greater than 1(not a single feature)
            # add the intermission videos and audio files for the 2, third, etc movies
            if self.playlistsize > 1:
                if extra_settings[ "intermission_video" ] > 0 or extra_settings[  "intermission_audio" ] or extra_settings[ "intermission_ratings" ]:
                    mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie = self._add_intermission_videos()
            # otherwise just build for a single video
            else:
                mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie = _get_queued_video_info( feature = 0 )
            self._create_playlist( mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie )
            # play the trivia slide show
        except:
            traceback.print_exc()

    def _add_intermission_videos( self ):
        utils.log( "Adding intermission Video(s)", xbmc.LOGNOTICE )
        count = 0
        index_count = 1
        for feature in range( 1, self.playlistsize ):
            mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie = _get_queued_video_info( feature = index_count )
            if is_3d_movie and _3d_settings[ "enable_3d_intro" ]:
                if _3d_settings[ "3d_audio_videos_folder" ] and video_settings[ "enable_audio" ]:
                    audio_videos_folder        = _3d_settings[ "3d_audio_videos_folder" ]
                elif video_settings[ "enable_audio" ]:
                    audio_videos_folder        = video_settings[ "audio_videos_folder" ]
                if _3d_settings[ "3d_ratings_videos_folder" ] and video_settings[ "enable_ratings" ]:
                    rating_videos_folder      = _3d_settings[ "3d_rating_videos_folder" ]
                elif video_settings[ "enable_ratings" ]:
                    rating_videos_folder      = video_settings[ "rating_videos_folder" ]
                if _3d_settings[ "3d_intermission_video" ]:
                    intermission_video_file   = _3d_settings[ "3d_intermission_video_file" ]
                    intermission_video_folder = _3d_settings[ "3d_intermission_video_folder" ]
                    intermission_video        = _3d_settings[ "3d_intermission_video" ]
                    intermission_video_type   = _3d_settings[ "3d_intermission_video_type" ]
                else:
                    intermission_video_file   = extra_settings[ "intermission_video_file" ]
                    intermission_video_folder = extra_settings[ "intermission_video_folder" ]
                    intermission_video        = extra_settings[ "intermission_video" ]
                    intermission_video_type   = extra_settings[ "intermission_video_type" ]
            else:
                audio_videos_folder           = video_settings[ "audio_videos_folder" ]
                rating_videos_folder          = video_settings[ "rating_videos_folder" ]
                intermission_video_file       = extra_settings[ "intermission_video_file" ]
                intermission_video_folder     = extra_settings[ "intermission_video_folder" ]
                intermission_video            = extra_settings[ "intermission_video" ]
                intermission_video_type       = extra_settings[ "intermission_video_type" ]            
            #count = index_count
            # add intermission video
            if extra_settings[ "intermission_video" ] > 0:
                utils.log( "Inserting intermission Video(s): %s" % intermission_video, xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=intermission_video,
                                           path=( intermission_video_file, intermission_video_folder, )[ intermission_video_type == "folder" ],
                                          genre="Intermission",
                                         writer="Intermission",
                                          index=index_count
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Intermission Label into Trigger List
                    self.trigger_list.insert( index_count, "Intermission" ) 
                if xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size and intermission_video > 1:
                    index_count += extra_settings[ "intermission_video" ] - 1
                elif xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size and intermission_video == 1:
                    index_count += extra_settings[ "intermission_video" ]
            # get rating video
            if video_settings[ "enable_ratings" ] and extra_settings[ "intermission_ratings" ] and rating_videos_folder != "":
                utils.log( "Inserting Intermission Rating Video", xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=1 * ( rating_videos_folder != "" ),
                                           path=rating_videos_folder + mpaa + ".avi",
                                          genre="Movie Rating",
                                         writer="Movie Rating",
                                         index = index_count
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Rating Label into Trigger List
                    self.trigger_list.insert( index_count, "MPAA Rating" )
                if xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size:
                    index_count += 1
            # get Dolby/DTS videos
            if video_settings[ "enable_audio" ]  and extra_settings[ "intermission_audio" ] and audio_videos_folder:
                utils.log( "Inserting Intermission Audio Format Video", xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=1 * ( audio_videos_folder != "" ),
                                          path = audio_videos_folder + audio_formats.get( audio, "Other" ) + audio_videos_folder[ -1 ],
                                          genre="Audio Format",
                                         writer="Audio Format",
                                         index = index_count
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Audio Format Label into Trigger List
                    self.trigger_list.insert( index_count, "Audio Format" )
                if xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size:
                    index_count += 1
            index_count += 1
        # return info from first movie in playlist
        mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie = _get_queued_video_info( 0 )
        return mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie

    def _create_playlist( self, mpaa, audio, genre, movie, equivalent_mpaa, is_3d_movie ):
        # TODO: try to get a local thumb for special videos?
        utils.log( "Building Cinema Experience Playlist", xbmc.LOGNOTICE )
        # setup for 3d videos
        if is_3d_movie and _3d_settings[ "enable_3d_intro" ]:
            if _3d_settings[ "3d_enable_audio" ] and video_settings[ "enable_audio" ]:
                audio_videos_folder     = _3d_settings[ "3d_audio_videos_folder" ]
            elif not ( _3d_settings[ "3d_override" ] ) and video_settings[ "enable_audio" ]:
                audio_videos_folder     = video_settings[ "audio_videos_folder" ]
            if _3d_settings[ "3d_enable_ratings" ] and video_settings[ "enable_ratings" ]:
                rating_videos_folder   = _3d_settings[ "3d_rating_videos_folder" ]
            elif not ( _3d_settings[ "3d_override" ] ) and video_settings[ "enable_ratings" ]:
                rating_videos_folder   = video_settings[ "rating_videos_folder" ]
            if _3d_settings[ "3d_fpv_intro" ]:
                fpv_intro_file         = _3d_settings[ "3d_fpv_intro_file" ]
                fpv_intro_folder       = _3d_settings[ "3d_fpv_intro_folder" ]
                fpv_intro              = _3d_settings[ "3d_fpv_intro" ]
                fpv_intro_type         = _3d_settings[ "3d_fpv_intro_type" ]
            elif not ( _3d_settings[ "3d_override" ] ):
                fpv_intro_file         = video_settings[ "fpv_intro_file" ]
                fpv_intro_folder       = video_settings[ "fpv_intro_folder" ]
                fpv_intro              = video_settings[ "fpv_intro" ]
                fpv_intro_type         = video_settings[ "fpv_intro_type" ]
            if _3d_settings[ "3d_outro" ]:
                fpv_outro_file         = _3d_settings[ "3d_fpv_outro_file" ]
                fpv_outro_folder       = _3d_settings[ "3d_fpv_outro_folder" ]
                fpv_outro              = _3d_settings[ "3d_fpv_outro" ]
                fpv_outro_type         = _3d_settings[ "3d_fpv_outro_type" ]
            elif not ( _3d_settings[ "3d_override" ] ):
                fpv_outro_file         = video_settings[ "fpv_outro_file" ]
                fpv_outro_folder       = video_settings[ "fpv_outro_folder" ]
                fpv_outro              = video_settings[ "fpv_outro" ]
                fpv_outro_type         = video_settings[ "fpv_outro_type" ]
            if _3d_settings[ "3d_countdown_video" ]:
                countdown_video        = _3d_settings[ "3d_countdown_video" ]
                countdown_video_type   = _3d_settings[ "3d_countdown_video_type" ]
                countdown_video_file   = _3d_settings[ "3d_countdown_video_file" ]
                countdown_video_folder = _3d_settings[ "3d_countdown_video_folder" ]
            elif not ( _3d_settings[ "3d_override" ] ):
                countdown_video        = video_settings[ "countdown_video" ]
                countdown_video_type   = video_settings[ "countdown_video_type" ]
                countdown_video_file   = video_settings[ "countdown_video_file" ]
                countdown_video_folder = video_settings[ "countdown_video_folder" ]
        else:
            audio_videos_folder        = video_settings[ "audio_videos_folder" ]
            rating_videos_folder       = video_settings[ "rating_videos_folder" ]
            fpv_intro                  = video_settings[ "fpv_intro" ]
            fpv_intro_type             = video_settings[ "fpv_intro_type" ]
            fpv_intro_file             = video_settings[ "fpv_intro_file" ]
            fpv_intro_folder           = video_settings[ "fpv_intro_folder" ]
            fpv_outro                  = video_settings[ "fpv_outro" ]
            fpv_outro_type             = video_settings[ "fpv_outro_type" ]
            fpv_outro_file             = video_settings[ "fpv_outro_file" ]
            fpv_outro_folder           = video_settings[ "fpv_outro_folder" ]
            countdown_video            = video_settings[ "countdown_video" ]
            countdown_video_type       = video_settings[ "countdown_video_type" ]
            countdown_video_file       = video_settings[ "countdown_video_file" ]
            countdown_video_folder     = video_settings[ "countdown_video_folder" ]
        # get Dolby/DTS videos
        if video_settings[ "enable_audio" ] and audio_videos_folder:
            utils.log( "Adding Audio Format Video", xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=1 * ( audio_videos_folder != "" ),
                                       path=audio_videos_folder + audio_formats.get( audio, "Other" ) + audio_videos_folder[ -1 ],
                                      genre="Audio Format",
                                     writer="Audio Format",
                                      index=0
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Audio Format Label into Trigger List
                self.trigger_list.insert( 0, "Audio Format" )
        # get rating video
        if video_settings[ "enable_ratings" ]:
            utils.log( "Adding Ratings Video", xbmc.LOGNOTICE )
            utils.log( "    Path: %s" % rating_videos_folder )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=1 * ( rating_videos_folder != "" ),
                                       path=rating_videos_folder + mpaa + ".avi",
                                      genre="MPAA Rating",
                                     writer="MPAA Rating",
                                      index=0
                              )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Rating Label into Trigger List
                self.trigger_list.insert( 0, "MPAA Rating" )
        # get feature presentation intro videos
        if video_settings[ "fpv_intro" ] > 0:
            utils.log( "Adding Feature Presentation Intro Videos: %s Videos" % fpv_intro, xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=fpv_intro,
                                       path=( fpv_intro_file, fpv_intro_folder, )[ fpv_intro_type == "folder" ],
                                      genre="Feature Presentation Intro",
                                     writer="Feature Presentation Intro",
                                      index=0
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Feature Presentation Label into Trigger List
                self.trigger_list.insert( 0, "Feature Presentation Intro" )
        # Add Countdown video
        if video_settings[ "countdown_video" ] > 0:
            utils.log( "Adding Countdown Videos: %s Video(s)" % countdown_video, xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=countdown_video,
                                       path=( countdown_video_file, countdown_video_folder, )[ countdown_video_type == "folder" ],
                                      genre="Countdown",
                                     writer="Countdown",
                                      index=0
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Countdown Label into Trigger List
                self.trigger_list.insert( 0, "Countdown" )
        # get 3D Trailers
        if is_3d_movie and _3d_settings[ "3d_trailers" ]:
            utils.log( "Retriving 3D Trailers: %s Trailers" % _3d_settings[ "3d_trailer_count" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _3d_trailers = _get_trailers(  items=_3d_settings[ "3d_trailer_count" ],
                                 equivalent_mpaa=equivalent_mpaa,
                                            mpaa=mpaa,
                                           genre=genre,
                                           movie=movie,
                                            mode="3D"
                                        )
            for trailer in _3d_trailers:
                # get trailers
                _get_special_items(    playlist=self.playlist,
                                           items=1,
                                            path=trailer[ 2 ],
                                           genre=trailer[ 9 ] or "3D Movie Trailer",
                                           title=trailer[ 1 ],
                                       thumbnail=trailer[ 3 ],
                                            plot=trailer[ 4 ],
                                         runtime=trailer[ 5 ],
                                            mpaa=trailer[ 6 ],
                                    release_date=trailer[ 7 ],
                                          studio=trailer[ 8 ] or "3D Movie Trailer",
                                          writer= "3D Movie Trailer",
                                        director=trailer[ 11 ],
                                           index=0
                                  )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert 3D Trailer Label into Trigger List
                self.trigger_list.insert( 0, "3D Movie Trailer" )
        # 3D Intro Video
        if is_3d_movie and _3d_settings[ "3d_intro" ]:
            utils.log( "Adding 3D Intro Video: %s Videos" % _3d_settings[ "3d_intro" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=_3d_settings[ "3d_intro" ],
                                       path=( _3d_settings[ "3d_intro_file" ], _3d_settings[ "3d_intro_folder" ], )[ _3d_settings[ "3d_intro_type" ] == "folder" ],
                                      genre="3D Intro",
                                     writer="3D Intro",
                                      index=0
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert 3D Intro Label into Trigger List
                self.trigger_list.insert( 0, "3D Intro" )
        # get trailers
        if trailer_settings[ "trailer_count" ] > 0:
            utils.log( "Retriving Trailers: %s Trailers" % trailer_settings[ "trailer_count" ], xbmc.LOGNOTICE )
            trailers = _get_trailers(  items=trailer_settings[ "trailer_count" ],
                             equivalent_mpaa=equivalent_mpaa,
                                        mpaa=mpaa,
                                       genre=genre,
                                       movie=movie,
                                        mode="playlist"
                                    )
            # get coming attractions outro videos
            if video_settings[ "cav_outro" ] > 0:
                utils.log( "Adding Coming Attraction Outro Video: %s Videos" % video_settings[ "cav_outro" ], xbmc.LOGNOTICE )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                _get_special_items(    playlist=self.playlist,
                                          items=video_settings[ "cav_outro" ] * ( len( trailers ) > 0 ),
                                           path=( video_settings[ "cav_outro_file" ], video_settings[ "cav_outro_folder" ], )[ video_settings[ "cav_outro_type" ] == "folder" ],
                                          genre="Coming Attractions Outro",
                                         writer="Coming Attractions Outro",
                                          index=0
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Coming Attraction Outro Label into Trigger List
                    self.trigger_list.insert( 0, "Coming Attractions Outro" )
            # enumerate through our list of trailers and add them to our playlist
            utils.log( "Adding Trailers: %s Trailers" % len( trailers ), xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            for trailer in trailers:
                # get trailers
                _get_special_items(    playlist=self.playlist,
                                           items=1,
                                            path=trailer[ 2 ],
                                           genre=trailer[ 9 ] or "Movie Trailer",
                                           title=trailer[ 1 ],
                                       thumbnail=trailer[ 3 ],
                                            plot=trailer[ 4 ],
                                         runtime=trailer[ 5 ],
                                            mpaa=trailer[ 6 ],
                                    release_date=trailer[ 7 ],
                                          studio=trailer[ 8 ] or "Movie Trailer",
                                          writer= "Movie Trailer",
                                        director=trailer[ 11 ],
                                           index=0
                                  )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Trailer Label into Trigger List
                self.trigger_list.insert( 0, "Movie Trailer" )
            # get coming attractions intro videos
            if video_settings[ "cav_intro" ] > 0:
                utils.log( "Adding Coming Attraction Intro Videos: %s Videos" % video_settings[ "cav_intro" ], xbmc.LOGNOTICE )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                _get_special_items(    playlist=self.playlist,
                                          items=video_settings[ "cav_intro" ] * ( len( trailers ) > 0 ),
                                           path=( video_settings[ "cav_intro_file" ], video_settings[ "cav_intro_folder" ], )[ video_settings[ "cav_intro_type" ] == "folder" ],
                                      thumbnail="DefaultVideo.png",
                                          genre="Coming Attractions Intro",
                                         writer="Coming Attractions Intro",
                                          index=0
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Coming Attraction Intro Label into Trigger List
                    self.trigger_list.insert( 0, "Coming Attractions Intro" )
        # get movie theater experience intro videos
        if video_settings[ "mte_intro" ] > 0:
            utils.log( "Adding Movie Theatre Intro Videos: %s Videos" % video_settings[ "mte_intro" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=video_settings[ "mte_intro" ],
                                       path=( video_settings[ "mte_intro_file" ], video_settings[ "mte_intro_folder" ], )[ video_settings[ "mte_intro_type" ] == "folder" ],
                                      genre="Movie Theater Intro",
                                     writer="Movie Theater Intro",
                                      index=0
                              )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Movie Theatre Intro Label into Trigger List
                self.trigger_list.insert( 0, "Movie Theater Intro" )
        # get trivia outro video(s)
        if trivia_settings[ "trivia_mode" ] != 0:
            utils.log( "Adding Trivia Outro Videos: %s Videos" % video_settings[ "trivia_outro" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=video_settings[ "trivia_outro" ],
                                       path=( video_settings[ "trivia_outro_file" ], video_settings[ "trivia_outro_folder" ], )[ video_settings[ "trivia_outro_type" ] == "folder" ],
                                      genre="Trivia Outro",
                                     writer="Trivia Outro",
                                      index=0
                                #media_type="video/picture"
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Trivia Outro Label into Trigger List
                self.trigger_list.insert( 0, "Trivia Outro" )
        # get feature presentation outro videos
        if video_settings[ "fpv_outro" ] > 0:
            utils.log( "Adding Feature Presentation Outro Videos: %s Videos" % fpv_outro, xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=fpv_outro,
                                       path=( fpv_outro_file, fpv_outro_folder, )[ fpv_outro_type == "folder" ],
                                      genre="Feature Presentation Outro",
                                     writer="Feature Presentation Outro",
                              )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Feature Presentation Outro Label into Trigger List
                self.trigger_list.append( "Feature Presentation Outro" )
        # 3D Outro Video
        if is_3d_movie and _3d_settings[ "3d_outro" ]:
            utils.log( "Adding 3D Outro Video: %s Videos" % _3d_settings[ "3d_outro" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=_3d_settings[ "3d_outro" ],
                                       path=( _3d_settings[ "3d_outro_file" ], _3d_settings[ "3d_outro_folder" ], )[ _3d_settings[ "3d_outro_type" ] == "folder" ],
                                      genre="3D Outro",
                                     writer="3D Outro",
                               )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert 3D Outro Label into Trigger List
                self.trigger_list.append( "3D Outro" )
        # get movie theater experience outro videos
        if video_settings[ "mte_outro" ] > 0:
            utils.log( "Adding Movie Theatre Outro Videos: %s Videos" % video_settings[ "mte_outro" ], xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items( playlist=self.playlist,
                                      items=video_settings[ "mte_outro" ],
                                       path=( video_settings[ "mte_outro_file" ], video_settings[ "mte_outro_folder" ], )[ video_settings[ "mte_outro_type" ] == "folder" ],
                                      genre="Movie Theatre Outro",
                                     writer="Movie Theatre Outro",
                              )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Movie Theatre Outro Label into Trigger List
                self.trigger_list.append( "Movie Theatre Outro" )
        utils.log( "Playlist Size: %s" % xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size(), xbmc.LOGNOTICE )
        utils.log( "Trigger List Size: %d" % len(self.trigger_list), xbmc.LOGNOTICE )
        return self.trigger_list
