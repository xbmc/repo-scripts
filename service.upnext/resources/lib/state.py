# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from . import utils


# keeps track of the state parameters
class State:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.play_mode = utils.settings('autoPlayMode')
        self.short_play_mode = utils.settings('shortPlayMode')
        self.short_play_notification = utils.settings('shortPlayNotification')
        self.short_play_length = int(utils.settings('shortPlayLength')) * 60
        self.include_watched = utils.settings('includeWatched') == 'true'
        self.current_tv_show_id = None
        self.current_episode_id = None
        self.tv_show_id = None
        self.played_in_a_row = 1
        self.last_file = None
        self.track = False
        self.pause = False
