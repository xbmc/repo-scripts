import os
from datetime import timedelta

import xbmcaddon
import xbmcgui
import xbmcvfs
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.player import Player
from resources.lib.player.player_utils import (get_types_replaced_by_type,
                                               run_addon)
from resources.lib.timer.period import Period
from resources.lib.timer.timer import (END_TYPE_NO, FADE_IN_FROM_MIN,
                                       FADE_OUT_FROM_CURRENT, TIMER_WEEKLY,
                                       Timer)
from resources.lib.timer.timerwithperiod import TimerWithPeriod
from resources.lib.utils.datetime_utils import abs_time_diff


class SchedulerAction:

    _player = None

    _beginningTimers = None
    _runningTimers = None
    _endingTimers = None

    _timerToPlayAV = None
    _timerToStopAV = None
    _timerToPlaySlideshow = None
    _timerToStopSlideshow = None
    _timersToRunScript = None
    _timerWithSystemAction = None
    _forceResumeResetTypes = None

    _fader = None
    _volume = None

    _hasStartOrEndTimer = False
    _hasFader = False

    def __init__(self, player: Player) -> None:

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
                _tts = self._getTimerToStopSlideshow(
                ) if timer.s_mediatype == PICTURE else self._getTimerToStopAV()
                if not _tts or timerWithPeriod.getPeriod().getStart() >= _tts.getPeriod().getStart():
                    self._setTimerToStopAny(timerWithPeriod)

            elif timer.is_play_at_end_timer():
                self._setTimerToPlayAny(timerWithPeriod)

            if timer.is_fading_timer():
                self._volume = self._volume if self._volume and self._volume > timer.i_return_vol else timer.i_return_vol

        def _collectFadingTimer(timer: Timer, period: Period) -> None:

            if (self._fader == None
                    or self._getFader().getPeriod().getStart() > period.getStart()):
                self._fader = TimerWithPeriod(timer, period)

        def _collectTimers(timers: 'list[Timer]', now: timedelta) -> None:

            self._hasStartOrEndTimer = False
            self._hasFader = False
            for timer in timers:
                period = timer.get_matching_period(now)

                if period is not None and not timer.b_active:
                    _collectBeginningTimer(timer, period)
                    self._hasStartOrEndTimer = True

                elif period is None and timer.b_active:
                    _collectEndingTimer(timer, Period(
                        now - timer.td_duration, now))
                    self._hasStartOrEndTimer = True

                elif period is not None and timer.is_play_at_start_timer() and timer.is_stop_at_end_timer():
                    _collectRunningTimer(timer, period)

                if period is not None and timer.is_fading_timer():
                    _collectFadingTimer(timer, period)
                    self._hasFader = True

        def _handleNestedStoppingTimer(timerToStop: TimerWithPeriod) -> None:

            if timerToStop:
                _stopMediatype = timerToStop.getTimer().s_mediatype
                _types_replaced_by_type = get_types_replaced_by_type(
                    _stopMediatype)
                for overlappingTimer in self._getRunningTimers():
                    if (overlappingTimer.getTimer().s_mediatype in _types_replaced_by_type
                            and timerToStop.getPeriod().getStart() < overlappingTimer.getPeriod().getStart()
                            and timerToStop.getPeriod().getEnd() < overlappingTimer.getPeriod().getEnd()):

                        self._forceResumeResetTypes.extend(
                            _types_replaced_by_type if not timerToStop.getTimer().is_resuming_timer() else list())

                        if _stopMediatype in [AUDIO, VIDEO]:
                            self._timerToStopAV = None

                        elif _stopMediatype == PICTURE:
                            self._timerToStopSlideshow = None

                        return

                if timerToStop.getTimer().is_resuming_timer():
                    enclosingTimers = [twp for twp in self._getRunningTimers(
                    ) if (twp.getPeriod().getStart() < timerToStop.getPeriod().getStart()
                          and twp.getPeriod().getEnd() > timerToStop.getPeriod().getEnd())]
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
                    elif timer.i_return_vol == None:
                        timer.i_return_vol = self._player.getVolume()

                if timer.is_play_at_start_timer():
                    self._setTimerToPlayAny(twp)

                elif timer.is_stop_at_start_timer():
                    self._setTimerToStopAny(twp)

        def _handleSystemAction() -> None:

            if self._getTimerWithSystemAction():
                self._timerToPlayAV = None
                self._timerToStopAV = self._getTimerWithSystemAction()
                self._timerToPlaySlideshow = None
                self._timerToStopSlideshow = self._getTimerWithSystemAction()
                self._fader = None
                self._forceResumeResetTypes.extend(TYPES)

        def _sumupEffectivePlayerAction() -> None:

            def _sumUp(timerToPlay: TimerWithPeriod, timerToStop: TimerWithPeriod) -> TimerWithPeriod:

                if timerToPlay:
                    if timerToStop and timerToStop.getPeriod().getEnd() == timerToPlay.getPeriod().getStart():
                        self._forceResumeResetTypes.extend(get_types_replaced_by_type(
                            timerToStop.getTimer().s_mediatype) if not timerToStop.getTimer().is_resuming_timer() else list())

                    timerToStop = None

                return timerToStop

            timerToPlayAV = self._getTimerToPlayAV()
            if timerToPlayAV and PICTURE in get_types_replaced_by_type(timerToPlayAV.getTimer().s_mediatype):
                self._timerToPlaySlideshow = None

            self._timerToStopAV = _sumUp(
                timerToPlayAV, self._getTimerToStopAV())
            self._timerToStopSlideshow = _sumUp(
                self._getTimerToPlaySlideshow(), self._getTimerToStopSlideshow())

            fader = self._getFader()
            if fader and (self._timerToStopAV == fader or self._timerToStopSlideshow == fader):
                self._fader = None

        def _determineVolume(now: timedelta) -> None:

            if self._getTimerWithSystemAction():
                self._volume = self._player.getDefaultVolume()
                return

            fader = self._getFader()
            if not fader:
                return

            timer = fader.getTimer()

            delta_now_start = abs_time_diff(
                now, fader.getPeriod().getStart())
            delta_end_start = abs_time_diff(
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
        if self._hasStartOrEndTimer:
            _handleNestedStoppingTimer(self._getTimerToStopAV())
            _handleNestedStoppingTimer(self._getTimerToStopSlideshow())
            _handleStartingTimers()
            _handleSystemAction()
            _sumupEffectivePlayerAction()

        if self._hasStartOrEndTimer or self._hasFader:
            _determineVolume(now)

    def _getBeginningTimers(self) -> 'list[TimerWithPeriod]':

        return self._beginningTimers

    def _getEndingTimers(self) -> 'list[TimerWithPeriod]':

        return self._endingTimers

    def _setTimerToStopAny(self, twp: TimerWithPeriod) -> None:

        if twp.getTimer().s_mediatype == PICTURE:
            self._timerToStopSlideshow = twp

        else:
            self._timerToStopAV = twp

    def _getTimerToStopAV(self) -> TimerWithPeriod:

        return self._timerToStopAV

    def _getTimerToStopSlideshow(self) -> TimerWithPeriod:

        return self._timerToStopSlideshow

    def _getRunningTimers(self) -> 'list[TimerWithPeriod]':

        return self._runningTimers

    def _getFader(self) -> TimerWithPeriod:

        return self._fader

    def _setTimerToPlayAny(self, twp: TimerWithPeriod) -> None:

        if twp.getTimer().is_script_timer():
            self._timersToRunScript.append(twp)

        elif twp.getTimer().s_mediatype == PICTURE:
            self._timerToPlaySlideshow = twp

        else:
            self._timerToPlayAV = twp

    def _getTimerToPlayAV(self) -> TimerWithPeriod:

        return self._timerToPlayAV

    def _getTimerToPlaySlideshow(self) -> TimerWithPeriod:

        return self._timerToPlaySlideshow

    def _getTimersToRunScripts(self) -> 'list[TimerWithPeriod]':

        return self._timersToRunScript

    def _getTimerWithSystemAction(self) -> TimerWithPeriod:

        return self._timerWithSystemAction

    def perform(self) -> None:

        def _performPlayerAction() -> None:

            timerToPlay = self._getTimerToPlayAV()
            timerToStop = self._getTimerToStopAV()
            if timerToPlay:
                self._player.playTimer(timerToPlay.getTimer())

            elif timerToStop:
                self._player.resumeFormerOrStop(timerToStop.getTimer())

            for type in self._forceResumeResetTypes:
                self._player.resetResumeStatus(type)

            timerToPlaySlideshow = self._getTimerToPlaySlideshow()
            timerToStopSlideshow = self._getTimerToStopSlideshow()

            if not timerToPlay or timerToPlay.getTimer().s_mediatype != VIDEO:
                if timerToPlaySlideshow:
                    self._player.playTimer(timerToPlaySlideshow.getTimer())

                elif timerToStopSlideshow:
                    self._player.resumeFormerOrStop(
                        timerToStopSlideshow.getTimer())

        def _setVolume() -> None:

            if self._volume != None:
                self._player.setVolume(self._volume)

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

        def _consumeSingleRunTimers() -> None:

            def _reset(ltwp: 'list[TimerWithPeriod]') -> None:

                for twp in ltwp:
                    timer = twp.getTimer()
                    if TIMER_WEEKLY not in timer.days:
                        if twp.getPeriod().getStart().days in timer.days:
                            timer.days.remove(twp.getPeriod().getStart().days)

                        if not timer.days:
                            Timer(timer.i_timer).save_to_settings()
                        else:
                            timer.save_to_settings()

            _reset(self._getEndingTimers())
            if self._getTimerWithSystemAction():
                _reset(self._getRunningTimers())

        def _runScripts() -> None:

            for twp in self._getTimersToRunScripts():
                run_addon(twp.getTimer().s_path)

        def _performSystemAction() -> None:

            timer = self._getTimerWithSystemAction()
            if timer:
                timer.getTimer().execute_system_action()

        if self._hasStartOrEndTimer:
            _performPlayerAction()

        _setVolume()

        if self._hasStartOrEndTimer:
            _runScripts()
            _showNotifications()
            _consumeSingleRunTimers()
            _performSystemAction()

    def reset(self) -> None:

        self._beginningTimers = list()
        self._runningTimers = list()
        self._endingTimers = list()
        self._forceResumeResetTypes = list()

        self._hasStartOrEndTimer = False
        self._hasFader = False

        self._fader = None
        self._timerToPlayAV = None
        self._timerToStopAV = None
        self._timerToPlaySlideshow = None
        self._timerToStopSlideshow = None
        self._timersToRunScript = list()
        self._timerWithSystemAction = None
        self._volume = None
