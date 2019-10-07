#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcgui

''' Python 2<->3 compatibility
'''
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from resources.lib.helper import *

########################

LISTING = {
          'index': [
              {'name': ADDON.getLocalizedString(32011), 'browse': 'folder', 'content': 'mixed'},
              {'name': xbmc.getLocalizedString(342), 'browse': 'folder', 'content': 'movie'},
              {'name': xbmc.getLocalizedString(20343), 'browse': 'folder', 'content': 'tvshow'}
              ],
          'mixed': [
              {'name': ADDON.getLocalizedString(32013), 'info': 'getinprogress'},
              {'name': ADDON.getLocalizedString(32009), 'info': 'getbygenre'}
              ],
          'movie': [
              {'name': ADDON.getLocalizedString(32013), 'info': 'getinprogress'},
              {'name': xbmc.getLocalizedString(20382), 'info': 'getbyargs', 'filter_args': '{"field": "playcount", "operator": "lessthan", "value": "1"}', 'limit': '50', 'sort_args': '{"order": "descending", "method": "dateadded"}'},
              {'name': ADDON.getLocalizedString(32007), 'info': 'getsimilar'},
              {'name': ADDON.getLocalizedString(32014), 'info': 'getsimilar', 'pos': '0'},
              {'name': ADDON.getLocalizedString(32009), 'info': 'getbygenre'},
              {'name': xbmc.getLocalizedString(135), 'info': 'getgenre'},
              {'name': ADDON.getLocalizedString(32012), 'info': 'getbyargs', 'limit': '50', 'sort_args': '{"order": "descending", "method": "rating"}'},
              {'name': xbmc.getLocalizedString(16101), 'info': 'getbyargs', 'filter_args': '{"field": "playcount", "operator": "lessthan", "value": "1"}', 'sort_args': '{"order": "ascending", "method": "title"}'},
              {'name': xbmc.getLocalizedString(590), 'info': 'getbyargs', 'sort_args': '{"method": "random"}', 'limit': '50'}
              ],
          'tvshow': [
              {'name': ADDON.getLocalizedString(32013), 'info': 'getinprogress'},
              {'name': ADDON.getLocalizedString(32008), 'info': 'getnextup'},
              {'name': ADDON.getLocalizedString(32015), 'info': 'getnewshows'},
              {'name': ADDON.getLocalizedString(32010), 'info': 'getnewshows', 'showall': 'true'},
              {'name': ADDON.getLocalizedString(32007), 'info': 'getsimilar'},
              {'name': ADDON.getLocalizedString(32014), 'info': 'getsimilar', 'pos': '0'},
              {'name': ADDON.getLocalizedString(32009), 'info': 'getbygenre'},
              {'name': xbmc.getLocalizedString(135), 'info': 'getgenre'},
              {'name': ADDON.getLocalizedString(32012), 'info': 'getbyargs', 'limit': '50', 'sort_args': '{"order": "descending", "method": "rating"}'},
              {'name': xbmc.getLocalizedString(16101), 'info': 'getbyargs', 'filter_args': '{"field": "numwatched", "operator": "lessthan", "value": "1"}', 'sort_args': '{"order": "ascending", "method": "title"}'},
              {'name': xbmc.getLocalizedString(590), 'info': 'getbyargs', 'sort_args': '{"method": "random"}', 'limit': '50'}
              ]
          }

########################

class PluginListing(object):
    def __init__(self,params,li):
        self.li = li
        self.folder = params.get('folder')
        self.browse = params.get('browse')
        self.tag = params.get('tag')
        self.available_tags = params.get('available_tags')

        if self.browse == 'widgets':
            self.list_widgets()
        elif self.browse == 'folder':
            self.list_folder()
        else:
            self.list_index()


    def list_index(self):
        tags_movies = self._get_tags('movie')
        tags_tvshows = self._get_tags('tvshow')

        for item in LISTING['index']:
            content = item.get('content')
            browse = 'widgets'
            folder = None
            available_tags = None

            if content == 'movie' and tags_movies:
                browse = 'folder'
                available_tags = tags_movies

            elif content == 'tvshow' and tags_tvshows:
                browse = 'folder'
                available_tags = tags_tvshows

            elif content == 'mixed' and (tags_movies or tags_tvshows):
                browse = 'folder'
                available_tags = tags_movies + tags_tvshows


            url = self._encode_url(browse=browse,
                                   folder=content,
                                   available_tags=available_tags,
                                   plugincat=encode_string(item['name'])
                                   )

            self._add_item(item['name'],url)


    def list_folder(self):
        folders = self._generate_subfolder()

        for item in folders:
            url = self._encode_url(browse='widgets',
                                   folder=self.folder,
                                   tag=item.get('tag'),
                                   plugincat=encode_string(item['name'])
                                   )

            self._add_item(item['name'],url)


    def list_widgets(self):
        content_type = self.folder if self.folder in ['tvshow','movie'] else None

        for item in LISTING[self.folder]:
            url = self._encode_url(info=item.get('info'),
                                   type=content_type,
                                   tag=self.tag,
                                   pos=item.get('pos'),
                                   filter_args=item.get('filter_args'),
                                   sort_args=item.get('sort_args'),
                                   limit=item.get('limit'),
                                   showall=item.get('showall'),
                                   plugincat=encode_string(item.get('name'))
                                   )

            self._add_item(item['name'],url)


    def _generate_subfolder(self):
        items = [{'name': ADDON.getLocalizedString(32022), 'browse': 'widgets'}]

        duplicate_handler = []
        for item in eval(self.available_tags):
            if item not in duplicate_handler:
                duplicate_handler.append(item)
                items.append({'name': '"' + item + '" ' + ADDON.getLocalizedString(32023), 'browse': 'widgets', 'tag': item})

        return items


    def _get_tags(self,library):
        tags = []
        json_query = json_call('VideoLibrary.GetTags',
                                properties=['title'],
                                params={'type': library}
                                )

        try:
            for tag in json_query['result']['tags']:
                tags.append(tag.get('label'))
        except KeyError:
            pass

        return tags


    def _encode_url(self,**kwargs):
        empty_keys = [key for key,value in kwargs.items() if not value or value is None]
        for key in empty_keys:
            del kwargs[key]

        return '{0}?{1}'.format(sys.argv[0], urlencode(kwargs))


    def _add_item(self,label,url):
        icon = 'special://home/addons/' + ADDON_ID + '/resources/icon.png'
        list_item = xbmcgui.ListItem(label=label)
        list_item.setInfo('video', {'title': label, 'mediatype': 'video'})
        list_item.setArt({'icon': 'DefaultFolder.png','thumb': icon})
        self.li.append((url, list_item, True))