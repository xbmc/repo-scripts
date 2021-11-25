import xbmcgui
from resources.lib.timer.abstract_set_timer import (CONFIRM_YES,
                                                    AbstractSetTimer)
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.set_timer import SetTimer
from resources.lib.timer.timer import TIMER_OFF


class SetQuickEpgTimer(AbstractSetTimer):

    def perform_ahead(self, preselection):

        found = -1
        for i in range(2, TIMERS):
            if found == -1 and self.addon.getSetting("timer_%i" % i) == str(preselection["activation"]) and preselection["starttime"] == self.addon.getSetting("timer_%s_start" % i) and preselection["path"] == self.addon.getSetting("timer_%s_filename" % i):
                found = i

        if found != -1:
            preselection["timer"] = found

        preselection["fade"] = 0
        return True

    def ask_timer(self):

        free_slots = [i for i in range(2, TIMERS) if self.addon.getSetting(
            "timer_%i" % i) == TIMER_OFF]

        if len(free_slots) > 0:
            return free_slots[0]

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32027), self.addon.getLocalizedString(32115))

        SetTimer(self.listitem)

        return None

    def ask_duration(self, listitem, preselection):

        return preselection["duration"]

    def confirm(self, preselection):

        line1 = preselection["label"]

        line2 = (self.addon.getLocalizedString(32024)) % (
            self.addon.getLocalizedString(32034 + preselection["activation"]),
            preselection["starttime"],
            preselection["endtime"])

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32116) % self.addon.getLocalizedString(32004 + preselection["timer"]), "\n".join([line1, line2]))

        return CONFIRM_YES
