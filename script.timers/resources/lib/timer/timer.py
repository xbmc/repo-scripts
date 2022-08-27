from datetime import timedelta

import xbmc
import xbmcaddon
from resources.lib.timer.period import Period
from resources.lib.utils.datetime_utils import (DEFAULT_TIME,
                                                format_from_seconds,
                                                parse_time,
                                                periods_to_human_readable,
                                                time_duration_str)
from resources.lib.utils.vfs_utils import is_script

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

    # master data
    id = None
    label = ""
    start = DEFAULT_TIME
    end_type = END_TYPE_NO
    duration = DEFAULT_TIME
    end = DEFAULT_TIME
    system_action = SYSTEM_ACTION_NONE
    media_action = MEDIA_ACTION_START
    path = ""
    media_type = ""
    repeat = False
    shuffle = False
    resume = False
    fade = FADE_OFF
    vol_min = 75
    vol_max = 100
    notify = True

    # state
    active = False
    return_vol = None
    periods = list()
    days = list()
    duration_timedelta = timedelta()

    def __init__(self, i):

        self._addon = xbmcaddon.Addon()
        self.id = i
        self.periods = list()
        self.days = list()

    def compute(self):

        def _build_end_time(td_start: timedelta, end_type: int, duration_timedelta: timedelta, end: str) -> 'tuple[timedelta, timedelta]':

            if end_type == END_TYPE_DURATION:
                td_end = td_start + duration_timedelta

            elif end_type == END_TYPE_TIME:
                td_end = parse_time(end, td_start.days)

                if td_end < td_start:
                    td_end += timedelta(days=1)

            else:  # END_TYPE_NO
                td_end = td_start + timedelta(seconds=1)

            return td_end, td_end - td_start

        td_start = parse_time(self.start)
        td_end, td_duration = _build_end_time(
            td_start=td_start, end_type=self.end_type, duration_timedelta=parse_time(self.duration), end=self.end)

        self.end = format_from_seconds(td_end.seconds)
        self.duration = format_from_seconds(td_duration.seconds)
        self.duration_timedelta = td_duration

        periods = list()
        for i_day in self.days:
            td_start = parse_time(self.start, i_day)
            td_end, self.duration_timedelta = _build_end_time(td_start,
                                                              self.end_type,
                                                              self.duration_timedelta,
                                                              self.end)

            periods.append(Period(td_start, td_end))

        self.periods = periods

    def get_periods(self) -> 'list[Period]':

        return self.periods

    def get_matching_period(self, time_: timedelta) -> Period:

        for period in self.get_periods():

            in_period = period.getStart() <= time_ < period.getEnd()
            if in_period:
                return period

        return None

    def get_duration(self) -> str:

        if self.end_type == END_TYPE_DURATION:
            return self.duration

        elif self.end_type == END_TYPE_TIME:
            return time_duration_str(self.start, self.end)

        else:
            return DEFAULT_TIME

    def periods_to_human_readable(self) -> str:

        self.compute()
        return periods_to_human_readable(self.days, start=self.start, end=self.end if self.end_type != END_TYPE_NO else None)

    def is_fading_timer(self) -> bool:

        return self.fade != FADE_OFF and self.end_type != END_TYPE_NO

    def _is_playing_media_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_AT_END, MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_START] and self.path

    def is_play_at_start_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_STOP] and self.path

    def is_stop_at_start_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_STOP, MEDIA_ACTION_STOP_START]

    def is_stop_at_end_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_AT_END]

    def is_play_at_end_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_STOP_START, MEDIA_ACTION_START_AT_END] and self.path

    def is_resuming_timer(self) -> bool:

        return self.media_action == MEDIA_ACTION_START_STOP and self.resume

    def is_script_timer(self) -> bool:

        return is_script(self.path)

    def is_system_execution_timer(self) -> bool:

        return self.system_action != SYSTEM_ACTION_NONE

    def execute_system_action(self) -> None:

        if self.system_action == SYSTEM_ACTION_SHUTDOWN_KODI:
            xbmc.shutdown()

        elif self.system_action == SYSTEM_ACTION_QUIT_KODI:
            xbmc.executebuiltin("Quit()")

        elif self.system_action == SYSTEM_ACTION_STANDBY:
            xbmc.executebuiltin("Suspend()")

        elif self.system_action == SYSTEM_ACTION_HIBERNATE:
            xbmc.executebuiltin("Hibernate()")

        elif self.system_action == SYSTEM_ACTION_POWEROFF:
            xbmc.executebuiltin("Powerdown()")
