import xbmc
import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.timer.timer import MEDIA_ACTION_STOP_AT_END, Timer
from resources.lib.utils import datetime_utils


class SetSleep(AbstractSetTimer):

    def is_supported(self, label: str, path: str) -> bool:

        return True

    def perform_ahead(self, timer: Timer) -> bool:

        timer.notify = False
        return True

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return self.addon.getLocalizedString(32004)

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.duration

        seektime = xbmc.getInfoLabel("PVR.EpgEventSeekTime(hh:mm:ss)")
        if seektime and xbmc.getInfoLabel("PVR.EpgEventSeekTime(hh:mm:ss)") != "00:00:00":
            _current = xbmc.getInfoLabel("PVR.EpgEventRemainingTime(hh:mm)")

        else:
            _default_duration = self.addon.getSetting("sleep_default_duration")
            _current = timer.get_duration()
            _current = _default_duration if datetime_utils.DEFAULT_TIME else _current

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return self.addon.getSettingInt("sleep_system_action"), MEDIA_ACTION_STOP_AT_END

    def ask_fader(self, timer: Timer) -> 'tuple[int, int, int]':

        return self.addon.getSettingInt("sleep_fade"), self.addon.getSettingInt("vol_min_default"), self.addon.getSettingInt("vol_default")
