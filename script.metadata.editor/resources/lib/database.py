#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.json_map import *

########################

class Database(object):
    def __init__(self,dbid=None,dbtype=None,append=''):
        self.dbid = dbid
        self.append = append
        self.data = {}

        if dbtype:
            if dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
                library = 'Video'
                self.data['nfo'] = True

            elif dbtype in ['set']:
                library = 'Video'
                self.data['nfo'] = False

            else:
                library = 'Audio'
                self.data['nfo'] = False

            self.set_details = '%sLibrary.Set%sDetails' % (library, dbtype.replace('set', 'movieset'))
            self.param = '%sid' % dbtype

    def result(self):
        return self.data

    def write(self,key,value):
        if not isinstance(key, list):
            key = [key]
            value = [value]

        for k in key:
            json_call(self.set_details,
                      params={'%s' % k: value[key.index(k)], self.param: int(self.dbid)},
                      debug=LOG_JSON
                      )

    def movies(self):
        self._items('video', 'movie')

    def movie(self):
        self._item('video', 'movie')

    def sets(self):
        self._items('video', 'set')

    def set(self):
        self._item('video', 'set')

    def tvshows(self):
        self._items('video', 'tvshow')

    def tvshow(self):
        self._item('video', 'tvshow')

        if self.data['tvshow'] and 'episodes' in self.append:
            tvshowid = self.data['tvshow'][0].get('tvshowid')
            self._items('video', 'episode', {'tvshowid': int(tvshowid)})

    def episode(self):
        self._item('video', 'episode')

    def episodes(self):
        self._items('video', 'episode')

    def musicvideo(self):
        self._item('video', 'musicvideo')

    def musicvideos(self):
        self._items('video', 'musicvideo')

    def artist(self):
        self._item('audio', 'artist')

    def artists(self):
        self._items('audio', 'artist')

    def album(self):
        self._item('audio', 'album')

    def albums(self):
        self._items('audio', 'album')

    def song(self):
        self._item('audio', 'song')

    def songs(self):
        self._items('audio', 'song')

    def genre(self):
        movie = []
        tvshow = []
        musicvideo = []
        music = []
        video = []
        audio = []

        # video db
        for i in ['movie', 'tvshow', 'musicvideo']:
            genres = json_call('VideoLibrary.GetGenres',
                               properties=['title'],
                               params={'type': i}
                               )
            genres = genres.get('result', {}).get('genres', [])

            for genre in genres:
                eval(i).append(genre.get('label'))

        # audio db
        genres = json_call('AudioLibrary.GetGenres',
                           properties=['title']
                           )
        genres = genres.get('result', {}).get('genres', [])

        for genre in genres:
            music.append(genre.get('label'))

        self.data['moviegenres'] = movie
        self.data['tvshowgenres'] = tvshow
        self.data['musicvideogenres'] = musicvideo
        self.data['musicgenres'] = music
        self.data['videogenres'] = list(set(movie + tvshow + musicvideo))
        self.data['audiogenres'] = list(set(music + musicvideo))

    def tags(self):
        tags = json_call('VideoLibrary.GetTags',
                         properties=['title']
                         )
        self.data['tags'] = tags.get('result', {}).get('tags', [])

    def _item(self,library,dbtype):
        item = json_call('%sLibrary.Get%sDetails' % (library, dbtype.replace('set', 'movieset')),
                         properties=JSON_MAP.get('%s_properties' % dbtype),
                         params={'%sid' % dbtype: int(self.dbid)}
                         )
        self.data[dbtype] = [item.get('result', {}).get('%sdetails' % dbtype)]

    def _items(self,library,dbtype,params=None,query_filter=None):
        items = json_call('%sLibrary.Get%ss' % (library, dbtype.replace('set', 'movieset')),
                          properties=JSON_MAP.get('%ss_properties' % dbtype),
                          params=params,
                          query_filter=query_filter
                          )
        self.data[dbtype] = items.get('result', {}).get('%ss' % dbtype, [])