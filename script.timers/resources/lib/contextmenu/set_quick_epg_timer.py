import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_YES,
                                                          AbstractSetTimer)
from resources.lib.timer import storage
from resources.lib.timer.timer import Timer


class SetQuickEpgTimer(AbstractSetTimer):

    def perform_ahead(self, timer: Timer) -> bool:

        timers = storage.load_timers_from_storage()

        found = -1
        for i, t in enumerate(timers):
            if (found == -1
                    and timer.days == t.days
                    and timer.start == t.start
                    and timer.path == t.path):

                found = i

        if found != -1:
            timer.id = timers[found].id

        return True

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return timer.duration

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, True

    def confirm(self, timer: Timer) -> int:

        return CONFIRM_YES
