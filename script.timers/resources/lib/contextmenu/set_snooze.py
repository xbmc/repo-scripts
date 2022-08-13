import time

import xbmc
import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.player import player_utils
from resources.lib.player.mediatype import AUDIO, VIDEO
from resources.lib.timer.timer import (MEDIA_ACTION_STOP_START,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils.datetime_utils import DEFAULT_TIME


class SetSnooze(AbstractSetTimer):

    def is_supported(self, label: str, path: str) -> bool:

        return True

    def perform_ahead(self, timer: Timer) -> bool:

        apwpl = player_utils.get_active_players_with_playlist()
        if apwpl and (VIDEO in apwpl or AUDIO in apwpl):
            state = apwpl[VIDEO] if VIDEO in apwpl else apwpl[AUDIO]
            timer.path = player_utils.add_player_state_to_path(state)
            return True

        return super().is_supported(label=timer.label, path=timer.path)

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return self.addon.getLocalizedString(32005)

    def ask_starttime(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return time.strftime("%H:%M", time.localtime())

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        _default_duration = self.addon.getSetting("snooze_default_duration")
        _current = timer.get_duration()
        _current = _default_duration if DEFAULT_TIME else _current

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, False

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_STOP_START

    def post_apply(self, timer: Timer, confirm: int) -> None:

        xbmc.Player().stop()
