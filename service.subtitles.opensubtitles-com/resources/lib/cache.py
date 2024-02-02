from __future__ import absolute_import
import json

from time import time

import xbmcgui

from resources.lib.utilities import log


class Cache(object):
    u"""Caches Python values as JSON."""

    def __init__(self, key_prefix=u""):
        self.key_prefix = key_prefix
        self._win = xbmcgui.Window(10000)

    def set(self, key, value, expires=60 * 60 * 24 * 7):

        log(__name__, "caching %s" % (key) )
        if self.key_prefix:
            key = "%s:%s" % (self.key_prefix, key) 

        expires += time()

        cache_data_str = json.dumps(dict(value=value, expires=expires))

        self._win.setProperty(key, cache_data_str)

    def get(self, key, default=None):

        log(__name__, "got request for %s from cache" % (key) )
        result = default

        if self.key_prefix:
            key = "%s:%s" % (self.key_prefix, key) 

        cache_data_str = self._win.getProperty(key)

        if cache_data_str:
            cache_data = json.loads(cache_data_str)
            if cache_data[u"expires"] > time():
                result = cache_data[u"value"]
                log(__name__, "got %s from cache" % (key) )

        return result
