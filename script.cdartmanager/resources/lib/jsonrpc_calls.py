# -*- coding: utf-8 -*-
# script.cdartmanager 
# jsonrpc_calls.py

import os

import xbmc
from json_utils import retrieve_json_dict
import utils

empty = []


def get_thumbnail_path(database_id, type):
    utils.log("jsonrpc_calls.py - Retrieving Thumbnail Path for %s id: %s" % (type, database_id), xbmc.LOGDEBUG)
    if type in ("cover", "cdart", "album") and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["thumbnail"], "albumid": %d}, "id": 1}''' % database_id
        json_thumb = retrieve_json_dict(json_query, items='albumdetails', force_log=False)
    elif type in ("fanart", "clearlogo", "artistthumb", "artist") and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["thumbnail"], "artistid": %d}, "id": 1}''' % database_id
        json_thumb = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    else:
        utils.log("jsonrpc_calls.py - Improper type or database_id", xbmc.LOGDEBUG)
        return empty
    if json_thumb:
        return json_thumb["thumbnail"]
    else:
        return empty


def get_fanart_path(database_id, type):
    utils.log("jsonrpc_calls.py - Retrieving Fanart Path for %s id: %s" % (type, database_id), xbmc.LOGDEBUG)
    if type in ("cover", "cdart", "album") and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["fanart"], "albumid": %d}, "id": 1}''' % database_id
        json_fanart = retrieve_json_dict(json_query, items='albumdetails', force_log=False)
    elif type in ("fanart", "clearlogo", "artistthumb", "artist") and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["fanart"], "artistid": %d}, "id": 1}''' % database_id
        json_fanart = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    else:
        utils.log("jsonrpc_calls.py - Improper type or database_id", xbmc.LOGDEBUG)
        return empty
    if json_fanart:
        return json_fanart["fanart"]
    else:
        return empty


def get_all_local_artists(all_artists=True):
    utils.log("jsonrpc_calls.py - Retrieving all local artists", xbmc.LOGDEBUG)
    if all_artists:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "albumartistsonly": false }, "id": 1}'''
    else:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "albumartistsonly": true }, "id": 1}'''
    json_artists = retrieve_json_dict(json_query, items='artists', force_log=False)
    if json_artists:
        return json_artists
    else:
        return empty


def retrieve_artist_details(artist_id):
    utils.log("jsonrpc_calls.py - Retrieving Artist Details", xbmc.LOGDEBUG)
    json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["musicbrainzartistid"], "artistid": %d}, "id": 1}''' % artist_id
    json_artist_details = retrieve_json_dict(json_query, items='artistdetails', force_log=False)
    if json_artist_details:
        return json_artist_details
    else:
        return empty


def retrieve_album_list():
    utils.log("jsonrpc_calls.py - Retrieving Album List", xbmc.LOGDEBUG)
    json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": { "limits": { "start": 0 }, "properties": ["title", "artist", "musicbrainzalbumid", "musicbrainzalbumartistid"], "sort": {"order":"ascending"}}, "id": 1}'''
    json_albums = retrieve_json_dict(json_query, items='albums', force_log=False)
    if json_albums:
        return json_albums, len(json_albums)
    else:
        return empty, 0


def retrieve_album_details(album_id):
    utils.log("jsonrpc_calls.py - Retrieving Album Details", xbmc.LOGDEBUG)
    album_details = []
    json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["artist", "title", "musicbrainzalbumid", "musicbrainzalbumartistid"], "albumid": %d}, "id": 1}''' % album_id
    json_album_details = retrieve_json_dict(json_query, items='albumdetails', force_log=False)
    if json_album_details:
        album_details.append(json_album_details)
        return album_details
    else:
        return empty


def get_album_path(album_id):
    utils.log("jsonrpc_calls.py - Retrieving Album Path", xbmc.LOGDEBUG)
    paths = []
    albumartistmbids = []
    albumreleasembids = []
    json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "properties": ["file", "musicbrainzalbumartistid", "musicbrainzalbumid"], "filter": { "albumid": %d }, "sort": {"method":"path","order":"ascending"} }, "id": 1}''' % album_id
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
