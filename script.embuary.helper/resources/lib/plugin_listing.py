#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcgui
from urllib.parse import urlencode

from resources.lib.helper import *

########################

LISTING = {
          'index': [
              {'name': ADDON.getLocalizedString(32011), 'browse': 'folder', 'content': 'mixed'},
              {'name': xbmc.getLocalizedString(342), 'browse': 'folder', 'content': 'movie'},
              {'name': xbmc.getLocalizedString(20343), 'browse': 'folder', 'content': 'tvshow'},
              {'name': ADDON.getLocalizedString(32036), 'browse': 'widgets', 'content': 'seasonal'}
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
              ],
          'seasonal': [
              {'name': ADDON.getLocalizedString(32032), 'info': 'getseasonal', 'list': 'xmas'},
              {'name': ADDON.getLocalizedString(32032) + ' (' + xbmc.getLocalizedString(342) + ')', 'info': 'getseasonal', 'list': 'xmas', 'type': 'movie'},
              {'name': ADDON.getLocalizedString(32032) + ' (' + xbmc.getLocalizedString(20343) + ')', 'info': 'getseasonal', 'list': 'xmas', 'type': 'tvshow'},
              {'name': ADDON.getLocalizedString(32033) + ' (Halloween)', 'info': 'getseasonal', 'list': 'horror'},
              {'name': ADDON.getLocalizedString(32033) + ' (Halloween - ' + xbmc.getLocalizedString(342) + ')', 'info': 'getseasonal', 'list': 'horror', 'type': 'movie'},
              {'name': ADDON.getLocalizedString(32033) + ' (Halloween - ' + xbmc.getLocalizedString(20343) + ')', 'info': 'getseasonal', 'list': 'horror', 'type': 'tvshow'},
              {'name': ADDON.getLocalizedString(32034) + ' (Star Wars)', 'info': 'getseasonal', 'list': 'starwars'},
              {'name': ADDON.getLocalizedString(32035) + ' (Star Trek)', 'info': 'getseasonal', 'list': 'startrek'}
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

        if self.folder == 'movie':
            self.plugin_category = xbmc.getLocalizedString(342)
        elif self.folder == 'tvshow':
            self.plugin_category = xbmc.getLocalizedString(20343)
        elif self.folder == 'mixed':
            self.plugin_category = ADDON.getLocalizedString(32011)
        else:
            self.plugin_category = ''

        if self.tag and self.plugin_category:
            self.plugin_category = self.plugin_category + ' (' + self.tag + ')'

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
                                   available_tags=available_tags
                                   )

            self._add_item(item['name'], url)

    def list_folder(self):
        folders = self._generate_subfolder()

        for item in folders:
            url = self._encode_url(browse='widgets',
                                   folder=self.folder,
                                   tag=item.get('tag')
                                   )

            self._add_item(item['name'], url)

    def list_widgets(self):
        content_type = self.folder if self.folder in ['tvshow','movie'] else None

        for item in LISTING[self.folder]:
            if item.get('info') == 'getbyargs':
                category_label = item.get('name')
            else:
                category_label = None

            if content_type == None and item.get('type') in ['tvshow','movie']:
                dbtype = item.get('type')
            else:
                dbtype = content_type

            url = self._encode_url(info=item.get('info'),
                                   type=dbtype,
                                   tag=self.tag,
                                   pos=item.get('pos'),
                                   filter_args=item.get('filter_args'),
                                   sort_args=item.get('sort_args'),
                                   limit=item.get('limit'),
                                   showall=item.get('showall'),
                                   list=item.get('list'),
                                   category_label=category_label
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
        empty_keys = [key for key,value in list(kwargs.items()) if not value or value is None]
        for key in empty_keys:
            del kwargs[key]

        return '{0}?{1}'.format(sys.argv[0], urlencode(kwargs))

    def _add_item(self,label,url):
        icon = 'special://home/addons/' + ADDON_ID + '/resources/icon.png'
        list_item = xbmcgui.ListItem(label=label, offscreen=True)
        list_item.setInfo('video', {'title': label, 'mediatype': 'video'})
        list_item.setArt({'icon': 'DefaultFolder.png','thumb': icon})
        self.li.append((url, list_item, True))
        set_plugincontent(content='videos', category=self.plugin_category)