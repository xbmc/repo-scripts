from datetime import timedelta

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

    __is_unit_test__ = False

    def __init__(self, player: Player) -> None:

        self._player = player
        self.reset()

    def initFromTimers(self, timers: 'list[Timer]', now: timedelta) -> None:

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
                _tts = self._getTimerToStopSlideshow(
                ) if timer.media_type == PICTURE else self._getTimerToStopAV()
                if (not _tts
                        or _tts.getTimer().is_resuming_timer() and timerWithPeriod.getPeriod().getStart() >= _tts.getPeriod().getStart()):
                    self._setTimerToStopAny(timerWithPeriod)

            elif timer.is_play_at_end_timer():
                self._setTimerToPlayAny(timerWithPeriod)

            if timer.is_fading_timer():
                self._volume = self._volume if self._volume and self._volume > timer.return_vol else timer.return_vol

        def _collectFadingTimer(timer: Timer, period: Period) -> None:

            if (self._fader == None
                    or self._getFader().getPeriod().getStart() > period.getStart()):
                self._fader = TimerWithPeriod(timer, period)

        def _collectTimers(timers: 'list[Timer]', now: timedelta) -> None:

            self._hasStartOrEndTimer = False
            self._hasFader = False
            for timer in timers:
                period = timer.get_matching_period(now)

                if period is not None and not timer.active:
                    _collectBeginningTimer(timer, period)
                    self._hasStartOrEndTimer = True

                elif period is None and timer.active:
                    _collectEndingTimer(timer, Period(
                        now - timer.duration_timedelta, now))
                    self._hasStartOrEndTimer = True

                elif period is not None and timer.is_play_at_start_timer() and timer.is_stop_at_end_timer():
                    _collectRunningTimer(timer, period)

                if period is not None and timer.is_fading_timer():
                    _collectFadingTimer(timer, period)
                    self._hasFader = True

        def _handleNestedStoppingTimer(timerToStop: TimerWithPeriod) -> None:

            if timerToStop:
                _stopMediatype = timerToStop.getTimer().media_type
                _types_replaced_by_type = get_types_replaced_by_type(
                    _stopMediatype)
                for overlappingTimer in self._getRunningTimers():
                    if (overlappingTimer.getTimer().media_type in _types_replaced_by_type
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
                        timer.return_vol = fader.getTimer().return_vol
                    elif timer.return_vol == None:
                        timer.return_vol = self._player.getVolume()

                if timer.is_play_at_start_timer():
                    self._setTimerToPlayAny(twp)

                elif timer.is_stop_at_start_timer():
                    self._setTimerToStopAny(twp)

        def _handleSystemAction() -> None:

            timerWithSystemAction = self._getTimerWithSystemAction()
            if not timerWithSystemAction:
                return

            addon = xbmcaddon.Addon()
            lines = list()
            lines.append(addon.getLocalizedString(32270))
            lines.append(addon.getLocalizedString(
                32081 + timerWithSystemAction.getTimer().system_action))
            lines.append(addon.getLocalizedString(32271))
            abort = xbmcgui.Dialog().yesno(heading="%s: %s" % (addon.getLocalizedString(32256), timerWithSystemAction.getTimer().label),
                                           message="\n".join(lines),
                                           yeslabel=addon.getLocalizedString(
                                               32273),
                                           nolabel=addon.getLocalizedString(
                                               32272),
                                           autoclose=10000)

            if not abort or self.__is_unit_test__:
                self._timerToPlayAV = None
                self._timerToStopAV = timerWithSystemAction
                self._timerToPlaySlideshow = None
                self._timerToStopSlideshow = timerWithSystemAction
                self._fader = None
                self._forceResumeResetTypes.extend(TYPES)

            else:
                self._timerWithSystemAction = None

        def _sumupEffectivePlayerAction() -> None:

            def _sumUp(timerToPlay: TimerWithPeriod, timerToStop: TimerWithPeriod) -> TimerWithPeriod:

                if timerToPlay:
                    if timerToStop and timerToStop.getPeriod().getEnd() == timerToPlay.getPeriod().getStart():
                        self._forceResumeResetTypes.extend(get_types_replaced_by_type(
                            timerToStop.getTimer().media_type) if not timerToStop.getTimer().is_resuming_timer() else list())

                    timerToStop = None

                return timerToStop

            timerToPlayAV = self._getTimerToPlayAV()
            if timerToPlayAV and PICTURE in get_types_replaced_by_type(timerToPlayAV.getTimer().media_type):
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

            vol_min = timer.vol_min
            vol_max = timer.return_vol if timer.fade == FADE_OUT_FROM_CURRENT else timer.vol_max
            vol_diff = vol_max - vol_min

            if timer.fade == FADE_IN_FROM_MIN:
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

        if twp.getTimer().media_type == PICTURE:
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

        elif twp.getTimer().media_type == PICTURE:
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

            if not timerToPlay or timerToPlay.getTimer().media_type != VIDEO:
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

                if timer.notify and timer.end_type != END_TYPE_NO:
                    icon = get_asset_path("icon_sleep.png")
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32101), timer.label, icon)

            for twp in self._getBeginningTimers():
                timer = twp.getTimer()
                if timer.notify:
                    icon = get_asset_path(
                        "icon_alarm.png" if timer.end_type == END_TYPE_NO else "icon_sleep.png")
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32100), timer.label, icon=icon)

        def _consumeSingleRunTimers() -> None:

            def _reset(ltwp: 'list[TimerWithPeriod]') -> None:

                for twp in ltwp:
                    timer = twp.getTimer()
                    if TIMER_WEEKLY not in timer.days:
                        if twp.getPeriod().getStart().days in timer.days:
                            timer.days.remove(twp.getPeriod().getStart().days)

                        if not timer.days:
                            storage.delete_timer(timer.id)
                        else:
                            storage.save_timer(timer=timer)

            _reset(self._getEndingTimers())
            if self._getTimerWithSystemAction():
                _reset(self._getRunningTimers())

        def _runScripts() -> None:

            for twp in self._getTimersToRunScripts():
                run_addon(twp.getTimer().path)

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
