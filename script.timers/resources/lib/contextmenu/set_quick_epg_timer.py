import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_YES,
                                                          AbstractSetTimer)
from resources.lib.contextmenu.selection import Selection
from resources.lib.contextmenu.set_timer import SetTimer
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.timer import TIMER_OFF


class SetQuickEpgTimer(AbstractSetTimer):

    def perform_ahead(self, preselection: Selection) -> bool:

        found = -1
        for i in range(2, TIMERS):
            if found == -1 and self.addon.getSettingInt("timer_%i" % i) == preselection.activation and preselection.startTime == self.addon.getSettingString("timer_%s_start" % i) and preselection.path == self.addon.getSettingString("timer_%s_filename" % i):
                found = i

        if found != -1:
            preselection.timer = found

        preselection.fade = 0
        return True

    def ask_timer(self):

        free_slots = [i for i in range(2, TIMERS) if self.addon.getSettingInt(
            "timer_%i" % i) == TIMER_OFF]

        if len(free_slots) > 0:
            return free_slots[0]

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32027), self.addon.getLocalizedString(32115))

        SetTimer(self.listitem)

        return None

    def ask_duration(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        return preselection.duration

    def ask_repeat_resume(self, preselection: Selection) -> 'tuple[bool, bool]':

        return False, True

    def confirm(self, preselection: Selection) -> int:

        line1 = preselection.label

        line2 = (self.addon.getLocalizedString(32024)) % (
            self.addon.getLocalizedString(32200 + preselection.activation),
            preselection.startTime,
            preselection.endTime)

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32116) % self.addon.getLocalizedString(32004 + preselection.timer), "\n".join([line1, line2]))

        return CONFIRM_YES
