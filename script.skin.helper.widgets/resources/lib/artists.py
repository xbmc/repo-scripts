#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    artists.py
    all artists widgets provided by the script
'''

from utils import create_main_entry
from metadatautils import kodi_constants, extend_dict, process_method_on_list
import xbmc


class Artists(object):
    '''all artist widgets provided by the script'''

    def __init__(self, addon, metadatautils, options):
        '''Initializations pass our common classes and the widget options as arguments'''
        self.metadatautils = metadatautils
        self.addon = addon
        self.options = options
        self.enable_artwork = self.addon.getSetting("music_enable_artwork") == "true"

    def listing(self):
        '''main listing with all our artist nodes'''
        all_items = [
            (self.addon.getLocalizedString(32063), "recent&mediatype=artists", "DefaultMusicArtists.png"),
            (self.addon.getLocalizedString(32065), "recommended&mediatype=artists", "DefaultMusicArtists.png"),
            (self.addon.getLocalizedString(32064), "random&mediatype=artists", "DefaultMusicArtists.png"),
            (xbmc.getLocalizedString(10134), "favourites&mediatype=artists", "DefaultMusicArtists.png")
        ]
        return process_method_on_list(create_main_entry, all_items)

    def favourites(self):
        '''get favourites'''
        from favourites import Favourites
        self.options["mediafilter"] = "artists"
        return Favourites(self.addon, self.metadatautils, self.options).favourites()

    def recommended(self):
        ''' get recommended artists - library artists sorted by rating '''
        all_items = self.metadatautils.kodidb.artists(sort=kodi_constants.SORT_RATING,
                                                filters=[], limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_artist, all_items)

    def recent(self):
        ''' get recently added artists '''
        all_items = self.metadatautils.kodidb.artists(sort=kodi_constants.SORT_DATEADDED, filters=[],
                                                limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_artist, all_items)

    def random(self):
        ''' get random artists '''
        all_items = self.metadatautils.kodidb.artists(sort=kodi_constants.SORT_RANDOM, filters=[],
                                                limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_artist, all_items)

    def process_artist(self, item):
        '''transform the json received from kodi into something we can use'''
        if self.enable_artwork:
            extend_dict(item, self.metadatautils.get_music_artwork(item["label"][0]))
        item["file"] = "musicdb://artists/%s" % item["artistid"]
        item["isFolder"] = True
        return item
