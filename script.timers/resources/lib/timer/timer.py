from datetime import datetime, timedelta

import xbmcaddon
from resources.lib.timer.period import Period
from resources.lib.utils import datetime_utils
from resources.lib.utils.vfs_utils import is_script

TIMER_WEEKLY = 7
TIMER_BY_DATE = 8

END_TYPE_NO = 0
END_TYPE_DURATION = 1
END_TYPE_TIME = 2

SYSTEM_ACTION_NONE = 0
SYSTEM_ACTION_SHUTDOWN_KODI = 1
SYSTEM_ACTION_QUIT_KODI = 2
SYSTEM_ACTION_STANDBY = 3
SYSTEM_ACTION_HIBERNATE = 4
SYSTEM_ACTION_POWEROFF = 5
SYSTEM_ACTION_CEC_STANDBY = 6
SYSTEM_ACTION_RESTART_KODI = 7
SYSTEM_ACTION_REBOOT_SYSTEM = 8

MEDIA_ACTION_NONE = 0
MEDIA_ACTION_START_STOP = 1
MEDIA_ACTION_START = 2
MEDIA_ACTION_START_AT_END = 3
MEDIA_ACTION_STOP_START = 4
MEDIA_ACTION_STOP = 5
MEDIA_ACTION_STOP_AT_END = 6
MEDIA_ACTION_PAUSE = 7

FADE_OFF = 0
FADE_IN_FROM_MIN = 1
FADE_OUT_FROM_MAX = 2
FADE_OUT_FROM_CURRENT = 3

STATE_WAITING = 0
STATE_STARTING = 1
STATE_RUNNING = 2
STATE_ENDING = 3


