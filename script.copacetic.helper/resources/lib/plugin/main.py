# author: realcopacetic, sualfred

import urllib.parse as urllib

import xbmcplugin

from resources.lib.plugin.content import *
from resources.lib.utilities import sys
from resources.lib.plugin.listing import PluginListing


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
        path = sys.argv[2]

        try:
            args = path[1:]
            self.params = dict(urllib.parse_qsl(args))

            ''' Workaround to get the correct values for titles with special characters
            '''
            if ('title=\'\"' and '\"\'') in args:
                start_pos = args.find('title=\'\"')
                end_pos = args.find('\"\'')
                clean_title = args[start_pos+8:end_pos]
                self.params['title'] = clean_title

        except Exception:
            self.params = {}

    def getinfos(self):
        li = list()
        plugin = PluginContent(self.params, li)
        self._execute(plugin, self.info)
        self._additems(li)

    def listing(self):
        li = list()
        PluginListing(self.params,li)
        self._additems(li)

    def _execute(self, plugin, action):
        getattr(plugin, action.lower())()

    def _additems(self, li):
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))