#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcgui
import requests

from resources.lib.helper import *
from resources.lib.tmdb_utils import *

########################

class TMDBVideos(object):
    def __init__(self,call_request):
        self.result = {}
        self.call = call_request['call']
        self.tmdb_id = call_request['tmdb_id']
        self.local_movies = call_request['local_movies']
        self.local_shows = call_request['local_shows']
        self.movie = get_bool(self.call,'movie')
        self.tvshow = get_bool(self.call,'tv')

        if self.tmdb_id:
            cache_key = str(call_request) + DEFAULT_LANGUAGE + COUNTRY_CODE
            self.details = get_cache(cache_key)

            if not self.details:
                self.details = tmdb_item_details(self.call,self.tmdb_id,append_to_response='release_dates,content_ratings,external_ids,credits,videos,translations')

            if not self.details:
                return

            self.created_by = self.details['created_by'] if self.details.get('created_by') else ''
            self.cast = self.details['credits']['cast']
            self.crew = self.details['credits']['crew']
            self.videos = self.details['videos']['results']
            self.details['crew'] = self.crew

            self.result['details'] = self.get_details()
            self.result['cast'] = self.get_cast()
            self.result['crew'] = self.get_crew()
            self.result['similar'] = self.get_similar()
            self.result['youtube'] = self.get_yt_videos()
            self.result['images'] = self.get_images()

            write_cache(cache_key,self.details)

    def __getitem__(self, key):
        return self.result.get(key,'')

    def get_details(self):
        li = list()

        if self.movie:
            list_item, is_local = tmdb_handle_movie(self.details,self.local_movies,full_info=True)
        elif self.tvshow:
            list_item, is_local = tmdb_handle_tvshow(self.details,self.local_shows,full_info=True)

        li.append(list_item)
        return li

    def get_cast(self):
        li = list()

        for item in self.cast:
            item['label2'] = item.get('character','')
            list_item = tmdb_handle_credits(item)
            li.append(list_item)

        return li

    def get_crew(self):
        li_clean_crew = list()
        li_crew_duplicate_handler_id = list()
        li = list()

        ''' Add creators to crew
        '''
        for item in self.created_by:
            item['job'] = 'Creator'
            item['department'] = 'Directing'
            li_clean_crew.append(item)
            li_crew_duplicate_handler_id.append(item['id'])

        ''' Filter crew and merge duplicate crew members if they were responsible for different jobs
        '''
        for item in self.crew:
            if item['job'] in ['Creator','Director','Producer','Screenplay','Writer','Original Music Composer','Novel','Storyboard','Executive Producer','Comic Book']:
                if item['id'] not in li_crew_duplicate_handler_id:
                    li_clean_crew.append(item)
                    li_crew_duplicate_handler_id.append(item['id'])
                else:
                    for duplicate in li_clean_crew:
                        if duplicate['id'] == item['id']:
                            duplicate['job'] = duplicate['job'] + ' / ' + item['job']

        ''' Sort crew output based on department
        '''
        for item in li_clean_crew:
            if item['department'] == 'Directing':
                item['label2'] = item.get('job','')
                list_item = tmdb_handle_credits(item)
                li.append(list_item)

        for item in li_clean_crew:
            if item['department'] == 'Writing':
                item['label2'] = item.get('job','')
                list_item = tmdb_handle_credits(item)
                li.append(list_item)

        for item in li_clean_crew:
            if item['department'] == 'Production':
                item['label2'] = item.get('job','')
                list_item = tmdb_handle_credits(item)
                li.append(list_item)

        for item in li_clean_crew:
            if item['department'] == 'Sound':
                item['job'] = 'Music Composer' if item['job'] == 'Original Music Composer' else item['job']
                item['label2'] = item.get('job','')
                list_item = tmdb_handle_credits(item)
                li.append(list_item)

        return li

    def get_similar(self):
        similar = tmdb_item_details(self.call,self.tmdb_id,'similar')
        similar = similar['results']
        li = list()

        if self.movie:
            similar = sort_dict(similar,'release_date',True)

            for item in similar:
                list_item, is_local = tmdb_handle_movie(item,self.local_movies)
                li.append(list_item)

        elif self.tvshow:
            similar = sort_dict(similar,'first_air_date',True)

            for item in similar:
                list_item, is_local = tmdb_handle_tvshow(item,self.local_shows)
                li.append(list_item)

        return li

    def get_images(self):
        cache_key = str(self.tmdb_id) + self.call + 'images' + DEFAULT_LANGUAGE
        images = get_cache(cache_key)
        li = list()

        if not images:
            images = tmdb_item_details(self.call,self.tmdb_id,'images',use_language=False,include_image_language='%s,en,null' % DEFAULT_LANGUAGE)
            images = images['backdrops']

            if images:
                write_cache(cache_key,images)

        for item in images:
            list_item = tmdb_handle_images(item)
            li.append(list_item)

        return li

    def get_yt_videos(self):
        cache_key = str(self.tmdb_id) + self.call + 'ytvideos' + DEFAULT_LANGUAGE
        videos = get_cache(cache_key)
        li = list()

        if not videos:
            videos = self.videos

            ''' Add EN videos next to the user configured language
            '''
            if DEFAULT_LANGUAGE != FALLBACK_LANGUAGE:
                videos_en = tmdb_item_details(self.call,self.tmdb_id,'videos',use_language=False)
                videos_en = videos_en.get('results')
                videos = videos + videos_en

            ''' Check online status of all videos to prevent dead links
            '''
            online_videos = []
            for item in videos:
                request = requests.head('https://img.youtube.com/vi/%s/0.jpg' % str(item['key']))
                if request.status_code == requests.codes.ok:
                    online_videos.append(item)

            videos = online_videos

            if videos:
                write_cache(cache_key,videos)

        for item in videos:
            if item['site'] == 'YouTube':
                list_item = tmdb_handle_yt_videos(item)
                if not list_item == 404:
                    li.append(list_item)

        return li