#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    musivideos.py
    all musivideos widgets provided by the script
'''

from utils import create_main_entry
from metadatautils import kodi_constants, process_method_on_list
import xbmc


class Musicvideos(object):
    '''all musicvideo widgets provided by the script'''
    options = {}
    kodidb = None
    addon = None

    def __init__(self, addon, metadatautils, options):
        '''Initialization'''
        self.addon = addon
        self.metadatautils = metadatautils
        self.options = options

    def listing(self):
        '''main listing with all our musicvideo nodes'''
        tag = self.options.get("tag", "")
        all_items = [
            (self.addon.getLocalizedString(32061), "inprogress&mediatype=musicvideos&tag=%s" %
                tag, "DefaultTvShows.png"),
            (self.addon.getLocalizedString(32040), "recent&mediatype=musicvideos&tag=%s" %
                tag, "DefaultRecentlyAddedmusicvideos.png"),
            (self.addon.getLocalizedString(32062), "random&mediatype=musicvideos&tag=%s" %
                tag, "DefaultTvShows.png"),
            (xbmc.getLocalizedString(10134), "favourites&mediatype=musicvideos&tag=%s" %
                tag, "DefaultMovies.png")]
        return process_method_on_list(create_main_entry, all_items)

    def favourites(self):
        '''get favourites'''
        from favourites import Favourites
        self.options["mediafilter"] = "musicvideos"
        return Favourites(self.addon, self.metadatautils, self.options).favourites()

    def recommended(self):
        ''' get recommended musicvideos - library musicvideos with score higher than 7 '''
        filters = [kodi_constants.FILTER_RATING]
        if self.options["hide_watched"]:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        return self.metadatautils.kodidb.musicvideos(sort=kodi_constants.SORT_RATING, filters=filters,
                                                limits=(0, self.options["limit"]))

    def recent(self):
        ''' get recently added musicvideos '''
        filters = []
        if self.options["hide_watched"]:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        return self.metadatautils.kodidb.musicvideos(sort=kodi_constants.SORT_DATEADDED, filters=filters,
                                                limits=(0, self.options["limit"]))

    def random(self):
        ''' get random musicvideos '''
        filters = []
        if self.options["hide_watched"]:
            filters.append(kodi_constants.FILTER_UNWATCHED)
        return self.metadatautils.kodidb.musicvideos(sort=kodi_constants.SORT_DATEADDED, filters=filters,
                                                limits=(0, self.options["limit"]))

    def inprogress(self):
        ''' get in progress musicvideos '''
        return self.metadatautils.kodidb.musicvideos(sort=kodi_constants.SORT_LASTPLAYED, filters=[
                                                kodi_constants.FILTER_INPROGRESS], limits=(0, self.options["limit"]))
