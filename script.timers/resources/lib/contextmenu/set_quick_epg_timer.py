import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_YES,
                                                          AbstractSetTimer)
from resources.lib.contextmenu.set_timer import SetTimer
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.timer import FADE_OFF, Timer


class SetQuickEpgTimer(AbstractSetTimer):

    def perform_ahead(self, timer: Timer) -> bool:

        found = -1
        for i in range(2, TIMERS):
            label, path, start, days = Timer.get_quick_info(i)
            if (found == -1
                    and timer.days == days
                    and timer.s_start == start
                    and timer.s_path == path):

                found = i

        if found != -1:
            timer.i_timer = found

        timer.i_fade = FADE_OFF
        return True

    def ask_timer(self, timerid: int) -> int:

        free_slots = [i for i in range(2, TIMERS) if self.addon.getSetting(
            "timer_%i_days" % i) == ""]

        if len(free_slots) > 0:
            return free_slots[0]

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32027), self.addon.getLocalizedString(32115))

        SetTimer(self._label, self._path)

        return None

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return timer.s_duration

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, True

    def confirm(self, timer: Timer) -> int:

        line1 = timer.s_label

        line2 = (self.addon.getLocalizedString(32024)) % (
            self.days_to_short(timer.days),
            timer.s_start,
            timer.s_end)

        xbmcgui.Dialog().notification(self.addon.getLocalizedString(
            32116) % self.addon.getLocalizedString(32004 + timer.i_timer), "\n".join([line1, line2]))

        return CONFIRM_YES
