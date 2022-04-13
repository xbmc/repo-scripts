from datetime import timedelta

import xbmc
import xbmcaddon
from resources.lib.timer.period import Period
from resources.lib.utils import datetime_utils, settings_utils

SLEEP_TIMER = 0
SNOOZE_TIMER = 1

TIMER_OFF = 0
TIMER_ONCE = [i + 1 for i in range(7)]

TIMER_DAYS_PRESETS = [
    [],                      # off
    [0],                     # mon
    [1],                     # tue
    [2],                     # wed
    [3],                     # thu
    [4],                     # fri
    [5],                     # sat
    [6],                     # sun
    [0],                     # mons
    [1],                     # tues
    [2],                     # weds
    [3],                    # thus
    [4],                    # fris
    [5],                    # sats
    [6],                    # suns
    [0, 1, 2, 3],           # mon-thu
    [0, 1, 2, 3, 4],        # mon-fri
    [0, 1, 2, 3, 4, 5],     # mon-sat
    [1, 2, 3, 4],           # tue-fri
    [3, 4, 5],              # thu-sat
    [4, 5],                 # fri-sat
    [4, 5, 6],              # fri-sun
    [5, 6],                 # sat-sun
    [5, 6, 0],              # sat-mon
    [6, 0, 1, 2],           # sun-wed
    [6, 0, 1, 2, 3],        # sun-thu
    [0, 1, 2, 3, 4, 5, 6]   # everyday
]

END_TYPE_NO = 0
END_TYPE_DURATION = 1
END_TYPE_TIME = 2

SYSTEM_ACTION_NONE = 0
SYSTEM_ACTION_SHUTDOWN_KODI = 1
SYSTEM_ACTION_QUIT_KODI = 2
SYSTEM_ACTION_STANDBY = 3
SYSTEM_ACTION_HIBERNATE = 4
SYSTEM_ACTION_POWEROFF = 5

MEDIA_ACTION_NONE = 0
MEDIA_ACTION_START_STOP = 1
MEDIA_ACTION_START = 2
MEDIA_ACTION_START_AT_END = 3
MEDIA_ACTION_STOP_START = 4
MEDIA_ACTION_STOP = 5
MEDIA_ACTION_STOP_AT_END = 6

FADE_OFF = 0
FADE_IN_FROM_MIN = 1
FADE_OUT_FROM_MAX = 2
FADE_OUT_FROM_CURRENT = 3


