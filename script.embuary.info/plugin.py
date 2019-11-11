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
from resources.lib.widgets import *

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
        except Exception:
            self.params = {}

    def listing(self):
        li = list()
        PluginListing(self.params,li)
        self._additems(li)

    def getinfos(self):
        li = list()
        plugin = PluginContent(self.params,li)
        self._execute(plugin,self.info)
        self._additems(li)

    def actions(self):
        plugin = PluginActions(self.params)
        self._execute(plugin,self.action)

    def _execute(self,plugin,action):
        getattr(plugin,action.lower())()

    def _additems(self,li):
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))


if __name__ == '__main__':
    Main()