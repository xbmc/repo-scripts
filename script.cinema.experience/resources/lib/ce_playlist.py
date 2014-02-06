# -*- coding: utf-8 -*-
import traceback, os, re, sys
from urllib import quote_plus
from random import shuffle, random

import xbmc, xbmcaddon, xbmcgui, xbmcvfs

log_sep = "-"*70

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
trivia_settings          = sys.modules[ "__main__" ].trivia_settings
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
video_settings           = sys.modules[ "__main__" ].video_settings
audio_formats            = sys.modules[ "__main__" ].audio_formats
_3d_settings             = sys.modules[ "__main__" ]._3d_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from json_utils import find_movie_details, retrieve_json_dict
import utils, music
from folder import absolute_listdir

parser = music.parse()

def _get_trailers( items, equivalent_mpaa, mpaa, genre, movie, mode = "download" ):
    utils.log( "[ce_playlist.py] - _get_trailers started" )
    # return if not user preference
    settings = []
    settings = trailer_settings.copy()
    if not items:
        return []
    if settings[ "trailer_play_mode" ] == 1 and mode == "playlist" and settings[ "trailer_scraper" ] in ( "amt_database", "amt_current" ):
        settings[ "trailer_scraper" ] = "local"
        settings[ "trailer_folder" ] = settings[ "trailer_download_folder" ]
    if mode == "3D":
        settings[ "trailer_scraper" ] = "local"
        settings[ "trailer_folder" ] = _3d_settings[ "3d_trailer_folder" ]
        settings[ "trailer_count" ] = _3d_settings[ "3d_trailer_count" ]
        settings[ "trailer_limit_mpaa" ] = _3d_settings[ "3d_trailer_limit_mpaa" ]
        settings[ "trailer_limit_genre" ] = _3d_settings[ "3d_trailer_limit_genre" ]
        settings[ "trailer_trailer_rating" ] = _3d_settings[ "3d_trailer_rating" ]
        settings[ "trailer_unwatched_only" ] = _3d_settings[ "3d_trailer_unwatched_only" ]
    # get the correct scraper
    sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "scrapers" ) )
    exec "from %s import scraper as scraper" % ( settings[ "trailer_scraper" ], )
    Scraper = scraper.Main( equivalent_mpaa, mpaa, genre, settings, movie )
    # fetch trailers
    trailers = Scraper.fetch_trailers()
    # return results
    return trailers
    