class Timer():

    def __init__(self, i: int) -> None:

        self._addon = xbmcaddon.Addon()

        # master data
        self.id: int = i
        self.label: str = ""
        self.days: 'list[int]' = list()
        self.date: str = ""
        self.start: str = datetime_utils.DEFAULT_TIME
        self.start_offset: int = 0
        self.end_type: int = END_TYPE_NO
        self.duration: str = datetime_utils.DEFAULT_TIME
        self.duration_offset: int = 0
        self.end: str = datetime_utils.DEFAULT_TIME
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
        self.priority: int = 0

        # state
        self.periods: 'list[Period]' = list()
        self.duration_timedelta: timedelta = timedelta()
        self.state: int = STATE_WAITING
        self.current_period: Period = None
        self.upcoming_event: datetime = None
        self.return_vol: int = None

    def init(self) -> None:

        def _build_end_time(start: 'timedelta | datetime', end_type: int, duration_timedelta: timedelta, end: str, end_offset=0, duration_offset=0) -> 'tuple[timedelta | datetime, timedelta | datetime]':

            if end_type == END_TYPE_DURATION:
                end_time = start + duration_timedelta + \
                    timedelta(seconds=duration_offset)

            elif end_type == END_TYPE_TIME:

                end_time = datetime_utils.parse_time(
                    end) + timedelta(seconds=end_offset)
                if type(start) == datetime:
                    end_time = datetime(year=start.year, month=start.month, day=start.day,
                                        hour=int(
                                            end_time.total_seconds() // 3600),
                                        minute=int(
                                            end_time.total_seconds() % 3600) // 60,
                                        second=int(end_time.total_seconds() % 60))
                else:
                    end_time = end_time + timedelta(days=start.days)

                if end_time < start:
                    end_time += timedelta(days=1)

            else:  # END_TYPE_NO
                end_time = start + timedelta(seconds=1)

            return end_time, end_time - start

        td_start = datetime_utils.parse_time(self.start) + \
            timedelta(seconds=self.start_offset)
        self.start = datetime_utils.format_from_seconds(td_start.seconds)
        self.start_offset = td_start.seconds % 60

        td_end, td_duration = _build_end_time(
            start=td_start, end_type=self.end_type, duration_timedelta=datetime_utils.parse_time(
                self.duration),
            end=self.end,
            end_offset=self.end_offset,
            duration_offset=self.duration_offset)
        self.end = datetime_utils.format_from_seconds(td_end.seconds)
        self.end_offset = td_end.seconds % 60
        self.duration = datetime_utils.format_from_seconds(td_duration.seconds)
        self.duration_offset = td_duration.seconds % 60
        self.duration_timedelta = td_duration

        if self.is_weekly_timer():
            self.date = ""

        if self.is_timer_by_date():

            self.days = [TIMER_BY_DATE]
            dt_start = datetime_utils.parse_datetime_str(
                f"{self.date} {self.start}") + timedelta(seconds=self.start_offset)
            dt_end, self.duration_timedelta = _build_end_time(start=dt_start,
                                                              end_type=self.end_type,
                                                              duration_timedelta=self.duration_timedelta,
                                                              end=self.end,
                                                              end_offset=self.end_offset,
                                                              duration_offset=self.duration_offset)

            self.periods = [Period(dt_start, dt_end)]

        else:
            periods = list()
            for i_day in self.days:
                if i_day == TIMER_WEEKLY:
                    continue

                td_start = datetime_utils.parse_time(self.start, i_day) + \
                    timedelta(seconds=self.start_offset)
                td_end, self.duration_timedelta = _build_end_time(start=td_start,
                                                                  end_type=self.end_type,
                                                                  duration_timedelta=self.duration_timedelta,
                                                                  end=self.end,
                                                                  end_offset=self.end_offset,
                                                                  duration_offset=self.duration_offset)

                periods.append(Period(td_start, td_end))

            self.periods = periods

    def _apply_weekday_periods(self, dtd: datetime_utils.DateTimeDelta) -> 'tuple[Period, datetime]':

        td_upcoming_event: timedelta = None
        current_period: Period = None

        for period in self.periods:

            if period.start > dtd.td:
                td_upcoming_event = period.start if td_upcoming_event is None or td_upcoming_event > period.start else td_upcoming_event

            elif dtd.td < period.end:
                current_period = period
                td_upcoming_event = period.end
                break

        if not td_upcoming_event and self.periods:
            td_upcoming_event = self.periods[0].start + timedelta(days=7)

        upcoming_event = datetime_utils.apply_for_datetime(
            dtd.dt, td_upcoming_event) if dtd.dt else None

        return Period.to_datetime_period(current_period, base=dtd.dt) if current_period else None, upcoming_event

    def _apply_date_period(self, dtd: datetime_utils.DateTimeDelta) -> 'tuple[Period, datetime]':

        if not dtd.dt or not self.periods:
            return None, None

        date_period: Period = self.periods[0]
        current_period: Period = None
        upcoming_event: datetime = None

        if date_period.start > dtd.dt:
            upcoming_event = date_period.start

        elif dtd.dt < date_period.end:
            current_period = date_period
            upcoming_event = date_period.end

        return current_period, upcoming_event

    def apply(self, dtd: datetime_utils.DateTimeDelta) -> None:

        if self.is_timer_by_date():
            self.current_period, self.upcoming_event = self._apply_date_period(
                dtd)

        else:
            self.current_period, self.upcoming_event = self._apply_weekday_periods(
                dtd)

        if self.current_period is not None and self.state is not STATE_RUNNING:
            self.state = STATE_STARTING

        elif self.current_period is None and self.state is not STATE_WAITING:
            self.current_period = Period(
                dtd.dt - self.duration_timedelta, dtd.dt)
            self.state = STATE_ENDING

        elif self.current_period is None:
            self.state = STATE_WAITING

        else:
            self.state = STATE_RUNNING

    def get_duration(self) -> str:

        if self.end_type == END_TYPE_DURATION:
            return self.duration

        elif self.end_type == END_TYPE_TIME:
            return datetime_utils.time_duration_str(self.start, self.end)

        else:
            return datetime_utils.DEFAULT_TIME

    def _timeStr(self, timeStr: str, offset: int) -> str:

        return "%s:%02i" % (timeStr, offset) if offset else timeStr

    def _mediaActionStr(self) -> str:

        if self.media_action == MEDIA_ACTION_START_STOP:
            return self._addon.getLocalizedString(32072)

        elif self.media_action == MEDIA_ACTION_START:
            return self._addon.getLocalizedString(32073)

        elif self.media_action == MEDIA_ACTION_START_AT_END:
            return self._addon.getLocalizedString(32074)

        elif self.media_action == MEDIA_ACTION_STOP_START:
            return self._addon.getLocalizedString(32075)

        elif self.media_action == MEDIA_ACTION_STOP:
            return self._addon.getLocalizedString(32076)

        elif self.media_action == MEDIA_ACTION_STOP_AT_END:
            return self._addon.getLocalizedString(32077)

        elif self.media_action == MEDIA_ACTION_PAUSE:
            return self._addon.getLocalizedString(32089)

        else:
            return self._addon.getLocalizedString(32071)

    def _systemActionStr(self) -> str:

        if self.system_action == SYSTEM_ACTION_SHUTDOWN_KODI:
            return self._addon.getLocalizedString(32082)

        elif self.system_action == SYSTEM_ACTION_QUIT_KODI:
            return self._addon.getLocalizedString(32083)

        elif self.system_action == SYSTEM_ACTION_STANDBY:
            return self._addon.getLocalizedString(32084)

        elif self.system_action == SYSTEM_ACTION_HIBERNATE:
            return self._addon.getLocalizedString(32085)

        elif self.system_action == SYSTEM_ACTION_POWEROFF:
            return self._addon.getLocalizedString(32086)

        elif self.system_action == SYSTEM_ACTION_CEC_STANDBY:
            return self._addon.getLocalizedString(32093)

        elif self.system_action == SYSTEM_ACTION_RESTART_KODI:
            return self._addon.getLocalizedString(32094)

        elif self.system_action == SYSTEM_ACTION_REBOOT_SYSTEM:
            return self._addon.getLocalizedString(32099)

        else:
            return self._addon.getLocalizedString(32071)

    def _endTypeStr(self) -> str:

        if self.end_type == END_TYPE_DURATION:
            return self._addon.getLocalizedString(32064)

        elif self.end_type == END_TYPE_TIME:
            return self._addon.getLocalizedString(32065)

        else:
            return self._addon.getLocalizedString(32063)

    def _fadeStr(self) -> str:

        if self.fade == FADE_IN_FROM_MIN:
            return self._addon.getLocalizedString(32121)

        elif self.fade == FADE_OUT_FROM_MAX:
            return self._addon.getLocalizedString(32122)

        elif self.fade == FADE_OUT_FROM_CURRENT:
            return self._addon.getLocalizedString(32123)

        else:
            return self._addon.getLocalizedString(32120)

    def _playerOptionStr(self) -> str:

        options = list()
        if self.repeat:
            options.append(self._addon.getLocalizedString(32078))

        if self.shuffle:
            options.append(self._addon.getLocalizedString(32088))

        if self.resume:
            options.append(self._addon.getLocalizedString(32079))

        return ", ".join(options)

    def format(self, format: str, max_: int = 0, shorten: int = 0) -> str:

        format = format.replace("$H", str(self.periods_to_human_readable()))
        format = format.replace("$S", self._timeStr(
            self.start, self.start_offset))
        format = format.replace(
            "$E", self._timeStr(self.end, self.end_offset))
        format = format.replace("$T", self._timeStr(self.start, self.start_offset) + (
            " - %s" % self._timeStr(self.end, self.end_offset) if self.end_type else ""))
        format = format.replace("$e", self._endTypeStr())
        format = format.replace("$M", self._mediaActionStr())
        format = format.replace("$O", self._playerOptionStr())
        format = format.replace("$F", self._fadeStr())
        format = format.replace("$P", self._systemActionStr())
        format = format.replace("$L", self.label if not max_ or not shorten or (len(self.label) + len(format))
                                < max_ else self.label[:max(max_ - len(format), shorten)] + "...")
        return format

    def periods_to_human_readable(self) -> str:

        self.init()
        _start = self._timeStr(self.start, self.start_offset)
        _end = self._timeStr(self.end, self.end_offset)
        return datetime_utils.periods_to_human_readable(self.days, start=_start, end=_end if self.end_type != END_TYPE_NO else None, date=self.date)

    def set_timer_by_date(self, date: str) -> None:

        self.days = [TIMER_BY_DATE]
        self.date = date

    def to_timer_by_date(self, base: 'datetime | None') -> bool:

        if not base:
            return False

        elif self.is_off() or self.is_weekly_timer():
            self.date = ""
            return False

        elif self.is_timer_by_date():
            return True

        _, upcoming_event = self._apply_weekday_periods(
            datetime_utils.DateTimeDelta(base))
        self.date = datetime_utils.to_date_str(upcoming_event)
        if len(self.days) == 1:
            self.set_timer_by_date(self.date)
            return True

        return False

    def is_timer_by_date(self) -> bool:

        return TIMER_BY_DATE in self.days

    def is_weekly_timer(self) -> bool:

        return TIMER_WEEKLY in self.days

    def is_off(self) -> bool:

        return not self.days

    def is_fading_timer(self) -> bool:

        return self.fade != FADE_OFF and self.end_type != END_TYPE_NO

    def is_playing_media_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_AT_END, MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_START] and self.path

    def is_play_at_start_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START, MEDIA_ACTION_START_STOP] and self.path

    def is_stop_at_start_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_STOP, MEDIA_ACTION_STOP_START]

    def is_stop_at_end_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_START_STOP, MEDIA_ACTION_STOP_AT_END]

    def is_play_at_end_timer(self) -> bool:

        return self.media_action in [MEDIA_ACTION_STOP_START, MEDIA_ACTION_START_AT_END] and self.path

    def is_pause_timer(self) -> bool:

        return self.media_action == MEDIA_ACTION_PAUSE

    def is_resuming_timer(self) -> bool:

        return self.media_action == MEDIA_ACTION_START_STOP and self.resume

    def is_script_timer(self) -> bool:

        return is_script(self.path)

    def is_system_execution_timer(self) -> bool:

        return self.system_action != SYSTEM_ACTION_NONE

    def to_dict(self) -> 'dict':

        return {
            "days": self.days,
            "date": self.date,
            "duration": self.duration,
            "duration_offset": self.duration_offset,
            "end": self.end,
            "end_offset": self.end_offset,
            "end_type": self.end_type,
            "fade": self.fade,
            "id": self.id,
            "label": self.label,
            "media_action": self.media_action,
            "media_type": self.media_type,
            "notify": self.notify,
            "path": self.path,
            "priority": self.priority,
            "repeat": self.repeat,
            "resume": self.resume,
            "shuffle": self.shuffle,
            "start": self.start,
            "start_offset": self.start_offset,
            "system_action": self.system_action,
            "vol_min": self.vol_min,
            "vol_max": self.vol_max
        }

    def __str__(self) -> str:

        return "Timer[id=%i, label=%s, state=%s, prio=%i, days=%s, date=%s, start=%s:%02i, endtype=%s, duration=%s:%02i, end=%s:%02i, systemaction=%s, mediaaction=%s, path=%s, type=%s, repeat=%s, shuffle=%s, resume=%s, fade=%s, min=%i, max=%i, returnvol=%i, notify=%s]" % (self.id, self.label, ["waiting", "starting", "running", "ending"][self.state], self.priority,
                                                                                                                                                                                                                                                                                 [["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "weekly", "date"][d] for d in self.days],
                                                                                                                                                                                                                                                                                 self.date,
                                                                                                                                                                                                                                                                                 self.start,
                                                                                                                                                                                                                                                                                 self.start_offset,
                                                                                                                                                                                                                                                                                 self._endTypeStr(),
                                                                                                                                                                                                                                                                                 self.duration, self.duration_offset,
                                                                                                                                                                                                                                                                                 self.end, self.end_offset,
                                                                                                                                                                                                                                                                                 self._systemActionStr(),
                                                                                                                                                                                                                                                                                 self._mediaActionStr(),
                                                                                                                                                                                                                                                                                 self.path,
                                                                                                                                                                                                                                                                                 self.media_type,
                                                                                                                                                                                                                                                                                 self.repeat,
                                                                                                                                                                                                                                                                                 self.shuffle,
                                                                                                                                                                                                                                                                                 self.resume,
                                                                                                                                                                                                                                                                                 self._fadeStr(),
                                                                                                                                                                                                                                                                                 self.vol_min,
                                                                                                                                                                                                                                                                                 self.vol_max,
                                                                                                                                                                                                                                                                                 self.return_vol or self.vol_max,
                                                                                                                                                                                                                                                                                 self.notify)
