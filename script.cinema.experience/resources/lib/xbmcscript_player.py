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
        mpaa = audio = genre = movie = equivalent_mpaa = ""
        try:
            # create the playlist
            self.playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
            # Check to see if multiple features have been set in settings
            # if multiple features is greater than 1(not a single feature)
            # add the intermission videos and audio files for the 2, third, etc movies
            if self.playlistsize > 1:
                if extra_settings[ "intermission_video" ] > 0 or extra_settings[  "intermission_audio" ] or extra_settings[ "intermission_ratings" ]:
                    mpaa, audio, genre, movie, equivalent_mpaa = self._add_intermission_videos()
            # otherwise just build for a single video
            else:
                mpaa, audio, genre, movie, equivalent_mpaa = _get_queued_video_info( feature = 0 )
            self._create_playlist( mpaa, audio, genre, movie, equivalent_mpaa )
            # play the trivia slide show
        except:
            traceback.print_exc()

    def _add_intermission_videos( self ):
        utils.log( "Adding intermission Video(s)", xbmc.LOGNOTICE )
        count = 0
        index_count = 1
        for feature in range( 1, self.playlistsize ):
            mpaa, audio, genre, movie, equivalent_mpaa = _get_queued_video_info( feature = index_count )
            #count = index_count
            # add intermission video
            if extra_settings[ "intermission_video" ] > 0:
                utils.log( "Inserting intermission Video(s): %s" % extra_settings[ "intermission_video" ], xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=extra_settings[ "intermission_video" ],
                                           path=( extra_settings[ "intermission_video_file" ], extra_settings[ "intermission_video_folder" ], )[ extra_settings[ "intermission_video_type" ] == "folder" ],
                                          genre="Intermission",
                                         writer="Intermission",
                                          index=index_count
                                   )
                for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                    # Insert Intermission Label into Trigger List
                    self.trigger_list.insert( index_count, "Intermission" ) 
                if xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size and extra_settings[ "intermission_video" ] > 1:
                    index_count += extra_settings[ "intermission_video" ] - 1
                elif xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > p_size and extra_settings[ "intermission_video" ] == 1:
                    index_count += extra_settings[ "intermission_video" ]
            # get rating video
            if video_settings[ "enable_ratings" ] and extra_settings[ "intermission_ratings" ] and video_settings[ "rating_videos_folder" ] != "":
                utils.log( "Inserting Intermission Rating Video", xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=1 * ( video_settings[ "rating_videos_folder" ] != "" ),
                                           path=video_settings[ "rating_videos_folder" ] + mpaa + ".avi",
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
            if video_settings[ "enable_audio" ]  and extra_settings[ "intermission_audio" ] and video_settings[ "audio_videos_folder" ]:
                utils.log( "Inserting Intermission Audio Format Video", xbmc.LOGNOTICE )
                utils.log( "    playlist Position: %d" % index_count )
                p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
                utils.log( "    p_size: %d" % p_size )
                _get_special_items(    playlist=self.playlist,
                                          items=1 * ( video_settings[ "audio_videos_folder" ] != "" ),
                                          path = video_settings[ "audio_videos_folder" ] + audio_formats.get( audio, "Other" ) + video_settings[ "audio_videos_folder" ][ -1 ],
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
        mpaa, audio, genre, movie, equivalent_mpaa = _get_queued_video_info( 0 )
        return mpaa, audio, genre, movie, equivalent_mpaa

    def _create_playlist( self, mpaa, audio, genre, movie, equivalent_mpaa ):
        # TODO: try to get a local thumb for special videos?
        utils.log( "Building Cinema Experience Playlist", xbmc.LOGNOTICE )
        # Add Countdown video
        utils.log( "Adding Countdown Videos: %s Video(s)" % video_settings[ "countdown_video" ], xbmc.LOGNOTICE )
        p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
        _get_special_items(    playlist=self.playlist,
                                  items=video_settings[ "countdown_video" ],
                                   path=( video_settings[ "countdown_video_file" ], video_settings[ "countdown_video_folder" ], )[ video_settings[ "countdown_video_type" ] == "folder" ],
                                  genre="Countdown",
                                 writer="Countdown",
                                  index=0
                           )
        for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
            # Insert Countdown Label into Trigger List
            self.trigger_list.insert( 0, "Countdown" )
        # get Dolby/DTS videos
        if video_settings[ "enable_audio" ] and video_settings[ "audio_videos_folder" ]:
            utils.log( "Adding Audio Format Video", xbmc.LOGNOTICE )
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=1 * ( video_settings[ "audio_videos_folder" ] != "" ),
                                       path=video_settings[ "audio_videos_folder" ] + audio_formats.get( audio, "Other" ) + video_settings[ "audio_videos_folder" ][ -1 ],
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
            p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            _get_special_items(    playlist=self.playlist,
                                      items=1 * ( video_settings[ "rating_videos_folder" ] != "" ),
                                       path=video_settings[ "rating_videos_folder" ] + mpaa + ".avi",
                                      genre="MPAA Rating",
                                     writer="MPAA Rating",
                                      index=0
                              )
            for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
                # Insert Rating Label into Trigger List
                self.trigger_list.insert( 0, "MPAA Rating" )
        # get feature presentation intro videos
        utils.log( "Adding Feature Presentation Intro Videos: %s Videos" % video_settings[ "fpv_intro" ], xbmc.LOGNOTICE )
        p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
        _get_special_items(    playlist=self.playlist,
                                  items=video_settings[ "fpv_intro" ],
                                   path=( video_settings[ "fpv_intro_file" ], video_settings[ "fpv_intro_folder" ], )[ video_settings[ "fpv_intro_type" ] == "folder" ],
                                  genre="Feature Presentation Intro",
                                 writer="Feature Presentation Intro",
                                  index=0
                           )
        for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
            # Insert Feature Presentation Label into Trigger List
            self.trigger_list.insert( 0, "Feature Presentation Intro" )
        # get trailers
        utils.log( "Retriving Trailers: %s Trailers" % trailer_settings[ "trailer_count" ], xbmc.LOGNOTICE )
        trailers = _get_trailers(  items=trailer_settings[ "trailer_count" ],
                         equivalent_mpaa=equivalent_mpaa,
                                    mpaa=mpaa,
                                   genre=genre,
                                   movie=movie,
                                    mode="playlist"
                                )
        # get coming attractions outro videos
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
        utils.log( "Adding Feature Presentation Outro Videos: %s Videos" % video_settings[ "fpv_outro" ], xbmc.LOGNOTICE )
        p_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
        _get_special_items(    playlist=self.playlist,
                                  items=video_settings[ "fpv_outro" ],
                                   path=( video_settings[ "fpv_outro_file" ], video_settings[ "fpv_outro_folder" ], )[ video_settings[ "fpv_outro_type" ] == "folder" ],
                                  genre="Feature Presentation Outro",
                                 writer="Feature Presentation Outro",
                          )
        for count in range( 0, ( xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() - p_size ) ):
            # Insert Feature Presentation Outro Label into Trigger List
            self.trigger_list.append( "Feature Presentation Outro" )
        # get movie theater experience outro videos
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