def _getnfo( path ):
    
    '''
            id=trailer[ 0 ]
            path=trailer[ 2 ],
            genre=trailer[ 9 ],
            title=trailer[ 1 ],
            thumbnail=trailer[ 3 ],
            plot=trailer[ 4 ],
            runtime=trailer[ 5 ],
            mpaa=trailer[ 6 ],
            release_date=trailer[ 7 ],
            studio=trailer[ 8 ],
            director=trailer[ 11 ]
    '''
    utils.log( "Retrieving Trailer NFO file" )
    try:
        path = os.path.splitext( path )[0] + ".nfo"
        usock = xbmcvfs.File( path )
        # read source
        xmlSource =  usock.read()
        # close socket
        usock.close()
    except:
        xmlSource = ""
    xmlSource = xmlSource.replace("\n    ","")
    # if only
    xmlSource = xmlSource.replace('<movieinfo>','<movieinfo id="0">')
    # gather all trailer records <movieinfo>
    new_trailer = []
    #title = plot = runtime = mpaa = release_date = studio = genre = director = ""
    trailer = re.findall( '<movieinfo id="(.*?)"><title>(.*?)</title><quality>(.*?)</quality><runtime>(.*?)</runtime><releasedate>(.*?)</releasedate><mpaa>(.*?)</mpaa><genre>(.*?)</genre><studio>(.*?)</studio><director>(.*?)</director><cast>(.*?)</cast><plot>(.*?)</plot><thumb>(.*?)</thumb>', xmlSource )
    if trailer:
        utils.log( "CE XML Match Found" )
        for item in trailer:
            new_trailer += item
        return new_trailer[ 1 ], new_trailer[ 10 ], new_trailer[ 3 ], new_trailer[ 5 ], new_trailer[ 4 ], new_trailer[ 7 ], new_trailer[ 6 ], new_trailer[ 8 ]
    else:
        utils.log( "HD-Trailers.Net Downloader XML Match Found" )
        title = "".join(re.compile("<title>(.*?)</title>", re.DOTALL).findall(xmlSource)) or ""
        plot = "".join(re.compile("<plot>(.*?)</plot>", re.DOTALL).findall(xmlSource)) or ""
        runtime = "".join(re.compile("<runtime>(.*?)</runtime>", re.DOTALL).findall(xmlSource)) or ""
        mpaa = "".join(re.compile("<mpaa>(.*?)</mpaa>", re.DOTALL).findall(xmlSource)) or ""
        release_date = "".join(re.compile("<premiered>(.*?)</premiered>", re.DOTALL).findall(xmlSource)) or ""
        studio = "".join(re.compile("<studio>(.*?)</studio>", re.DOTALL).findall(xmlSource)) or ""
        genres = re.compile("<genre>(.*?)</genre>", re.DOTALL).findall(xmlSource) or ""
        if genres == "":
            genre = ""
        else:
            genre = genres[0]   # get the first genre
            for g in genres[1:]: # now loop from the second genre and add it with a " / " in between
                genre = genre + " / " + g
        director = "".join(re.compile("<director>(.*?)</director>", re.DOTALL).findall(xmlSource)) or ""
        return title, plot, runtime, mpaa, release_date, studio, genre, director
    
def _set_trailer_info( trailer ):
    utils.log( "Setting Trailer Info" )
    title = plot = runtime = mpaa = release_date = studio = genre = director = ""
    if xbmcvfs.exists( os.path.splitext( trailer )[ 0 ] + ".nfo" ):
        utils.log( "Trailer .nfo file FOUND" )
        title, plot, runtime, mpaa, release_date, studio, genre, director = _getnfo( trailer )
    else:
        utils.log( "Trailer .nfo file NOT FOUND" )
    result = ( xbmc.getCacheThumbName( trailer ), # id
               title or os.path.basename( trailer ).split( "-trailer." )[ 0 ], # title
               trailer, # trailer
               _get_trailer_thumbnail( trailer ), # thumb
               plot, # plot
               runtime, # runtime
               mpaa, # mpaa
               release_date, # release date
               studio, # studio
               genre, # genre
               "Movie Trailer", # writer
               director, # director 32613
              )
    return result
    
def _get_trailer_thumbnail( path ):
    utils.log( "Getting Trailer Thumbnail" )
    # check for a thumb based on trailername.tbn
    thumbnail = os.path.splitext( path )[ 0 ] + ".tbn"
    utils.log( "Looking for thumbnail: %s" % thumbnail )
    # if thumb does not exist try stripping -trailer
    if not xbmcvfs.exists( thumbnail ):
        thumbnail = os.path.splitext( path )[ 0 ] + ".jpg"
        utils.log( "Looking for thumbnail: %s" % thumbnail )
        if not xbmcvfs.exists( thumbnail ):
            thumbnail = "%s.tbn" % ( os.path.splitext( path )[ 0 ].replace( "-trailer", "" ), )
            utils.log( "Thumbnail not found, Trying: %s" % thumbnail )
            if not xbmcvfs.exists( thumbnail ):
                thumbnail = "%s.jpg" % ( os.path.splitext( path )[ 0 ].replace( "-trailer", "" ), )
                utils.log( "Looking for thumbnail: %s" % thumbnail )
                if not xbmcvfs.exists( thumbnail ):
                    thumbnail = os.path.join( os.path.dirname( path ), "movie.tbn" )
                    utils.log( "Thumbnail not found, Trying: %s" % thumbnail )
                    # if thumb does not exist return empty
                    if not xbmcvfs.exists( thumbnail ):
                        # set empty string
                        thumbnail = ""
                        utils.log( "Thumbnail not found" )
    if thumbnail:
        utils.log( "Thumbnail found: %s" % thumbnail )
    # return result
    return thumbnail

