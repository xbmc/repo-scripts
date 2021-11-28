from datetime import timedelta

import xbmcaddon
from resources.lib.timer import util

SLEEP_TIMER = 0
SNOOZE_TIMER = 1

TIMER_ONCE = [str(i) for i in range(7)]
TIMER_OFF = "25"

TIMER_DAYS_PRESETS = {
    "0": [0],                     # mon
    "1": [1],                     # tue
    "2": [2],                     # wed
    "3": [3],                     # thu
    "4": [4],                     # fri
    "5": [5],                     # sat
    "6": [6],                     # sun
    "7": [0],                     # mons
    "8": [1],                     # tues
    "9": [2],                     # weds
    "10": [3],                    # thus
    "11": [4],                    # fris
    "12": [5],                    # sats
    "13": [6],                    # suns
    "14": [0, 1, 2, 3],           # mon-thu
    "15": [0, 1, 2, 3, 4],        # mon-fri
    "26": [0, 1, 2, 3, 4, 5],     # mon-sat
    "16": [1, 2, 3, 4],           # tue-fri
    "17": [3, 4, 5],              # thu-sat
    "18": [4, 5],                 # fri-sat
    "19": [4, 5, 6],              # fri-sun
    "20": [5, 6],                 # sat-sun
    "21": [5, 6, 0],              # sat-mon
    "22": [6, 0, 1, 2],           # sun-wed
    "23": [6, 0, 1, 2, 3],        # sun-thu
    "24": [0, 1, 2, 3, 4, 5, 6],  # everyday
    "25": [],                     # off
    "": []                        # off
}

END_TYPE_NO = "0"
END_TYPE_DURATION = "1"
END_TYPE_TIME = "2"

ACTION_NO = "0"
ACTION_START_STOP = "1"
ACTION_START = "2"
ACTION_START_AT_END = "3"
ACTION_STOP = "4"
ACTION_STOP_AT_END = "5"
ACTION_POWERDOWN_AT_END = "6"

FADE_OFF = "0"
FADE_IN_FROM_MIN = "1"
FADE_OUT_FROM_MAX = "2"
FADE_OUT_FROM_CURRENT = "3"


class Timer():

    _addon = None

    i_timer = None

    s_label = ""
    s_schedule = TIMER_OFF
    s_start = util.DEFAULT_TIME
    s_end_type = END_TYPE_NO
    s_duration = util.DEFAULT_TIME
    s_end = util.DEFAULT_TIME
    s_action = ACTION_START
    s_filename = ""
    s_fade = FADE_OFF
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
        self.s_action = [ACTION_STOP,
                         ACTION_START_AT_END][i] if i < 2 else ACTION_START
        self.s_fade = FADE_OUT_FROM_CURRENT if i == SLEEP_TIMER else FADE_OFF

    @staticmethod
    def init_from_settings(i):

        def _build_end_time(td_start, s_end_type, td_duration, s_end):

            if s_end_type == END_TYPE_DURATION:
                td_end = td_start + td_duration

            elif s_end_type == END_TYPE_TIME:
                td_end = util.parse_time(s_end, td_start.days)

                if td_end < td_start:
                    td_end += timedelta(days=1)

            else:  # END_TYPE_NO
                td_end = td_start + timedelta(seconds=1)

            return td_end, td_end - td_start

        addon = xbmcaddon.Addon()

        timer = Timer(i)
        timer.s_label = addon.getSetting("timer_%i_label" % i)
        timer.s_action = addon.getSetting("timer_%i_action" % i)
        timer.s_fade = addon.getSetting("timer_%i_fade" % i)
        timer.i_vol_min = int(
            "0%s" % addon.getSetting("timer_%i_vol_min" % i))
        timer.i_vol_max = int(
            "0%s" % addon.getSetting("timer_%i_vol_max" % i))
        timer.s_filename = addon.getSetting("timer_%i_filename" % i)
        timer.s_schedule = addon.getSetting("timer_%i" % i)
        timer.days = TIMER_DAYS_PRESETS[timer.s_schedule]
        timer.s_start = addon.getSetting("timer_%i_start" % i)
        timer.s_end_type = addon.getSetting("timer_%i_end_type" % i)
        timer.s_end = addon.getSetting("timer_%i_end" % i)
        timer.s_duration = addon.getSetting("timer_%i_duration" % i)
        timer.td_duration = util.parse_time(timer.s_duration)
        timer.b_notify = (
            "true" == addon.getSetting("timer_%i_notify" % i))

        timer.i_return_vol = None
        timer.b_active = False

        timer.periods = list()
        for i_day in TIMER_DAYS_PRESETS[timer.s_schedule]:
            td_start = util.parse_time(timer.s_start, i_day)
            td_end, timer.td_duration = _build_end_time(td_start,
                                                        timer.s_end_type,
                                                        timer.td_duration,
                                                        timer.s_end)

            timer.periods.append((td_start, td_end))

        return timer

    def update_or_replace_from_settings(self):

        timer_from_settings = Timer.init_from_settings(self.i_timer)

        changed = (timer_from_settings.s_schedule != self.s_schedule)
        changed |= (timer_from_settings.s_start != self.s_start)
        changed |= (timer_from_settings.s_end_type != self.s_end_type)
        if self.s_end_type == END_TYPE_DURATION:
            changed |= (timer_from_settings.s_duration != self.s_duration)
        elif self.s_end_type == END_TYPE_TIME:
            changed |= (timer_from_settings.s_end != self.s_end)

        changed |= (timer_from_settings.s_action != self.s_action)
        if self.s_action in [ACTION_START_STOP, ACTION_START, ACTION_START_AT_END]:
            changed |= (timer_from_settings.s_filename != self.s_filename)

        changed |= (timer_from_settings.s_fade != self.s_fade)
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
        self._addon.setSetting("timer_%i_label" %
                               self.i_timer, self.s_label)
        self._addon.setSetting("timer_%i" % self.i_timer, self.s_schedule)
        self._addon.setSetting("timer_%i_start" %
                               self.i_timer, self.s_start)
        self._addon.setSetting("timer_%i_end_type" %
                               self.i_timer, self.s_end_type)
        self._addon.setSetting("timer_%i_duration" %
                               self.i_timer, self.s_duration)
        self._addon.setSetting("timer_%i_end" % self.i_timer, self.s_end)
        self._addon.setSetting("timer_%i_action" %
                               self.i_timer, self.s_action)
        self._addon.setSetting("timer_%i_filename" %
                               self.i_timer, self.s_filename)
        self._addon.setSetting("timer_%i_fade" % self.i_timer, self.s_fade)
        self._addon.setSetting("timer_%i_vol_min" %
                               self.i_timer, str(self.i_vol_min))
        self._addon.setSetting("timer_%i_vol_max" %
                               self.i_timer, str(self.i_vol_max))
        self._addon.setSetting("timer_%i_notify" %
                               self.i_timer, "true" if self.b_notify else "false")
        util.activateOnSettingsChangedEvents(self._addon)

    def get_matching_period(self, time_):

        for period in self.periods:

            in_period = period[0] <= time_ < period[1]
            if in_period:
                return period

        return None

    def is_fading_timer(self):

        return self.s_fade != FADE_OFF and self.s_end_type != END_TYPE_NO

    def is_starting_timer(self):

        return self.s_action in [ACTION_START_STOP, ACTION_START] and self.s_filename

    def is_stopping_timer(self):

        return self.s_action in [ACTION_START_STOP, ACTION_STOP_AT_END]
