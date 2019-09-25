#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.utils import *

''' Python 2<->3 compatibility
'''
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

########################

INDEX = [
        {'name': ADDON.getLocalizedString(32029), 'info': 'movies', 'call': 'top_rated'},
        {'name': ADDON.getLocalizedString(32030), 'info': 'movies', 'call': 'now_playing'},
        {'name': ADDON.getLocalizedString(32031), 'info': 'movies', 'call': 'upcoming'},
        {'name': ADDON.getLocalizedString(32032), 'info': 'movies', 'call': 'popular'},
        {'name': ADDON.getLocalizedString(32033), 'info': 'tvshows', 'call': 'top_rated'},
        {'name': ADDON.getLocalizedString(32034), 'info': 'tvshows', 'call': 'popular'},
        {'name': ADDON.getLocalizedString(32035), 'info': 'tvshows', 'call': 'airing_today'},
        {'name': ADDON.getLocalizedString(32036), 'info': 'tvshows', 'call': 'on_the_air'}
        ]

########################

class PluginListing(object):
    def __init__(self,params,li):
        self.li = li
        self.widgets()

    def widgets(self):
        for widget in INDEX:
            label = widget['name']
            url = '{0}?{1}'.format(sys.argv[0], urlencode({'info': widget['info'], 'call': widget['call']}))

            list_item = xbmcgui.ListItem(label=label)
            list_item.setInfo('video', {'title': label, 'mediatype': 'video'})
            list_item.setArt({'icon': 'DefaultFolder.png', 'thumb': 'special://home/addons/script.embuary.info/resources/icon.png'})
            self.li.append((url, list_item, True))


class PluginContent(object):
    def __init__(self,params,li):
        self.li = li
        self.local_media = get_local_media()
        self.call = params.get('call')

    def movies(self):
        result = self._query('movie',self.call)
        self._process_movies(result)

    def tvshows(self):
        result = self._query('tv',self.call)
        self._process_tvshows(result)

    def _query(self,content_type,call):
        tmdb = get_cache(content_type + call)

        if not tmdb:
            tmdb = tmdb_query(action=content_type,
                                call=call,
                                params={'region': COUNTRY_CODE}
                                )

            write_cache(content_type + call,tmdb,3)

        return tmdb['results']

    def _process_movies(self,result):
        for item in result:
            list_item, is_local = tmdb_handle_movie(item,local_items=self.local_media['movies'])
            self._add(list_item,item,'movie')

    def _process_tvshows(self,result):
        for item in result:
            list_item, is_local = tmdb_handle_tvshow(item,local_items=self.local_media['shows'])
            self._add(list_item,item,'tv')

    def _add(self,list_item,item,content):
        url = 'plugin://script.embuary.info/?action=runscript&call=%s&id=%s' % (content,item['id'])
        self.li.append((url, list_item, False))


class PluginActions(object):
    def __init__(self,params):
        self.id = params.get('id')
        self.call = params.get('call')

    def runscript(self):
        execute('RunScript(script.embuary.info,call=%s,tmdb_id=%s)' % (self.call,self.id))
