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

index = [
        {'name': ADDON.getLocalizedString(32011), 'action': 'folder', 'type': 'mixed'},
        {'name': xbmc.getLocalizedString(342), 'action': 'folder', 'type': 'movies'},
        {'name': xbmc.getLocalizedString(20343), 'action': 'folder', 'type': 'tvshows'}
        ]

mixed = [
        {'name': ADDON.getLocalizedString(32013), 'action': 'getinprogress'},
        {'name': ADDON.getLocalizedString(32009), 'action': 'getbygenre'}
        ]

movies = [
        {'name': ADDON.getLocalizedString(32013), 'action': 'getinprogress'},
        {'name': ADDON.getLocalizedString(32007), 'action': 'getsimilar'},
        {'name': ADDON.getLocalizedString(32014), 'action': 'getsimilar', 'pos': '0'},
        {'name': ADDON.getLocalizedString(32009), 'action': 'getbygenre'},
        {'name': xbmc.getLocalizedString(135), 'action': 'getgenre'}
        ]

tvshows = [
        {'name': ADDON.getLocalizedString(32013), 'action': 'getinprogress'},
        {'name': ADDON.getLocalizedString(32008), 'action': 'getnextup'},
        {'name': ADDON.getLocalizedString(32015), 'action': 'getnewshows'},
        {'name': ADDON.getLocalizedString(32010), 'action': 'getnewshows', 'showall': 'true'},
        {'name': ADDON.getLocalizedString(32007), 'action': 'getsimilar'},
        {'name': ADDON.getLocalizedString(32014), 'action': 'getsimilar', 'pos': '0'},
        {'name': ADDON.getLocalizedString(32009), 'action': 'getbygenre'},
        {'name': xbmc.getLocalizedString(135), 'action': 'getgenre'}
        ]

emby_movies = [
        {'name': ADDON.getLocalizedString(32013), 'action': 'getinprogress'},
        {'name': xbmc.getLocalizedString(20382), 'action': 'getbyargs', 'filter': '{"field": "playcount", "operator": "lessthan", "value": "1"}', 'limit': '50', 'sort': '{"order": "descending", "method": "dateadded"}'},
        {'name': ADDON.getLocalizedString(32007), 'action': 'getsimilar'},
        {'name': ADDON.getLocalizedString(32014), 'action': 'getsimilar', 'pos': '0'},
        {'name': ADDON.getLocalizedString(32009), 'action': 'getbygenre'},
        {'name': ADDON.getLocalizedString(32012), 'action': 'getbyargs', 'limit': '50', 'sort': '{"order": "descending", "method": "rating"}'},
        {'name': xbmc.getLocalizedString(16101), 'action': 'getbyargs', 'filter': '{"field": "playcount", "operator": "lessthan", "value": "1"}', 'sort': '{"order": "ascending", "method": "title"}'},
        {'name': xbmc.getLocalizedString(590), 'action': 'getbyargs', 'sort': '{"method": "random"}', 'limit': '50'},
        ]

emby_tvshows = [
        {'name': ADDON.getLocalizedString(32013), 'action': 'getinprogress'},
        {'name': ADDON.getLocalizedString(32008), 'action': 'getnextup'},
        {'name': ADDON.getLocalizedString(32015), 'action': 'getnewshows'},
        {'name': ADDON.getLocalizedString(32010), 'action': 'getnewshows', 'showall': 'true'},
        {'name': ADDON.getLocalizedString(32007), 'action': 'getsimilar'},
        {'name': ADDON.getLocalizedString(32014), 'action': 'getsimilar', 'pos': '0'},
        {'name': ADDON.getLocalizedString(32009), 'action': 'getbygenre'},
        {'name': ADDON.getLocalizedString(32012), 'action': 'getbyargs', 'limit': '50', 'sort': '{"order": "descending", "method": "rating"}'},
        {'name': xbmc.getLocalizedString(16101), 'action': 'getrbyargs', 'filter': '{"field": "numwatched", "operator": "lessthan", "value": "1"}', 'sort': '{"order": "ascending", "method": "title"}'},
        {'name': xbmc.getLocalizedString(590), 'action': 'getbyargs', 'sort': '{"method": "random"}', 'limit': '50'},
        ]

########################

class PluginListing(object):

    def __init__(self,params,li):
        self.li = li
        self.folder = params.get('folder','')
        self.tag = params.get('tag','')
        self.cat_type = None

        if self.folder:
            if 'tvshows' in self.folder:
                self.cat_type = 'tvshow'
            elif 'movies' in self.folder:
                self.cat_type = 'movie'

            self.widgets()

        else:
            self.folders()


    def folders(self):
        for folder in index:
            url = self._encode_url(folder=folder['type'])
            self._add_item(folder['name'],url)

        if visible('System.HasAddon(plugin.video.emby'):
            i = 0
            for prop in range(30):
                tag = winprop('emby.wnodes.%s.cleantitle' % i)
                database = winprop('emby.wnodes.%s.type' % i)

                if database == 'movies' or database == 'tvshows':
                    label = 'Emby: %s' % winprop('emby.wnodes.%s.title' % i)
                    url = self._encode_url(folder='emby_%s' % database,tag=tag)
                    self._add_item(label,url)

                i += 1


    def widgets(self):
        for widget in globals()[self.folder]:
            url = self._get_url(widget)
            self._add_item(widget['name'],url)


    def _get_url(self,widget):
        return self._encode_url(info=widget['action'], type=self.cat_type, tag=self.tag, pos=widget.get('pos',''), filter_args=widget.get('filter',''), sort_args=widget.get('sort',''), limit=widget.get('limit',''), showall=widget.get('showall',''))


    def _encode_url(self,**kwargs):
        empty_keys = [key for key,value in kwargs.iteritems() if not value or value is None]
        for key in empty_keys:
            del kwargs[key]

        return '{0}?{1}'.format(sys.argv[0], urlencode(kwargs))


    def _add_item(self,label,url):
        icon = 'special://home/addons/script.embuary.helper/resources/icon.png'
        source = self.folder or url

        if 'emby_' in source:
            icon = 'special://home/addons/plugin.video.emby/icon.png'

        list_item = xbmcgui.ListItem(label=label)
        list_item.setInfo('video', {'title': label, 'mediatype': 'video'})
        list_item.setArt({'icon': 'DefaultFolder.png','thumb': icon})
        self.li.append((url, list_item, True))
