# -*- coding: utf-8 -*-
# script.cdartmanager
# jsonrpc_calls.py

import os
import utils
import xbmc
import traceback

from utils import log
from cdam import MediaType

empty = {}


def get_thumbnail_path(database_id, type_):
    utils.log("jsonrpc_calls.py - Retrieving Thumbnail Path for %s id: %s" % (type_, database_id))
    if type_ == MediaType.ALBUM and database_id:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", ' \
                     '"params": {"properties": ["thumbnail"], "albumid": %d}, "id": 1}' % database_id
        json_thumb = retrieve_json_dict(json_query, items='albumdetails', force_log=False)
    elif type_ == MediaType.ARTIST and database_id:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", ' \
                     '"params": {"properties": ["thumbnail"], "artistid": %d}, "id": 1}' % database_id
        json_thumb = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    else:
        utils.log("jsonrpc_calls.py - Improper type or database_id")
        return empty
    if json_thumb:
        return json_thumb["thumbnail"]
    else:
        return empty


def get_fanart_path(database_id):
    utils.log("jsonrpc_calls.py - Retrieving Fanart Path for Artist id: %s" % database_id)
    if database_id:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", ' \
                     '"params": {"properties": ["fanart"], "artistid": %d}, "id": 1}' % database_id
        json_fanart = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    else:
        utils.log("jsonrpc_calls.py - Improper type or database_id")
        return empty
    if json_fanart:
        return json_fanart["fanart"]
    else:
        return empty


def get_all_local_artists(all_artists=True):
    utils.log("jsonrpc_calls.py - Retrieving all local artists")
    if all_artists:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", ' \
                     '"params": { "albumartistsonly": false }, "id": 1}'
    else:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", ' \
                     '"params": { "albumartistsonly": true }, "id": 1}'
    json_artists = retrieve_json_dict(json_query, items='artists', force_log=False)
    if json_artists:
        return json_artists
    else:
        return empty


def retrieve_artist_details(artist_id):
    utils.log("jsonrpc_calls.py - Retrieving Artist Details")
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", ' \
                 '"params": {"properties": ["musicbrainzartistid"], "artistid": %d}, "id": 1}' % artist_id
    json_artist_details = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    if json_artist_details:
        return json_artist_details
    else:
        return empty


def retrieve_album_list():
    utils.log("jsonrpc_calls.py - Retrieving Album List")
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", ' \
                 '"params": { "limits": { "start": 0 }, ' \
                 '"properties": ["title", "artist", "musicbrainzalbumid", "musicbrainzalbumartistid"], ' \
                 '"sort": {"order":"ascending"}}, "id": 1}'
    json_albums = retrieve_json_dict(json_query, items='albums', force_log=False)
    if json_albums:
        return json_albums, len(json_albums)
    else:
        return empty, 0


def retrieve_album_details(album_id):
    utils.log("jsonrpc_calls.py - Retrieving Album Details")
    album_details = []
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", ' \
                 '"params": {"properties": ["artist", "title", "musicbrainzalbumid", "musicbrainzalbumartistid"], ' \
                 '"albumid": %d}, "id": 1}' % album_id
    json_album_details = retrieve_json_dict(json_query, items='albumdetails', force_log=False)
    if json_album_details:
        album_details.append(json_album_details)
        return album_details
    else:
        return empty


def get_album_path(album_id):
    utils.log("jsonrpc_calls.py - Retrieving Album Path")
    paths = []
    albumartistmbids = []
    albumreleasembids = []
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", ' \
                 '"params": { "properties": ["file", "musicbrainzalbumartistid", "musicbrainzalbumid"], ' \
                 '"filter": { "albumid": %d }, "sort": {"method":"path","order":"ascending"} }, "id": 1}' % album_id
    json_songs_detail = retrieve_json_dict(json_query, items='songs', force_log=False)
    if json_songs_detail:
        for song in json_songs_detail:
            path = os.path.dirname(song['file'])
            paths.append(path)
            albumartistmbid = song['musicbrainzalbumartistid']
            albumartistmbids.append(albumartistmbid)
            albumreleasembid = song['musicbrainzalbumid']
            albumreleasembids.append(albumreleasembid)
        return paths, albumartistmbids, albumreleasembids
    else:
        return empty


def retrieve_json_dict(json_query, items='items', force_log=False):
    """ retrieve_json_dict()
        This function returns the response from a json rpc query in a dict(hash) form

        requirements:
            json_query - a properly formed json rpc request for return
            items - the specific key being looked for, example for VideoLibrary.GetMovies - 'movies' is the key,
            'items' is a common response(can be left blank then)
    """
    xbmc.log("[json_utils.py] - JSONRPC Query -\n%s" % json_query, level=xbmc.LOGDEBUG)
    response = xbmc.executeJSONRPC(json_query)
    if force_log:
        xbmc.log("[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % response, level=xbmc.LOGDEBUG)
    if response.startswith("{"):
        response = eval(response, {"true": True, "false": False, "null": None})
        try:
            if 'result' in response:
                result = response['result']
                json_dict = result[items]
                return json_dict
            else:
                xbmc.log("[json_utils.py] - retrieve_json_dict - No response from XBMC", level=xbmc.LOGNOTICE)
                xbmc.log(response, level=xbmc.LOGDEBUG)
                return None
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
            xbmc.log("[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % response, level=xbmc.LOGNOTICE)
            xbmc.log("[json_utils.py] - retrieve_json_dict - Error trying to get json response", level=xbmc.LOGNOTICE)
            return empty
    else:
        return empty
