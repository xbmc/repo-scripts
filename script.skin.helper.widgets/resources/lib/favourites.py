#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    favourites.py
    all favourites widgets provided by the script
'''

from metadatautils import extend_dict, process_method_on_list
from utils import create_main_entry
import xbmc
import xbmcvfs
from urllib import quote_plus


class Favourites(object):
    '''all favourites widgets provided by the script'''

    def __init__(self, addon, metadatautils, options):
        '''Initializations pass our common classes and the widget options as arguments'''
        self.metadatautils = metadatautils
        self.addon = addon
        self.options = options
        self.enable_artwork = self.addon.getSetting("music_enable_artwork") == "true"
        self.browse_album = self.addon.getSetting("music_browse_album") == "true"

    def listing(self):
        '''main listing with only our favourites nodes'''
        all_items = [
            (xbmc.getLocalizedString(10134),
             "favourites&mediatype=favourites",
             "DefaultFile.png"),
            (self.addon.getLocalizedString(32001),
             "favourites&mediatype=favourites&mediafilter=media",
             "DefaultMovies.png")]
        return process_method_on_list(create_main_entry, all_items)

    def favourites(self):
        '''show kodi favourites'''
        all_items = []
        media_filter = self.options.get("mediafilter", "")

        # emby favorites
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.emby) + Skin.HasSetting(SmartShortcuts.emby)"):
            if media_filter in ["media", "movies"]:
                filters = [{"operator": "contains", "field": "tag", "value": "Favorite movies"}]
                all_items += self.metadatautils.kodidb.movies(filters=filters)

            if media_filter in ["media", "tvshows"]:
                filters = [{"operator": "contains", "field": "tag", "value": "Favorite tvshows"}]
                for item in self.metadatautils.kodidb.tvshows(filters=filters):
                    item["file"] = "videodb://tvshows/titles/%s" % item["tvshowid"]
                    item["isFolder"] = True
                    all_items.append(item)

        # Kodi favourites
        for fav in self.metadatautils.kodidb.favourites():
            details = {}

            # try to match with tvshow or album
            if fav["type"] == "window":
                details = self.find_window_match(fav, media_filter)

            # try to match with song, movie, musicvideo or episode
            elif fav["type"] == "media":
                details = self.find_media_match(fav, media_filter)

            # add unknown item in the result...
            if not details and not media_filter:
                details = self.find_other_match(fav)

            # if we have a result, append to the list
            if details:
                all_items.append(details)

        return all_items

    def find_window_match(self, fav, media_filter):
        '''try to get a match for tvshow or album favourites listing'''
        match = {}
        # check for tvshow
        if not media_filter or media_filter == "tvshows":
            if fav["windowparameter"].startswith("videodb://tvshows/titles"):
                try:
                    tvshowid = int(fav["windowparameter"].split("/")[-2])
                    result = self.metadatautils.kodidb.tvshow(tvshowid)
                    if result:
                        result["file"] = "videodb://tvshows/titles/%s" % tvshowid
                        result["isFolder"] = True
                        match = result
                except Exception:
                    pass

        # check for album
        if not match and (not media_filter or media_filter in ["albums", "media"]):
            if "musicdb://albums/" in fav["windowparameter"]:
                result = self.metadatautils.kodidb.album(fav["windowparameter"].replace("musicdb://albums/", ""))
                if result:
                    if self.enable_artwork:
                        extend_dict(result, self.metadatautils.get_music_artwork(result["label"], result["artist"][0]))
                    if self.browse_album:
                        result["file"] = "musicdb://albums/%s" % result["albumid"]
                        result["isFolder"] = True
                    else:
                        result["file"] = u"plugin://script.skin.helper.service?action=playalbum&albumid=%s" \
                            % result["albumid"]
                    match = result
        return match

    def find_media_match(self, fav, media_filter):
        ''' try to get a match for movie/episode/song/musicvideo for favourite'''
        match = {}
        # apparently only the filepath can be used for the search
        filename = fav["path"]
        if "/" in filename:
            sep = "/"
        else:
            sep = "\\"
        file_path = filename.split(sep)[-1]
        filters = [{"operator": "contains", "field": "filename", "value": file_path}]
        # is this a movie?
        if not match and (not media_filter or media_filter in ["movies", "media"]):
            for item in self.metadatautils.kodidb.movies(filters=filters):
                if item['file'] == fav["path"]:
                    match = item
        # is this an episode ?
        if not match and (not media_filter or media_filter in ["episodes", "media"]):
            for item in self.metadatautils.kodidb.episodes(filters=filters):
                if item['file'] == fav["path"]:
                    match = item
        # is this a song ?
        if not match and (not media_filter or media_filter in ["songs", "media"]):
            for item in self.metadatautils.kodidb.songs(filters=filters):
                if item['file'] == fav["path"]:
                    if self.enable_artwork:
                        extend_dict(item, self.metadatautils.get_music_artwork(item["title"], item["artist"][0]))
                    match = item
        # is this a musicvideo ?
        if not match and (not media_filter or media_filter in ["musicvideos", "media"]):
            for item in self.metadatautils.kodidb.musicvideos(filters=filters):
                if item['file'] == fav["path"]:
                    match = item
        return match

    @staticmethod
    def find_other_match(fav):
        '''create listitem for any other item in favourites'''
        item = {}
        is_folder = False
        if fav["type"] == "window":
            media_path = fav["windowparameter"]
            is_folder = True
        elif fav["type"] == "media":
            media_path = fav["path"]
        else:
            media_path = 'plugin://script.skin.helper.service/?action=launch&path=%s'\
                % quote_plus(fav.get("path"))
        if not fav.get("label"):
            fav["label"] = fav.get("title")
        if not fav.get("title"):
            fav["label"] = fav.get("label")

        thumb = fav.get("thumbnail")
        fanart = ""
        if "plugin://" in fav["path"]:
            # get fanart and thumb for addons
            addon = fav["path"].split("plugin://")[1].split("/")[0]
            if not (xbmcvfs.exists(thumb) or xbmc.skinHasImage(thumb)):
                if xbmcvfs.exists("special://home/addons/%s/icon.png" % addon):
                    thumb = "special://home/addons/%s/icon.png" % addon
            if xbmcvfs.exists("special://home/addons/%s/fanart.jpg" % addon):
                fanart = "special://home/addons/%s/fanart.jpg" % addon

        item = {
            "label": fav.get("label"),
            "title": fav.get("title"),
            "thumbnail": thumb,
            "fanart": fanart,
            "file": media_path,
            "type": "favourite",
            "art": {
                "landscape": thumb,
                "poster": thumb,
                "fanart": fanart}
        }
        if is_folder:
            item["isFolder"] = True
        return item
