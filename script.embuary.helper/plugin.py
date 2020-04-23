#!/usr/bin/python

########################

import xbmcplugin
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