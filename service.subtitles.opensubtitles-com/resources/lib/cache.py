import json

from time import time

import xbmcgui

from resources.lib.utilities import log


class Cache(object):
    """Caches Python values as JSON."""

    def __init__(self, key_prefix=""):
        self.key_prefix = key_prefix
        self._win = xbmcgui.Window(10000)

    def set(self, key, value, expires=60 * 60 * 24 * 7):

        log(__name__, f"caching {key}")
        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        expires += time()

        cache_data_str = json.dumps(dict(value=value, expires=expires))

        self._win.setProperty(key, cache_data_str)

    def get(self, key, default=None):

        log(__name__, f"got request for {key} from cache")
        result = default

        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        cache_data_str = self._win.getProperty(key)

        if cache_data_str:
            cache_data = json.loads(cache_data_str)
            if cache_data["expires"] > time():
                result = cache_data["value"]
                log(__name__, f"got {key} from cache")

        return result
