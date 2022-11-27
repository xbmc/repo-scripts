from datetime import timedelta, datetime

import xbmc
import xbmcaddon
from resources.lib.timer.period import Period
from resources.lib.utils.datetime_utils import (DEFAULT_TIME,
                                                apply_for_now,
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

    def __init__(self, i: int) -> None:

        self._addon = xbmcaddon.Addon()

        # master data
        self.id: int = i
        self.label: str = ""
        self.start: str = DEFAULT_TIME
        self.start_offset: int = 0
        self.end_type: int = END_TYPE_NO
        self.duration: str = DEFAULT_TIME
        self.duration_offset: int = 0
        self.end: str = DEFAULT_TIME
        self.end_offset: int = 0
        self.system_action: int = SYSTEM_ACTION_NONE
        self.media_action: int = MEDIA_ACTION_START
        self.path: str = ""
        self.media_type: str = ""
        self.repeat: bool = False
        self.shuffle: bool = False
        self.resume: bool = False
        self.fade: int = FADE_OFF
        self.vol_min: int = 75
        self.vol_max: int = 100
        self.notify: bool = True

        # state
        self.active: bool = False
        self.return_vol: int = None
        self.periods: 'list[Period]' = list()
        self.days: 'list[int]' = list()
        self.duration_timedelta: timedelta = timedelta()

    def compute(self) -> None:

        def _build_end_time(td_start: timedelta, end_type: int, duration_timedelta: timedelta, end: str, end_offset=0, duration_offset=0) -> 'tuple[timedelta, timedelta]':

            if end_type == END_TYPE_DURATION:
                td_end = td_start + duration_timedelta + \
                    timedelta(seconds=duration_offset)

            elif end_type == END_TYPE_TIME:
                td_end = parse_time(end, td_start.days) + \
                    timedelta(seconds=end_offset)

                if td_end < td_start:
                    td_end += timedelta(days=1)

            else:  # END_TYPE_NO
                td_end = td_start + timedelta(seconds=1)

            return td_end, td_end - td_start

        td_start = parse_time(self.start) + \
            timedelta(seconds=self.start_offset)
        self.start = format_from_seconds(td_start.seconds)
        self.start_offset = td_start.seconds % 60

        td_end, td_duration = _build_end_time(
            td_start=td_start, end_type=self.end_type, duration_timedelta=parse_time(
                self.duration),
            end=self.end,
            end_offset=self.end_offset,
            duration_offset=self.duration_offset)
        self.end = format_from_seconds(td_end.seconds)
        self.end_offset = td_end.seconds % 60
        self.duration = format_from_seconds(td_duration.seconds)
        self.duration_offset = td_duration.seconds % 60
        self.duration_timedelta = td_duration

        periods = list()
        for i_day in self.days:
            if i_day == TIMER_WEEKLY:
                continue

            td_start = parse_time(self.start, i_day) + \
                timedelta(seconds=self.start_offset)
            td_end, self.duration_timedelta = _build_end_time(td_start,
                                                              self.end_type,
                                                              self.duration_timedelta,
                                                              self.end)

            periods.append(Period(td_start, td_end))

        self.periods = periods

    def get_matching_period_and_upcoming_event(self, dt_now: datetime, td_time: timedelta) -> 'tuple[Period, datetime]':

        upcoming_event: timedelta = None

        for period in self.periods:

            if period.start > td_time:
                upcoming_event = period.start if upcoming_event is None or upcoming_event > period.start else upcoming_event

            elif td_time < period.end:
                return period, apply_for_now(dt_now, period.end) if dt_now else None

        if not upcoming_event and self.periods:
            upcoming_event = self.periods[0].start + timedelta(days=7)

        return None, apply_for_now(dt_now, upcoming_event) if dt_now else None

    def get_duration(self) -> str:

        if self.end_type == END_TYPE_DURATION:
            return self.duration

        elif self.end_type == END_TYPE_TIME:
            return time_duration_str(self.start, self.end)

        else:
            return DEFAULT_TIME

    def periods_to_human_readable(self) -> str:

        self.compute()
        _start = "%s:%02i" % (
            self.start, self.start_offset) if self.start_offset else self.start
        _end = "%s:%02i" % (
            self.end, self.end_offset) if self.end_offset else self.end
        return periods_to_human_readable(self.days, start=_start, end=_end if self.end_type != END_TYPE_NO else None)

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
