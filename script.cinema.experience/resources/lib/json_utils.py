# -*- coding: utf-8 -*-

import xbmc, xbmcaddon
import traceback, sys, os

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils

def RepresentsNumber(s):
    try: 
        int(s)
        return True
    except ValueError:
        try:
            float(s)
            return True
        except ValueError:
            return False
            
def RepresentsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


def retrieve_json_dict(json_query, items='items', force_log=False ):
    """ retrieve_json_dict()
        This function returns the response from a json rpc query in a dict(hash) form

        requirements:
            json_query - a properly formed json rpc request for return
            items - the specific key being looked for, example for VideoLibrary.GetMovies - 'movies' is the key, 'items' is a common response(can be left blank then)
    """
    utils.log( "[json_utils.py] - JSONRPC Query -\n%s" % json_query )
    true = True
    false = False
    null = None
    json_response = xbmc.executeJSONRPC( json_query )
    # disable debug logging if items = 'movies' or albums as these can fill spam the log with a lot of information
    if ( items != 'movies' and items != 'albums' ) or force_log: 
        utils.log( "[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % json_response )
    response = json_response
    if response.startswith( "{" ):
        response = eval( response )
    try:
        if response.has_key( 'result' ):
            result = response['result']
            json_dict = result[ items ]
            return json_dict
        elif response.has_key( 'error' ):
            utils.log( "[json_utils.py] - retrieve_json_dict - Error trying to get json response" )
            utils.log( "%s" % response )
            return None
        else:
            utils.log( "[json_utils.py] - retrieve_json_dict - No response from XBMC", xbmc.LOGNOTICE )
            utils.log( "%s" % response )
            return None
    except:
        traceback.print_exc()
        utils.log( "[json_utils.py] - retrieve_json_dict - Error trying to get json response" )
        return None

def retrieve_movie_db():
    """ retrieve_movie_database()
    
        Retrieves Movie Database from XBMC via JSON RPC
    """
    movie_db=None
    movies_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"fields": ["title", "thumbnail", "file", "plot", "plotoutline", "rating", "runtime", "director", "genre", "mpaa", "votes", "trailer", "tagline", "top250", "studio", "year", "writer", "streamDetails" ] }, "id": 1}'
    movie_db = retrieve_json_dict( movies_query, 'movies' )
    if movie_db:
        utils.log( "[json_utils.py] - retrieve_movie_database - Successfully retrieved database" )
    else:
        utils.log( "[json_utils.py] - retrieve_movie_database - No database found" )
    return movie_db

def retrieve_video_playlist():
    """ retrieve_video_playlist()

        Retrieves the movie items in a video playlist from XBMC and returns it as a dict.
        If a video playlist is not available, 'None' is returned
    """
    video_playlist_getitems_query = '{"jsonrpc": "2.0", "method": "VideoPlaylist.GetItems", "params": {"fields": ["title", "thumbnail", "file", "plot", "plotoutline", "rating", "runtime", "director", "genre", "mpaa", "votes", "trailer", "tagline", "top250", "studio", "year", "writer", "streamDetails" ] }, "id": 1}'
    video_playlist = retrieve_json_dict( video_playlist_getitems_query, 'items' )
    return video_playlist
    
def find_movie_details( movie_db=None, field="title", match_value=None ):
    """ find_movie_details( movie_db, field="title", match_value )

        Searchs for a Movie match to the supplied 'field' and matched text, returns matching movie details
        
        Requirements:
            field = key to be matched to - JSON RPC fields
            movie_db = a dict containing the contents from retrieve_movie_database, if left empty will retrieve database dict from retrieve_movie_database
            match_value = what is being searched for 
    """
    utils.log( "[json_utils.py] - find_movie_details - field: %s, matche_value: %s" % ( field, match_value ) )
    movie_return = None
    if not movie_db:
        movie_db = retrieve_movie_db()
    if movie_db:
        for movie in movie_db:
            if not RepresentsNumber( movie[field] ) or field == 'title': # check to see if value trying to be matched is a number(integer or floating point) or if the search field is 'title'
                if movie[field].lower() == match_value.lower():
                    movie_return = movie
                    break
            else:
                if RepresentsInt( movie[field] ):
                    if movie[field] == int( match_value ):
                        movie_return = movie
                        break
                else:
                    if movie[field] == float( match_value ):
                        movie_return = movie
                        break
    else:
        utils.log( "[json_utils.py] - find_movie_details - No database found" )
    return movie_return
    
def insert_movie_into_playlist( movie_db=None, title="", index=0 ):
    """ insert_movie_into_playlist( movie_db, title, index )

        Uses find_movie_details to add a movie to playlist via movie title

        Requirements:
            title - the title of the movie to add
            movie_db - a dict containing the XBMC Movie DB, if not supplied will retrieve it.(optional)
            index - and integer for locating the insertion point(optional)
    """
    if not movie_db:
        movie_db = retrieve_movie_db()
    insert_movieid_to_video_playlist = '{"jsonrpc": "2.0", "method": "VideoPlaylist.Insert", "params": {"item": {"movieid": %d}, "index": %d}, "id": 1}'
    matched_movie = find_movie_details( movie_db=movie_db, field='title', match_value=title )
    if matched_movie:
        utils.log( "[json_utils.py] - insert_movie_into_playlist - Matched Title: %s" % title )
        result = xbmc.executeJSONRPC( insert_movieid_into_video_playlist % matched_movie['movieid'] )
        utils.log( "[json_utils.py] - insert_movie_into_playlist - JSONRPC Result -\n%s" % result )
        true = True
        false = False
        null = None
        if result.startswith( "{" ):
            result = eval( result )
        if result['result'] == "OK":
            utils.log( "[json_utils.py] - insert_movie_into_playlist - Title: %s, Succeeded" % title )
        else:
            utils.log( "[json_utils.py] - insert_movie_into_playlist - Title: %s, Failed" % title )
    else:
        utils.log( "[json_utils.py] - insert_movie_into_playlist - Unable to match Title: %s" % title )

def add_movie_to_playlist( movie_db=None, title="" ):
    """ add_movie_to_playlist( title )

        Uses find_movie_details to add a movie to playlist via movie title

        Requirements:
            title - the title of the movie to add
            movie_db - a dict containing the XBMC Movie DB, if not supplied will retrieve it.
    """
    if not movie_db:
        movie_db = retrieve_movie_db()
    add_movieid_to_video_playlist = '{"jsonrpc": "2.0", "method": "VideoPlaylist.Add", "params": {"item": {"movieid": %d} }, "id": 1}'
    matched_movie = find_movie_details( movie_db=movie_db, field='title', match_value=title )
    if matched_movie:
        utils.log( "[json_utils.py] - add_movie_to_playlist - Matched Title: %s" % title )
        result = xbmc.executeJSONRPC( add_movieid_to_video_playlist % matched_movie['movieid'] )
        utils.log( "[json_utils.py] - add_movie_to_playlist - JSONRPC Result -\n%s" % result )
        true = True
        false = False
        null = None
        if result.startswith( "{" ):
            result = eval( result )
        if result['result'] == "OK":
            utils.log( "[json_utils.py] - add_movie_to_playlist - Title: %s, Succeeded" % title )
        else:
            utils.log( "[json_utils.py] - add_movie_to_playlist - Title: %s, Failed" % title )
    else:
        utils.log( "[json_utils.py] - add_movie_to_playlist - Unable to match Title: %s" % title )
