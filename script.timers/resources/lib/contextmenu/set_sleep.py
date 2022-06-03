import xbmc
import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.timer.timer import (MEDIA_ACTION_STOP_AT_END, SLEEP_TIMER,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils.datetime_utils import DEFAULT_TIME


class SetSleep(AbstractSetTimer):

    def is_supported(self, label: str, path: str) -> bool:

        return True

    def ask_timer(self, timerid: int) -> int:

        return SLEEP_TIMER

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return self.addon.getLocalizedString(32004)

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.s_duration

        if xbmc.getInfoLabel("PVR.EpgEventSeekTime(hh:mm:ss)") != "00:00:00":
            _current = xbmc.getInfoLabel("PVR.EpgEventRemainingTime(hh:mm)")

        else:
            _current = timer.get_duration()
            _current = "01:00" if DEFAULT_TIME else _current

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_STOP_AT_END
