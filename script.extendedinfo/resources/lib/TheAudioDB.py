# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
from Utils import *
from LocalDB import local_db

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
            desc += "[CR][CR][B]%s:[/B][CR][CR]%s" % (LANG(185), album['strReview'])
        album = {'artist': album['strArtist'],
                 'mbid': album['strMusicBrainzID'],
                 'id': album['idAlbum'],
                 'audiodb_id': album['idAlbum'],
                 'Description': desc,
                 'path': "",
                 'mediatype': "album",
                 'Plot': desc,
                 'genre': album['strGenre'],
                 'Mood': album['strMood'],
                 'Style': album['strStyle'],
                 'Speed': album['strSpeed'],
                 'Theme': album['strTheme'],
                 'Type': album['strReleaseFormat'],
                 'thumb': album['strAlbumThumb'],
                 'spine': album['strAlbumSpine'],
                 'cdart': album['strAlbumCDart'],
                 'thumbback': album['strAlbumThumbBack'],
                 'loved': album['intLoved'],
                 'location': album['strLocation'],
                 'itunes_id': album['strItunesID'],
                 'amazon_id': album['strAmazonID'],
                 'year': album['intYearReleased'],
                 'Sales': album['intSales'],
                 'name': album['strAlbum'],
                 'Label': album['strAlbum']}
        albums.append(album)
    return local_db.compare_album_with_library(albums)


def handle_tracks(results):
    tracks = []
    if not results.get('track'):
        return None
    for item in results['track']:
        youtube_id = extract_youtube_id(item.get('strMusicVid', ''))
        track = {'Track': item['strTrack'],
                 'Artist': item['strArtist'],
                 'mediatype': "song",
                 'mbid': item['strMusicBrainzID'],
                 'Album': item['strAlbum'],
                 'thumb': "http://i.ytimg.com/vi/" + youtube_id + "/0.jpg",
                 'path': convert_youtube_url(item['strMusicVid']),
                 'Label': item['strTrack']}
        tracks.append(track)
    return tracks


def handle_musicvideos(results):
    if not results.get('mvids'):
        return []
    mvids = []
    for item in results['mvids']:
        youtube_id = extract_youtube_id(item.get('strMusicVid', ''))
        mvid = {'Track': item['strTrack'],
                'Description': item['strDescriptionEN'],
                'id': item['idTrack'],
                'mediatype': "musicvideo",
                'thumb': "http://i.ytimg.com/vi/" + youtube_id + "/0.jpg",
                'path': convert_youtube_url(item['strMusicVid']),
                'Label': item['strTrack']}
        mvids.append(mvid)
    return mvids


def extended_artist_info(results):
    artists = []
    if not results.get('artists'):
        return None
    local_bio = 'strBiography' + SETTING("LanguageID").upper()
    for artist in results['artists']:
        description = ""
        if local_bio in artist and artist[local_bio]:
            description = fetch(artist, local_bio)
        elif artist.get('strBiographyEN'):
            description = fetch(artist, 'strBiographyEN')
        elif artist.get('strBiography'):
            description = fetch(artist, 'strBiography')
        banner = artist.get('strArtistBanner')
        if not banner:
            banner = ""
        if 'strReview' in artist and artist['strReview']:
            description += "[CR]" + fetch(artist, 'strReview')
        artist = {'artist': fetch(artist, 'strArtist'),
                  'mbid': fetch(artist, 'strMusicBrainzID'),
                  'Banner': banner,
                  'mediatype': "artist",
                  'Logo': fetch(artist, 'strArtistLogo'),
                  'fanart': fetch(artist, 'strArtistFanart'),
                  'fanart2': fetch(artist, 'strArtistFanart2'),
                  'fanart3': fetch(artist, 'strArtistFanart3'),
                  'Born': fetch(artist, 'intBornYear'),
                  'Formed': fetch(artist, 'intFormedYear'),
                  'Died': fetch(artist, 'intDiedYear'),
                  'Disbanded': fetch(artist, 'intDiedYear'),
                  'Mood': fetch(artist, 'strMood'),
                  'Artist_Born': fetch(artist, 'intBornYear'),
                  'Artist_Formed': fetch(artist, 'intFormedYear'),
                  'Artist_Died': fetch(artist, 'intDiedYear'),
                  'Artist_Disbanded': fetch(artist, 'strDisbanded'),
                  'Artist_Mood': fetch(artist, 'strMood'),
                  'Country': fetch(artist, 'strCountryCode'),
                  'CountryName': fetch(artist, 'strCountry'),
                  'Website': fetch(artist, 'strWebsite'),
                  'Twitter': fetch(artist, 'strTwitter'),
                  'Facebook': fetch(artist, 'strFacebook'),
                  'LastFMChart': fetch(artist, 'strLastFMChart'),
                  'Gender': fetch(artist, 'strGender'),
                  'audiodb_id': fetch(artist, 'idArtist'),
                  'Description': description,
                  'Plot': description,
                  'path': "",
                  'genre': fetch(artist, 'strGenre'),
                  'Style': fetch(artist, 'strStyle'),
                  'thumb': fetch(artist, 'strArtistThumb'),
                  'Art(Thumb)': fetch(artist, 'strArtistThumb'),
                  'Members': fetch(artist, 'intMembers')}
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
    url = "%s%s.php?%s" % (BASE_URL, url, urllib.urlencode(params))
    return get_JSON_response(url=url,
                             folder="TheAudioDB")
