#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    musicartwork.py
    Get metadata for music
'''

from utils import log_msg, extend_dict, ADDON_ID, strip_newlines, download_artwork
from mbrainz import MusicBrainz
from lastfm import LastFM
from theaudiodb import TheAudioDb
import os
import xbmc
import xbmcvfs
import xbmcgui
from urllib import quote_plus
from difflib import SequenceMatcher as SM
from simplecache import use_cache


class MusicArtwork(object):
    '''get metadata and artwork for music'''

    def __init__(self, metadatautils=None):
        '''Initialize - optionaly provide our base MetadataUtils class'''
        if not metadatautils:
            from metadatautils import MetadataUtils
            self.metadatautils = MetadataUtils
        else:
            self.metadatautils = metadatautils
        self.cache = self.metadatautils.cache
        self.lastfm = LastFM()
        self.mbrainz = MusicBrainz()
        self.audiodb = TheAudioDb()

    def get_music_artwork(self, artist, album, track, disc, ignore_cache=False, flush_cache=False, manual=False):
        '''
            get music metadata by providing artist and/or album/track
            returns combined result of artist and album metadata
        '''
        if artist == track or album == track:
            track = ""
        artists = self.get_all_artists(artist, track)
        album = self.get_clean_title(album)
        track = self.get_clean_title(track)

        # retrieve artist and album details
        artist_details = self.get_artists_metadata(artists, album, track,
                                                   ignore_cache=ignore_cache, flush_cache=flush_cache, manual=manual)
        album_artist = artist_details.get("albumartist", artist)
        if album or track:
            album_details = self.get_album_metadata(album_artist, album, track, disc,
                                                    ignore_cache=ignore_cache, flush_cache=flush_cache, manual=manual)
        else:
            album_details = {"art": {}}

        # combine artist details and album details
        details = extend_dict(album_details, artist_details)

        # combine artist plot and album plot as extended plot
        if artist_details.get("plot") and album_details.get("plot"):
            details["extendedplot"] = "%s  --  %s" % (album_details["plot"], artist_details["plot"])
        else:
            details["extendedplot"] = details.get("plot", "")

        # append track title to results
        if track:
            details["title"] = track

        # return the endresult
        return details

    def music_artwork_options(self, artist, album, track, disc):
        '''show options for music artwork'''
        options = []
        options.append(self.metadatautils.addon.getLocalizedString(32028))  # Refresh item (auto lookup)
        options.append(self.metadatautils.addon.getLocalizedString(32036))  # Choose art
        options.append(self.metadatautils.addon.getLocalizedString(32034))  # Open addon settings
        header = self.metadatautils.addon.getLocalizedString(32015)
        dialog = xbmcgui.Dialog()
        ret = dialog.select(header, options)
        del dialog
        if ret == 0:
            # Refresh item (auto lookup)
            self.get_music_artwork(artist, album, track, disc, ignore_cache=True)
        elif ret == 1:
            # Choose art
            self.get_music_artwork(artist, album, track, disc, ignore_cache=True, manual=True)
        elif ret == 2:
            # Open addon settings
            xbmc.executebuiltin("Addon.OpenSettings(%s)" % ADDON_ID)

    def get_artists_metadata(self, artists, album, track, ignore_cache=False, flush_cache=False, manual=False):
        '''collect artist metadata for all artists'''
        artist_details = {"art": {}}
        # for multi artist songs/albums we grab details from all artists
        if len(artists) == 1:
            # single artist
            artist_details = self.get_artist_metadata(
                artists[0], album, track, ignore_cache=ignore_cache, flush_cache=flush_cache, manual=manual)
            artist_details["albumartist"] = artists[0]
        else:
            # multi-artist track
            # The first artist with details is considered the main artist
            # all others are assumed as featuring artists
            artist_details = {"art": {}}
            feat_artist_details = {"art": {}}
            for artist in artists:
                if not (artist_details.get("plot") or artist_details.get("art")):
                    # get main artist details
                    artist_details["albumartist"] = artist
                    artist_details = self.get_artist_metadata(
                        artist, album, track, ignore_cache=ignore_cache, manual=manual)
                else:
                    # assume featuring artist
                    feat_artist_details = extend_dict(
                        feat_artist_details, self.get_artist_metadata(
                            artist, album, track, ignore_cache=ignore_cache, manual=manual))

            # combined images to use as multiimage (for all artists)
            # append featuring artist details
            for arttype in ["banners", "fanarts", "clearlogos", "thumbs"]:
                art = artist_details["art"].get(arttype, [])
                art += feat_artist_details["art"].get(arttype, [])
                if art:
                    # use the extrafanart plugin entry to display multi images
                    artist_details["art"][arttype] = "plugin://script.skin.helper.service/"\
                        "?action=extrafanart&fanarts=%s" % quote_plus(repr(art))
                    # also set extrafanart path
                    if arttype == "fanarts":
                        artist_details["art"]["extrafanart"] = artist_details["art"][arttype]
        # return the result
        return artist_details

    # pylint: disable-msg=too-many-local-variables
    def get_artist_metadata(self, artist, album, track, ignore_cache=False, flush_cache=False, manual=False):
        '''collect artist metadata for given artist'''
        details = {"art": {}}
        cache_str = "music_artwork.artist.%s" % artist.lower()
        # retrieve details from cache
        cache = self.metadatautils.cache.get(cache_str)
        if not cache and flush_cache:
            # nothing to do - just return empty results
            return details
        elif cache and flush_cache:
            # only update kodi metadata for updated counts etc
            details = extend_dict(self.get_artist_kodi_metadata(artist), cache)
        elif cache and not ignore_cache:
            # we have a valid cache - return that
            details = cache
        elif cache and manual:
            # user wants to manually override the artwork in the cache
            details = self.manual_set_music_artwork(cache, "artist")
        else:
            # nothing in cache - start metadata retrieval
            log_msg("get_artist_metadata --> artist: %s - album: %s - track: %s" % (artist, album, track))
            details["cachestr"] = cache_str
            local_path = ""
            local_path_custom = ""
            # get metadata from kodi db
            details = extend_dict(details, self.get_artist_kodi_metadata(artist))
            # get artwork from songlevel path
            if details.get("diskpath") and self.metadatautils.addon.getSetting("music_art_musicfolders") == "true":
                details["art"] = extend_dict(details["art"], self.lookup_artistart_in_folder(details["diskpath"]))
                local_path = details["diskpath"]
            # get artwork from custom folder
            if self.metadatautils.addon.getSetting("music_art_custom") == "true":
                custom_path = self.metadatautils.addon.getSetting("music_art_custom_path").decode("utf-8")
                if custom_path:
                    diskpath = self.get_customfolder_path(custom_path, artist)
                    log_msg("custom path on disk for artist: %s --> %s" % (artist, diskpath))
                    if diskpath:
                        details["art"] = extend_dict(details["art"], self.lookup_artistart_in_folder(diskpath))
                        local_path_custom = diskpath
                        details["customartpath"] = diskpath
            # lookup online metadata
            if self.metadatautils.addon.getSetting("music_art_scraper") == "true":
                if not album and not track:
                    album = details.get("ref_album")
                    track = details.get("ref_track")
                # prefer the musicbrainzid that is already in the kodi database - only perform lookup if missing
                mb_artistid = details.get("musicbrainzartistid", self.get_mb_artist_id(artist, album, track))
                details["musicbrainzartistid"] = mb_artistid
                if mb_artistid:
                    # get artwork from fanarttv
                    if self.metadatautils.addon.getSetting("music_art_scraper_fatv") == "true":
                        details["art"] = extend_dict(details["art"], self.metadatautils.fanarttv.artist(mb_artistid))
                    # get metadata from theaudiodb
                    if self.metadatautils.addon.getSetting("music_art_scraper_adb") == "true":
                        details = extend_dict(details, self.audiodb.artist_info(mb_artistid))
                    # get metadata from lastfm
                    if self.metadatautils.addon.getSetting("music_art_scraper_lfm") == "true":
                        details = extend_dict(details, self.lastfm.artist_info(mb_artistid))
                    # download artwork to music folder
                    if local_path and self.metadatautils.addon.getSetting("music_art_download") == "true":
                        details["art"] = download_artwork(local_path, details["art"])
                    # download artwork to custom folder
                    if local_path_custom and self.metadatautils.addon.getSetting("music_art_download_custom") == "true":
                        details["art"] = download_artwork(local_path_custom, details["art"])
                    # fix extrafanart
                    if details["art"].get("fanarts"):
                        for count, item in enumerate(details["art"]["fanarts"]):
                            details["art"]["fanart.%s" % count] = item
                        if not details["art"].get("extrafanart") and len(details["art"]["fanarts"]) > 1:
                            details["art"]["extrafanart"] = "plugin://script.skin.helper.service/"\
                                "?action=extrafanart&fanarts=%s" % quote_plus(repr(details["art"]["fanarts"]))
                    # multi-image path for all images for each arttype
                    for arttype in ["banners", "clearlogos", "thumbs"]:
                        art = details["art"].get(arttype, [])
                        if len(art) > 1:
                            # use the extrafanart plugin entry to display multi images
                            details["art"][arttype] = "plugin://script.skin.helper.service/"\
                                "?action=extrafanart&fanarts=%s" % quote_plus(repr(art))
        # set default details
        if not details.get("artist"):
            details["artist"] = artist
        if details["art"].get("thumb"):
            details["art"]["artistthumb"] = details["art"]["thumb"]

        # always store results in cache and return results
        self.metadatautils.cache.set(cache_str, details)
        return details

    def get_album_metadata(self, artist, album, track, disc, ignore_cache=False, flush_cache=False, manual=False):
        '''collect all album metadata'''
        cache_str = "music_artwork.album.%s.%s.%s" % (artist.lower(), album.lower(), disc.lower())
        if not album:
            cache_str = "music_artwork.album.%s.%s" % (artist.lower(), track.lower())
        details = {"art": {}}
        details["cachestr"] = cache_str

        # retrieve details from cache
        cache = self.metadatautils.cache.get(cache_str)
        if not cache and flush_cache:
            # nothing to do - just return empty results
            return details
        elif cache and flush_cache:
            # only update kodi metadata for updated counts etc
            details = extend_dict(self.get_album_kodi_metadata(artist, album, track, disc), cache)
        elif cache and not ignore_cache:
            # we have a valid cache - return that
            details = cache
        elif cache and manual:
            # user wants to manually override the artwork in the cache
            details = self.manual_set_music_artwork(cache, "album")
        else:
            # nothing in cache - start metadata retrieval
            local_path = ""
            local_path_custom = ""
            # get metadata from kodi db
            details = extend_dict(details, self.get_album_kodi_metadata(artist, album, track, disc))
            # get artwork from songlevel path
            if details.get("diskpath") and self.metadatautils.addon.getSetting("music_art_musicfolders") == "true":
                details["art"] = extend_dict(details["art"], self.lookup_albumart_in_folder(details["diskpath"]))
                local_path = details["diskpath"]
            # get artwork from custom folder
            if self.metadatautils.addon.getSetting("music_art_custom") == "true":
                custom_path = self.metadatautils.addon.getSetting("music_art_custom_path").decode("utf-8")
                if custom_path:
                    diskpath = self.get_custom_album_path(custom_path, artist, album, disc)
                    if diskpath:
                        details["art"] = extend_dict(details["art"], self.lookup_albumart_in_folder(diskpath))
                        local_path_custom = diskpath
                        details["customartpath"] = diskpath
            # lookup online metadata
            if self.metadatautils.addon.getSetting("music_art_scraper") == "true":
                # prefer the musicbrainzid that is already in the kodi database - only perform lookup if missing
                mb_albumid = details.get("musicbrainzalbumid")
                if not mb_albumid:
                    mb_albumid = self.get_mb_album_id(artist, album, track)
                if mb_albumid:
                    # get artwork from fanarttv
                    if self.metadatautils.addon.getSetting("music_art_scraper_fatv") == "true":
                        details["art"] = extend_dict(details["art"], self.metadatautils.fanarttv.album(mb_albumid))
                    # get metadata from theaudiodb
                    if self.metadatautils.addon.getSetting("music_art_scraper_adb") == "true":
                        details = extend_dict(details, self.audiodb.album_info(mb_albumid))
                    # get metadata from lastfm
                    if self.metadatautils.addon.getSetting("music_art_scraper_lfm") == "true":
                        details = extend_dict(details, self.lastfm.album_info(mb_albumid))
                    # metadata from musicbrainz
                    if not details.get("year") or not details.get("genre"):
                        details = extend_dict(details, self.mbrainz.get_albuminfo(mb_albumid))
                    # musicbrainz thumb as last resort
                    if not details["art"].get("thumb"):
                        details["art"]["thumb"] = self.mbrainz.get_albumthumb(mb_albumid)
                    # download artwork to music folder
                    if local_path and self.metadatautils.addon.getSetting("music_art_download") == "true":
                        details["art"] = download_artwork(local_path, details["art"])
                    # download artwork to custom folder
                    if local_path_custom and self.metadatautils.addon.getSetting("music_art_download_custom") == "true":
                        details["art"] = download_artwork(local_path_custom, details["art"])
        # set default details
        if not details.get("album") and details.get("title"):
            details["album"] = details["title"]
        if details["art"].get("thumb"):
            details["art"]["albumthumb"] = details["art"]["thumb"]

        # store results in cache and return results
        self.metadatautils.cache.set(cache_str, details)
        return details

    # pylint: enable-msg=too-many-local-variables

    def get_artist_kodi_metadata(self, artist):
        '''get artist details from the kodi database'''
        details = {}
        filters = [{"operator": "is", "field": "artist", "value": artist}]
        result = self.metadatautils.kodidb.artists(filters=filters, limits=(0, 1))
        if result:
            details = result[0]
            details["title"] = details["artist"]
            details["plot"] = strip_newlines(details["description"])
            if details["musicbrainzartistid"] and isinstance(details["musicbrainzartistid"], list):
                details["musicbrainzartistid"] = details["musicbrainzartistid"][0]
            filters = [{"artistid": details["artistid"]}]
            artist_albums = self.metadatautils.kodidb.albums(filters=filters)
            details["albums"] = []
            details["albumsartist"] = []
            details["albumscompilations"] = []
            details["tracks"] = []
            bullet = "•".decode("utf-8")
            details["albums.formatted"] = u""
            details["tracks.formatted"] = u""
            details["tracks.formatted2"] = u""
            details["albumsartist.formatted"] = u""
            details["albumscompilations.formatted"] = u""
            # enumerate albums for this artist
            for artist_album in artist_albums:
                details["albums"].append(artist_album["label"])
                details["albums.formatted"] += u"%s %s [CR]" % (bullet, artist_album["label"])
                if artist in artist_album["displayartist"]:
                    details["albumsartist"].append(artist_album["label"])
                    details["albumsartist.formatted"] += u"%s %s [CR]" % (bullet, artist_album["label"])
                else:
                    details["albumscompilations"].append(artist_album["label"])
                    details["albumscompilations.formatted"] += u"%s %s [CR]" % (bullet, artist_album["label"])
                # enumerate songs for this album
                filters = [{"albumid": artist_album["albumid"]}]
                album_tracks = self.metadatautils.kodidb.songs(filters=filters)
                if album_tracks:
                    # retrieve path on disk by selecting one song for this artist
                    if not details.get("ref_track") and not len(artist_album["artistid"]) > 1:
                        song_path = album_tracks[0]["file"]
                        details["diskpath"] = self.get_artistpath_by_songpath(song_path, artist)
                        details["ref_album"] = artist_album["title"]
                        details["ref_track"] = album_tracks[0]["title"]
                    for album_track in album_tracks:
                        details["tracks"].append(album_track["title"])
                        tr_title = album_track["title"]
                        if album_track["track"]:
                            tr_title = "%s. %s" % (album_track["track"], album_track["title"])
                        details["tracks.formatted"] += u"%s %s [CR]" % (bullet, tr_title)
                        duration = album_track["duration"]
                        total_seconds = int(duration)
                        minutes = total_seconds / 60
                        seconds = total_seconds - (minutes * 60)
                        duration = "%s:%s" % (minutes, str(seconds).zfill(2))
                        details["tracks.formatted2"] += u"%s %s (%s)[CR]" % (bullet, tr_title, duration)
            details["albumcount"] = len(details["albums"])
            details["albumsartistcount"] = len(details["albumsartist"])
            details["albumscompilationscount"] = len(details["albumscompilations"])
            # do not retrieve artwork from item as there's no way to write it back
            # and it will already be retrieved if user enables to get the artwork from the song path
        return details

    def get_album_kodi_metadata(self, artist, album, track, disc):
        '''get album details from the kodi database'''
        details = {}
        filters = [{"operator": "is", "field": "album", "value": album}]
        filters.append({"operator": "is", "field": "artist", "value": artist})
        if artist and track and not album:
            # get album by track
            result = self.metadatautils.kodidb.songs(filters=filters)
            for item in result:
                album = item["album"]
                break
        if artist and album:
            result = self.metadatautils.kodidb.albums(filters=filters)
            if result:
                details = result[0]
                details["plot"] = strip_newlines(details["description"])
                filters = [{"albumid": details["albumid"]}]
                album_tracks = self.metadatautils.kodidb.songs(filters=filters)
                details["tracks"] = []
                bullet = "•".decode("utf-8")
                details["tracks.formatted"] = u""
                details["tracks.formatted2"] = ""
                details["runtime"] = 0
                for item in album_tracks:
                    details["tracks"].append(item["title"])
                    details["tracks.formatted"] += u"%s %s [CR]" % (bullet, item["title"])
                    duration = item["duration"]
                    total_seconds = int(duration)
                    minutes = total_seconds / 60
                    seconds = total_seconds - (minutes * 60)
                    duration = "%s:%s" % (minutes, str(seconds).zfill(2))
                    details["runtime"] += item["duration"]
                    details["tracks.formatted2"] += u"%s %s (%s)[CR]" % (bullet, item["title"], duration)
                    if not details.get("diskpath"):
                        if not disc or item["disc"] == int(disc):
                            details["diskpath"] = self.get_albumpath_by_songpath(item["file"])
                details["art"] = {}
                details["songcount"] = len(album_tracks)
                # get album total duration pretty printed as mm:ss
                total_seconds = int(details["runtime"])
                minutes = total_seconds / 60
                seconds = total_seconds - (minutes * 60)
                details["duration"] = "%s:%s" % (minutes, str(seconds).zfill(2))
                # do not retrieve artwork from item as there's no way to write it back
                # and it will already be retrieved if user enables to get the artwork from the song path
        return details

    def get_mb_artist_id(self, artist, album, track):
        '''lookup musicbrainz artist id with query of artist and album/track'''
        artistid = self.mbrainz.get_artist_id(artist, album, track)
        if not artistid and self.metadatautils.addon.getSetting("music_art_scraper_lfm") == "true":
            artistid = self.lastfm.get_artist_id(artist, album, track)
        if not artistid and self.metadatautils.addon.getSetting("music_art_scraper_adb") == "true":
            artistid = self.audiodb.get_artist_id(artist, album, track)
        return artistid

    def get_mb_album_id(self, artist, album, track):
        '''lookup musicbrainz album id with query of artist and album/track'''
        albumid = self.mbrainz.get_album_id(artist, album, track)
        if not albumid and self.metadatautils.addon.getSetting("music_art_scraper_lfm") == "true":
            albumid = self.lastfm.get_album_id(artist, album, track)
        if not albumid and self.metadatautils.addon.getSetting("music_art_scraper_adb") == "true":
            albumid = self.audiodb.get_album_id(artist, album, track)
        return albumid

    def manual_set_music_artwork(self, details, mediatype):
        '''manual override artwork options'''
        from utils import manual_set_artwork
        if mediatype == "artist" and "artist" in details:
            header = "%s: %s" % (xbmc.getLocalizedString(13511), details["artist"])
        else:
            header = "%s: %s" % (xbmc.getLocalizedString(13511), xbmc.getLocalizedString(558))
        changemade, artwork = manual_set_artwork(details["art"], mediatype, header)
        # save results if any changes made
        if changemade:
            details["art"] = artwork
            refresh_needed = False
            download_art = self.metadatautils.addon.getSetting("music_art_download") == "true"
            download_art_custom = self.metadatautils.addon.getSetting("music_art_download_custom") == "true"
            # download artwork to music folder if needed
            if details.get("diskpath") and download_art:
                details["art"] = download_artwork(details["diskpath"], details["art"])
                refresh_needed = True
            # download artwork to custom folder if needed
            if details.get("customartpath") and download_art_custom:
                details["art"] = download_artwork(details["customartpath"], details["art"])
                refresh_needed = True
            # reload skin to make sure new artwork is visible
            if refresh_needed:
                xbmc.sleep(500)
                xbmc.executebuiltin("ReloadSkin()")
        # return endresult
        return details

    @staticmethod
    def get_artistpath_by_songpath(songpath, artist):
        '''get the artist path on disk by listing the song's path'''
        result = ""
        if "\\" in songpath:
            delim = "\\"
        else:
            delim = "/"
        # just move up the directory tree (max 3 levels) untill we find the directory
        for trypath in [songpath.rsplit(delim, 2)[0] + delim,
                        songpath.rsplit(delim, 3)[0] + delim, songpath.rsplit(delim, 1)[0] + delim]:
            if trypath.split(delim)[-2].lower() == artist.lower():
                result = trypath
                break
        return result

    @staticmethod
    def get_albumpath_by_songpath(songpath):
        '''get the album path on disk by listing the song's path'''
        if "\\" in songpath:
            delim = "\\"
        else:
            delim = "/"
        return songpath.rsplit(delim, 1)[0] + delim

    @staticmethod
    def lookup_artistart_in_folder(folderpath):
        '''lookup artwork in given folder'''
        artwork = {}
        files = xbmcvfs.listdir(folderpath)[1]
        for item in files:
            item = item.decode("utf-8")
            if item in ["banner.jpg", "clearart.png", "poster.png", "fanart.jpg", "landscape.jpg"]:
                key = item.split(".")[0]
                artwork[key] = folderpath + item
            elif item == "logo.png":
                artwork["clearlogo"] = folderpath + item
            elif item == "folder.jpg":
                artwork["thumb"] = folderpath + item
        # extrafanarts
        efa_path = folderpath + "extrafanart/"
        if xbmcvfs.exists(efa_path):
            files = xbmcvfs.listdir(efa_path)[1]
            artwork["fanarts"] = []
            if files:
                artwork["extrafanart"] = efa_path
                for item in files:
                    item = efa_path + item.decode("utf-8")
                    artwork["fanarts"].append(item)
        return artwork

    @staticmethod
    def lookup_albumart_in_folder(folderpath):
        '''lookup artwork in given folder'''
        artwork = {}
        files = xbmcvfs.listdir(folderpath)[1]
        for item in files:
            item = item.decode("utf-8")
            if item in ["cdart.png", "disc.png"]:
                artwork["discart"] = folderpath + item
            elif item == "folder.jpg":
                artwork["thumb"] = folderpath + item
        return artwork

    def get_custom_album_path(self, custom_path, artist, album, disc):
        '''try to locate the custom path for the album'''
        artist_path = self.get_customfolder_path(custom_path, artist)
        album_path = ""
        if artist_path:
            album_path = self.get_customfolder_path(artist_path, album)
            if album_path and disc:
                if "\\" in album_path:
                    delim = "\\"
                else:
                    delim = "/"
                dirs = xbmcvfs.listdir(album_path)[0]
                for directory in dirs:
                    directory = directory.decode("utf-8")
                    if disc in directory:
                        return os.path.join(album_path, directory) + delim
        return album_path

    def get_customfolder_path(self, customfolder, foldername, sublevel=False):
        '''search recursively (max 2 levels) for a specific folder'''
        cachestr = "customfolder_path.%s.%s" % (customfolder, foldername)
        folder_path = self.cache.get(cachestr)
        if not folder_path:
            if "\\" in customfolder:
                delim = "\\"
            else:
                delim = "/"
            dirs = xbmcvfs.listdir(customfolder)[0]
            for strictness in [1, 0.95, 0.9, 0.8]:
                for directory in dirs:
                    directory = directory.decode("utf-8")
                    curpath = os.path.join(customfolder, directory) + delim
                    match = SM(None, foldername.lower(), directory.lower()).ratio()
                    if match >= strictness:
                        folder_path = curpath
                    elif not sublevel:
                        # check if our requested path is in a sublevel of the current path
                        # restrict the number of sublevels to just one for now for performance reasons
                        folder_path = self.get_customfolder_path(curpath, foldername, True)
                    if folder_path:
                        break
                if folder_path:
                    break
            if not sublevel:
                self.cache.set(cachestr, folder_path)
        return folder_path

    @staticmethod
    def get_clean_title(title):
        '''strip all unwanted characters from track name'''
        title = title.split("/")[0]
        title = title.split("(")[0]
        title = title.split("[")[0]
        title = title.split("ft.")[0]
        title = title.split("Ft.")[0]
        title = title.split("Feat.")[0]
        title = title.split("Featuring")[0]
        title = title.split("featuring")[0]
        return title.strip()

    @staticmethod
    def get_all_artists(artist, track):
        '''extract multiple artists from both artist and track string'''
        artists = []
        feat_artists = []

        # fix for band names which actually contain the kodi splitter (slash) in their name...
        specials = ["AC/DC"]  # to be completed with more artists
        for special in specials:
            if special in artist:
                artist = artist.replace(special, special.replace("/", ""))

        for splitter in ["ft.", "feat.", "featuring", "Ft.", "Feat.", "Featuring"]:
            # replace splitter by kodi default splitter for easier split all later
            artist = artist.replace(splitter, u"/")

            # extract any featuring artists from trackname
            if splitter in track:
                track_parts = track.split(splitter)
                if len(track_parts) > 1:
                    feat_artist = track_parts[1].replace(")", "").replace("(", "").strip()
                    feat_artists.append(feat_artist)

        # break all artists string into list
        all_artists = artist.split("/") + feat_artists
        for item in all_artists:
            item = item.strip()
            if item not in artists:
                artists.append(item)
            # & can be a both a splitter or part of artist name
            for item2 in item.split("&"):
                item2 = item2.strip()
                if item2 not in artists:
                    artists.append(item2)
        return artists
