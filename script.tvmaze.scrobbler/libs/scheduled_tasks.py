# coding: utf-8
# (c) Roman Miroshnychenko <roman1972@gmail.com> 2021
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

"""Periodic tasks"""

from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

import xbmc

from .kodi_service import ADDON, logger
from .scrobbling_service import pull_watched_episodes

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def _should_pull():
    pull_enabled = ADDON.getSettingBool('periodic_pull')
    pull_during_playback = ADDON.getSettingBool('pull_during_playback')
    player_has_media = xbmc.getCondVisibility('Player.HasMedia')
    return pull_enabled and (not player_has_media or pull_during_playback)


def periodic_pull():
    if _should_pull():
        now = datetime.now()
        pull_interval_hours_str = ADDON.getSettingString('pull_interval_hours')
        if not pull_interval_hours_str:
            logger.error('Pulling interval is not set')
            return
        pull_interval_hours = int(pull_interval_hours_str)
        time_last_pulled_str = ADDON.getSettingString('time_last_pulled')
        time_last_pulled = (datetime.strptime(time_last_pulled_str, TIME_FORMAT)
                            if time_last_pulled_str else None)
        if (time_last_pulled is None
                or now - timedelta(hours=pull_interval_hours) > time_last_pulled):
            pull_watched_episodes()
            ADDON.setSettingString('time_last_pulled', now.strftime(TIME_FORMAT))
            logger.info('Pulled watched episodes from TVmaze')
