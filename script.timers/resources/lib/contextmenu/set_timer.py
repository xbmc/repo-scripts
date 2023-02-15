import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_CUSTOM,
                                                          AbstractSetTimer)
from resources.lib.timer.concurrency import ask_overlapping_timers
from resources.lib.timer.timer import (MEDIA_ACTION_START,
                                       MEDIA_ACTION_START_STOP, Timer)
from resources.lib.utils.datetime_utils import DEFAULT_TIME
from resources.lib.utils.settings_utils import (load_timer_into_settings,
                                                select_timer)


class SetTimer(AbstractSetTimer):

    def ask_timer(self, timerid: int) -> int:

        extra = ["<%s>" % self.addon.getLocalizedString(
            32250), "<%s>" % self.addon.getLocalizedString(32102)]
        timers, idx = select_timer(extra=extra)

        if not idx:
            return None

        elif idx[0] == 0:
            return super().ask_timer(timerid)

        elif idx[0] == 1:
            self.addon.openSettings()
            return None

        elif idx[0] > 1:
            return timers[idx[0] - 2].id

    def ask_days(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'list[int]':

        options = [self.addon.getLocalizedString(32200 + i) for i in range(7)]
        options.append(self.addon.getLocalizedString(32036))

        selection = xbmcgui.Dialog().multiselect(
            self.addon.getLocalizedString(32104), options, preselect=timer.days)
        if not selection:
            return None
        else:
            return selection

    def ask_starttime(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        start = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32105), timer.start)
        if start == "":
            return None
        else:
            return ("0%s" % start.strip())[-5:]

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), timer.duration)
        if duration == "":
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return timer.repeat, timer.resume and timer.duration != DEFAULT_TIME

    def ask_fader(self, timer: Timer) -> 'tuple[int, int, int]':

        return timer.fade, timer.vol_min, timer.vol_max

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return timer.system_action, MEDIA_ACTION_START_STOP if timer.duration != DEFAULT_TIME else MEDIA_ACTION_START

    def handle_overlapping_timers(self, timer: Timer, overlapping_timers: 'list[Timer]') -> int:

        return ask_overlapping_timers(timer, overlapping_timers)

    def confirm(self, timer: Timer) -> int:

        msg = "$L\n$H\n%s: $M\n%s: $F\n$O" % (self.addon.getLocalizedString(
            32070), self.addon.getLocalizedString(32091))
        return xbmcgui.Dialog().yesnocustom(heading=self.addon.getLocalizedString(32107),
                                            message=timer.format(msg).strip(),
                                            customlabel=self.addon.getLocalizedString(
                                                32102),
                                            nolabel=self.addon.getLocalizedString(
                                                32022),
                                            yeslabel=self.addon.getLocalizedString(32023))

    def post_apply(self, timer: Timer, confirm: int) -> None:

        if confirm == CONFIRM_CUSTOM:
            load_timer_into_settings(timer)
            self.addon.openSettings()
        else:
            super().post_apply(timer=timer, confirm=confirm)
