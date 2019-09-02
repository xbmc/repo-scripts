#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcgui

from resources.lib.helper import *
from resources.lib.tmdb_utils import *

########################

class TMDBPersons(object):
    def __init__(self,call_request):
        self.tmdb_id = call_request['tmdb_id']
        self.local_movies = call_request['local_movies']
        self.local_shows = call_request['local_shows']
        self.result = {}

        if self.tmdb_id:
            cache_key = str(call_request) + DEFAULT_LANGUAGE
            self.details = get_cache(cache_key)

            if not self.details:
                self.details = tmdb_item_details('person',self.tmdb_id,append_to_response='translations,movie_credits,tv_credits,images')

            if not self.details:
                return

            self.movies = self.details['movie_credits']['cast']
            self.tvshows = self.details['tv_credits']['cast']
            self.images = self.details['images']['profiles']
            self.local_movie_count = 0
            self.local_tv_count = 0

            self.result['movies'] = self.get_movie_list()
            self.result['tvshows'] = self.get_tvshow_list()
            self.result['person'] = self.get_person_details()
            self.result['images'] = self.get_person_images()

            write_cache(cache_key,self.details)

    def __getitem__(self, key):
        return self.result.get(key,'')

    def get_person_details(self):
        li = list()

        list_item = tmdb_handle_person(self.details)
        list_item.setProperty('LocalMovies', str(self.local_movie_count))
        list_item.setProperty('LocalTVShows', str(self.local_tv_count))
        list_item.setProperty('LocalMedia', str(self.local_movie_count + self.local_tv_count))
        li.append(list_item)

        return li

    def get_movie_list(self):
        movies = sort_dict(self.movies,'release_date',True)
        li = list()
        duplicate_handler = list()

        for item in movies:
            skip_movie = False

            ''' Filter to only show real movies and to skip documentaries / behind the scenes / etc
            '''
            if FILTER_MOVIES and item.get('character'):
                for genre in item['genre_ids']:
                    if genre == 99 and ('himself' in item.get('character').lower() or 'herself' in item['character'].lower()):
                        skip_movie = True
                        break

            if not skip_movie and item['id'] not in duplicate_handler:
                list_item, is_local = tmdb_handle_movie(item,self.local_movies)
                li.append(list_item)
                duplicate_handler.append(item['id'])

                if is_local:
                    self.local_movie_count += 1

        return li

    def get_tvshow_list(self):
        tvshows = sort_dict(self.tvshows,'first_air_date',True)
        li = list()
        duplicate_handler = list()

        for item in tvshows:
            skip_show = False

            ''' Filter to only show real TV series and to skip talk, reality or news shows
            '''
            if FILTER_SHOWS:
                if not item['genre_ids']:
                    skip_show = True
                else:
                    for genre in item['genre_ids']:
                        if genre in FILTER_SHOWS_BLACKLIST:
                            skip_show = True
                            break

            if not skip_show and item['id'] not in duplicate_handler:
                list_item, is_local = tmdb_handle_tvshow(item,self.local_shows)
                li.append(list_item)
                duplicate_handler.append(item['id'])

                if is_local:
                    self.local_tv_count += 1

        return li

    def get_person_images(self):
        li = list()

        for item in self.images:
            list_item = tmdb_handle_images(item)
            li.append(list_item)

        return li