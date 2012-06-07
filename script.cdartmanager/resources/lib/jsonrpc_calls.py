# -*- coding: utf-8 -*-
# script.cdart.manager 
# jsonrpc_calls

import xbmc, xbmcaddon, xbmcvfs
import os
from json_utils import retrieve_json_dict

def get_thumbnail_path( database_id, type ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Thumbnail Path for %sid: %s" % ( type, database_id ), xbmc.LOGDEBUG )
    if type in ( "cover", "cdart", "album" ) and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["thumbnail"], "albumid": %d}, "id": 1}''' % database_id
        json_thumb = retrieve_json_dict( json_query, items='albumdetails', force_log=False )
    elif type in ( "fanart", "clearlogo", "artistthumb", "artist" ) and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["thumbnail"], "artistid": %d}, "id": 1}''' % database_id
        json_thumb = retrieve_json_dict( json_query, items='artistdetails', force_log=False )
    else:
        xbmc.log( "[script.cdartmanager] - pre_eden_code - Improper type or database_id", xbmc.LOGDEBUG )
        return None
    if json_thumb:
        return json_thumb["thumbnail"]
    else:
        return None
        
def get_fanart_path( database_id, type ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Fanart Path for %sid: %s" % ( type, database_id ), xbmc.LOGDEBUG )
    if type in ( "cover", "cdart", "album" ) and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["fanart"], "albumid": %d}, "id": 1}''' % database_id
        json_fanart = retrieve_json_dict( json_query, items='albumdetails', force_log=False )
    elif type in ( "fanart", "clearlogo", "artistthumb", "artist" ) and database_id:
        json_query = '''{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["fanart"], "artistid": %d}, "id": 1}''' % database_id
        json_fanart = retrieve_json_dict( json_query, items='artistdetails', force_log=False )
    else:
        xbmc.log( "[script.cdartmanager] - pre_eden_code - Improper type or database_id", xbmc.LOGDEBUG )
        return None
    if json_fanart:
        return json_fanart["fanart"]
    else:
        return None
        
def get_all_local_artists( all_artists = True ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving all local artists", xbmc.LOGDEBUG )
    if all_artists:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "albumartistsonly": false }, "id": 1}'
    else:
        json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "albumartists_only": true }, "id": 1}'
    json_artists = retrieve_json_dict(json_query, items='artists', force_log=False )
    if json_artists:
        return json_artists
    else:
        return None

def retrieve_artist_details( artist_id ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Album Path", xbmc.LOGDEBUG )
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["musicbrainzartistid"], "artistid": %d}, "id": 1}' % artist_id
    json_artist_details = retrieve_json_dict(json_query, items='artistdetails', force_log=False )
    if json_artist_details:
        return json_artist_details
    else:
        return None
        
def retrieve_album_list():
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Album List"        , xbmc.LOGDEBUG )
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": { "limits": { "start": 0 }, "properties": ["title", "artist", "musicbrainzalbumid", "musicbrainzalbumartistid"], "sort": {"order":"ascending"}}, "id": 1}'
    json_albums = retrieve_json_dict(json_query, items='albums', force_log=False )
    if json_albums:
        return json_albums, len(json_albums)
    else:
        return None, 0
    
def retrieve_album_details( album_id ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Album Path", xbmc.LOGDEBUG )
    album_details = []
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["artist", "title", "musicbrainzalbumid", "musicbrainzalbumartistid"], "albumid": %d}, "id": 1}' % album_id
    json_album_details = retrieve_json_dict(json_query, items='albumdetails', force_log=False )
    if json_album_details:
        album_details.append( json_album_details )
        return album_details
    else:
        return None

def get_album_path( album_id ):
    xbmc.log( "[script.cdartmanager] - pre_eden_code - Retrieving Album Path", xbmc.LOGDEBUG )
    paths = []
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"albumid": %d, "properties": ["file", "musicbrainzalbumartistid"], "sort": {"method":"fullpath","order":"ascending"}}, "id": 1}' % album_id
    json_songs_detail = retrieve_json_dict(json_query, items='songs', force_log=False )
    if json_songs_detail:
        for song in json_songs_detail:
            path = os.path.dirname( song['file'] )
            paths.append( path )
        return paths
    else:
        return None