def _get_special_items( playlist, items, path, genre, title="", thumbnail="", plot="",
                        runtime="", mpaa="", release_date="0 0 0", studio="", writer="",
                        director="", index=-1, media_type="video"
                      ):
    utils.log( "_get_special_items() Started" )
    video_list = []
    # return if not user preference
    if not items:
        utils.log( "No Items added to playlist" )
        return
    # if path is a file check if file exists
    if os.path.splitext( path )[ 1 ] and not path.startswith( "http://" ) and not xbmcvfs.exists( path ):
        utils.log( "_get_special_items() - File Does not Exist" )
        return
    # parse playlist file
    if ( os.path.splitext( path )[ 1 ] ).lower() in ( "m3u", "pls", "asf", "ram" ):
        utils.log( "Video Playlist: %s" % path )
        if ( os.path.splitext( path )[ 1 ] ).lower() == ".m3u":
            video_list = parser.parse_m3u( path, xbmc.getSupportedMedia( media_type ) )
        elif ( os.path.splitext( path )[ 1 ] ).lower() == ".pls":
            video_list = parser.parse_pls( path, xbmc.getSupportedMedia( media_type ) )
        elif ( os.path.splitext( path )[ 1 ] ).lower() == ".asf":
            video_list = parser.parse_asf( path, xbmc.getSupportedMedia( media_type ) )
        elif ( os.path.splitext( path )[ 1 ] ).lower() == ".ram":
            video_list = parser.parse_ram( path, xbmc.getSupportedMedia( media_type ) )
        if not video_list:
            utils.log( "Playlist empty or has unsupported media files" )
            return
        try:
            for item in video_list[::-1]:
                utils.log( "Checking Path: %s" % item )
                # format a title (we don't want the ugly extension)
                video_title = title or os.path.splitext( os.path.basename( item ) )[ 0 ]
                # create the listitem and fill the infolabels
                listitem = _get_listitem( title=video_title,
                                            url=item,
                                      thumbnail=thumbnail,
                                           plot=plot,
                                        runtime=runtime,
                                           mpaa=mpaa,
                                   release_date=release_date,
                                         studio=studio or "Cinema Experience",
                                          genre=genre or "Movie Trailer",
                                         writer=writer,
                                       director=director
                                        )
                # add our video/picture to the playlist or list
                if isinstance( playlist, list ):
                    playlist += [ ( item, listitem, ) ]
                else:
                    playlist.add( item, listitem, index=index )
        except:
            traceback.print_exc()
    else:
        # set default paths list
        tmp_paths = [ path ]
        # if path is a folder fetch # videos/pictures
        if path.endswith( "/" ) or path.endswith( "\\" ):
            utils.log( "_get_special_items() - Path: %s" % path )
            # initialize our lists
            tmp_paths = absolute_listdir( path, media_type = media_type, recursive = True )
            shuffle( tmp_paths )
        # enumerate thru and add our videos/pictures
        for count in range( items ):
            try:
                # set our path
                path = tmp_paths[ count ]
                utils.log( "Checking Path: %s" % path )
                # format a title (we don't want the ugly extension)
                title = title or os.path.splitext( os.path.basename( path ) )[ 0 ]
                # create the listitem and fill the infolabels
                listitem = _get_listitem( title=title,
                                            url=path,
                                      thumbnail=thumbnail,
                                           plot=plot,
                                        runtime=runtime,
                                           mpaa=mpaa,
                                   release_date=release_date,
                                         studio=studio or "Cinema Experience",
                                          genre=genre or "Movie Trailer",
                                         writer=writer,
                                       director=director
                                        )
                # add our video/picture to the playlist or list
                if isinstance( playlist, list ):
                    playlist += [ ( path, listitem, ) ]
                else:
                    playlist.add( path, listitem, index=index )
            except:
                if items > count:
                    utils.log( "Looking for %d files, but only found %d" % ( items, count), xbmc.LOGNOTICE )
                    break
                else:
                    traceback.print_exc()

