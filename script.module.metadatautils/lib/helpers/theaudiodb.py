#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    theaudiodb.py
    Get metadata from theaudiodb
'''

from utils import get_json, strip_newlines, KODI_LANGUAGE, get_compare_string
from simplecache import use_cache
import xbmcvfs


class TheAudioDb(object):
    '''get metadata from the audiodb'''
    api_key = "12376f5352254d85853987"
    ignore_cache = False

    def __init__(self, simplecache=None):
        '''Initialize - optionaly provide simplecache object'''
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache

    def search(self, artist, album, track):
        '''get musicbrainz id by query of artist, album and/or track'''
        artistid = ""
        albumid = ""
        artist = artist.lower()
        params = {'s': artist, 'a': album}
        data = self.get_data("searchalbum.php", params)
        if data and data.get("album") and len(data.get("album")) > 0:
            adbdetails = data["album"][0]
            # safety check - only allow exact artist match
            foundartist = adbdetails.get("strArtist", "").lower()
            if foundartist and get_compare_string(foundartist) == get_compare_string(artist):
                albumid = adbdetails.get("strMusicBrainzID", "")
                artistid = adbdetails.get("strMusicBrainzArtistID", "")
        if (not artistid or not albumid) and artist and track:
            params = {'s': artist, 't': track}
            data = self.get_data("searchtrack.php", params)
            if data and data.get("track") and len(data.get("track")) > 0:
                adbdetails = data["track"][0]
                # safety check - only allow exact artist match
                foundartist = adbdetails.get("strArtist", "").lower()
                if foundartist and get_compare_string(foundartist) == get_compare_string(artist):
                    albumid = adbdetails.get("strMusicBrainzID", "")
                    artistid = adbdetails.get("strMusicBrainzArtistID", "")
        return (artistid, albumid)

    def get_artist_id(self, artist, album, track):
        '''get musicbrainz id by query of artist, album and/or track'''
        return self.search(artist, album, track)[0]

    def get_album_id(self, artist, album, track):
        '''get musicbrainz id by query of artist, album and/or track'''
        return self.search(artist, album, track)[1]

    def artist_info(self, artist_id):
        '''get artist metadata by musicbrainz id'''
        details = {"art": {}}
        data = self.get_data("/artist-mb.php", {'i': artist_id})
        if data and data.get("artists"):
            adbdetails = data["artists"][0]
            if adbdetails.get("strArtistBanner") and xbmcvfs.exists(adbdetails.get("strArtistBanner")):
                details["art"]["banner"] = adbdetails.get("strArtistBanner")
                details["art"]["banners"] = [adbdetails.get("strArtistBanner")]
            details["art"]["fanarts"] = []
            if adbdetails.get("strArtistFanart") and xbmcvfs.exists(adbdetails.get("strArtistFanart")):
                details["art"]["fanart"] = adbdetails.get("strArtistFanart")
                details["art"]["fanarts"].append(adbdetails.get("strArtistFanart"))
            if adbdetails.get("strArtistFanart2") and xbmcvfs.exists(adbdetails.get("strArtistFanart2")):
                details["art"]["fanarts"].append(adbdetails.get("strArtistFanart2"))
            if adbdetails.get("strArtistFanart3") and xbmcvfs.exists(adbdetails.get("strArtistFanart3")):
                details["art"]["fanarts"].append(adbdetails.get("strArtistFanart3"))
            if adbdetails.get("strArtistLogo") and xbmcvfs.exists(adbdetails.get("strArtistLogo")):
                details["art"]["clearlogo"] = adbdetails.get("strArtistLogo")
                details["art"]["clearlogos"] = [adbdetails.get("strArtistLogo")]
            if adbdetails.get("strArtistThumb") and xbmcvfs.exists(adbdetails.get("strArtistThumb")):
                details["art"]["thumb"] = adbdetails["strArtistThumb"]
                details["art"]["thumbs"] = [adbdetails["strArtistThumb"]]
            if adbdetails.get("strBiography" + KODI_LANGUAGE.upper()):
                details["plot"] = adbdetails["strBiography" + KODI_LANGUAGE.upper()]
            if adbdetails.get("strBiographyEN") and not details.get("plot"):
                details["plot"] = adbdetails.get("strBiographyEN")
            if details.get("plot"):
                details["plot"] = strip_newlines(details["plot"])
            if adbdetails.get("strArtistAlternate"):
                details["alternamename"] = adbdetails["strArtistAlternate"]
            if adbdetails.get("intFormedYear"):
                details["formed"] = adbdetails["intFormedYear"]
            if adbdetails.get("intBornYear"):
                details["born"] = adbdetails["intBornYear"]
            if adbdetails.get("intDiedYear"):
                details["died"] = adbdetails["intDiedYear"]
            if adbdetails.get("strDisbanded"):
                details["disbanded"] = adbdetails["strDisbanded"]
            if adbdetails.get("strStyle"):
                details["style"] = adbdetails["strStyle"].split("/")
            if adbdetails.get("strGenre"):
                details["genre"] = adbdetails["strGenre"].split("/")
            if adbdetails.get("strMood"):
                details["mood"] = adbdetails["strMood"].split("/")
            if adbdetails.get("strWebsite"):
                details["homepage"] = adbdetails["strWebsite"]
            if adbdetails.get("strFacebook"):
                details["facebook"] = adbdetails["strFacebook"]
            if adbdetails.get("strTwitter"):
                details["twitter"] = adbdetails["strTwitter"]
            if adbdetails.get("strGender"):
                details["gender"] = adbdetails["strGender"]
            if adbdetails.get("intMembers"):
                details["members"] = adbdetails["intMembers"]
            if adbdetails.get("strCountry"):
                details["country"] = adbdetails["strCountry"].split(", ")
        return details

    def album_info(self, album_id):
        '''get album metadata by musicbrainz id'''
        details = {"art": {}}
        data = self.get_data("/album-mb.php", {'i': album_id})
        if data and data.get("album"):
            adbdetails = data["album"][0]
            if adbdetails.get("strAlbumThumb") and xbmcvfs.exists(adbdetails.get("strAlbumThumb")):
                details["art"]["thumb"] = adbdetails.get("strAlbumThumb")
                details["art"]["thumbs"] = [adbdetails.get("strAlbumThumb")]
            if adbdetails.get("strAlbumCDart") and xbmcvfs.exists(adbdetails.get("strAlbumCDart")):
                details["art"]["discart"] = adbdetails.get("strAlbumCDart")
                details["art"]["discarts"] = [adbdetails.get("strAlbumCDart")]
            if adbdetails.get("strDescription%s" % KODI_LANGUAGE.upper()):
                details["plot"] = adbdetails.get("strDescription%s" % KODI_LANGUAGE.upper())
            if not details.get("plot") and adbdetails.get("strDescriptionEN"):
                details["plot"] = adbdetails.get("strDescriptionEN")
            if details.get("plot"):
                details["plot"] = strip_newlines(details["plot"])
            if adbdetails.get("strGenre"):
                details["genre"] = adbdetails["strGenre"].split("/")
            if adbdetails.get("strStyle"):
                details["style"] = adbdetails["strStyle"].split("/")
            if adbdetails.get("strMood"):
                details["mood"] = adbdetails["strMood"].split("/")
            if adbdetails.get("intYearReleased"):
                details["year"] = adbdetails["intYearReleased"]
            if adbdetails.get("intScore"):
                details["rating"] = adbdetails["intScore"]
            if adbdetails.get("strAlbum"):
                details["title"] = adbdetails["strAlbum"]
        return details

    @use_cache(60)
    def get_data(self, endpoint, params):
        '''helper method to get data from theaudiodb json API'''
        endpoint = 'http://www.theaudiodb.com/api/v1/json/%s/%s' % (self.api_key, endpoint)
        data = get_json(endpoint, params)
        if data:
            return data
        else:
            return {}
