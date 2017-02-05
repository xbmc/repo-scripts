#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    songs.py
    all songs widgets provided by the script
'''

from utils import create_main_entry
from operator import itemgetter
from metadatautils import kodi_constants, extend_dict, process_method_on_list
import xbmc


class Songs(object):
    '''all song widgets provided by the script'''

    def __init__(self, addon, metadatautils, options):
        '''Initializations pass our common classes and the widget options as arguments'''
        self.metadatautils = metadatautils
        self.addon = addon
        self.options = options
        self.enable_artwork = self.addon.getSetting("music_enable_artwork") == "true"

    def listing(self):
        '''main listing with all our song nodes'''
        all_items = [
            (self.addon.getLocalizedString(32013), "recentplayed&mediatype=songs", "DefaultMusicSongs.png"),
            (self.addon.getLocalizedString(32012), "recent&mediatype=songs", "DefaultMusicSongs.png"),
            (self.addon.getLocalizedString(32016), "recommended&mediatype=songs", "DefaultMusicSongs.png"),
            (self.addon.getLocalizedString(32055), "similar&mediatype=songs", "DefaultMusicSongs.png"),
            (self.addon.getLocalizedString(32034), "random&mediatype=songs", "DefaultMusicSongs.png"),
            (xbmc.getLocalizedString(10134), "favourites&mediatype=songs", "DefaultMusicAlbums.png")
        ]
        return process_method_on_list(create_main_entry, all_items)

    def favourites(self):
        '''get favourites'''
        from favourites import Favourites
        self.options["mediafilter"] = "songs"
        return Favourites(self.addon, self.metadatautils, self.options).favourites()

    def favourite(self):
        '''synonym to favourites'''
        return self.favourites()

    def recommended(self):
        ''' get recommended songs - library songs with score higher than 7 '''
        filters = [kodi_constants.FILTER_RATING_MUSIC]
        items = self.metadatautils.kodidb.songs(sort=kodi_constants.SORT_RATING, filters=filters,
                                           limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_song, items)

    def recent(self):
        ''' get recently added songs '''
        items = self.metadatautils.kodidb.get_json(
            "AudioLibrary.GetRecentlyAddedSongs",
            filters=[],
            fields=kodi_constants.FIELDS_SONGS,
            limits=(
                0,
                self.options["limit"]),
            returntype="songs")
        return process_method_on_list(self.process_song, items)

    def random(self):
        ''' get random songs '''
        items = self.metadatautils.kodidb.songs(sort=kodi_constants.SORT_RANDOM, filters=[],
                                           limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_song, items)

    def recentplayed(self):
        ''' get in progress songs '''
        items = self.metadatautils.kodidb.songs(sort=kodi_constants.SORT_LASTPLAYED, filters=[],
                                           limits=(0, self.options["limit"]))
        return process_method_on_list(self.process_song, items)

    def similar(self):
        ''' get similar songs for recent played song'''
        all_items = []
        all_titles = list()
        ref_song = self.get_random_played_song()
        if ref_song:
            # get all songs for the genres in the song
            genres = ref_song["genre"]
            similar_title = ref_song["title"]
            for genre in genres:
                genre = genre.split(";")[0]
                self.options["genre"] = genre
                genre_songs = self.get_genre_songs(genre)
                for item in genre_songs:
                    # prevent duplicates so skip reference song and titles already in the list
                    if not item["title"] in all_titles and not item["title"] == similar_title:
                        item["extraproperties"] = {"similartitle": similar_title}
                        all_items.append(item)
                        all_titles.append(item["title"])
        # return the list capped by limit and sorted by rating
        items = sorted(all_items, key=itemgetter("rating"), reverse=True)[:self.options["limit"]]
        return process_method_on_list(self.process_song, items)

    def get_random_played_song(self):
        '''gets a random played song from kodi_constants.'''
        songs = self.metadatautils.kodidb.songs(sort=kodi_constants.SORT_RANDOM,
                                           filters=[kodi_constants.FILTER_WATCHED], limits=(0, 1))
        if songs:
            return songs[0]
        else:
            return None

    def get_genre_songs(self, genre, limit=100):
        '''helper method to get all songs in a specific genre'''
        filters = [{"operator": "contains", "field": "genre", "value": genre}]
        return self.metadatautils.kodidb.songs(sort=kodi_constants.SORT_RANDOM, filters=filters, limits=(0, limit))

    def process_song(self, item):
        '''additional actions on a song item'''
        if self.enable_artwork:
            extend_dict(item, self.metadatautils.get_music_artwork(item["artist"][0],
                                                              item["album"], item["title"], str(item["disc"])))
        return item
