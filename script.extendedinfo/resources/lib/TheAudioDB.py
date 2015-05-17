import xbmc
from Utils import *
from local_db import CompareAlbumWithLibrary

AUDIO_DB_KEY = '58353d43204d68753987fl'
BASE_URL = 'http://www.theaudiodb.com/api/v1/json/%s/' % (AUDIO_DB_KEY)


def HandleAudioDBAlbumResult(results):
    albums = []
    if 'album' in results and results['album']:
        localdescription = 'strDescription' + xbmc.getLanguage(xbmc.ISO_639_1).upper()
        for album in results['album']:
            if localdescription in album and album[localdescription]:
                Description = album.get(localdescription, "")
            elif 'strDescriptionEN' in album and album['strDescriptionEN']:
                Description = album['strDescriptionEN']
            elif 'strDescription' in album and album['strDescription']:
                Description = album['strDescription']
            else:
                Description = ""
            if 'strReview' in album and album['strReview']:
                Description += "[CR][CR][B]" + xbmc.getLocalizedString(185) + ":[/B][CR][CR]" + album['strReview']
            album = {'artist': album['strArtist'],
                     'Label2': album['strArtist'],
                     'mbid': album['strMusicBrainzID'],
                     'id': album['idAlbum'],
                     'audiodbid': album['idAlbum'],
                     'Description': Description,
                     'Path': "",
                     'Plot': Description,
                     'Genre': album['strGenre'],
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
        albums = CompareAlbumWithLibrary(albums)
    else:
        log("Error when handling HandleAudioDBAlbumResult results")
    return albums


def HandleAudioDBTrackResult(results):
    tracks = []
    if 'track' in results and results['track']:
        for track in results['track']:
            if 'strMusicVid' in track and track['strMusicVid']:
                Thumb = "http://i.ytimg.com/vi/" + ExtractYoutubeID(track.get('strMusicVid', '')) + "/0.jpg"
                Path = ConvertYoutubeURL(track['strMusicVid'])
            else:
                Thumb = ""
                Path = ""
            track = {'Track': track['strTrack'],
                     'Artist': track['strArtist'],
                     'mbid': track['strMusicBrainzID'],
                     'Album': track['strAlbum'],
                     'Thumb': Thumb,
                     'Path': Path,
                     'Label': track['strTrack']}
            tracks.append(track)
    else:
        log("Error when handling HandleAudioDBTrackResult results")
        prettyprint(results)
    return tracks


def HandleAudioDBMusicVideoResult(results):
    mvids = []
    if 'mvids' in results and results['mvids']:
        for mvid in results['mvids']:
            mvid = {'Track': mvid['strTrack'],
                    'Description': mvid['strDescriptionEN'],
                    'id': mvid['idTrack'],
                    'Thumb': "http://i.ytimg.com/vi/" + ExtractYoutubeID(mvid.get('strMusicVid', '')) + "/0.jpg",
                    'Path': ConvertYoutubeURL(mvid['strMusicVid']),
                    'Label': mvid['strTrack']}
            mvids.append(mvid)
    else:
        log("Error when handling HandleAudioDBMusicVideoResult results")
    return mvids


def GetExtendedAudioDBInfo(results):
    artists = []
    if 'artists' in results and results['artists']:
        for artist in results['artists']:
            localbio = 'strBiography' + ADDON.getSetting("LanguageID").upper()
            if localbio in artist and artist[localbio]:
                Description = fetch(artist, localbio)
            elif 'strBiographyEN' in artist and artist['strBiographyEN']:
                Description = fetch(artist, 'strBiographyEN')
            elif 'strBiography' in artist and artist['strBiography']:
                Description = fetch(artist, 'strBiography')
            else:
                Description = ""
            if 'strArtistBanner' in artist and artist['strArtistBanner']:
                banner = artist['strArtistBanner']
            else:
                banner = ""
            if 'strReview' in artist and artist['strReview']:
                Description += "[CR]" + fetch(artist, 'strReview')
            artist = {'artist': fetch(artist, 'strArtist'),
                      'mbid': fetch(artist, 'strMusicBrainzID'),
                      'Banner': banner,
                      'Logo': fetch(artist, 'strArtistLogo'),
                      'Fanart': fetch(artist, 'strArtistFanart'),
                      'Fanart2': fetch(artist, 'strArtistFanart2'),
                      'Fanart3': fetch(artist, 'strArtistFanart3'),
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
                      'audiodbid': fetch(artist, 'idArtist'),
                      'Description': Description,
                      'Plot': Description,
                      'Path': "",
                      'Genre': fetch(artist, 'strGenre'),
                      'Style': fetch(artist, 'strStyle'),
                      'Thumb': fetch(artist, 'strArtistThumb'),
                      'Art(Thumb)': fetch(artist, 'strArtistThumb'),
                      'Members': fetch(artist, 'intMembers')}
            artists.append(artist)
    else:
        log("Error when handling GetExtendedAudioDBInfo results")
    if artists:
        return artists[0]
    else:
        return {}


def GetDiscography(search_string):
    url = 'searchalbum.php?s=%s' % (url_quote(search_string))
    results = Get_JSON_response(BASE_URL + url)
    return HandleAudioDBAlbumResult(results)


def GetArtistDetails(search_string):
    url = 'search.php?s=%s' % (url_quote(search_string))
    results = Get_JSON_response(BASE_URL + url)
    return GetExtendedAudioDBInfo(results)


def GetMostLovedTracks(search_string="", mbid=""):
    if mbid:
        pass
    else:
        url = 'track-top10.php?s=%s' % (url_quote(search_string))
    log("GetMostLoveTracks URL:" + url)
    results = Get_JSON_response(BASE_URL + url)
    return HandleAudioDBTrackResult(results)


def GetAlbumDetails(audiodbid="", mbid=""):
    if audiodbid:
        url = 'album.php?m=%s' % (audiodbid)
    elif mbid:
        url = 'album-mb.php?i=%s' % (mbid)
    results = Get_JSON_response(BASE_URL + url)
    return HandleAudioDBAlbumResult(results)[0]


def GetMusicVideos(audiodbid):
    if audiodbid:
        url = 'mvid.php?i=%s' % (audiodbid)
        results = Get_JSON_response(BASE_URL + url)
        return HandleAudioDBMusicVideoResult(results)
    else:
        return []


def GetTrackDetails(audiodbid):
    if audiodbid:
        url = 'track.php?m=%s' % (audiodbid)
        results = Get_JSON_response(BASE_URL + url)
        return HandleAudioDBTrackResult(results)
    else:
        return []
