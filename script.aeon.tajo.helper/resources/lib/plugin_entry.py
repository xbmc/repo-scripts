#!/usr/bin/python

########################

import sys
import xbmcplugin
import urllib.parse as urlparse

from resources.lib.helper import *
from resources.lib.plugin_content import *

########################


class PluginMain:
    # Explicit allowlist of plugin info methods exposed via plugin:// URLs.
    # Restricting dispatch to this whitelist prevents arbitrary method
    # invocation on PluginContent (including private methods).
    ALLOWED_METHODS = {
        'getbydbid',
        'getresourceimages',
        'getitemsbyactor',
        'getcast',
    }

    def __init__(self):
        self._parse_argv()
        self.info = self.params.get('info')

        if self.info:
            self.getinfos()
        else:
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def _parse_argv(self):
        path = sys.argv[2]

        try:
            args = path[1:]
            self.params = dict(urlparse.parse_qsl(args))

            ''' workaround to get the correct values for titles with special characters
            '''
            if ('title=\'"' and '"\'') in args:
                start_pos=args.find('title=\'"')
                end_pos=args.find('"\'')
                clean_title = args[start_pos+8:end_pos]
                self.params['title'] = clean_title

        except Exception:
            self.params = {}

    def getinfos(self):
        li = list()
        plugin = PluginContent(self.params, li)
        method_name = self.info.lower()
        if method_name in self.ALLOWED_METHODS:
            getattr(plugin, method_name)()
        else:
            log('Invalid plugin info method requested: %s' % method_name)
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
