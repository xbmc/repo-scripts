# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Uses LastFM API  to query data from LastFM.

The get_* functions are called to query LastFM API.

"""

import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from resources.kutil131 import ItemList

from resources.kutil131 import utils

LAST_FM_API_KEY = 'd942dd5ca4c9ee5bd821df58cf8130d4'
GOOGLE_MAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?'


def _handle_albums(results: dict) -> ItemList:
    """Converts TADB query results to kutils131 ItemList

    Args:
        results (dict): TADB albums for an artist

    Returns:
        ItemList: a kutils131 ItemList od dicts
    """
    albums = ItemList(content_type="albums")
    if not results:
        return albums
    if 'topalbums' in results and "album" in results['topalbums']:
        for album in results['topalbums']['album']:
            albums.append({'artist': album['artist']['name'],
                           'mbid': album.get('mbid', ""),
                           'mediatype': "album",
                           'thumb': album['image'][-1]['#text'],
                           'label': f"{album['artist']['name']} - {album['name']}",
                           'title': album['name']})
            albums.append(album)
    return albums


def _handle_artists(results) -> ItemList:
    """Converts TADB artist query to kutils131 ItemList

    Args:
        results (_type_): _description_

    Returns:
        ItemList: a kutils131 ItemList of artist info as dicts
    """
    artists = ItemList(content_type="artists")
    if not results:
        return artists
    for artist in results['artist']:
        if 'name' not in artist:
            continue
        artist = {'title': artist['name'],
                  'label': artist['name'],
                  'mediatype': "artist",
                  'mbid': artist.get('mbid'),
                  'thumb': artist['image'][-1]['#text'],
                  'Listeners': format(int(artist.get('listeners', 0)), ",d")}
        artists.append(artist)
    return artists


def get_top_artists() -> ItemList:
    """Queries LastFM api chart.getTopArtists method for top 100 artists

    Returns:
        ItemList: a kutils131 object that wraps a list of artist
        info dicts
    """
    results: Optional[dict] = get_data(method="chart.getTopArtists",
                       params={"limit": "100"})
    return _handle_artists(results['artists'])


def get_artist_albums(artist_mbid: str) -> ItemList:
    """Queries LastFM api artist.getTopAlbums method for an artist

    Gets 50 albums with title, mbid, and cover image

    Args:
        artist_mbid (str): The musicbrainz id for the artist

    Returns:
        ItemList: a kutils131object that wraps a list of albums
        info dicts
    """
    if not artist_mbid:
        return ItemList(content_type="albums")
    results = get_data(method="artist.getTopAlbums",
                       params={"mbid": artist_mbid})
    return _handle_albums(results)


def get_similar_artists(artist_mbid: str) -> ItemList:
    """Queries LastFM api artist.getsimilar for artists

   Gets name, mbid, and thumb image of similar artists

    Args:
        artist_mbid (str): The musicbrainz id for the artist

    Returns:
        ItemList: a kutils131 object that wraps a list of artists info dicts
    """
    if not artist_mbid:
        return ItemList(content_type="artists")
    params = {"mbid": artist_mbid,
              "limit": "400"}
    results = get_data(method="artist.getSimilar",
                       params=params)
    if results and "similarartists" in results:
        return _handle_artists(results['similarartists'])


def get_track_info(artist_name="", track="") -> dict:
    """ Queries LastFM api

    Args:
        artist_name (str, optional): The artist name. Defaults to "".
        track (str, optional): The track name. Defaults to "".

    Returns:
        dict: LastFM info including scrobles of a song.
    """
    if not artist_name or not track:
        return {}
    params = {"artist": artist_name,
              "track": track}
    results: Optional[dict] = get_data(method="track.getInfo",
                       params=params)
    if not results:
        return {}
    summary = results['track']['wiki']['summary'] if "wiki" in results['track'] else ""
    return {'playcount': str(results['track']['playcount']),
            'thumb': str(results['track']['playcount']),
            'summary': clean_text(summary)}


def get_data(method: str, params=None, cache_days=0.5) -> dict:
    """helper function runs query including using local cache

    Args:
        method (str): LastFM api method
        params (dict, optional): LastFM method parameters.  Defaults to None.
        cache_days (float, optional): Days to use cache/query. Defaults to 0.5.

    Returns:
        dict:  The json.loads results from the query
    """
    params = params if params else {}
    params["method"] = method
    params["api_key"] = LAST_FM_API_KEY
    params["format"] = "json"
    params = {k: str(v) for k, v in params.items() if v}
    url = f"{BASE_URL}{urllib.parse.urlencode(params)}"
    return utils.get_JSON_response(url=url,
                                   cache_days=cache_days,
                                   folder="LastFM")


def clean_text(text) -> str:
    """Helper function to unescape chars

    Args:
        text (str): text string to unescape

    Returns:
        str: text string
    """
    if not text:
        return ""
    text = re.sub(
        '(From Wikipedia, the free encyclopedia)|(Description above from the Wikipedia.*?Wikipedia)', '', text)
    text = re.sub('<(.|\n|\r)*?>', '', text)
    text = text.replace('<br \/>', '[CR]')
    text = text.replace('<em>', '[I]').replace('</em>', '[/I]')
    text = text.replace('&amp;', '&')
    text = text.replace('&gt;', '>').replace('&lt;', '<')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    text = re.sub("\n\\.$", "", text)
    text = text.replace(
        'User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '')
    removals = {'\u200b', " ", "\n"}
    while text:
        s = text[0]
        e = text[-1]
        if s in removals:
            text = text[1:]
        elif e in removals:
            text = text[:-1]
        elif s.startswith(".") and not s.startswith(".."):
            text = text[1:]
        else:
            break
    return text.strip()
