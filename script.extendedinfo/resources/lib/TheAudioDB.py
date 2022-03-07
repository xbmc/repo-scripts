# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Modules with get_* functions to query TADB

Requires user API key (subscription basis) to access
TODO:  handle user api key 

"""

import urllib.error
import urllib.parse
import urllib.request
from typing import Union

import xbmc

from kutils import AudioItem, ItemList, VideoItem, addon, local_db, utils

AUDIO_DB_KEY = '58353d43204d68753987fl'  #key no longer accepted
BASE_URL = 'https://www.theaudiodb.com/api/v1/json'
PLUGIN_BASE = 'plugin://script.extendedinfo/?info='


def _handle_albums(results):
    """[summary]

    Args:
        results ([type]): [description]

    Returns:
        [type]: [description]
    """
    albums = ItemList(content_type="albums")
    if not results.get('album'):
        return albums
    local_desc = 'strDescription' + xbmc.getLanguage(xbmc.ISO_639_1).upper()
    for item in results['album']:
        desc = ""
        if local_desc in item and item[local_desc]:
            desc = item.get(local_desc, "")
        elif item.get('strDescriptionEN'):
            desc = item['strDescriptionEN']
        elif item.get('strDescription'):
            desc = item['strDescription']
        if item.get('strReview'):
            desc += "[CR][CR][B]%s:[/B][CR][CR]%s" % (
                addon.LANG(185), item['strReview'])
        album = AudioItem(label=item['strAlbum'],
                          path="")
        album.set_infos({'artist': item['strArtist'],
                         'album': item['strAlbum'],
                         'mediatype': "album",
                         'genre': item['strGenre'],
                         'year': item['intYearReleased']})
        album.set_properties({'mbid': item['strMusicBrainzID'],
                              'id': item['idAlbum'],
                              'audiodb_id': item['idAlbum'],
                              'album_description': desc,
                              'album_mood': item['strMood'],
                              'album_style': item['strStyle'],
                              'speed': item['strSpeed'],
                              'album_Theme': item['strTheme'],
                              'type': item['strReleaseFormat'],
                              'loved': item['intLoved'],
                              'location': item['strLocation'],
                              'itunes_id': item['strItunesID'],
                              'amazon_id': item['strAmazonID'],
                              'sales': item['intSales']})
        album.set_artwork({'thumb': item['strAlbumThumb'],
                           'spine': item['strAlbumSpine'],
                           'cdart': item['strAlbumCDart'],
                           'thumbback': item['strAlbumThumbBack']})
        albums.append(album)
    return local_db.compare_album_with_library(albums)


def _handle_tracks(results: dict) -> ItemList:
    tracks = ItemList(content_type="songs")
    if not results.get('track'):
        return tracks
    for item in results['track']:
        youtube_id = utils.extract_youtube_id(item.get('strMusicVid', ''))
        track = AudioItem(label=item['strTrack'],
                          path="%syoutubevideo&&id=%s" % (PLUGIN_BASE, youtube_id))
        track.set_infos({'title': item['strTrack'],
                         'album': item['strAlbum'],
                         'artist': item['strArtist'],
                         'mediatype': "song"})
        track.set_properties({'mbid': item['strMusicBrainzID']})
        track.set_artwork(
            {'thumb': "http://i.ytimg.com/vi/%s/0.jpg" % youtube_id})
        tracks.append(track)
    return tracks


def _handle_musicvideos(results):
    mvids = ItemList(content_type="musicvideos")
    if not results.get('mvids'):
        return mvids
    for item in results['mvids']:
        youtube_id = utils.extract_youtube_id(item.get('strMusicVid', ''))
        mvid = VideoItem(label=item['strTrack'],
                         path="%syoutubevideo&&id=%s" % (PLUGIN_BASE, youtube_id))
        mvid.set_infos({'title': item['strTrack'],
                        'plot': item['strDescriptionEN'],
                        'mediatype': "musicvideo"})
        mvid.set_properties({'id': item['idTrack']})
        mvid.set_artwork(
            {'thumb': "http://i.ytimg.com/vi/%s/0.jpg" % youtube_id})
        mvids.append(mvid)
    return mvids


def extended_artist_info(results: dict) -> dict:
    if not results.get('artists'):
        return {}
    local_bio = 'strBiography' + addon.setting("LanguageID").upper()
    artist = results['artists'][0]
    description = ""
    if local_bio in artist and artist[local_bio]:
        description = artist.get(local_bio)
    elif artist.get('strBiographyEN'):
        description = artist.get('strBiographyEN')
    elif artist.get('strBiography'):
        description = artist.get('strBiography')
    if 'strReview' in artist and artist['strReview']:
        description += "[CR]" + artist.get('strReview')
    artist = {'label': artist.get('strArtist'),
              'artist': artist.get('strArtist'),
              'mediatype': "artist",
              'Country': artist.get('strCountry'),
              'mbid': artist.get('strMusicBrainzID'),
              'thumb': artist.get('strArtistThumb'),
              'Banner': artist.get('strArtistBanner'),
              'clearlogo': artist.get('strArtistLogo'),
              'fanart': artist.get('strArtistFanart'),
              'fanart2': artist.get('strArtistFanart2'),
              'fanart3': artist.get('strArtistFanart3'),
              'Artist_Mood': artist.get('strMood'),
              'Artist_Born': artist.get('intBornYear'),
              'Artist_Formed': artist.get('intFormedYear'),
              'Artist_Died': artist.get('intDiedYear'),
              'Artist_Disbanded': artist.get('strDisbanded'),
              'Artist_Mood': artist.get('strMood'),
              'Artist_Description': description,
              'Artist_Genre': artist.get('strGenre'),
              'Artist_Style': artist.get('strStyle'),
              'CountryCode': artist.get('strCountryCode'),
              'Website': artist.get('strWebsite'),
              'Twitter': artist.get('strTwitter'),
              'Facebook': artist.get('strFacebook'),
              'LastFMChart': artist.get('strLastFMChart'),
              'Gender': artist.get('strGender'),
              'audiodb_id': artist.get('idArtist'),
              'Members': artist.get('intMembers')}
    return artist


def get_artist_discography(search_str) -> ItemList:
    """returns artist's discography

    Args:
        search_str (str): Artist name

    Returns:
        [ItemList]: Kutils list instance of AudioItems
    """
    if not search_str:
        return ItemList(content_type="albums")
    params: dict = {"s": search_str}
    results: dict = get_data("searchalbum", params)
    return _handle_albums(results)


def get_artist_details(search_str) -> Union[ItemList, dict]:
    """gets artist details from TADB

    Args:
        search_str [str]: artist name

    Returns:
        Union[ItemList, dict]: the extended artist info
    """
    if not search_str:
        return ItemList(content_type="artists")
    params = {"s": search_str}
    results = get_data("search", params)
    return extended_artist_info(results)


def get_most_loved_tracks(search_str="", mbid="") -> Union[ItemList, list]:
    """ highest rated TADB soings for artist

    Args:
        search_str (str, optional): artist name. Defaults to "".
        mbid (str, optional): musicbrainz artist id. Defaults to "".

    Returns:
        Union[ItemList, list]: list of songs
    """
    if mbid:
        url = 'track-top10-mb'
        params = {"s": mbid}
    elif search_str:
        url = 'track-top10'
        params = {"s": search_str}
    else:
        return []
    results = get_data(url, params)
    return _handle_tracks(results)


def get_album_details(audiodb_id="", mbid=""):
    if audiodb_id:
        url = 'album'
        params = {"m": audiodb_id}
    elif mbid:
        url = 'album-mb'
        params = {"i": mbid}
    else:
        return []
    results = get_data(url, params)
    return _handle_albums(results)[0]


def get_musicvideos(audiodb_id):
    if not audiodb_id:
        return ItemList(content_type="musicvideos")
    params = {"i": audiodb_id}
    results = get_data("mvid", params)
    return _handle_musicvideos(results)


def get_track_details(audiodb_id: str) -> Union[ItemList, list]:
    """gets TADB info for a track

    Args:
        audiodb_id (str): The TADB id

    Returns:
        Union[ItemList, list]: List of track details
    """
    if not audiodb_id:
        return ItemList(content_type="songs")
    params = {"m": audiodb_id}
    results = get_data("track", params)
    return _handle_tracks(results)


def get_data(url: str, params: dict) -> dict:
    """returns a dict from TADB api query

    Args:
        url (str): the TADB GET query
        params (dict): TADB query pamaeters

    Returns:
        dict: TADB api response
    """
    tadb_key: str = addon.setting('TADB API Key')
    params: dict = {k: str(v) for k, v in params.items() if v}
    url: str = "{0}/{1}/{2}.php?{3}".format(BASE_URL,
                                            tadb_key, url, urllib.parse.urlencode(params))
    return utils.get_JSON_response(url=url,
                                   folder="TheAudioDB")
