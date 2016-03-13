# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import Utils

LAST_FM_API_KEY = 'd942dd5ca4c9ee5bd821df58cf8130d4'
GOOGLE_MAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?api_key=%s&format=json&' % (LAST_FM_API_KEY)


def handle_albums(results):
    albums = []
    if not results:
        return []
    if 'topalbums' in results and "album" in results['topalbums']:
        for album in results['topalbums']['album']:
            album = {'artist': album['artist']['name'],
                     'mbid': album.get('mbid', ""),
                     'mediatype': "album",
                     'thumb': album['image'][-1]['#text'],
                     'name': album['name']}
            albums.append(album)
    return albums


def handle_artists(results):
    artists = []
    if not results:
        return []
    for artist in results['artist']:
        if 'name' not in artist:
            continue
        artist = {'title': artist['name'],
                  'name': artist['name'],
                  'mediatype': "artist",
                  'mbid': artist.get('mbid'),
                  'thumb': artist['image'][-1]['#text'],
                  'Listeners': format(int(artist.get('listeners', 0)), ",d")}
        artists.append(artist)
    return artists


def get_top_artists():
    results = get_data(method="Chart.getTopArtists",
                       params={"limit": "100"})
    return handle_artists(results['artists'])


def get_artist_albums(artist_mbid):
    if not artist_mbid:
        return []
    results = get_data(method="Artist.getTopAlbums",
                       params={"mbid": artist_mbid})
    return handle_albums(results)


def get_similar_artists(artist_mbid):
    if not artist_mbid:
        return []
    params = {"mbid": artist_mbid,
              "limit": "400"}
    results = get_data(method="Artist.getSimilar",
                       params=params)
    if results and "similarartists" in results:
        return handle_artists(results['similarartists'])


def get_track_info(artist_name="", track=""):
    if not artist_name or not track:
        return []
    params = {"artist": artist_name,
              "track": track}
    results = get_data(method="track.getInfo",
                       params=params)
    if not results:
        return {}
    summary = results['track']['wiki']['summary'] if "wiki" in results['track'] else ""
    return {'playcount': str(results['track']['playcount']),
            'thumb': str(results['track']['playcount']),
            'summary': Utils.clean_text(summary)}


def get_data(method, params={}, cache_days=0.5):
    params["method"] = method
    # params = {k: v for k, v in params.items() if v}
    params = dict((k, v) for (k, v) in params.iteritems() if v)
    params = dict((k, unicode(v).encode('utf-8')) for (k, v) in params.iteritems())
    url = "{base_url}{params}".format(base_url=BASE_URL,
                                      params=urllib.urlencode(params))
    return Utils.get_JSON_response(url=url,
                                   cache_days=cache_days,
                                   folder="LastFM")
