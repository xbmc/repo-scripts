# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from utils import binge_mode, get_setting_bool, get_setting_int
from watchtimer import WatchTimer


# keeps track of the state parameters
class State:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.include_watched = get_setting_bool('includeWatched')
        self.current_tv_show_id = None
        self.current_episode_id = None
        self.tv_show_id = None
        self.played_in_a_row = 1
        self.last_file = None
        self.track = False
        self.pause = False
        self.queued = False
        self.playing_next = False
        self.watch_timer = WatchTimer()

    @property
    def play_mode(self):
        """What to do when nothing is selected (0: play next, 1: stop), read when needed so that
        switching Binge mode or this setting during an episode applies to it"""
        return 0 if binge_mode() else get_setting_int('autoPlayMode')
