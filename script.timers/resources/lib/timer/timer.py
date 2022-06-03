from datetime import timedelta

import xbmc
import xbmcaddon
from resources.lib.timer.period import Period
from resources.lib.utils.datetime_utils import (DEFAULT_TIME, parse_time,
                                                time_duration_str)
from resources.lib.utils.settings_utils import (
    activateOnSettingsChangedEvents, deactivateOnSettingsChangedEvents)
from resources.lib.utils.vfs_utils import is_script

SLEEP_TIMER = 0
SNOOZE_TIMER = 1

TIMER_WEEKLY = 7

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
    s_start = DEFAULT_TIME
    i_end_type = END_TYPE_NO
    s_duration = DEFAULT_TIME
    s_end = DEFAULT_TIME
    i_system_action = SYSTEM_ACTION_NONE
    i_media_action = MEDIA_ACTION_START
    s_path = ""
    s_mediatype = ""
    b_repeat = False
    b_shuffle = False
    b_resume = False
    i_fade = FADE_OFF
    i_vol_min = 75
    i_vol_max = 100
    b_notify = True

    i_return_vol = None
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
    def get_quick_info(i: int) -> 'tuple[str,str,str,list[int]]':

        addon = xbmcaddon.Addon()

        label = addon.getSettingString("timer_%i_label" % i)
        path = addon.getSettingString("timer_%i_path" % i)
        start = addon.getSetting("timer_%i_start" % i)
        days = addon.getSetting("timer_%i_days" % i)
        if days:
            days = [int(d) for d in days.split("|")]
        else:
            days = list()

        return label, path, start, days

    @staticmethod
    def init_from_settings(i: int) -> 'Timer':

        def _build_end_time(td_start: timedelta, i_end_type: int, td_duration: timedelta, s_end: str) -> 'tuple[timedelta, timedelta]':

            if i_end_type == END_TYPE_DURATION:
                td_end = td_start + td_duration

            elif i_end_type == END_TYPE_TIME:
                td_end = parse_time(s_end, td_start.days)

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
        timer.s_path = addon.getSettingString("timer_%i_path" % i)
        timer.s_mediatype = addon.getSettingString("timer_%i_mediatype" % i)
        timer.b_repeat = addon.getSettingBool("timer_%i_repeat" % i)
        timer.b_shuffle = addon.getSettingBool("timer_%i_shuffle" % i)
        timer.b_resume = addon.getSettingBool("timer_%i_resume" % i)
        days = addon.getSetting("timer_%i_days" % i)
        if days:
            timer.days = [int(d) for d in days.split("|")]
        else:
            days = list()

        timer.s_start = addon.getSetting("timer_%i_start" % i)
        timer.i_end_type = addon.getSettingInt("timer_%i_end_type" % i)
        timer.s_end = addon.getSetting("timer_%i_end" % i)
        timer.s_duration = addon.getSetting("timer_%i_duration" % i)
        timer.td_duration = parse_time(timer.s_duration)
        timer.b_notify = addon.getSettingBool("timer_%i_notify" % i)

        timer.i_return_vol = None
        timer.b_active = False

        timer.periods = list()
        for i_day in timer.days:
            td_start = parse_time(timer.s_start, i_day)
            td_end, timer.td_duration = _build_end_time(td_start,
                                                        timer.i_end_type,
                                                        timer.td_duration,
                                                        timer.s_end)

            timer.periods.append(Period(td_start, td_end))

        return timer

    def update_or_replace_from_settings(self) -> 'tuple[Timer, bool]':

        timer_from_settings = Timer.init_from_settings(self.i_timer)

        changed = (timer_from_settings.days != self.days)
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
            changed |= (timer_from_settings.s_path != self.s_path)
            changed |= (timer_from_settings.s_mediatype != self.s_mediatype)
            changed |= (timer_from_settings.b_repeat != self.b_repeat)
            changed |= (timer_from_settings.b_shuffle != self.b_shuffle)
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

        deactivateOnSettingsChangedEvents()
        self._addon.setSettingString("timer_%i_label" %
                                     self.i_timer, self.s_label)
        self._addon.setSetting(
            "timer_%i_days" % self.i_timer, "|".join([str(d) for d in self.days]))

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
        self._addon.setSettingString("timer_%i_path" %
                                     self.i_timer, self.s_path)
        self._addon.setSettingString("timer_%i_mediatype" %
                                     self.i_timer, self.s_mediatype)
        self._addon.setSettingBool("timer_%i_repeat" %
                                   self.i_timer, self.b_repeat)
        self._addon.setSettingBool("timer_%i_shuffle" %
                                   self.i_timer, self.b_shuffle)
        self._addon.setSettingBool("timer_%i_resume" %
                                   self.i_timer, self.b_resume)
        self._addon.setSettingInt("timer_%i_fade" % self.i_timer, self.i_fade)
        self._addon.setSettingInt("timer_%i_vol_min" %
                                  self.i_timer, self.i_vol_min)
        self._addon.setSettingInt("timer_%i_vol_max" %
                                  self.i_timer, self.i_vol_max)
        self._addon.setSettingBool("timer_%i_notify" %
                                   self.i_timer, self.b_notify)
        activateOnSettingsChangedEvents()

    def get_periods(self) -> 'list[Period]':

        return self.periods

    def get_matching_period(self, time_: timedelta) -> Period:

        for period in self.get_periods():

            in_period = period.getStart() <= time_ < period.getEnd()
            if in_period:
                return period

        return None

    def get_duration(self) -> str:

        if self.i_end_type == END_TYPE_DURATION:
            return self.s_duration

        elif self.i_end_type == END_TYPE_TIME:
            return time_duration_str(self.s_start, self.s_end)

        else:
            return DEFAULT_TIME

    def is_fading_timer(self) -> bool:

        return self.i_fade != FADE_OFF and self.i_end_type != END_TYPE_NO

    def _is_playing_media_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_AT_END, MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_START] and self.s_path

    def is_play_at_start_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_STOP] and self.s_path

    def is_stop_at_start_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_STOP, MEDIA_ACTION_STOP_START]

    def is_stop_at_end_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_AT_END]

    def is_play_at_end_timer(self) -> bool:

        return self.i_media_action in [MEDIA_ACTION_STOP_START, MEDIA_ACTION_START_AT_END] and self.s_path

    def is_resuming_timer(self) -> bool:

        return self.i_media_action == MEDIA_ACTION_START_STOP and self.b_resume

    def is_script_timer(self) -> bool:

        return is_script(self.s_path)

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
