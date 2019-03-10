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
from resources.lib.plugin_content import *
from resources.lib.plugin_utils import *

########################

class Main:

    def __init__(self):
        self._parse_argv()
        self.info = self.params.get('info')
        self.action = self.params.get('action')
        if self.info:
            self.getinfos()
        if self.action:
            self.actions()

    def _parse_argv(self):

        base_url = sys.argv[0]
        path = sys.argv[2]

        try:
            self.params = dict(urlparse.parse_qsl(path[1:]))
        except Exception:
            self.params = {}

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
            plugin.get_directed_by()
        elif self.info == 'getseasonal':
            plugin.get_seasonal()
        elif self.info == 'jumptoletter':
            plugin.jumptoletter()

        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def actions(self):
        if self.action == 'smsjump':
            smsjump(self.params)
        elif self.action == 'jumptoshow':
            jumptoshow(self.params)
        elif self.action == 'jumptoseason':
            jumptoseason(self.params)

if __name__ == '__main__':
    Main()