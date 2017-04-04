#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    Provides all kind of mediainfo for kodi media, returned as dict with details
'''

from helpers.animatedart import AnimatedArt
from helpers.tmdb import Tmdb
from helpers.omdb import Omdb
from helpers.imdb import Imdb
from helpers.google import GoogleImages
from helpers.channellogos import ChannelLogos
from helpers.fanarttv import FanartTv
from helpers.kodidb import KodiDb
import helpers.kodi_constants as kodi_constants
from helpers.pvrartwork import PvrArtwork
from helpers.studiologos import StudioLogos
from helpers.musicartwork import MusicArtwork
from helpers.utils import log_msg, ADDON_ID
from helpers.utils import get_clean_image as _get_clean_image
from helpers.utils import extend_dict as _extend_dict
from helpers.utils import get_duration as _get_duration
from helpers.utils import detect_plugin_content as _detect_plugin_content
from helpers.utils import process_method_on_list as _process_method_on_list
from simplecache import use_cache, SimpleCache
from thetvdb import TheTvDb
import xbmcaddon
import xbmcvfs


class MetadataUtils(object):
    '''
        Provides all kind of mediainfo for kodi media, returned as dict with details
    '''
    close_called = False

    def __init__(self):
        '''Initialize and load all our helpers'''
        self._studiologos_path = ""
        self.cache = SimpleCache()
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.kodidb = KodiDb()
        self.omdb = Omdb(self.cache)
        self.tmdb = Tmdb(self.cache)
        self.channellogos = ChannelLogos(self.kodidb)
        self.fanarttv = FanartTv(self.cache)
        self.imdb = Imdb(self.cache)
        self.google = GoogleImages(self.cache)
        self.studiologos = StudioLogos(self.cache)
        self.animatedart = AnimatedArt(self.cache, self.kodidb)
        self.thetvdb = TheTvDb()
        self.musicart = MusicArtwork(self)
        self.pvrart = PvrArtwork(self)
        log_msg("Initialized")

    def close(self):
        '''Cleanup instances'''
        self.close_called = True
        self.cache.close()
        self.addon = None
        del self.addon
        del self.kodidb
        del self.omdb
        del self.tmdb
        del self.channellogos
        del self.fanarttv
        del self.imdb
        del self.google
        del self.studiologos
        del self.animatedart
        del self.thetvdb
        del self.musicart
        del self.pvrart
        log_msg("Exited")

    def __del__(self):
        '''make sure close is called'''
        if not self.close_called:
            self.close()

    @use_cache(14)
    def get_extrafanart(self, file_path):
        '''helper to retrieve the extrafanart path for a kodi media item'''
        from helpers.extrafanart import get_extrafanart
        return get_extrafanart(file_path)

    def get_music_artwork(self, artist, album="", track="", disc="", ignore_cache=False, flush_cache=False):
        '''method to get music artwork for the goven artist/album/song'''
        return self.musicart.get_music_artwork(
            artist, album, track, disc, ignore_cache=ignore_cache, flush_cache=flush_cache)

    def music_artwork_options(self, artist, album="", track="", disc=""):
        '''options for music metadata for specific item'''
        return self.musicart.music_artwork_options(artist, album, track, disc)

    @use_cache(14)
    def get_extended_artwork(self, imdb_id="", tvdb_id="", tmdb_id="", media_type=""):
        '''get extended artwork for the given imdbid or tvdbid'''
        from urllib import quote_plus
        result = {"art": {}}
        if "movie" in media_type and tmdb_id:
            result["art"] = self.fanarttv.movie(tmdb_id)
        elif "movie" in media_type and imdb_id:
            result["art"] = self.fanarttv.movie(imdb_id)
        elif media_type in ["tvshow", "tvshows", "seasons", "episodes"]:
            if not tvdb_id:
                if imdb_id and not imdb_id.startswith("tt"):
                    tvdb_id = imdb_id
                elif imdb_id:
                    tvdb_id = self.thetvdb.get_series_by_imdb_id(imdb_id).get("tvdb_id")
            if tvdb_id:
                result["art"] = self.fanarttv.tvshow(tvdb_id)
        # add additional art with special path
        for arttype in ["fanarts", "posters", "clearlogos", "banners"]:
            if result["art"].get(arttype):
                result["art"][arttype] = "plugin://script.skin.helper.service/"\
                    "?action=extrafanart&fanarts=%s" % quote_plus(repr(result["art"][arttype]))
        return result

    @use_cache(14)
    def get_tmdb_details(self, imdb_id="", tvdb_id="", title="", year="", media_type="",
                         preftype="", manual_select=False, ignore_cache=False):
        '''returns details from tmdb'''
        result = {}
        if imdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                imdb_id, "imdb_id")
        elif tvdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                tvdb_id, "tvdb_id")
        elif title and media_type in ["movies", "setmovies", "movie"]:
            result = self.tmdb.search_movie(
                title, year, manual_select=manual_select)
        elif title and media_type in ["tvshows", "tvshow"]:
            result = self.tmdb.search_tvshow(
                title, year, manual_select=manual_select)
        elif title:
            result = self.tmdb.search_video(
                title, year, preftype=preftype, manual_select=manual_select)
        if result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(self.get_duration(result["runtime"]))
        return result

    def get_moviesetdetails(self, title, set_id):
        '''get a nicely formatted dict of the movieset details which we can for example set as window props'''
        # get details from tmdb
        from helpers.moviesetdetails import get_moviesetdetails
        return get_moviesetdetails(self, title, set_id)

    @use_cache(14)
    def get_streamdetails(self, db_id, media_type, ignore_cache=False):
        '''get a nicely formatted dict of the streamdetails '''
        from helpers.streamdetails import get_streamdetails
        return get_streamdetails(self.kodidb, db_id, media_type)

    def get_pvr_artwork(self, title, channel="", genre="", manual_select=False, ignore_cache=False):
        '''get artwork and mediadetails for PVR entries'''
        return self.pvrart.get_pvr_artwork(
            title, channel, genre, manual_select=manual_select, ignore_cache=ignore_cache)

    def pvr_artwork_options(self, title, channel="", genre=""):
        '''options for pvr metadata for specific item'''
        return self.pvrart.pvr_artwork_options(title, channel, genre)

    @use_cache(14)
    def get_channellogo(self, channelname):
        '''get channellogo for the given channel name'''
        return self.channellogos.get_channellogo(channelname)

    def get_studio_logo(self, studio):
        '''get studio logo for the given studio'''
        # dont use cache at this level because of changing logospath
        return self.studiologos.get_studio_logo(studio, self.studiologos_path)

    @property
    def studiologos_path(self):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        return self._studiologos_path

    @studiologos_path.setter
    def studiologos_path(self, value):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        self._studiologos_path = value

    def get_animated_artwork(self, imdb_id, manual_select=False, ignore_cache=False):
        '''get animated artwork, perform extra check if local version still exists'''
        artwork = self.animatedart.get_animated_artwork(
            imdb_id, manual_select, ignore_cache=ignore_cache)
        if not (manual_select or ignore_cache):
            refresh_needed = False
            if artwork.get("animatedposter") and not xbmcvfs.exists(
                    artwork["animatedposter"]):
                refresh_needed = True
            if artwork.get("animatedfanart") and not xbmcvfs.exists(
                    artwork["animatedfanart"]):
                refresh_needed = True
            if refresh_needed:
                artwork = self.animatedart.get_animated_artwork(
                    imdb_id, manual_select, ignore_cache=True)
        return {"art": artwork}

    @use_cache(14)
    def get_omdb_info(self, imdb_id="", title="", year="", content_type=""):
        '''Get (kodi compatible formatted) metadata from OMDB, including Rotten tomatoes details'''
        title = title.split(" (")[0]  # strip year appended to title
        result = {}
        if imdb_id:
            result = self.omdb.get_details_by_imdbid(imdb_id)
        elif title and content_type in ["seasons", "season", "episodes", "episode", "tvshows", "tvshow"]:
            result = self.omdb.get_details_by_title(title, "", "tvshows")
        elif title and year:
            result = self.omdb.get_details_by_title(title, year, content_type)
        if result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(self.get_duration(result["runtime"]))
        return result

    @use_cache(7)
    def get_top250_rating(self, imdb_id):
        '''get the position in the IMDB top250 for the given IMDB ID'''
        return self.imdb.get_top250_rating(imdb_id)

    @use_cache(14)
    def get_duration(self, duration):
        '''helper to get a formatted duration'''
        if isinstance(duration, (str, unicode)) and ":" in duration:
            dur_lst = duration.split(":")
            return {
                "Duration": "%s:%s" % (dur_lst[0], dur_lst[1]),
                "Duration.Hours": dur_lst[0],
                "Duration.Minutes": dur_lst[1],
                "Runtime": str((int(dur_lst[0]) * 60) + int(dur_lst[1])),
            }
        else:
            return _get_duration(duration)

    @use_cache(2)
    def get_tvdb_details(self, imdbid="", tvdbid=""):
        '''get metadata from tvdb by providing a tvdbid or tmdbid'''
        result = {}
        self.thetvdb.days_ahead = 365
        if not tvdbid and imdbid and not imdbid.startswith("tt"):
            # assume imdbid is actually a tvdbid...
            tvdbid = imdbid
        if tvdbid:
            result = self.thetvdb.get_series(tvdbid)
        elif imdbid:
            result = self.thetvdb.get_series_by_imdb_id(imdbid)
        if result:
            if result["status"] == "Continuing":
                # include next episode info
                result["nextepisode"] = self.thetvdb.get_nextaired_episode(result["tvdb_id"])
            # include last episode info
            result["lastepisode"] = self.thetvdb.get_last_episode_for_series(result["tvdb_id"])
            result["status"] = self.translate_string(result["status"])
            if result.get("runtime"):
                result["runtime"] = result["runtime"] / 60
                result.update(_get_duration(result["runtime"]))
        return result

    @use_cache(14)
    def get_imdbtvdb_id(self, title, content_type, year="", imdbid="", tvshowtitle=""):
        '''try to figure out the imdbnumber and/or tvdbid'''
        tvdbid = ""
        if content_type in ["seasons", "episodes"] or tvshowtitle:
            title = tvshowtitle
            content_type = "tvshows"
        if imdbid and not imdbid.startswith("tt"):
            if content_type in ["tvshows", "seasons", "episodes"]:
                tvdbid = imdbid
                imdbid = ""
        if not imdbid and year:
            imdbid = self.get_omdb_info(
                "", title, year, content_type).get("imdbnumber", "")
        if not imdbid:
            # repeat without year
            imdbid = self.get_omdb_info("", title, "", content_type).get("imdbnumber", "")
        # return results
        return (imdbid, tvdbid)

    def translate_string(self, _str):
        '''translate the received english string from the various sources like tvdb, tmbd etc'''
        translation = _str
        _str = _str.lower()
        if "continuing" in _str:
            translation = self.addon.getLocalizedString(32037)
        elif "ended" in _str:
            translation = self.addon.getLocalizedString(32038)
        elif "released" in _str:
            translation = self.addon.getLocalizedString(32040)
        return translation


def process_method_on_list(*args, **kwargs):
    '''expose our process_method_on_list method to public'''
    return _process_method_on_list(*args, **kwargs)


def detect_plugin_content(*args, **kwargs):
    '''expose our detect_plugin_content method to public'''
    return _detect_plugin_content(*args, **kwargs)


def extend_dict(*args, **kwargs):
    '''expose our extend_dict method to public'''
    return _extend_dict(*args, **kwargs)


def get_clean_image(*args, **kwargs):
    '''expose our get_clean_image method to public'''
    return _get_clean_image(*args, **kwargs)
