# -*- coding: utf-8 -*-
import traceback, os, re, sys
from urllib import quote_plus
from random import shuffle, random

__script__ = "Cinema Experience"
__scriptID__ = "script.cinema.experience"
__modname__ = "ce_playlist.py"

import xbmc, xbmcaddon, xbmcgui

log_message = "[ " + __scriptID__ + " ] - [ " + __modname__ + " ]"
log_sep = "-"*70

trivia_settings          = sys.modules[ "__main__" ].trivia_settings
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
feature_settings         = sys.modules[ "__main__" ].feature_settings
video_settings           = sys.modules[ "__main__" ].video_settings
audio_formats            = sys.modules[ "__main__" ].audio_formats
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from music import parse_playlist
from json_utils import find_movie_details, retrieve_json_dict
from utils import list_to_string
from xbmcvfs import exists as exists
from folder import dirEntries

def _get_trailers( items, equivalent_mpaa, mpaa, genre, movie, mode = "download" ):
    xbmc.log( "[script.cinema.experience] - [ce_playlist.py] - _get_trailers started", level=xbmc.LOGDEBUG )
    # return if not user preference
    settings = trailer_settings
    if not items:
        return []
    if settings[ "trailer_play_mode" ] == 1 and mode == "playlist" and settings[ "trailer_scraper" ] in ( "amt_database", "amt_current" ):
        settings[ "trailer_scraper" ] = "local"
        settings[ "trailer_folder" ] = settings[ "trailer_download_folder" ]
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
    xbmc.log("%s - Retrieving Trailer NFO file" % log_message, level=xbmc.LOGDEBUG )
    try:
        path = os.path.splitext( path )[0] + ".nfo"
        usock = open( path, "r" )
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
        xbmc.log("%s - CE XML Match Found" % log_message, level=xbmc.LOGDEBUG )
        for item in trailer:
            new_trailer += item
        return new_trailer[ 1 ], new_trailer[ 10 ], new_trailer[ 3 ], new_trailer[ 5 ], new_trailer[ 4 ], new_trailer[ 7 ], new_trailer[ 6 ], new_trailer[ 8 ]
    else:
        xbmc.log("%s - HD-Trailers.Net Downloader XML Match Found" % log_message, level=xbmc.LOGDEBUG )
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
    xbmc.log("%s - Setting Trailer Info" % log_message, level=xbmc.LOGDEBUG )
    title = plot = runtime = mpaa = release_date = studio = genre = director = ""
    if exists( os.path.splitext( trailer )[ 0 ] + ".nfo" ):
        xbmc.log("%s - Trailer .nfo file FOUND" % log_message, level=xbmc.LOGDEBUG )
        title, plot, runtime, mpaa, release_date, studio, genre, director = _getnfo( trailer )
    else:
        xbmc.log("%s - Trailer .nfo file NOT FOUND" % log_message, level=xbmc.LOGDEBUG )
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
    xbmc.log("%s - Getting Trailer Thumbnail" % log_message, level=xbmc.LOGDEBUG )
    # check for a thumb based on trailername.tbn
    thumbnail = os.path.splitext( path )[ 0 ] + ".tbn"
    xbmc.log("%s - Looking for thumbnail: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
    # if thumb does not exist try stripping -trailer
    if not exists( thumbnail ):
        thumbnail = os.path.splitext( path )[ 0 ] + ".jpg"
        xbmc.log("%s - Looking for thumbnail: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
        if not exists( thumbnail ):
            thumbnail = "%s.tbn" % ( os.path.splitext( path )[ 0 ].replace( "-trailer", "" ), )
            xbmc.log("%s - Thumbnail not found, Trying: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
            if not exists( thumbnail ):
                thumbnail = "%s.jpg" % ( os.path.splitext( path )[ 0 ].replace( "-trailer", "" ), )
                xbmc.log("%s - Looking for thumbnail: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
                if not exists( thumbnail ):
                    thumbnail = os.path.join( os.path.dirname( path ), "movie.tbn" )
                    xbmc.log("%s - Thumbnail not found, Trying: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
                    # if thumb does not exist return empty
                    if not exists( thumbnail ):
                        # set empty string
                        thumbnail = ""
                        xbmc.log("%s - Thumbnail not found" % log_message, level=xbmc.LOGDEBUG )
    if thumbnail:
        xbmc.log("%s - Thumbnail found: %s" % ( log_message, thumbnail), level=xbmc.LOGDEBUG )
    # return result
    return thumbnail

def _get_special_items( playlist, items, path, genre, title="", thumbnail="", plot="",
                        runtime="", mpaa="", release_date="0 0 0", studio="", writer="",
                        director="", index=-1, media_type="video"
                      ):
    xbmc.log( "%s - _get_special_items() Started" % log_message, level=xbmc.LOGDEBUG)
    # return if not user preference
    if not items:
        xbmc.log( "%s - No Items" % log_message, level=xbmc.LOGDEBUG)
        return
    # if path is a file check if file exists
    if os.path.splitext( path )[ 1 ] and not path.startswith( "http://" ) and not exists( path ):
        xbmc.log( "%s - _get_special_items() - File Does not Exist" % log_message, level=xbmc.LOGDEBUG)
        return
    # set default paths list
    tmp_paths = [ path ]
    # if path is a folder fetch # videos/pictures
    if path.endswith( "/" ) or path.endswith( "\\" ):
        xbmc.log( "%s - _get_special_items() - Path: %s" % ( log_message, path ), level=xbmc.LOGDEBUG)
        # initialize our lists
        tmp_paths = dirEntries( path, media_type, "TRUE" )
        shuffle( tmp_paths )
    # enumerate thru and add our videos/pictures
    for count in range( items ):
        try:
            # set our path
            path = tmp_paths[ count ]
            xbmc.log( "%s - Checking Path: %s" % ( log_message, path ), level=xbmc.LOGDEBUG)
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
                xbmc.log( "%s - Looking for %d files, but only found %d" % ( log_message, items, count), level=xbmc.LOGNOTICE)
                break
            else:
                traceback.print_exc()

def _get_listitem( title="", url="", thumbnail="", plot="", runtime="", mpaa="", release_date="0 0 0", studio="Cinema Experience", genre="", writer="", director=""):
    xbmc.log( "%s - _get_listitem() Started" % log_message, level=xbmc.LOGDEBUG)
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
    xbmc.log( "%s - _get_thumbnail() Started"  % log_message, level=xbmc.LOGDEBUG)
    xbmc.log( "%s - Thumbnail Url: %s" % ( log_message, url ), level=xbmc.LOGDEBUG )
    # if the cached thumbnail does not exist create the thumbnail based on filepath.tbn
    filename = xbmc.getCacheThumbName( url )
    thumbnail = os.path.join( BASE_CACHE_PATH, filename[ 0 ], filename )
    xbmc.log( "%s - Thumbnail Cached Filename: %s" % ( log_message, filename ), level=xbmc.LOGDEBUG )
    # if cached thumb does not exist try auto generated
    if not exists( thumbnail ):
        thumbnail = os.path.join( BASE_CACHE_PATH, filename[ 0 ], "auto-" + filename )
    if not exists( thumbnail ):
        thumbnail = "DefaultVideo.png"
    # return result
    return thumbnail

def build_music_playlist():
    xbmc.log( "%s - Building Music Playlist" % log_message, level=xbmc.LOGNOTICE)
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioPlaylist.Clear", "id": 1}')
    music_playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    track_location = []
    # check to see if playlist or music file is selected
    if trivia_settings[ "trivia_music" ] == 1:
        if trivia_settings[ "trivia_music_file" ].endswith(".m3u"):
            xbmc.log( "%s - Music Playlist: %s" % ( log_message, trivia_settings[ "trivia_music_file" ] ), level=xbmc.LOGDEBUG)
            playlist_file = open( trivia_settings[ "trivia_music_file" ], 'rb')
            saved_playlist = playlist_file.readlines()
            xbmc.log( "%s - Finished Reading Music Playlist" % log_message, level=xbmc.LOGDEBUG)
            track_info, track_location = parse_playlist( saved_playlist, xbmc.getSupportedMedia('music') )
        elif os.path.splitext( trivia_settings[ "trivia_music_file" ] )[1] in xbmc.getSupportedMedia('music'):
            for track in range(100):
                track_location.append( trivia_settings[ "trivia_music_file" ] )
    # otherwise
    else:
        if trivia_settings[ "trivia_music_folder" ]:
            # search given folder and subfolders for files
            track_location = dirEntries( trivia_settings[ "trivia_music_folder" ], "music", "TRUE" )
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
    elif rating.startswith("FSK"):
        if rating.startswith( "FSK:" ):
            rating = rating.split( ":" )[ 1 - ( len( rating.split( ":" ) ) == 1 ) ]
        else:
            rating = rating.split( " " )[ 1 - ( len( rating.split( " " ) ) == 1 ) ]
    else:
        rating = ( rating, "NR", )[ rating not in ( "0", "6", "12", "12A", "PG", "15", "16", "18", "R18", "MA", "U", ) ]
    if rating not in ( "G", "PG", "PG-13", "R", "NC-17", "Unrated", "NR" ):
        if rating in ("12", "12A",):
            equivalent_mpaa = "PG-13"
        elif rating in ( "15", "16" ):
            equivalent_mpaa = "R"
        elif rating in ( "0", "U" ):
            equivalent_mpaa = "G"
        elif rating in ( "6", ):
            equivalent_mpaa = "PG"
        elif rating in ("18", "R18", "MA",):
            equivalent_mpaa = "NC-17"
    else:
        equivalent_mpaa = rating
    return equivalent_mpaa, rating

# moved from pre_eden_code
def _store_playlist():
    p_list = []
    xbmc.log( "[script.cinema.experience] - Storing Playlist in memory", level=xbmc.LOGNOTICE )
    json_query = '{"jsonrpc": "2.0", "method": "Playlist.GetItems", "params": {"playlistid": 1, "properties": ["title", "file", "thumbnail", "streamdetails", "mpaa", "genre"] }, "id": 1}'
    p_list = retrieve_json_dict( json_query, items="items", force_log=False )
    return p_list
    
def _movie_details( movie_id ):
    movie_details = []
    xbmc.log( "[script.cinema.experience] - Retrieving Movie Details", level=xbmc.LOGNOTICE )
    json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": %d, "properties": ["title", "file", "thumbnail", "streamdetails", "mpaa", "genre"]}, "id": 1}' % movie_id
    movie_details = retrieve_json_dict( json_query, items="moviedetails", force_log=False )
    return movie_details
    
def _rebuild_playlist( plist ): # rebuild movie playlist
    xbmc.log( "[script.cinema.experience] - [ce_playlist.py] - Rebuilding Playlist", level=xbmc.LOGNOTICE )
    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    for movie in plist:
        try:
            xbmc.log( "[script.cinema.experience] - Movie Title: %s" % movie["title"], level=xbmc.LOGDEBUG )
            xbmc.log( "[script.cinema.experience] - Movie Thumbnail: %s" % movie["thumbnail"], level=xbmc.LOGDEBUG )
            xbmc.log( "[script.cinema.experience] - Full Movie Path: %s" % movie["file"], level=xbmc.LOGDEBUG )
            json_command = '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 1, "item": {"movieid": %d} }, "id": 1}' % movie["id"]
            json_response = xbmc.executeJSONRPC(json_command)
            xbmc.log( "[script.cinema.experience] - JSONRPC Response: \n%s" % movie["title"], level=xbmc.LOGDEBUG )
        except:
            traceback.print_exc()
        # give XBMC a chance to add to the playlist... May not be needed, but what's 50ms?
        xbmc.sleep( 50 )

def _get_queued_video_info( feature = 0 ):
    xbmc.log( "%s - _get_queued_video_info() Started" % log_message, level=xbmc.LOGDEBUG )
    equivalent_mpaa = "NR"
    try:
        # get movie name
        plist = _store_playlist()
        movie_detail = _movie_details( plist[feature]['id'] )
        movie_title = movie_detail['title']
        path = movie_detail['file']
        mpaa = movie_detail['mpaa']
        genre = list_to_string( movie_detail['genre'] )
        try:
            audio = movie_detail['streamdetails']['audio'][0]['codec']
        except:
            audio = "other"
        equivalent_mpaa, short_mpaa = get_equivalent_rating( mpaa )
    except:
        traceback.print_exc()
        movie_title = path = mpaa = audio = genre = movie = equivalent_mpaa, short_mpaa = ""
    # spew queued video info to log
    xbmc.log( "%s - Queued Movie Information" % log_message, level=xbmc.LOGDEBUG )
    xbmc.log( "%s %s" % ( log_message,log_sep ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s - Title: %s" % ( log_message, movie_title, ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s - Path: %s" % ( log_message, path, ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s - Genre: %s" % ( log_message, genre, ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s - MPAA: %s" % ( log_message, short_mpaa, ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s - Audio: %s" % ( log_message, audio, ), level=xbmc.LOGDEBUG )
    if video_settings[ "audio_videos_folder" ]:
        xbmc.log( "%s - Folder: %s" % ( log_message, ( video_settings[ "audio_videos_folder" ] + audio_formats.get( audio, "Other" ) + video_settings[ "audio_videos_folder" ][ -1 ], ) ), level=xbmc.LOGDEBUG )
    xbmc.log( "%s  %s" % ( log_message, log_sep ), level=xbmc.LOGDEBUG )
    # return results
    return short_mpaa, audio, genre, path, equivalent_mpaa

def _clear_playlists( mode="both" ):
    # clear playlists
    if mode in ( "video", "both" ):
        vplaylist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
        vplaylist.clear()
        xbmc.log( "[ script.cinema.experience ] - Video Playlist Cleared", level=xbmc.LOGNOTICE )
    if mode in ( "music", "both" ):
        mplaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        mplaylist.clear()
        xbmc.log( "[ script.cinema.experience ] - Music Playlist Cleared", level=xbmc.LOGNOTICE )
