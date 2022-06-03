import xbmc
import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.timer.timer import (MEDIA_ACTION_START,
                                       MEDIA_ACTION_START_AT_END, SNOOZE_TIMER,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils.datetime_utils import DEFAULT_TIME


class SetSnooze(AbstractSetTimer):

    def is_supported(self, label: str, path: str) -> bool:

        return True

    def ask_timer(self, timerid: int) -> int:

        return SNOOZE_TIMER

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return self.addon.getLocalizedString(32005)

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return DEFAULT_TIME

        _current = timer.get_duration()
        _current = "00:10" if DEFAULT_TIME else _current

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        if is_epg:
            return SYSTEM_ACTION_NONE, MEDIA_ACTION_START

        else:
            return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_AT_END

    def post_apply(self, timer: Timer, confirm: int) -> None:

        xbmc.Player().stop()
