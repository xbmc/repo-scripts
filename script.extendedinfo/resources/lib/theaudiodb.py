# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Module with get_* functions to query TADB

Requires user API key (subscription basis) to access

"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

import xbmc
from resources.kutil131 import ItemList, addon

from resources.kutil131 import AudioItem, VideoItem, local_db, utils

AUDIO_DB_KEY = '2'  #key no longer accepted - this is demo key
BASE_URL = 'https://www.theaudiodb.com/api/v1/json'
PLUGIN_BASE = 'plugin://script.extendedinfo/?info='


def _handle_albums(results:dict) -> ItemList:
    """Creates an ItemList of kutils131 AudioItems

    Args:
        results (dict): TADB album info

    Returns:
        ItemList: kutils131 ItemList of AudioItems
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
            desc += f"[CR][CR][B]{addon.LANG(185)}:[/B][CR][CR]{item['strReview']}"
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
    """Creates an ItemList of track AudioItems

    Args:
        results (dict): TADB tracks

    Returns:
        ItemList: The kutils131 itemlist of the tracts
    """
    tracks = ItemList(content_type="songs")
    if not results.get('track'):
        return tracks
    for item in results['track']:
        youtube_id = utils.extract_youtube_id(item.get('strMusicVid', ''))
        track = AudioItem(label=item['strTrack'],
                          path=f"{PLUGIN_BASE}youtubevideo&&id={youtube_id}")
        track.set_infos({'title': item['strTrack'],
                         'album': item['strAlbum'],
                         'artist': item['strArtist'],
                         'mediatype': "song"})
        track.set_properties({'mbid': item['strMusicBrainzID']})
        track.set_artwork(
            {'thumb': f"http://i.ytimg.com/vi/{youtube_id}/0.jpg"})
        tracks.append(track)
    return tracks


def _handle_musicvideos(results:dict) -> ItemList:
    """Creates an ItemList of TADB VideoItems 

    Args:
        results (dict): TADB musicvideos

    Returns:
        ItemList: the kutils131 ItemList of musicvideos
    """
    mvids = ItemList(content_type="musicvideos")
    if not results.get('mvids'):
        return mvids
    for item in results['mvids']:
        youtube_id = utils.extract_youtube_id(item.get('strMusicVid', ''))
        mvid = VideoItem(label=item['strTrack'],
                         path=f"{PLUGIN_BASE}youtubevideo&&id={youtube_id}")
        mvid.set_infos({'title': item['strTrack'],
                        'plot': item['strDescriptionEN'],
                        'mediatype': "musicvideo"})
        mvid.set_properties({'id': item['idTrack']})
        mvid.set_artwork(
            {'thumb': f"http://i.ytimg.com/vi/{youtube_id}/0.jpg"})
        mvids.append(mvid)
    return mvids


def extended_artist_info(results: dict) -> dict:
    """Gets artist info from TADB and returns artist dict

    Args:
        results (dict): TADB artist info

    Returns:
        dict: artist details using Kodi properties keywords
    """
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
        [ItemList]: kutils131 ItemList instance of AudioItems
    """
    if not search_str:
        return ItemList(content_type="albums")
    params: dict = {"s": search_str}
    results: dict = get_data("searchalbum", params)
    return _handle_albums(results)


def get_artist_details(search_str) -> ItemList | dict:
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
    if results:
        return extended_artist_info(results)
    else:
        utils.notify("No artist info from TheAudioDb")


def get_most_loved_tracks(search_str="", mbid="") -> ItemList | list:
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


def get_album_details(audiodb_id="", mbid="") -> ItemList | list:
    """Creates ItemList of TADB alubm detals

    Args:
        audiodb_id (str, optional): TADB album id "".
        mbid (str, optional): mbid album groupd id Defaults to "".

    Returns:
        list: empty if no results
        ItemList: kutils131 ItemList of album AudioItems
    """
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


def get_musicvideos(audiodb_id) -> ItemList:
    """Creates ItemList of musicvideo Videoitems

    Args:
        audiodb_id (str): TADB id

    Returns:
        ItemList: kutils131 ItemList
    """
    if not audiodb_id:
        return ItemList(content_type="musicvideos")
    params = {"i": audiodb_id}
    results = get_data("mvid", params)
    return _handle_musicvideos(results)


def get_track_details(audiodb_id: str) -> ItemList | list:
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
    if tadb_key is None or tadb_key == '':
        tadb_key = AUDIO_DB_KEY #limited function key
    params: dict = {k: str(v) for k, v in params.items() if v}
    url: str = f"{BASE_URL}/{tadb_key}/{url}.php?{urllib.parse.urlencode(params)}"
    return utils.get_JSON_response(url=url,
                                   folder="TheAudioDB")
