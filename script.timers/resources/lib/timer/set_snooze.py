import xbmc
import xbmcgui
from resources.lib.timer import util
from resources.lib.timer.abstract_set_timer import (DURATION_NO,
                                                    AbstractSetTimer)
from resources.lib.timer.scheduler import (ACTION_START, ACTION_START_AT_END,
                                           END_TYPE_DURATION, END_TYPE_TIME,
                                           SNOOZE_TIMER)


class SetSnooze(AbstractSetTimer):

    def ask_timer(self):

        return SNOOZE_TIMER

    def ask_label(self, listitem, preselection):

        return self.addon.getLocalizedString(32010)

    def ask_duration(self, listitem, preselection):

        if preselection["epg"]:
            return DURATION_NO

        timer = preselection["timer"]

        if self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_DURATION:
            _current = self.addon.getSetting("timer_%i_duration" % timer)

        elif self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_TIME:
            _current = util.time_duration_str(self.addon.getSetting(
                "timer_%i_start" % timer), self.addon.getSetting("timer_%i_end" % timer))

        else:
            _current = "00:10"

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), _current)
        if duration in ["", "0:00", "00:00"]:
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, listitem, preselection):

        if preselection["epg"]:
            return ACTION_START

        else:
            return ACTION_START_AT_END

    def post_apply(self, selection, confirm):

        xbmc.Player().stop()