def _get_listitem( title="", url="", thumbnail="", plot="", runtime="", mpaa="", release_date="0 0 0", studio="Cinema Experience", genre="", writer="", director=""):
    utils.log( "_get_listitem() Started" )
    # check for a valid thumbnail
    if not writer == "Movie Trailer":
        thumbnail = _get_thumbnail( ( thumbnail, url, )[ thumbnail == "" ] )
    else:
        if not thumbnail:
            thumbnail = "DefaultVideo.png"
    # set the default icon
    icon = "DefaultVideo.png"
    # only need to add label, icon and thumbnail, setInfo() and addSortMethod() takes care of label2
    listitem = xbmcgui.ListItem( title, iconImage=icon, thumbnailImage=thumbnail )
    # release date and year
    try:
        parts = release_date.split( " " )
        year = int( parts[ 2 ] )
    except:
        year = 0
    # add the different infolabels we want to sort by
    listitem.setInfo( type="Video", infoLabels={ "Title": title, "Plot": plot, "PlotOutline": plot, "RunTime": runtime, "MPAA": mpaa, "Year": year, "Studio": studio, "Genre": genre, "Writer": writer, "Director": director } )
    # return result
    return listitem
    
def _get_thumbnail( url ):
    utils.log( "_get_thumbnail() Started" )
    utils.log( "Thumbnail Url: %s" % url )
    # if the cached thumbnail does not exist create the thumbnail based on filepath.tbn
    filename = xbmc.getCacheThumbName( url )
    thumbnail = os.path.join( BASE_CACHE_PATH, filename[ 0 ], filename )
    utils.log( "Thumbnail Cached Filename: %s" % filename )
    # if cached thumb does not exist try auto generated
    if not xbmcvfs.exists( thumbnail ):
        thumbnail = os.path.join( BASE_CACHE_PATH, filename[ 0 ], "auto-" + filename )
    if not xbmcvfs.exists( thumbnail ):
        thumbnail = "DefaultVideo.png"
    # return result
    return thumbnail

def build_music_playlist():
    utils.log( "Building Music Playlist", xbmc.LOGNOTICE )
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioPlaylist.Clear", "id": 1}')
    music_playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    track_location = []
    # check to see if playlist or music file is selected
    if trivia_settings[ "trivia_music" ] == 1:
        if ( os.path.splitext( trivia_settings[ "trivia_music_file" ] )[ 1 ] ).lower() in ( "m3u", "pls", "asf", "ram" ):
            utils.log( "Music Playlist: %s" % trivia_settings[ "trivia_music_file" ] )
            if trivia_settings[ "trivia_music_file" ].endswith(".m3u"):
                track_location = parser.parse_m3u( trivia_settings[ "trivia_music_file" ], xbmc.getSupportedMedia('music') )
            elif trivia_settings[ "trivia_music_file" ].endswith(".pls"):
                track_location = parser.parse_pls( trivia_settings[ "trivia_music_file" ], xbmc.getSupportedMedia('music') )
            elif trivia_settings[ "trivia_music_file" ].endswith(".asf"):
                track_location = parser.parse_asf( trivia_settings[ "trivia_music_file" ], xbmc.getSupportedMedia('music') )
            elif trivia_settings[ "trivia_music_file" ].endswith(".ram"):
                track_location = parser.parse_ram( trivia_settings[ "trivia_music_file" ], xbmc.getSupportedMedia('music') )
        elif os.path.splitext( trivia_settings[ "trivia_music_file" ] )[1] in xbmc.getSupportedMedia('music'):
            for track in range(100):
                track_location.append( trivia_settings[ "trivia_music_file" ] )
    # otherwise
    else:
        if trivia_settings[ "trivia_music_folder" ]:
            # search given folder and subfolders for files
            track_location = absolute_listdir( trivia_settings[ "trivia_music_folder" ], media_type = "music", recursive = True )
    # shuffle playlist
    shuffle( track_location )
    for track in track_location:
        music_playlist.add( track,  )
        
