#!/usr/bin/python

########################

import xbmcplugin

''' Python 2<->3 compatibility
'''
try:
    from urllib2 import urlparse
except ImportError:
    import urllib.parse as urlparse

from resources.lib.helper import *
from resources.lib.plugin_listing import *
from resources.lib.plugin_content import *
from resources.lib.plugin_actions import *

########################

class Main:

    def __init__(self):
        self._parse_argv()
        self.info = self.params.get('info')
        self.action = self.params.get('action')
        if self.info:
            self.getinfos()
        elif self.action:
            self.actions()
        else:
            self.listing()


    def _parse_argv(self):
        base_url = sys.argv[0]
        path = sys.argv[2]

        try:
            args = path[1:]
            self.params = dict(urlparse.parse_qsl(args))

            ''' workaround to get the correct values for titles with special characters
            '''
            if ('title=\'\"' and '\"\'') in args:
                start_pos=args.find('title=\'\"')
                end_pos=args.find('\"\'')
                clean_title = args[start_pos+8:end_pos]
                self.params['title'] = clean_title

        except Exception:
            self.params = {}


    def listing(self):
        li = list()
        plugin = PluginListing(self.params,li)

        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))


    def getinfos(self):
        li = list()
        plugin = PluginContent(self.params,li)

        if self.info == 'getcast':
            plugin.get_cast()
        elif self.info == 'getsimilar':
            plugin.get_similar()
        elif self.info == 'getgenre':
            plugin.get_genre()
        elif self.info == 'getinprogress':
            plugin.get_inprogress()
        elif self.info == 'getnewshows':
            plugin.get_newshows()
        elif self.info == 'getnextup':
            plugin.get_nextup()
        elif self.info == 'getseasonepisodes':
            plugin.get_seasonepisodes()
        elif self.info == 'getseasons':
            plugin.get_seasons()
        elif self.info == 'getbygenre':
            plugin.get_mediabygenre()
        elif self.info == 'getdirectedby':
            plugin.get_directedby()
        elif self.info == 'getitemsbyactor':
            plugin.get_itemsbyactor()
        elif self.info == 'getseasonal':
            plugin.get_seasonal()
        elif self.info == 'jumptoletter':
            plugin.jumptoletter()
        elif self.info == 'bydbid':
            plugin.get_bydbid()
        elif self.info == 'byargs':
            plugin.get_byargs()

        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def actions(self):
        plugin = PluginActions(self.params)

        if self.action == 'smsjump':
            plugin.smsjump()
        elif self.action == 'folderjump':
            plugin.folderjump()


if __name__ == '__main__':
    Main()