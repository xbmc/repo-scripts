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

"""Misc utils"""

from __future__ import absolute_import, unicode_literals

import xbmc
from six import PY2, text_type, binary_type
from xbmcaddon import Addon

try:
    from typing import Text, Optional, Any, Dict  # pylint: disable=unused-import
except ImportError:
    pass

ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')

EPISODE_ORDER_MAP = {
    0: 'default',
    1: 'dvd_release',
    2: 'verbatim_order',
    3: 'country_premiere',
    4: 'streaming_premiere',
    5: 'broadcast_premiere',
    6: 'language_premiere',
}


class logger:
    log_message_prefix = '[{} ({})]: '.format(ADDON_ID, ADDON.getAddonInfo('version'))

    @staticmethod
    def log(message, level=xbmc.LOGDEBUG):
        # type: (Text, int) -> None
        if isinstance(message, binary_type):
            message = message.decode('utf-8')
        message = logger.log_message_prefix + message
        if PY2 and isinstance(message, text_type):
            message = message.encode('utf-8')
        xbmc.log(message, level)

    @staticmethod
    def info(message):
        # type: (Text) -> None
        logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def error(message):
        # type: (Text) -> None
        logger.log(message, xbmc.LOGERROR)

    @staticmethod
    def debug(message):
        # type: (Text) -> None
        logger.log(message, xbmc.LOGDEBUG)


def safe_get(dct, key, default=None):
    # type: (Dict[Text, Any], Text, Any) -> Any
    """
    Get a key from dict

    Returns the respective value or default if key is missing or the value is None.
    """
    if key in dct and dct[key] is not None:
        return dct[key]
    return default


def get_episode_order(path_settings):
    # type: (Dict[Text, Any]) -> Text
    episode_order_enum = path_settings.get('episode_order')
    if episode_order_enum is None:
        episode_order_enum = int(ADDON.getSetting('episode_order'))
    episode_order = EPISODE_ORDER_MAP.get(episode_order_enum, 'default')
    return episode_order