def get_equivalent_rating( rating ):
    if rating == "":
        rating = "NR"
    #MPAA    
    elif rating.startswith("Rated"):
        rating = rating.split( " " )[ 1 - ( len( rating.split( " " ) ) == 1 ) ]
        rating = ( rating, "NR", )[ rating not in ( "G", "PG", "PG-13", "R", "NC-17", "Unrated", ) ]
    #BBFC
    elif rating.startswith("UK"):
        if rating.startswith( "UK:" ):
            rating = rating.split( ":" )[ 1 - ( len( rating.split( ":" ) ) == 1 ) ]
        else:
            rating = rating.split( " " )[ 1 - ( len( rating.split( " " ) ) == 1 ) ]
        rating = ( rating, "NR", )[ rating not in ( "12", "12A", "PG", "15", "18", "R18", "MA", "U", ) ]
    #FSK
    elif rating.startswith("FSK"):
        if rating.startswith( "FSK:" ):
            rating = rating.split( ":" )[ 1 - ( len( rating.split( ":" ) ) == 1 ) ]
        else:
            rating = rating.split( " " )[ 1 - ( len( rating.split( " " ) ) == 1 ) ]
    #Germany [alternative FSK string]
    elif rating.startswith("Germany"):
        if rating.startswith( "Germany:" ):
            rating = rating.split( ":" )[ 1 - ( len( rating.split( ":" ) ) == 1 ) ]
        else:
            rating = rating.split( " " )[ 1 - ( len( rating.split( " " ) ) == 1 ) ]
    #DEJUS
    elif rating in ( "Livre", "10 Anos", "12 Anos", "14 Anos", "16 Anos", "18 Anos" ):
        rating = rating   # adding this just in case there is some with different labels in database
    else:
        rating = ( rating, "NR", )[ rating not in ( "0", "6", "12", "12A", "PG", "15", "16", "18", "R18", "MA", "U", ) ]
    if rating not in ( "G", "PG", "PG-13", "R", "NC-17", "Unrated", "NR" ):
        if rating in ("12", "12A", "12 Anos" ):
            equivalent_mpaa = "PG-13"
        elif rating in ( "15", "16", "14 Anos", "16 Anos" ):
            equivalent_mpaa = "R"
        elif rating in ( "0", "U", "Livre" ):
            equivalent_mpaa = "G"
        elif rating in ( "6", "10 Anos" ):
            equivalent_mpaa = "PG"
        elif rating in ("18", "R18", "MA", "18 Anos" ):
            equivalent_mpaa = "NC-17"
    else:
        equivalent_mpaa = rating
    return equivalent_mpaa, rating

# moved from pre_eden_code
def _store_playlist():
    p_list = []
    utils.log( "Storing Playlist in memory", xbmc.LOGNOTICE )
    json_query = '{"jsonrpc": "2.0", "method": "Playlist.GetItems", "params": {"playlistid": 1, "properties": ["title", "file", "thumbnail", "streamdetails", "mpaa", "genre"] }, "id": 1}'
    p_list = retrieve_json_dict( json_query, items="items", force_log=False )
    return p_list
    
def _movie_details( movie_id ):
    movie_details = []
    utils.log( "Retrieving Movie Details", xbmc.LOGNOTICE )
    json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": %d, "properties": ["title", "file", "thumbnail", "streamdetails", "mpaa", "genre"]}, "id": 1}' % movie_id
    movie_details = retrieve_json_dict( json_query, items="moviedetails", force_log=False )
    return movie_details
    
