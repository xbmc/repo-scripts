# coding: utf-8
# (c) Roman Miroshnychenko <roman1972@gmail.com> 2020
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

"""Monitor Kodi medialibrary updates"""

from __future__ import absolute_import, unicode_literals

import json

import xbmc

from .pulled_episodes_db import PulledEpisodesDb
from . import scrobbling_service as scrobbler
from .kodi_service import logger

try:
    from typing import Text  # pylint: disable=unused-import
except ImportError:
    pass


class KodiMonitor(xbmc.Monitor):  # pylint: disable=missing-docstring

    def onNotification(self, sender, method, data):
        # type: (Text, Text, Text) -> None
        """
        Example arguments::
            sender: xbmc
            method: VideoLibrary.OnUpdate
            data: {"item":{"id":10,"type":"episode"},"playcount":1}
        """
        if method == 'VideoLibrary.OnUpdate' and 'playcount' in data:
            item = json.loads(data)['item']
            if item.get('type') == 'episode':
                with PulledEpisodesDb() as database:
                    is_pulled = database.is_pulled(item['id'])
                if not is_pulled:
                    logger.debug('Updating episode details: {}'.format(data))
                    scrobbler.push_single_episode(item['id'])

    def onScanFinished(self, library):
        # type: (Text) -> None
        if library == 'video':
            scrobbler.sync_recent_episodes(show_warning=False)
            logger.debug('Recent episodes updated')
