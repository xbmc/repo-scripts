from datetime import timedelta

import xbmcaddon
from resources.lib.timer import util

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

ACTION_NO = 0
ACTION_START_STOP = 1
ACTION_START = 2
ACTION_START_AT_END = 3
ACTION_STOP = 4
ACTION_STOP_AT_END = 5
ACTION_SHUTDOWN_AT_END = 6
ACTION_QUIT_AT_END = 7
ACTION_SUSPEND_AT_END = 8
ACTION_HIBERNATE_AT_END = 9
ACTION_POWERDOWN_AT_END = 10

FADE_OFF = 0
FADE_IN_FROM_MIN = 1
FADE_OUT_FROM_MAX = 2
FADE_OUT_FROM_CURRENT = 3


class Timer():

    _addon = None

    i_timer = None

    s_label = ""
    i_schedule = TIMER_OFF
    s_start = util.DEFAULT_TIME
    i_end_type = END_TYPE_NO
    s_duration = util.DEFAULT_TIME
    s_end = util.DEFAULT_TIME
    i_action = ACTION_START
    s_filename = ""
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
        self.i_action = [ACTION_STOP_AT_END,
                         ACTION_START_AT_END][i] if i < 2 else ACTION_START
        self.i_fade = FADE_OUT_FROM_CURRENT if i == SLEEP_TIMER else FADE_OFF

    @staticmethod
    def init_from_settings(i):

        def _build_end_time(td_start, i_end_type, td_duration, s_end):

            if i_end_type == END_TYPE_DURATION:
                td_end = td_start + td_duration

            elif i_end_type == END_TYPE_TIME:
                td_end = util.parse_time(s_end, td_start.days)

                if td_end < td_start:
                    td_end += timedelta(days=1)

            else:  # END_TYPE_NO
                td_end = td_start + timedelta(seconds=1)

            return td_end, td_end - td_start

        addon = xbmcaddon.Addon()

        timer = Timer(i)
        timer.s_label = addon.getSettingString("timer_%i_label" % i)
        timer.i_action = addon.getSettingInt("timer_%i_action" % i)
        timer.i_fade = addon.getSettingInt("timer_%i_fade" % i)
        timer.i_vol_min = addon.getSettingInt("timer_%i_vol_min" % i)
        timer.i_vol_max = addon.getSettingInt("timer_%i_vol_max" % i)
        timer.s_filename = addon.getSettingString("timer_%i_filename" % i)
        timer.i_schedule = addon.getSettingInt("timer_%i" % i)
        timer.days = TIMER_DAYS_PRESETS[timer.i_schedule]
        timer.s_start = addon.getSetting("timer_%i_start" % i)
        timer.i_end_type = addon.getSettingInt("timer_%i_end_type" % i)
        timer.s_end = addon.getSetting("timer_%i_end" % i)
        timer.s_duration = addon.getSetting("timer_%i_duration" % i)
        timer.td_duration = util.parse_time(timer.s_duration)
        timer.b_notify = addon.getSettingBool("timer_%i_notify" % i)

        timer.i_return_vol = None
        timer.b_active = False

        timer.periods = list()
        for i_day in TIMER_DAYS_PRESETS[timer.i_schedule]:
            td_start = util.parse_time(timer.s_start, i_day)
            td_end, timer.td_duration = _build_end_time(td_start,
                                                        timer.i_end_type,
                                                        timer.td_duration,
                                                        timer.s_end)

            timer.periods.append((td_start, td_end))

        return timer

    def update_or_replace_from_settings(self):

        timer_from_settings = Timer.init_from_settings(self.i_timer)

        changed = (timer_from_settings.i_schedule != self.i_schedule)
        changed |= (timer_from_settings.s_start != self.s_start)
        changed |= (timer_from_settings.i_end_type != self.i_end_type)
        if self.i_end_type == END_TYPE_DURATION:
            changed |= (timer_from_settings.s_duration != self.s_duration)
        elif self.i_end_type == END_TYPE_TIME:
            changed |= (timer_from_settings.s_end != self.s_end)

        changed |= (timer_from_settings.i_action != self.i_action)
        if self.i_action in [ACTION_START_STOP, ACTION_START, ACTION_START_AT_END]:
            changed |= (timer_from_settings.s_filename != self.s_filename)

        changed |= (timer_from_settings.i_fade != self.i_fade)
        if self.is_fading_timer():
            changed |= (timer_from_settings.i_vol_min != self.i_vol_min)
            changed |= (timer_from_settings.i_vol_max != self.i_vol_max)

        if changed:
            return timer_from_settings
        else:
            self.s_label = timer_from_settings.s_label
            self.b_notify = timer_from_settings.b_notify
            return self

    def save_to_settings(self):

        util.deactivateOnSettingsChangedEvents(self._addon)
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
        self._addon.setSettingInt("timer_%i_action" %
                                  self.i_timer, self.i_action)
        self._addon.setSettingString("timer_%i_filename" %
                                     self.i_timer, self.s_filename)
        self._addon.setSettingInt("timer_%i_fade" % self.i_timer, self.i_fade)
        self._addon.setSettingInt("timer_%i_vol_min" %
                                  self.i_timer, self.i_vol_min)
        self._addon.setSettingInt("timer_%i_vol_max" %
                                  self.i_timer, self.i_vol_max)
        self._addon.setSettingBool("timer_%i_notify" %
                                   self.i_timer, self.b_notify)
        util.activateOnSettingsChangedEvents(self._addon)

    def get_matching_period(self, time_):

        for period in self.periods:

            in_period = period[0] <= time_ < period[1]
            if in_period:
                return period

        return None

    def is_fading_timer(self):

        return self.i_fade != FADE_OFF and self.i_end_type != END_TYPE_NO

    def is_starting_timer(self):

        return self.i_action in [ACTION_START_STOP, ACTION_START] and self.s_filename

    def is_stopping_timer(self):

        return self.i_action in [ACTION_START_STOP, ACTION_STOP_AT_END]
