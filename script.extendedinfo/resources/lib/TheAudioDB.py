# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import Utils
import addon
from LocalDB import local_db
import urllib

AUDIO_DB_KEY = '58353d43204d68753987fl'
BASE_URL = 'http://www.theaudiodb.com/api/v1/json/%s/' % (AUDIO_DB_KEY)


def handle_albums(results):
    albums = []
    if not results.get('album'):
        return None
    local_desc = 'strDescription' + xbmc.getLanguage(xbmc.ISO_639_1).upper()
    for album in results['album']:
        desc = ""
        if local_desc in album and album[local_desc]:
            desc = album.get(local_desc, "")
        elif album.get('strDescriptionEN'):
            desc = album['strDescriptionEN']
        elif album.get('strDescription'):
            desc = album['strDescription']
        if album.get('strReview'):
            desc += "[CR][CR][B]%s:[/B][CR][CR]%s" % (addon.LANG(185), album['strReview'])
        album = {'label': album['strAlbum'],
                 'artist': album['strArtist'],
                 'mediatype': "album",
                 'genre': album['strGenre'],
                 'year': album['intYearReleased'],
                 'mbid': album['strMusicBrainzID'],
                 'id': album['idAlbum'],
                 'audiodb_id': album['idAlbum'],
                 'album_description': desc,
                 'album_mood': album['strMood'],
                 'album_style': album['strStyle'],
                 'speed': album['strSpeed'],
                 'album_Theme': album['strTheme'],
                 'type': album['strReleaseFormat'],
                 'thumb': album['strAlbumThumb'],
                 'spine': album['strAlbumSpine'],
                 'cdart': album['strAlbumCDart'],
                 'thumbback': album['strAlbumThumbBack'],
                 'loved': album['intLoved'],
                 'location': album['strLocation'],
                 'itunes_id': album['strItunesID'],
                 'amazon_id': album['strAmazonID'],
                 'sales': album['intSales']}
        albums.append(album)
    return local_db.compare_album_with_library(albums)


def handle_tracks(results):
    tracks = []
    if not results.get('track'):
        return None
    for item in results['track']:
        youtube_id = Utils.extract_youtube_id(item.get('strMusicVid', ''))
        track = {'label': item['strTrack'],
                 'path': Utils.convert_youtube_url(item['strMusicVid']),
                 'title': item['strTrack'],
                 'album': item['strAlbum'],
                 'artist': item['strArtist'],
                 'mediatype': "song",
                 'mbid': item['strMusicBrainzID'],
                 "artwork": {'thumb': "http://i.ytimg.com/vi/" + youtube_id + "/0.jpg"}}
        tracks.append(track)
    return tracks


def handle_musicvideos(results):
    if not results.get('mvids'):
        return []
    mvids = []
    for item in results['mvids']:
        youtube_id = Utils.extract_youtube_id(item.get('strMusicVid', ''))
        mvid = {'label': item['strTrack'],
                'path': Utils.convert_youtube_url(item['strMusicVid']),
                'title': item['strTrack'],
                'plot': item['strDescriptionEN'],
                'mediatype': "musicvideo",
                'id': item['idTrack'],
                "artwork": {'thumb': "http://i.ytimg.com/vi/" + youtube_id + "/0.jpg"}}
        mvids.append(mvid)
    return mvids


def extended_artist_info(results):
    artists = []
    if not results.get('artists'):
        return None
    local_bio = 'strBiography' + addon.setting("LanguageID").upper()
    for artist in results['artists']:
        description = ""
        if local_bio in artist and artist[local_bio]:
            description = artist.get(local_bio)
        elif artist.get('strBiographyEN'):
            description = artist.get('strBiographyEN')
        elif artist.get('strBiography'):
            description = artist.get('strBiography')
        banner = artist.get('strArtistBanner')
        if not banner:
            banner = ""
        if 'strReview' in artist and artist['strReview']:
            description += "[CR]" + artist.get('strReview')
        artist = {'label': artist.get('strArtist'),
                  'artist': artist.get('strArtist'),
                  'mediatype': "artist",
                  'Country': artist.get('strCountry'),
                  'mbid': artist.get('strMusicBrainzID'),
                  'thumb': artist.get('strArtistThumb'),
                  'Banner': banner,
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
        artists.append(artist)
    if artists:
        return artists[0]
    else:
        return {}


def get_artist_discography(search_str):
    if not search_str:
        return []
    params = {"s": search_str}
    results = get_data("searchalbum", params)
    return handle_albums(results)


def get_artist_details(search_str):
    if not search_str:
        return []
    params = {"s": search_str}
    results = get_data("search", params)
    return extended_artist_info(results)


def get_most_loved_tracks(search_str="", mbid=""):
    if mbid:
        url = 'track-top10-mb'
        params = {"s": mbid}
    elif search_str:
        url = 'track-top10'
        params = {"s": search_str}
    else:
        return []
    results = get_data(url, params)
    return handle_tracks(results)


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
    return handle_albums(results)[0]


def get_musicvideos(audiodb_id):
    if not audiodb_id:
        return []
    params = {"i": audiodb_id}
    results = get_data("mvid", params)
    return handle_musicvideos(results)


def get_track_details(audiodb_id):
    if not audiodb_id:
        return []
    params = {"m": audiodb_id}
    results = get_data("track", params)
    return handle_tracks(results)


def get_data(url, params):
    params = {k: v for k, v in params.items() if v}
    params = {k: unicode(v).encode('utf-8') for k, v in params.items()}
    url = "%s%s.php?%s" % (BASE_URL, url, urllib.urlencode(params))
    return Utils.get_JSON_response(url=url,
                                   folder="TheAudioDB")
