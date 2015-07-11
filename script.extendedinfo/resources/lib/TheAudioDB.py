# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
from Utils import *
from local_db import compare_album_with_library

AUDIO_DB_KEY = '58353d43204d68753987fl'
BASE_URL = 'http://www.theaudiodb.com/api/v1/json/%s/' % (AUDIO_DB_KEY)


def handle_audiodb_albums(results):
    albums = []
    if 'album' in results and results['album']:
        local_description = 'strDescription' + xbmc.getLanguage(xbmc.ISO_639_1).upper()
        for album in results['album']:
            if local_description in album and album[local_description]:
                description = album.get(local_description, "")
            elif 'strDescriptionEN' in album and album['strDescriptionEN']:
                description = album['strDescriptionEN']
            elif 'strDescription' in album and album['strDescription']:
                description = album['strDescription']
            else:
                description = ""
            if 'strReview' in album and album['strReview']:
                description += "[CR][CR][B]" + LANG(185) + ":[/B][CR][CR]" + album['strReview']
            album = {'artist': album['strArtist'],
                     'mbid': album['strMusicBrainzID'],
                     'id': album['idAlbum'],
                     'audiodb_id': album['idAlbum'],
                     'Description': description,
                     'path': "",
                     'Plot': description,
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
        albums = compare_album_with_library(albums)
    else:
        log("Error when handling handle_audiodb_albums results")
    return albums


def handle_audiodb_tracks(results):
    tracks = []
    if 'track' in results and results['track']:
        for track in results['track']:
            if 'strMusicVid' in track and track['strMusicVid']:
                thumb = "http://i.ytimg.com/vi/" + extract_youtube_id(track.get('strMusicVid', '')) + "/0.jpg"
                path = convert_youtube_url(track['strMusicVid'])
            else:
                thumb = ""
                path = ""
            track = {'Track': track['strTrack'],
                     'Artist': track['strArtist'],
                     'mbid': track['strMusicBrainzID'],
                     'Album': track['strAlbum'],
                     'thumb': thumb,
                     'path': path,
                     'Label': track['strTrack']}
            tracks.append(track)
    else:
        log("Error when handling handle_audiodb_tracks results")
        prettyprint(results)
    return tracks


def handle_audiodb_musicvideos(results):
    mvids = []
    if 'mvids' in results and results['mvids']:
        for mvid in results['mvids']:
            mvid = {'Track': mvid['strTrack'],
                    'Description': mvid['strDescriptionEN'],
                    'id': mvid['idTrack'],
                    'thumb': "http://i.ytimg.com/vi/" + extract_youtube_id(mvid.get('strMusicVid', '')) + "/0.jpg",
                    'path': convert_youtube_url(mvid['strMusicVid']),
                    'Label': mvid['strTrack']}
            mvids.append(mvid)
    else:
        log("Error when handling handle_audiodb_musicvideos results")
    return mvids


def extended_artist_info(results):
    artists = []
    if 'artists' in results and results['artists']:
        for artist in results['artists']:
            local_bio = 'strBiography' + SETTING("LanguageID").upper()
            if local_bio in artist and artist[local_bio]:
                description = fetch(artist, local_bio)
            elif 'strBiographyEN' in artist and artist['strBiographyEN']:
                description = fetch(artist, 'strBiographyEN')
            elif 'strBiography' in artist and artist['strBiography']:
                description = fetch(artist, 'strBiography')
            else:
                description = ""
            if 'strArtistBanner' in artist and artist['strArtistBanner']:
                banner = artist['strArtistBanner']
            else:
                banner = ""
            if 'strReview' in artist and artist['strReview']:
                description += "[CR]" + fetch(artist, 'strReview')
            artist = {'artist': fetch(artist, 'strArtist'),
                      'mbid': fetch(artist, 'strMusicBrainzID'),
                      'Banner': banner,
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
    else:
        log("Error when handling extended_artist_info results")
    if artists:
        return artists[0]
    else:
        return {}


def get_artist_discography(search_str):
    url = 'searchalbum.php?s=%s' % (url_quote(search_str))
    results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
    return handle_audiodb_albums(results)


def get_artist_details(search_str):
    url = 'search.php?s=%s' % (url_quote(search_str))
    results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
    return extended_artist_info(results)


def get_most_loved_tracks(search_str="", mbid=""):
    if mbid:
        url = 'track-top10-mb.php?s=%s' % (mbid)
    else:
        url = 'track-top10.php?s=%s' % (url_quote(search_str))
    log("GetMostLoveTracks URL:" + url)
    results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
    return handle_audiodb_tracks(results)


def get_album_details(audiodb_id="", mbid=""):
    if audiodb_id:
        url = 'album.php?m=%s' % (audiodb_id)
    elif mbid:
        url = 'album-mb.php?i=%s' % (mbid)
    results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
    return handle_audiodb_albums(results)[0]


def get_musicvideos(audiodb_id):
    if audiodb_id:
        url = 'mvid.php?i=%s' % (audiodb_id)
        results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
        return handle_audiodb_musicvideos(results)
    else:
        return []


def get_track_details(audiodb_id):
    if audiodb_id:
        url = 'track.php?m=%s' % (audiodb_id)
        results = get_JSON_response(url=BASE_URL + url, folder="TheAudioDB")
        return handle_audiodb_tracks(results)
    else:
        return []
