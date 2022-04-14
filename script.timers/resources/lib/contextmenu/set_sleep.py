import xbmc
import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.contextmenu.selection import Selection
from resources.lib.timer.timer import (END_TYPE_DURATION, END_TYPE_TIME,
                                       MEDIA_ACTION_STOP_AT_END, SLEEP_TIMER,
                                       SYSTEM_ACTION_NONE)
from resources.lib.utils import datetime_utils


class SetSleep(AbstractSetTimer):

    def is_listitem_valid(self, listitem: xbmcgui.ListItem) -> bool:

        return True

    def ask_timer(self) -> int:

        return SLEEP_TIMER

    def ask_label(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        return self.addon.getLocalizedString(32004)

    def ask_duration(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        if preselection.epg:
            return preselection.duration

        timer = preselection.timer

        if xbmc.getInfoLabel("PVR.EpgEventSeekTime(hh:mm:ss)") != "00:00:00":
            _current = xbmc.getInfoLabel("PVR.EpgEventRemainingTime(hh:mm)")

        elif self.addon.getSettingInt("timer_%i_end_type" % timer) == END_TYPE_DURATION:
            _current = self.addon.getSetting("timer_%i_duration" % timer)

        elif self.addon.getSettingInt("timer_%i_end_type" % timer) == END_TYPE_TIME:
            _current = datetime_utils.time_duration_str(self.addon.getSettingString(
                "timer_%i_start" % timer), self.addon.getSetting("timer_%i_end" % timer))

        else:
            _current = "01:00"

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, listitem: xbmcgui.ListItem, preselection: Selection) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_STOP_AT_END