def _rebuild_playlist( plist ): # rebuild movie playlist
    utils.log( "Rebuilding Movie Playlist", xbmc.LOGNOTICE )
    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    for movie in plist:
        try:
            utils.log( "Movie Title: %s" % movie["title"] )
            utils.log( "Movie Thumbnail: %s" % movie["thumbnail"] )
            utils.log( "Full Movie Path: %s" % movie["file"] )
            json_command = '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 1, "item": {"movieid": %d} }, "id": 1}' % movie["id"]
            json_response = xbmc.executeJSONRPC(json_command)
            utils.log( "JSONRPC Response: \n%s" % movie["title"] )
        except:
            traceback.print_exc()
        # give XBMC a chance to add to the playlist... May not be needed, but what's 50ms?
        xbmc.sleep( 50 )

def _get_queued_video_info( feature = 0 ):
    utils.log( "_get_queued_video_info() Started" )
    equivalent_mpaa = "NR"
    try:
        # get movie name
        plist = _store_playlist()
        movie_detail = _movie_details( plist[feature]['id'] )
        movie_title = movie_detail['title']
        path = movie_detail['file']
        mpaa = movie_detail['mpaa']
        genre = utils.list_to_string( movie_detail['genre'] )
        try:
            audio = movie_detail['streamdetails']['audio'][0]['codec']
        except:
            audio = "other"
        try:
            stereomode = movie_detail['streamdetails']['video'][0]['stereomode']
        except:
            stereomode = ""
        equivalent_mpaa, short_mpaa = get_equivalent_rating( mpaa )
    except:
        traceback.print_exc()
        movie_title = path = mpaa = audio = genre = movie = equivalent_mpaa, short_mpaa, stereomode = ""
    if not stereomode in ( "mono", "" ):
        is_3d_movie = True
    elif stereomode == "": # if database still has an empty stereomode, test filename
        is_3d_movie = test_for_3d( path )
    else:
        is_3d_movie = False
    # spew queued video info to log
    utils.log( "Queued Movie Information" )
    utils.log( "%s" % log_sep )
    utils.log( "Title: %s" % movie_title )
    utils.log( "Path: %s" % path )
    utils.log( "Genre: %s" % genre )
    utils.log( "Rating: %s" % short_mpaa )
    utils.log( "Audio: %s" % audio )
    utils.log( "Stereo Mode: %s" % stereomode )
    utils.log( "3D Movie: %s" % ( "False", "True" )[ is_3d_movie ] )
    if video_settings[ "audio_videos_folder" ]:
        if is_3d_movie and _3d_settings[ "3d_audio_videos_folder" ]:
            utils.log( "Folder: %s" % ( _3d_settings[ "3d_audio_videos_folder" ] + audio_formats.get( audio, "Other" ) + _3d_settings[ "3d_audio_videos_folder" ][ -1 ], ) )
        else:
            utils.log( "Folder: %s" % ( video_settings[ "audio_videos_folder" ] + audio_formats.get( audio, "Other" ) + video_settings[ "audio_videos_folder" ][ -1 ], ) )
    utils.log( "%s" % log_sep )
    # return results
    return short_mpaa, audio, genre, path, equivalent_mpaa, is_3d_movie

def test_for_3d( path ):
    is_3d_movie = re.findall( _3d_settings[ "3d_movie_tags" ], path )
    if is_3d_movie:
        return True
    else:
        return False

def _clear_playlists( mode="both" ):
    # clear playlists
    if mode in ( "video", "both" ):
        vplaylist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
        vplaylist.clear()
        utils.log( "Video Playlist Cleared", xbmc.LOGNOTICE )
    if mode in ( "music", "both" ):
        mplaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        mplaylist.clear()
        utils.log( "Music Playlist Cleared", xbmc.LOGNOTICE )
