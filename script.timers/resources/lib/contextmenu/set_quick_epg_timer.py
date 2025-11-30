import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import AbstractSetTimer
from resources.lib.timer.concurrency import (ask_overlapping_timers,
                                             get_next_higher_prio,
                                             get_next_lower_prio)
from resources.lib.timer.timer import Timer
from resources.lib.utils.settings_utils import (CONFIRM_CUSTOM, CONFIRM_YES,
                                                trigger_settings_changed_event)


class SetQuickEpgTimer(AbstractSetTimer):

    def perform_ahead(self, timer: Timer) -> bool:

        timers = self.storage.load_timers_from_storage()

        found = -1
        for i, t in enumerate(timers):
            if (found == -1
                    and timer.days == t.days
                    and timer.date == t.date
                    and timer.start == t.start
                    and timer.path == t.path):

                found = i

        if found != -1:
            rv = xbmcgui.Dialog().yesnocustom(heading=self.addon.getLocalizedString(32260),
                                              message="%s\n\n%s" % (timers[found].format("$L\n$H"), self.addon.getLocalizedString(
                                                  32261)),
                                              customlabel=self.addon.getLocalizedString(
                                                  32262),
                                              yeslabel=self.addon.getLocalizedString(
                                                  32263),
                                              nolabel=self.addon.getLocalizedString(
                                                  32022)
                                              )

            if rv == CONFIRM_YES:
                timer.id = timers[found].id
                return True

            elif rv == CONFIRM_CUSTOM:
                self.storage.delete_timer(timers[found].id)
                trigger_settings_changed_event()
                xbmcgui.Dialog().notification(self.addon.getLocalizedString(
                    32000), self.addon.getLocalizedString(32029))

            return False

        return True

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return timer.duration

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, True

    def handle_overlapping_timers(self, timer: Timer, overlapping_timers: 'list[Timer]') -> int:

        strategy = self.addon.getSettingInt("quicktimer_priority")
        if strategy == 0:
            timer.priority = get_next_lower_prio(overlapping_timers)

        elif strategy == 1:
            timer.priority = get_next_higher_prio(overlapping_timers)

        elif strategy == 2:
            return ask_overlapping_timers(timer, overlapping_timers)

        return CONFIRM_YES

    def confirm(self, timer: Timer) -> int:

        return CONFIRM_YES