class Timer():

    _addon = None

    i_timer = None

    s_label = ""
    i_schedule = TIMER_OFF
    s_start = datetime_utils.DEFAULT_TIME
    i_end_type = END_TYPE_NO
    s_duration = datetime_utils.DEFAULT_TIME
    s_end = datetime_utils.DEFAULT_TIME
    i_system_action = SYSTEM_ACTION_NONE
    i_media_action = MEDIA_ACTION_START
    s_filename = ""
    b_repeat = False
    b_resume = False
    i_fade = FADE_OFF
    i_vol_min = 75
    i_vol_max = 100
    b_notify = True

    i_return_vol = 100
    b_active = False
    periods = list()
    days = list()
    td_duration = timedelta()

    def __init__(self, i):

        self._addon = xbmcaddon.Addon()
        self.s_label = self._addon.getLocalizedString(32004 + i)
        self.i_timer = i
        self.s_duration = ["01:00", "00:10"][i] if i < 2 else "00:00"
        self.i_media_action = [MEDIA_ACTION_STOP_AT_END,
                               MEDIA_ACTION_START_AT_END][i] if i < 2 else MEDIA_ACTION_START
        self.i_fade = FADE_OUT_FROM_CURRENT if i == SLEEP_TIMER else FADE_OFF
        self.periods = list()
        self.days = list()

    @staticmethod
    def init_from_settings(i: int) -> 'Timer':

        def _build_end_time(td_start: timedelta, i_end_type: int, td_duration: timedelta, s_end: str):

            if i_end_type == END_TYPE_DURATION:
                td_end = td_start + td_duration

            elif i_end_type == END_TYPE_TIME:
                td_end = datetime_utils.parse_time(s_end, td_start.days)

                if td_end < td_start:
                    td_end += timedelta(days=1)

            else:  # END_TYPE_NO
                td_end = td_start + timedelta(seconds=1)

            return td_end, td_end - td_start

        addon = xbmcaddon.Addon()

        timer = Timer(i)
        timer.s_label = addon.getSettingString("timer_%i_label" % i)
        timer.i_system_action = addon.getSettingInt(
            "timer_%i_system_action" % i)
        timer.i_media_action = addon.getSettingInt("timer_%i_media_action" % i)
        timer.i_fade = addon.getSettingInt("timer_%i_fade" % i)
        timer.i_vol_min = addon.getSettingInt("timer_%i_vol_min" % i)
        timer.i_vol_max = addon.getSettingInt("timer_%i_vol_max" % i)
        timer.s_filename = addon.getSettingString("timer_%i_filename" % i)
        timer.b_repeat = addon.getSettingBool("timer_%i_repeat" % i)
        timer.b_resume = addon.getSettingBool("timer_%i_resume" % i)
        timer.i_schedule = addon.getSettingInt("timer_%i" % i)
        timer.days = TIMER_DAYS_PRESETS[timer.i_schedule]
        timer.s_start = addon.getSetting("timer_%i_start" % i)
        timer.i_end_type = addon.getSettingInt("timer_%i_end_type" % i)
        timer.s_end = addon.getSetting("timer_%i_end" % i)
        timer.s_duration = addon.getSetting("timer_%i_duration" % i)
        timer.td_duration = datetime_utils.parse_time(timer.s_duration)
        timer.b_notify = addon.getSettingBool("timer_%i_notify" % i)

        timer.i_return_vol = None
        timer.b_active = False

        timer.periods = list()
        for i_day in TIMER_DAYS_PRESETS[timer.i_schedule]:
            td_start = datetime_utils.parse_time(timer.s_start, i_day)
            td_end, timer.td_duration = _build_end_time(td_start,
                                                        timer.i_end_type,
                                                        timer.td_duration,
                                                        timer.s_end)

            timer.periods.append(Period(td_start, td_end))

        return timer

    def update_or_replace_from_settings(self) -> 'tuple[Timer, bool]':

        timer_from_settings = Timer.init_from_settings(self.i_timer)

        changed = (timer_from_settings.i_schedule != self.i_schedule)
        changed |= (timer_from_settings.s_start != self.s_start)
        changed |= (timer_from_settings.i_end_type != self.i_end_type)
        if self.i_end_type == END_TYPE_DURATION:
            changed |= (timer_from_settings.s_duration != self.s_duration)
        elif self.i_end_type == END_TYPE_TIME:
            changed |= (timer_from_settings.s_end != self.s_end)

        changed |= (timer_from_settings.i_system_action !=
                    self.i_system_action)

        changed |= (timer_from_settings.i_media_action != self.i_media_action)
        if self._is_playing_media_timer():
            changed |= (timer_from_settings.s_filename != self.s_filename)
            changed |= (timer_from_settings.b_repeat != self.b_repeat)
            changed |= (timer_from_settings.b_resume != self.b_resume)

        changed |= (timer_from_settings.i_fade != self.i_fade)
        if self.is_fading_timer():
            changed |= (timer_from_settings.i_vol_min != self.i_vol_min)
            changed |= (timer_from_settings.i_vol_max != self.i_vol_max)

        if changed:
            return timer_from_settings, True
        else:
            self.s_label = timer_from_settings.s_label
            self.b_notify = timer_from_settings.b_notify
            return self, False

    def save_to_settings(self) -> None:

        settings_utils.deactivateOnSettingsChangedEvents()
        self._addon.setSettingString("timer_%i_label" %
                                     self.i_timer, self.s_label)
        self._addon.setSettingInt("timer_%i" % self.i_timer, self.i_schedule)
        self._addon.setSetting("timer_%i_start" %
                               self.i_timer, self.s_start)
        self._addon.setSettingInt("timer_%i_end_type" %
                                  self.i_timer, self.i_end_type)
        self._addon.setSetting("timer_%i_duration" %
                               self.i_timer, self.s_duration)
        self._addon.setSetting("timer_%i_end" % self.i_timer, self.s_end)
        self._addon.setSettingInt("timer_%i_system_action" %
                                  self.i_timer, self.i_system_action)
        self._addon.setSettingInt("timer_%i_media_action" %
                                  self.i_timer, self.i_media_action)
        self._addon.setSettingString("timer_%i_filename" %
                                     self.i_timer, self.s_filename)
        self._addon.setSettingBool("timer_%i_repeat" %
                                   self.i_timer, self.b_repeat)
        self._addon.setSettingBool("timer_%i_resume" %
                                   self.i_timer, self.b_resume)
        self._addon.setSettingInt("timer_%i_fade" % self.i_timer, self.i_fade)
        self._addon.setSettingInt("timer_%i_vol_min" %
                                  self.i_timer, self.i_vol_min)
        self._addon.setSettingInt("timer_%i_vol_max" %
                                  self.i_timer, self.i_vol_max)
        self._addon.setSettingBool("timer_%i_notify" %
                                   self.i_timer, self.b_notify)
        settings_utils.activateOnSettingsChangedEvents()

    def _get_periods(self) -> 'list[Period]':

        return self.periods

    def get_matching_period(self, time_: timedelta) -> Period:

        for period in self._get_periods():

            in_period = period.getStart() <= time_ < period.getEnd()
            if in_period:
                return period

        return None

    def is_fading_timer(self) -> bool:

        return self.i_fade != FADE_OFF and self.i_end_type != END_TYPE_NO

    def _is_playing_media_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_AT_END, MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_START]

    def is_play_at_start_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_STOP] and self.s_filename

    def is_stop_at_start_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_STOP, MEDIA_ACTION_STOP_START]

    def is_stop_at_end_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_AT_END]

    def is_play_at_end_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_STOP_START, MEDIA_ACTION_START_AT_END] and self.s_filename

    def is_system_execution_timer(self) -> bool:

        return self.i_system_action != SYSTEM_ACTION_NONE

    def execute_system_action(self) -> None:

        if self.i_system_action == SYSTEM_ACTION_SHUTDOWN_KODI:
            xbmc.shutdown()

        elif self.i_system_action == SYSTEM_ACTION_QUIT_KODI:
            xbmc.executebuiltin("Quit()")

        elif self.i_system_action == SYSTEM_ACTION_STANDBY:
            xbmc.executebuiltin("Suspend()")

        elif self.i_system_action == SYSTEM_ACTION_HIBERNATE:
            xbmc.executebuiltin("Hibernate()")

        elif self.i_system_action == SYSTEM_ACTION_POWEROFF:
            xbmc.executebuiltin("Powerdown()")
