# coding: utf-8
#
# Copyright (C) 2019, Roman Miroshnychenko aka Roman V.M. <roman1972@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Cache-related functionality"""

from __future__ import absolute_import, unicode_literals

import io
import json
import os
import time

import six
import xbmcgui
import xbmcvfs

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

from .utils import ADDON_ID, logger

try:
    from typing import Optional, Text, Dict, Any, Union  # pylint: disable=unused-import
except ImportError:
    pass


EPISODES_CACHE_TTL = 60 * 10  # 10 minutes


class MemoryCache(object):  # pylint: disable=useless-object-inheritance
    CACHE_KEY = '__tvmaze_scraper__'

    def __init__(self):
        self._window = xbmcgui.Window(10000)

    def set(self, obj_id, obj):
        # type: (Union[int, Text], Any) -> None
        cache = {
            'id': obj_id,
            'timestamp': time.time(),
            'object': obj,
        }
        cache_json = json.dumps(cache)
        self._window.setProperty(self.CACHE_KEY, cache_json)

    def get(self, obj_id):
        # type: (Union[int, Text]) -> Optional[Any]
        cache_json = self._window.getProperty(self.CACHE_KEY)
        if not cache_json:
            logger.debug('Memory cache empty')
            return None
        try:
            cache = json.loads(cache_json)
        except ValueError as exc:
            logger.debug('Memory cache error: {}'.format(exc))
            return None
        if cache['id'] != obj_id or time.time() - cache['timestamp'] > EPISODES_CACHE_TTL:
            logger.debug('Memory cache miss')
            return None
        logger.debug('Memory cache hit')
        return cache['object']


MEMORY_CACHE = MemoryCache()


def cache_episodes_map(show_id, episodes_map):
    # type: (Union[int, Text], Dict[Text, Any]) -> None
    MEMORY_CACHE.set(int(show_id), episodes_map)


def load_episodes_map_from_cache(show_id):
    # type: (Union[int, Text]) -> Optional[Dict[Text, Any]]
    episodes_map = MEMORY_CACHE.get(int(show_id))
    return episodes_map


def _get_cache_directory():  # pylint: disable=missing-docstring
    # type: () -> Text
    temp_dir = translatePath('special://temp')
    if isinstance(temp_dir, bytes):
        temp_dir = temp_dir.decode('utf-8')
    cache_dir = os.path.join(temp_dir, 'scrapers', ADDON_ID)
    if not xbmcvfs.exists(cache_dir):
        xbmcvfs.mkdir(cache_dir)
    return cache_dir


CACHE_DIR = _get_cache_directory()  # type: Text


def cache_show_info(show_info):
    # type: (Dict[Text, Any]) -> None
    """
    Save show_info dict to cache
    """
    file_name = str(show_info['id']) + '.json'
    cache_json = json.dumps(show_info)
    if isinstance(cache_json, six.text_type):
        cache_json = cache_json.encode('utf-8')
    with open(os.path.join(CACHE_DIR, file_name), 'wb') as fo:
        fo.write(cache_json)


def load_show_info_from_cache(show_id):
    # type: (Text) -> Optional[Dict[Text, Any]]
    """
    Load show info from a local cache

    :param show_id: show ID on TVmaze
    :return: show_info dict or None
    """
    file_name = str(show_id) + '.json'
    try:
        with io.open(os.path.join(CACHE_DIR, file_name), 'r',
                     encoding='utf-8') as fo:
            cache_json = fo.read()
        show_info = json.loads(cache_json)
        logger.debug('Show info cache hit')
        return show_info
    except (IOError, EOFError, ValueError) as exc:
        logger.debug('Cache error: {} {}'.format(type(exc), exc))
        return None
