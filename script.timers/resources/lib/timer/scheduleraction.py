import os
from datetime import timedelta

import xbmcaddon
import xbmcgui
import xbmcvfs
from resources.lib.player.player import Player
from resources.lib.timer.period import Period
from resources.lib.timer.timer import (END_TYPE_NO, FADE_IN_FROM_MIN,
                                       FADE_OUT_FROM_CURRENT, TIMER_ONCE,
                                       Timer)
from resources.lib.timer.timerwithperiod import TimerWithPeriod
from resources.lib.utils import datetime_utils


class SchedulerAction:

    _player = None

    _beginningTimers = None
    _runningTimers = None
    _endingTimers = None

    _fader = None
    _timerToPlay = None
    _timerToStop = None
    _timerWithSystemAction = None
    _volume = None

    _forceResumeReset = False

    def __init__(self, player) -> None:

        self._player = player
        self.reset()

    def initFromTimers(self, timers: 'list[Timer]', now: timedelta) -> None:

        def _collectBeginningTimer(timer: Timer, period: Period) -> None:

            self._beginningTimers.append(TimerWithPeriod(timer, period))
            timer.b_active = True

        def _collectRunningTimer(timer: Timer, period: Period) -> None:

            self._runningTimers.append(TimerWithPeriod(timer, period))

        def _collectEndingTimer(timer: Timer, period: Period) -> None:

            timerWithPeriod = TimerWithPeriod(timer, period)
            self._endingTimers.append(timerWithPeriod)
            timer.b_active = False
            if timer.is_system_execution_timer():
                self._timerWithSystemAction = timerWithPeriod

            elif timer.is_stop_at_end_timer():
                if not self._timerToStop or timerWithPeriod.getPeriod().getStart() >= self._getTimerToStop().getPeriod().getStart():
                    self._timerToStop = timerWithPeriod

            elif timer.is_play_at_end_timer():
                self._timerToPlay = timerWithPeriod

            if timer.is_fading_timer():
                self._volume = self._volume if self._volume and self._volume > timer.i_return_vol else timer.i_return_vol

        def _collectFadingTimer(timer: Timer, period: Period) -> None:

            if self._fader == None or self._getFader().getPeriod().getStart() < period.getStart():
                self._fader = TimerWithPeriod(timer, period)

        def _collectTimers(timers: 'list[Timer]', now: timedelta) -> None:

            for timer in timers:
                period = timer.get_matching_period(now)

                if period is not None and not timer.b_active:
                    _collectBeginningTimer(timer, period)

                elif period is None and timer.b_active:
                    _collectEndingTimer(timer, Period(
                        now - timer.td_duration, now))

                elif period is not None and timer.is_play_at_start_timer() and timer.is_stop_at_end_timer():
                    _collectRunningTimer(timer, period)

                if period is not None and timer.is_fading_timer():
                    _collectFadingTimer(timer, period)

        def _handleNestedStoppingTimer() -> None:

            timerToStop = self._getTimerToStop()
            if timerToStop:
                for otwp in self._getRunningTimers():
                    if timerToStop and timerToStop.getPeriod().getStart() < otwp.getPeriod().getStart() and timerToStop.getPeriod().getEnd() < otwp.getPeriod().getEnd():
                        self._forceResumeReset = not timerToStop.getTimer().b_resume
                        self._timerToStop = None
                        return

                if timerToStop.getTimer().b_resume:
                    enclosingTimers = [twp for twp in self._getRunningTimers(
                    ) if twp.getPeriod().getStart() < timerToStop.getPeriod().getStart() and twp.getPeriod().getEnd() > timerToStop.getPeriod().getEnd()]
                    self._beginningTimers.extend(enclosingTimers)

        def _handleStartingTimers() -> None:

            fader = self._getFader()
            startingTimers = self._getBeginningTimers()
            startingTimers.sort(key=lambda twp: twp.getPeriod().getStart())
            for twp in startingTimers:
                timer = twp.getTimer()
                if timer.is_fading_timer():
                    if fader and timer is not fader.getTimer():
                        timer.i_return_vol = fader.getTimer().i_return_vol
                    else:
                        timer.i_return_vol = self._getPlayer().get_volume()

                if timer.is_play_at_start_timer():
                    self._timerToPlay = twp

                elif timer.is_stop_at_start_timer():
                    self._timerToStop = twp

        def _sumupEffectivePlayerAction() -> None:

            if self._getTimerWithSystemAction():
                self._timerToPlay = None
                self._timerToStop = self._getTimerWithSystemAction()
                self._fader = None
                return

            timerToPlay = self._getTimerToPlay()
            timerToStop = self._getTimerToStop()
            if timerToPlay:
                if timerToStop and timerToStop.getPeriod().getEnd() == timerToPlay.getPeriod().getStart():
                    self._forceResumeReset = not timerToStop.getTimer().b_resume

                self._timerToStop = None

            elif self._timerToStop:
                self._fader = None

        def _determineVolume(now: timedelta) -> None:

            if self._getTimerWithSystemAction():
                self._volume = self._getPlayer().get_default_volume()
                return

            fader = self._getFader()
            if not fader:
                return

            timer = fader.getTimer()

            delta_now_start = datetime_utils.abs_time_diff(
                now, fader.getPeriod().getStart())
            delta_end_start = datetime_utils.abs_time_diff(
                fader.getPeriod().getEnd(), fader.getPeriod().getStart())
            delta_percent = delta_now_start / delta_end_start

            vol_min = timer.i_vol_min
            vol_max = timer.i_return_vol if timer.i_fade == FADE_OUT_FROM_CURRENT else timer.i_vol_max
            vol_diff = vol_max - vol_min

            if timer.i_fade == FADE_IN_FROM_MIN:
                self._volume = int(vol_min + vol_diff * delta_percent)
            else:
                self._volume = int(vol_max - vol_diff * delta_percent)

        _collectTimers(timers, now)
        _handleNestedStoppingTimer()
        _handleStartingTimers()
        _sumupEffectivePlayerAction()
        _determineVolume(now)

    def _getPlayer(self) -> Player:

        return self._player

    def _getBeginningTimers(self) -> 'list[TimerWithPeriod]':

        return self._beginningTimers

    def _getEndingTimers(self) -> 'list[TimerWithPeriod]':

        return self._endingTimers

    def _getTimerToStop(self) -> TimerWithPeriod:

        return self._timerToStop

    def _getRunningTimers(self) -> 'list[TimerWithPeriod]':

        return self._runningTimers

    def _getFader(self) -> TimerWithPeriod:

        return self._fader

    def _getTimerToPlay(self) -> TimerWithPeriod:

        return self._timerToPlay

    def _getTimerWithSystemAction(self) -> TimerWithPeriod:

        return self._timerWithSystemAction

    def perform(self) -> None:

        def _performPlayerAction() -> None:

            timerToPlay = self._getTimerToPlay()
            if timerToPlay:

                self._getPlayer().playTimer(timerToPlay.getTimer())

            elif self._getTimerToStop():
                self._getPlayer().resumeFormerOrStop()

            if self._forceResumeReset:
                self._getPlayer().resetResumeStatus()

        def _setVolume() -> None:

            if self._volume != None:
                self._getPlayer().set_volume(self._volume)

        def _showNotifications() -> None:

            addon = xbmcaddon.Addon()

            for twp in self._getEndingTimers():
                timer = twp.getTimer()

                if timer.b_notify and timer.i_end_type != END_TYPE_NO:
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32101), timer.s_label)

            for twp in self._getBeginningTimers():
                timer = twp.getTimer()
                if timer.b_notify:
                    icon_file = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')),
                                             "resources",
                                             "assets", "icon_alarm.png" if timer.i_end_type == END_TYPE_NO else "icon_sleep.png")
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32100), timer.s_label, icon=icon_file)

        def _resetSingleRunTimers() -> None:

            def _reset(ltwp: 'list[TimerWithPeriod]') -> None:

                for twp in ltwp:
                    timer = twp.getTimer()
                    if timer.i_schedule in TIMER_ONCE:
                        Timer(timer.i_timer).save_to_settings()

            _reset(self._getEndingTimers())
            if self._getTimerWithSystemAction():
                _reset(self._getRunningTimers())

        def _performSystemAction() -> None:

            timer = self._getTimerWithSystemAction()
            if timer:
                timer.getTimer().execute_system_action()

        _performPlayerAction()
        _setVolume()
        _showNotifications()
        _resetSingleRunTimers()
        _performSystemAction()

    def reset(self):

        self._beginningTimers = list()
        self._runningTimers = list()
        self._endingTimers = list()

        self._fader = None
        self._timerToPlay = None
        self._timerToStop = None
        self._timerWithSystemAction = None
        self._volume = None
        self._forceResumeReset = False
