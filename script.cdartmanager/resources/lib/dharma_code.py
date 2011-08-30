# -*- coding: utf-8 -*-
# script.cdart.manager 
# dharma code

import xbmc, xbmcaddon
import os, urllib
from json_utils import retrieve_json_dict

def get_all_local_artists():
    xbmc.log( "[script.cdartmanager] - dharma_code - Retrieving all local artists", xbmc.LOGDEBUG )
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "id": 1}'
    json_artists = retrieve_json_dict(json_query, items='artists', force_log=False )
    return json_artists
    
def retrieve_album_list():
    xbmc.log( "[script.cdartmanager] - dharma_code - Retrieving Album List"        , xbmc.LOGDEBUG )
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"fields": ["title", "artist"] }, "id": 1}'
    json_albums = retrieve_json_dict(json_query, items='albums', force_log=False )
    return json_albums, len(json_albums)

def retrieve_album_details( album_id ):
    xbmc.log( "[script.cdartmanager] - dharma_code - Retrieving Album Path", xbmc.LOGDEBUG )
    album_details = []
    album = {}
    try:
        xbmc.executehttpapi( "SetResponseFormat()" )
        xbmc.executehttpapi( "SetResponseFormat(OpenField,)" )
        httpapi_album_detail_query="""SELECT DISTINCT strAlbum, strArtist, idAlbum  FROM albumview WHERE idAlbum="%s" AND strAlbum !=''""" % album_id 
        album_title, artist_name, album_localid, dummy = xbmc.executehttpapi("QueryMusicDatabase(%s)" % urllib.quote_plus( httpapi_album_detail_query ), ).split( "</field>" )
        album['title'] = album_title
        album['artist'] = artist_name
        album['albumid'] = album_localid
        album_details.append( album )
    except:
        album['title'] = ""
        album['artist'] = ""
        album['albumid'] = ""
        album_details.append( album )
    return album_details

def get_album_path( album_id ):
    xbmc.log( "[script.cdartmanager] - dharma_code - Retrieving Album Path", xbmc.LOGDEBUG )
    paths = []
    json_query = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"albumid": %d, "fields": ["file"], "sort": {"method":"fullpath","order":"ascending"} }, "id": 1}' % album_id
    json_songs_detail = retrieve_json_dict(json_query, items='songs', force_log=False )
    if json_songs_detail:
        for song in json_songs_detail:
            path = os.path.dirname( song['file'] )
            paths.append( path )
    return paths