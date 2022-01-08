import xbmc
import xbmcgui
from resources.lib.timer import util
from resources.lib.timer.abstract_set_timer import AbstractSetTimer
from resources.lib.timer.timer import (ACTION_STOP_AT_END, END_TYPE_DURATION,
                                       END_TYPE_TIME, SLEEP_TIMER)


class SetSleep(AbstractSetTimer):

    def ask_timer(self):

        return SLEEP_TIMER

    def ask_label(self, listitem, preselection):

        return self.addon.getLocalizedString(32004)

    def ask_duration(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["duration"]

        timer = preselection["timer"]

        if xbmc.getInfoLabel("PVR.EpgEventSeekTime(hh:mm:ss)") != "00:00:00":
            _current = xbmc.getInfoLabel("PVR.EpgEventRemainingTime(hh:mm)")

        elif self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_DURATION:
            _current = self.addon.getSetting("timer_%i_duration" % timer)

        elif self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_TIME:
            _current = util.time_duration_str(self.addon.getSetting(
                "timer_%i_start" % timer), self.addon.getSetting("timer_%i_end" % timer))

        else:
            _current = "01:00"

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, listitem, preselection):

        return ACTION_STOP_AT_END
