#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    albums.py
    all albums widgets provided by the script
'''

from utils import create_main_entry
from operator import itemgetter
from metadatautils import kodi_constants, extend_dict, process_method_on_list
import xbmc


class Albums(object):
    '''all album widgets provided by the script'''

    def __init__(self, addon, metadatautils, options):
        '''Initializations pass our common classes and the widget options as arguments'''
        self.metadatautils = metadatautils
        self.addon = addon
        self.options = options
        self.enable_artwork = self.addon.getSetting("music_enable_artwork") == "true"
        self.browse_album = self.addon.getSetting("music_browse_album") == "true"

    def listing(self):
        '''main listing with all our album nodes'''
        all_items = [
            (xbmc.getLocalizedString(517), "recentplayed&mediatype=albums", "DefaultMusicAlbums.png"),
            (xbmc.getLocalizedString(359), "recent&mediatype=albums", "DefaultMusicAlbums.png"),
            (self.addon.getLocalizedString(32015), "recommended&mediatype=albums", "DefaultMusicAlbums.png"),
            (self.addon.getLocalizedString(32056), "similar&mediatype=albums", "DefaultMusicAlbums.png"),
            (self.addon.getLocalizedString(32033), "random&mediatype=albums", "DefaultMusicAlbums.png"),
            (xbmc.getLocalizedString(10134), "favourites&mediatype=albums", "DefaultMusicAlbums.png")
        ]
        return process_method_on_list(create_main_entry, all_items)

    def favourites(self):
        '''get favourites'''
        from favourites import Favourites
        self.options["mediafilter"] = "albums"
        return Favourites(self.addon, self.metadatautils, self.options).favourites()

    def recommended(self):
        ''' get recommended albums - library albums with sorted by rating '''
        all_items = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_RATING,
                                                filters=[], limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_album, all_items)

    def recent(self):
        ''' get recently added albums '''
        all_items = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_DATEADDED, filters=[],
                                                limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_album, all_items)

    def random(self):
        ''' get random albums '''
        all_items = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_RANDOM, filters=[],
                                                limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_album, all_items)

    def recentplayed(self):
        ''' get in progress albums '''
        all_items = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_LASTPLAYED, filters=[],
                                                limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_album, all_items)

    def similar(self):
        ''' get similar albums for recent played album'''
        all_items = []
        all_titles = list()
        ref_album = self.get_random_played_album()
        if not ref_album:
            ref_album = self.get_random_highrated_album()
        if ref_album:
            # get all albums for the genres in the album
            genres = ref_album["genre"]
            similar_title = ref_album["title"]
            for genre in genres:
                genre = genre.split(";")[0]
                self.options["genre"] = genre
                genre_albums = self.get_genre_albums(genre)
                for item in genre_albums:
                    # prevent duplicates so skip reference album and titles already in the list
                    if not item["title"] in all_titles and not item["title"] == similar_title:
                        item["extraproperties"] = {"similartitle": similar_title}
                        all_items.append(item)
                        all_titles.append(item["title"])
        # return the list capped by limit and sorted by rating
        all_items = sorted(all_items, key=itemgetter("rating"), reverse=True)[:self.options["limit"]]
        return process_method_on_list(self.process_album, all_items)

    def get_random_played_album(self):
        '''gets a random played album from kodi.'''
        albums = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_RANDOM,
                                             filters=[kodi_constants.FILTER_WATCHED], limits=(0, 1))
        if albums:
            return albums[0]
        else:
            return None

    def get_random_highrated_album(self):
        '''gets a random high rated album from kodi.'''
        albums = self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_RATING,
                                             filters=[], limits=(0, 1))
        if albums:
            return albums[0]
        else:
            return None

    def get_genre_albums(self, genre, limit=100):
        '''helper method to get all albums in a specific genre'''
        filters = [{"operator": "contains", "field": "genre", "value": genre}]
        return self.metadatautils.kodidb.albums(sort=kodi_constants.SORT_RANDOM, filters=filters, limits=(0, limit))

    def process_album(self, item):
        '''transform the json received from kodi into something we can use'''
        if self.enable_artwork:
            extend_dict(item, self.metadatautils.get_music_artwork(item["artist"][0], item["title"]))
        if self.browse_album:
            item["file"] = "musicdb://albums/%s" % item["albumid"]
            item["isFolder"] = True
        else:
            item["file"] = u"plugin://script.skin.helper.service?action=playalbum&albumid=%s" % item["albumid"]
        return item
