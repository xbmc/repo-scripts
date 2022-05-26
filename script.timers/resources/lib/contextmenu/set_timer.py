import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_EDIT,
                                                          AbstractSetTimer)
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.timer import (MEDIA_ACTION_START,
                                       MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils.datetime_utils import DEFAULT_TIME


class SetTimer(AbstractSetTimer):

    def ask_timer(self, timerid: int) -> int:

        options = [self.addon.getLocalizedString(32102)]
        for i in range(2, TIMERS):
            label, path, start, days = Timer.get_quick_info(i)
            options.append("%i: %s (%s%s)" % (
                i - 1,
                label,
                self.days_to_short(
                    days) or self.addon.getLocalizedString(32034),
                ", %s" % start if days else ""
            ))

        selection = xbmcgui.Dialog().select(
            self.addon.getLocalizedString(32103), options, preselect=0)
        if selection == -1:
            return None
        elif selection == 0:
            self.addon.openSettings()
            return None
        else:
            return selection + 1

    def ask_days(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'list[int]':

        if is_epg:
            return timer.days

        options = [self.addon.getLocalizedString(32200 + i) for i in range(7)]
        options.append(self.addon.getLocalizedString(32036))

        selection = xbmcgui.Dialog().multiselect(
            self.addon.getLocalizedString(32104), options, preselect=timer.days)
        if not selection:
            return None
        else:
            return selection

    def ask_starttime(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.s_start

        start = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32105), timer.s_start)
        if start == "":
            return None
        else:
            return ("0%s" % start.strip())[-5:]

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.s_duration

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), timer.s_duration)
        if duration == "":
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, timer.s_duration != DEFAULT_TIME

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_STOP if timer.s_duration != DEFAULT_TIME else MEDIA_ACTION_START

    def confirm(self, timer: Timer) -> int:

        line1 = timer.s_label

        line2 = (self.addon.getLocalizedString(32024) if timer.s_duration != DEFAULT_TIME else self.addon.getLocalizedString(32025)) % (
            self.days_to_short(timer.days),
            timer.s_start,
            timer.s_end if timer.s_duration != DEFAULT_TIME else "")

        line3 = "%s: %s" % (self.addon.getLocalizedString(32070),
                            self.addon.getLocalizedString(
                                32072) if timer.s_duration != DEFAULT_TIME else self.addon.getLocalizedString(32073)
                            )

        line4 = "%s: %s" % (self.addon.getLocalizedString(32091),
                            self.addon.getLocalizedString(32120 + timer.i_fade))

        return xbmcgui.Dialog().yesnocustom(self.addon.getLocalizedString(32107) % self.addon.getLocalizedString(32004 + timer.i_timer),
                                            "\n".join(
                                                [line1, line2, line3, line4]),
                                            self.addon.getLocalizedString(
                                                32021),
                                            self.addon.getLocalizedString(
                                                32022),
                                            self.addon.getLocalizedString(32023))

    def post_apply(self, timer: Timer, confirm: int) -> None:

        if confirm == CONFIRM_EDIT:
            self.addon.openSettings()
