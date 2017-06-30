#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    tvshows.py
    all tvshows widgets provided by the script
'''

from utils import create_main_entry
from operator import itemgetter
from metadatautils import kodi_constants, process_method_on_list, TheTvDb
import xbmc


class Tvshows(object):
    '''all tvshow widgets provided by the script'''

    def __init__(self, addon, metadatautils, options):
        '''Initializations pass our common classes and the widget options as arguments'''
        self.metadatautils = metadatautils
        self.addon = addon
        self.options = options
        self.thetvdb = TheTvDb()

    def listing(self):
        '''main listing with all our tvshow nodes'''
        tag = self.options.get("tag", "")
        if tag:
            label_prefix = u"%s - " % tag
        else:
            label_prefix = u""
        icon = "DefaultTvShows.png"
        all_items = [
            (label_prefix + self.addon.getLocalizedString(32044), "inprogress&mediatype=tvshows&tag=%s" % tag, icon),
            (label_prefix + self.addon.getLocalizedString(32045), "recent&mediatype=tvshows&tag=%s" % tag, icon),
            (label_prefix + self.addon.getLocalizedString(32037), "recommended&mediatype=tvshows&tag=%s" % tag, icon),
            (label_prefix + self.addon.getLocalizedString(32041), "random&mediatype=tvshows&tag=%s" % tag, icon),
            (label_prefix + self.addon.getLocalizedString(32047), "top250&mediatype=tvshows&tag=%s" % tag, icon),
            (label_prefix + xbmc.getLocalizedString(135), "browsegenres&mediatype=tvshows&tag=%s" % tag, icon),
        ]
        if not tag:
            all_items += [
                (self.addon.getLocalizedString(32014), "similar&mediatype=tvshows", icon),
                (xbmc.getLocalizedString(10134), "favourites&mediatype=tvshows", icon),
                (xbmc.getLocalizedString(20459), "tags&mediatype=tvshows", icon)
            ]
        if tag:
            # add episode nodes with tag filter
            all_items += [
                (label_prefix + self.addon.getLocalizedString(32027), "inprogress&mediatype=episodes&tag=%s" %
                    tag, icon),
                (label_prefix + self.addon.getLocalizedString(32039), "recent&mediatype=episodes&tag=%s" %
                    tag, icon),
                (label_prefix + self.addon.getLocalizedString(32002), "next&mediatype=episodes&tag=%s" %
                    tag, icon),
                (label_prefix + self.addon.getLocalizedString(32008), "random&mediatype=episodes&tag=%s" %
                    tag, icon)]
        return process_method_on_list(create_main_entry, all_items)

    def tags(self):
        '''get tags listing'''
        all_items = []
        for item in self.metadatautils.kodidb.files("videodb://tvshows/tags"):
            details = (item["label"], "listing&mediatype=tvshows&tag=%s" % item["label"], "DefaultTags.png")
            all_items.append(create_main_entry(details))
        return all_items

    def recommended(self):
        ''' get recommended tvshows - library tvshows with score higher than 7 '''
        filters = [kodi_constants.FILTER_RATING]
        if self.options["hide_watched"]:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        tvshows = self.metadatautils.kodidb.tvshows(
            sort=kodi_constants.SORT_RATING, filters=filters, limits=(
                0, self.options["limit"]))
        return process_method_on_list(self.process_tvshow, tvshows)

    def recent(self):
        ''' get recently added tvshows '''
        filters = []
        if self.options["hide_watched"]:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        tvshows = self.metadatautils.kodidb.tvshows(
            sort=kodi_constants.SORT_DATEADDED, filters=filters, limits=(
                0, self.options["limit"]))
        return process_method_on_list(self.process_tvshow, tvshows)

    def random(self):
        ''' get random tvshows '''
        filters = []
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        tvshows = self.metadatautils.kodidb.tvshows(
            sort=kodi_constants.SORT_RANDOM, filters=filters, limits=(
                0, self.options["limit"]))
        return process_method_on_list(self.process_tvshow, tvshows)

    def inprogress(self):
        ''' get in progress tvshows '''
        filters = [kodi_constants.FILTER_INPROGRESS]
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        tvshows = self.metadatautils.kodidb.tvshows(
            sort=kodi_constants.SORT_LASTPLAYED, filters=filters, limits=(
                0, self.options["limit"]))
        return process_method_on_list(self.process_tvshow, tvshows)

    def similar(self):
        ''' get similar tvshows for given imdbid or just from random watched title if no imdbid'''
        imdb_id = self.options.get("imdbid", "")
        all_items = []
        all_titles = list()
        # lookup tvshow by imdbid or just pick a random watched tvshow
        ref_tvshow = None
        if imdb_id:
            # get tvshow by imdbid
            ref_tvshow = self.metadatautils.kodidb.tvshow_by_imdbid(imdb_id)
        if not ref_tvshow:
            # just get a random watched tvshow
            ref_tvshow = self.get_random_watched_tvshow()
        if ref_tvshow:
            # get all tvshows for the genres in the tvshow
            genres = ref_tvshow["genre"]
            similar_title = ref_tvshow["title"]
            for genre in genres:
                self.options["genre"] = genre
                genre_tvshows = self.forgenre()
                for item in genre_tvshows:
                    # prevent duplicates so skip reference tvshow and titles already in the list
                    if not item["title"] in all_titles and not item["title"] == similar_title:
                        item["extraproperties"] = {"similartitle": similar_title, "originalpath": item["file"]}
                        all_items.append(item)
                        all_titles.append(item["title"])
        # return the list capped by limit and sorted by rating
        tvshows = sorted(all_items, key=itemgetter("rating"), reverse=True)[:self.options["limit"]]
        return process_method_on_list(self.process_tvshow, tvshows)

    def forgenre(self):
        ''' get top rated tvshows for given genre'''
        genre = self.options.get("genre", "")
        all_items = []
        if not genre:
            # get a random genre if no genre provided
            json_result = self.metadatautils.kodidb.genres("tvshow")
            if json_result:
                genre = json_result[0]["label"]
        if genre:
            # get all tvshows from the same genre
            for item in self.get_genre_tvshows(genre, self.options["hide_watched"], self.options["limit"]):
                # append original genre as listitem property for later reference by skinner
                item["extraproperties"] = {"genretitle": genre, "originalpath": item["file"]}
                all_items.append(item)

        # return the list sorted by rating
        tvshows = sorted(all_items, key=itemgetter("rating"), reverse=True)
        return process_method_on_list(self.process_tvshow, tvshows)

    def top250(self):
        ''' get imdb top250 tvshows in library '''
        all_items = []
        filters = []
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        fields = ["imdbnumber"]
        if KODI_VERSION > 16:
            fields.append("uniqueid")
        all_tvshows = self.metadatautils.kodidb.get_json(
            'VideoLibrary.GetTvShows', fields=fields, returntype="tvshows", filters=filters)
        top_250 = self.metadatautils.imdb.get_top250_db()
        for tvshow in all_tvshows:
            # grab imdbid
            imdbnumber = tvshow["imdbnumber"]
            if not imdbnumber and "uniqueid" in tvshow:
                for value in tvshow["uniqueid"]:
                    if value.startswith("tt"):
                        imdbnumber = value
            if imdbnumber and not imdbnumber.startswith("tt"):
                # we have a tvdb id
                tvdb_info = self.thetvdb.get_series(imdbnumber)
                if tvdb_info:
                    imdbnumber = tvdb_info["imdbnumber"]
                else:
                    imdbnumber = None
            if imdbnumber and imdbnumber in top_250:
                tvshow_full = self.metadatautils.kodidb.tvshow(tvshow["tvshowid"])
                tvshow_full["top250_rank"] = int(top_250[imdbnumber])
                all_items.append(tvshow_full)
        tvshows = sorted(all_items, key=itemgetter("top250_rank"))[:self.options["limit"]]
        return process_method_on_list(self.process_tvshow, tvshows)

    def browsegenres(self):
        '''
            special entry which can be used to create custom genre listings
            returns each genre with poster/fanart artwork properties from 5
            random tvshows in the genre.
            TODO: get auto generated collage pictures from skinhelper's metadatautils ?
        '''
        all_genres = self.metadatautils.kodidb.genres("tvshow")
        return process_method_on_list(self.get_genre_artwork, all_genres)

    def get_genre_artwork(self, genre_json):
        '''helper method for browsegenres'''
        # for each genre we get 5 random items from the library and attach the artwork to the genre listitem
        genre_json["art"] = {}
        genre_json["file"] = "videodb://tvshows/genres/%s/" % genre_json["genreid"]
        if self.options.get("tag"):
            genre_json["file"] = "plugin://script.skin.helper.widgets?"\
                "mediatype=tvshows&action=forgenre&tag=%s&genre=%s" % (self.options["tag"], genre_json["label"])
        genre_json["isFolder"] = True
        genre_json["IsPlayable"] = "false"
        genre_json["thumbnail"] = genre_json.get("thumbnail",
                                                 "DefaultGenre.png")  # TODO: get icon from resource addon ?
        genre_json["type"] = "genre"
        genre_tvshows = self.get_genre_tvshows(genre_json["label"], False, 5)
        if not genre_tvshows:
            return None
        for count, genre_tvshow in enumerate(genre_tvshows):
            genre_json["art"]["poster.%s" % count] = genre_tvshow["art"].get("poster", "")
            genre_json["art"]["fanart.%s" % count] = genre_tvshow["art"].get("fanart", "")
            if "fanart" not in genre_json["art"]:
                # set genre's primary fanart image to first movie fanart
                genre_json["art"]["fanart"] = genre_tvshow["art"].get("fanart", "")
        return genre_json

    def nextaired(self):
        '''legacy method: get nextaired episodes instead'''
        from episodes import Episodes
        eps = Episodes(self.addon, self.metadatautils.kodidb, self.options)
        result = eps.nextaired()
        del eps
        return result

    def get_random_watched_tvshow(self):
        '''gets a random watched or inprogress tvshow from kodi_constants.'''
        filters = [kodi_constants.FILTER_WATCHED, kodi_constants.FILTER_INPROGRESS]
        tvshows = self.metadatautils.kodidb.tvshows(
            sort=kodi_constants.SORT_RANDOM,
            filters=filters,
            filtertype="or",
            limits=(
                0,
                1))
        if tvshows:
            return tvshows[0]
        else:
            return None

    def get_genre_tvshows(self, genre, hide_watched=False, limit=100):
        '''helper method to get all tvshows in a specific genre'''
        filters = [{"operator": "is", "field": "genre", "value": genre}]
        if hide_watched:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        if self.options.get("tag"):
            filters.append({"operator": "contains", "field": "tag", "value": self.options["tag"]})
        return self.metadatautils.kodidb.tvshows(sort=kodi_constants.SORT_RANDOM, filters=filters, limits=(0, limit))

    @staticmethod
    def process_tvshow(item):
        '''set optional details to tvshow item'''
        item["file"] = "videodb://tvshows/titles/%s" % item["tvshowid"]
        item["isFolder"] = True
        return item

    def favourites(self):
        '''get favourites'''
        from favourites import Favourites
        self.options["mediafilter"] = "tvshows"
        return Favourites(self.addon, self.metadatautils, self.options).favourites()

    def favourite(self):
        '''synonym to favourites'''
        return self.favourites()
