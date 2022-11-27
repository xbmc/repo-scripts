from datetime import datetime, timedelta

import xbmcaddon
import xbmcgui
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.player import Player
from resources.lib.player.player_utils import (get_types_replaced_by_type,
                                               run_addon)
from resources.lib.timer import storage
from resources.lib.timer.period import Period
from resources.lib.timer.timer import (END_TYPE_NO, FADE_IN_FROM_MIN,
                                       FADE_OUT_FROM_CURRENT, TIMER_WEEKLY,
                                       Timer)
from resources.lib.timer.timerwithperiod import TimerWithPeriod
from resources.lib.utils.datetime_utils import abs_time_diff
from resources.lib.utils.vfs_utils import get_asset_path


class SchedulerAction:

    def __init__(self, player: Player) -> None:

        self._player: Player = player

        self._beginningTimers: 'list[TimerWithPeriod]' = None
        self._runningTimers: 'list[TimerWithPeriod]' = None
        self._endingTimers: 'list[TimerWithPeriod]' = None

        self._timerToPlayAV: TimerWithPeriod = None
        self._timerToStopAV: TimerWithPeriod = None
        self._timerToPlaySlideshow: TimerWithPeriod = None
        self._timerToStopSlideshow: TimerWithPeriod = None
        self._timersToRunScript: 'list[TimerWithPeriod]' = None
        self._timerWithSystemAction: TimerWithPeriod = None
        self._forceResumeResetTypes: 'list[str]' = None

        self._fader: TimerWithPeriod = None

        self.hasEventToPerform: bool = False
        self.upcoming_event: datetime = None

        self.__is_unit_test__: bool = False

        self.reset()

    def calculate(self, timers: 'list[Timer]', dt_now: datetime, td_now: timedelta) -> None:

        def _collectBeginningTimer(timer: Timer, period: Period) -> None:

            self._beginningTimers.append(TimerWithPeriod(timer, period))
            timer.active = True

        def _collectRunningTimer(timer: Timer, period: Period) -> None:

            self._runningTimers.append(TimerWithPeriod(timer, period))

        def _collectEndingTimer(timer: Timer, period: Period) -> None:

            timerWithPeriod = TimerWithPeriod(timer, period)
            self._endingTimers.append(timerWithPeriod)
            timer.active = False
            if timer.is_system_execution_timer():
                self._timerWithSystemAction = timerWithPeriod

            if timer.is_stop_at_end_timer():
                _tts = self._timerToStopSlideshow if timer.media_type == PICTURE else self._timerToStopAV
                if (not _tts
                        or _tts.timer.is_resuming_timer() and timerWithPeriod.period.start >= _tts.period.start):
                    self._setTimerToStopAny(timerWithPeriod)

            elif timer.is_play_at_end_timer():
                self._setTimerToPlayAny(timerWithPeriod)

        def _collectFadingTimer(timer: Timer, period: Period) -> None:

            if (self._fader == None
                    or self._fader.period.start > period.start):
                self._fader = TimerWithPeriod(timer, period)

        def _collectTimers(timers: 'list[Timer]', dt_now: datetime, td_now: timedelta) -> None:

            for timer in timers:
                matching_period, upcoming_event = timer.get_matching_period_and_upcoming_event(dt_now, td_now)

                if matching_period is not None and not timer.active:
                    _collectBeginningTimer(timer, matching_period)
                    self.hasEventToPerform = True

                elif matching_period is None and timer.active:
                    _collectEndingTimer(timer, Period(
                        td_now - timer.duration_timedelta, td_now))
                    self.hasEventToPerform = True

                elif matching_period is not None and timer.is_play_at_start_timer() and timer.is_stop_at_end_timer():
                    _collectRunningTimer(timer, matching_period)

                if matching_period is not None and timer.is_fading_timer():
                    _collectFadingTimer(timer, matching_period)

                if upcoming_event is not None:
                    self.upcoming_event = upcoming_event if self.upcoming_event is None or self.upcoming_event > upcoming_event else self.upcoming_event

        def _handleNestedStoppingTimer(timerToStop: TimerWithPeriod) -> None:

            if timerToStop:
                _stopMediatype = timerToStop.timer.media_type
                _types_replaced_by_type = get_types_replaced_by_type(
                    _stopMediatype)
                for overlappingTimer in self._runningTimers:
                    if (overlappingTimer.timer.media_type in _types_replaced_by_type
                            and timerToStop.period.start < overlappingTimer.period.start
                            and timerToStop.period.end < overlappingTimer.period.end):

                        self._forceResumeResetTypes.extend(
                            _types_replaced_by_type if not timerToStop.timer.is_resuming_timer() else list())

                        if _stopMediatype in [AUDIO, VIDEO]:
                            self._timerToStopAV = None

                        elif _stopMediatype == PICTURE:
                            self._timerToStopSlideshow = None

                        return

                if timerToStop.timer.is_resuming_timer():
                    enclosingTimers = [twp for twp in self._runningTimers if (twp.period.start < timerToStop.period.start
                                                                              and twp.period.end > timerToStop.period.end)]
                    self._beginningTimers.extend(enclosingTimers)

        def _handleStartingTimers() -> None:

            self._beginningTimers.sort(key=lambda twp: twp.period.start)
            for twp in self._beginningTimers:
                timer = twp.timer
                if timer.is_fading_timer():
                    if self._fader and timer is not self._fader.timer:
                        timer.return_vol = self._fader.timer.return_vol
                    elif timer.return_vol == None:
                        timer.return_vol = self._player.getVolume()

                if timer.is_play_at_start_timer():
                    self._setTimerToPlayAny(twp)

                elif timer.is_stop_at_start_timer():
                    self._setTimerToStopAny(twp)

        def _handleSystemAction() -> None:

            if not self._timerWithSystemAction:
                return

            addon = xbmcaddon.Addon()
            lines = list()
            lines.append(addon.getLocalizedString(32270))
            lines.append(addon.getLocalizedString(
                32081 + self._timerWithSystemAction.timer.system_action))
            lines.append(addon.getLocalizedString(32271))
            abort = xbmcgui.Dialog().yesno(heading="%s: %s" % (addon.getLocalizedString(32256), self._timerWithSystemAction.timer.label),
                                           message="\n".join(lines),
                                           yeslabel=addon.getLocalizedString(
                                               32273),
                                           nolabel=addon.getLocalizedString(
                                               32272),
                                           autoclose=10000)

            if not abort or self.__is_unit_test__:
                self._timerToPlayAV = None
                self._timerToStopAV = self._timerWithSystemAction
                self._timerToPlaySlideshow = None
                self._timerToStopSlideshow = self._timerWithSystemAction
                self._fader = None
                self._forceResumeResetTypes.extend(TYPES)

            else:
                self._timerWithSystemAction = None

        def _sumupEffectivePlayerAction() -> None:

            def _sumUp(timerToPlay: TimerWithPeriod, timerToStop: TimerWithPeriod) -> TimerWithPeriod:

                if timerToPlay:
                    if timerToStop and timerToStop.period.end == timerToPlay.period.start:
                        self._forceResumeResetTypes.extend(get_types_replaced_by_type(
                            timerToStop.timer.media_type) if not timerToStop.timer.is_resuming_timer() else list())

                    timerToStop = None

                return timerToStop

            if self._timerToPlayAV and PICTURE in get_types_replaced_by_type(self._timerToPlayAV.timer.media_type):
                self._timerToPlaySlideshow = None

            self._timerToStopAV = _sumUp(
                self._timerToPlayAV, self._timerToStopAV)
            self._timerToStopSlideshow = _sumUp(
                self._timerToPlaySlideshow, self._timerToStopSlideshow)

            if self._fader and (self._timerToStopAV == self._fader or self._timerToStopSlideshow == self._fader):
                self._fader = None

        self.reset()

        _collectTimers(timers, dt_now, td_now)

        if self.hasEventToPerform:
            _handleNestedStoppingTimer(self._timerToStopAV)
            _handleNestedStoppingTimer(self._timerToStopSlideshow)
            _handleStartingTimers()
            _handleSystemAction()
            _sumupEffectivePlayerAction()

    def _setTimerToStopAny(self, twp: TimerWithPeriod) -> None:

        if twp.timer.media_type == PICTURE:
            self._timerToStopSlideshow = twp

        else:
            self._timerToStopAV = twp

    def getFaderInterval(self) -> float:

        if not self._fader:
            return None

        delta_end_start = abs_time_diff(
            self._fader.period.end, self._fader.period.start)

        vol_max = self._fader.timer.return_vol if self._fader.timer.fade == FADE_OUT_FROM_CURRENT else self._fader.timer.vol_max
        vol_diff = vol_max - self._fader.timer.vol_min

        return delta_end_start/vol_diff

    def _setTimerToPlayAny(self, twp: TimerWithPeriod) -> None:

        if twp.timer.is_script_timer():
            self._timersToRunScript.append(twp)

        elif twp.timer.media_type == PICTURE:
            self._timerToPlaySlideshow = twp

        else:
            self._timerToPlayAV = twp

    def fade(self, td_now: timedelta) -> None:

        if not self._fader:
            return

        delta_now_start = abs_time_diff(
            td_now, self._fader.period.start)
        delta_end_start = abs_time_diff(
            self._fader.period.end, self._fader.period.start)
        delta_percent = delta_now_start / delta_end_start

        vol_max = self._fader.timer.return_vol if self._fader.timer.fade == FADE_OUT_FROM_CURRENT else self._fader.timer.vol_max
        vol_diff = vol_max - self._fader.timer.vol_min

        if self._fader.timer.fade == FADE_IN_FROM_MIN:
            _volume = int(round(self._fader.timer.vol_min +
                          vol_diff * delta_percent, 0))
        else:
            _volume = int(round(vol_max - vol_diff * delta_percent, 0))

        self._player.setVolume(_volume)

    def perform(self, td_now: timedelta) -> None:

        def _performPlayerAction() -> None:

            if self._timerToPlayAV:
                self._player.playTimer(self._timerToPlayAV.timer)

            elif self._timerToStopAV:
                self._player.resumeFormerOrStop(self._timerToStopAV.timer)

            for type in self._forceResumeResetTypes:
                self._player.resetResumeStatus(type)

            if not self._timerToPlayAV or self._timerToPlayAV.timer.media_type != VIDEO:
                if self._timerToPlaySlideshow:
                    self._player.playTimer(self._timerToPlaySlideshow.timer)

                elif self._timerToStopSlideshow:
                    self._player.resumeFormerOrStop(
                        self._timerToStopSlideshow.timer)

        def _setVolume(td_now: timedelta) -> None:

            if self._timerWithSystemAction:
                self._player.setVolume(self._player.getDefaultVolume())
                return

            else:
                self.fade(td_now)

            return_vols = [
                twp.timer.return_vol for twp in self._endingTimers if twp.timer.is_fading_timer()]
            if return_vols:
                self._player.setVolume(max(return_vols))

        def _showNotifications() -> None:

            addon = xbmcaddon.Addon()

            for twp in self._endingTimers:
                timer = twp.timer

                if timer.notify and timer.end_type != END_TYPE_NO:
                    icon = get_asset_path("icon_sleep.png")
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32101), timer.label, icon)

            for twp in self._beginningTimers:
                timer = twp.timer
                if timer.notify:
                    icon = get_asset_path(
                        "icon_alarm.png" if timer.end_type == END_TYPE_NO else "icon_sleep.png")
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32100), timer.label, icon=icon)

        def _consumeSingleRunTimers() -> None:

            def _reset(ltwp: 'list[TimerWithPeriod]') -> None:

                for twp in ltwp:
                    timer = twp.timer
                    if TIMER_WEEKLY not in timer.days:
                        if twp.period.start.days in timer.days:
                            timer.days.remove(twp.period.start.days)

                        if not timer.days:
                            storage.delete_timer(timer.id)
                        else:
                            storage.save_timer(timer=timer)

            _reset(self._endingTimers)
            if self._timerWithSystemAction:
                _reset(self._runningTimers)

        def _runScripts() -> None:

            for twp in self._timersToRunScript:
                run_addon(twp.timer.path)

        def _performSystemAction() -> None:

            if self._timerWithSystemAction:
                self._timerWithSystemAction.timer.execute_system_action()

        if self.hasEventToPerform:
            _performPlayerAction()

        _setVolume(td_now)

        if self.hasEventToPerform:
            _runScripts()
            _showNotifications()
            _consumeSingleRunTimers()
            _performSystemAction()

        self.hasEventToPerform = False

    def reset(self) -> None:

        self._beginningTimers = list()
        self._runningTimers = list()
        self._endingTimers = list()
        self._forceResumeResetTypes = list()

        self.hasEventToPerform = False
        self.upcoming_event = None

        self._fader = None
        self._timerToPlayAV = None
        self._timerToStopAV = None
        self._timerToPlaySlideshow = None
        self._timerToStopSlideshow = None
        self._timersToRunScript = list()
        self._timerWithSystemAction = None
