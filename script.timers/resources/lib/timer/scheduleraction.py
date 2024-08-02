from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.player import Player
from resources.lib.player.player_utils import (get_types_replaced_by_type,
                                               run_addon)
from resources.lib.timer.notification import showNotification
from resources.lib.timer.storage import Storage
from resources.lib.timer.timer import (FADE_IN_FROM_MIN, FADE_OUT_FROM_CURRENT,
                                       STATE_ENDING, STATE_RUNNING,
                                       STATE_STARTING, STATE_WAITING,
                                       SYSTEM_ACTION_CEC_STANDBY,
                                       SYSTEM_ACTION_HIBERNATE,
                                       SYSTEM_ACTION_POWEROFF,
                                       SYSTEM_ACTION_QUIT_KODI,
                                       SYSTEM_ACTION_RESTART_KODI,
                                       SYSTEM_ACTION_REBOOT_SYSTEM,
                                       SYSTEM_ACTION_SHUTDOWN_KODI,
                                       SYSTEM_ACTION_STANDBY, TIMER_WEEKLY,
                                       Timer)
from resources.lib.utils.datetime_utils import DateTimeDelta, abs_time_diff


class SchedulerAction:

    def __init__(self, player: Player, storage: Storage) -> None:

        self._player: Player = player
        self.storage = storage

        self.upcoming_event: datetime = None
        self.upcoming_timer: Timer = None
        self.hasEventToPerform: bool = False

        self.timerToPlayAV: Timer = None
        self.timerToPauseAV: Timer = None
        self.timerToUnpauseAV: Timer = None
        self.timerToStopAV: Timer = None
        self.timerToPlaySlideshow: Timer = None
        self.timerToStopSlideshow: Timer = None
        self.timersToRunScript: 'list[Timer]' = None
        self.timerWithSystemAction: Timer = None
        self.fader: Timer = None

        self._beginningTimers: 'list[Timer]' = None
        self._runningTimers: 'list[Timer]' = None
        self._endingTimers: 'list[Timer]' = None
        self._forceResumeResetTypes: 'list[str]' = None

        self.__is_unit_test__: bool = False

        self.reset()

    def calculate(self, timers: 'list[Timer]', now: DateTimeDelta) -> None:

        def _collectEndingTimer(timer: Timer) -> None:

            self._endingTimers.append(timer)

            if timer.is_system_execution_timer():
                self.timerWithSystemAction = timer

            if timer.is_stop_at_end_timer():
                _tts = self.timerToStopSlideshow if timer.media_type == PICTURE else self.timerToStopAV
                if (not _tts
                        or _tts.priority < timer.priority
                        or _tts.is_resuming_timer() and timer.current_period.start >= _tts.current_period.start):
                    self._setTimerToStopAny(timer)

            elif timer.is_play_at_end_timer():
                self._setTimerToPlayAny(timer)

            elif timer.is_pause_timer():
                self.timerToUnpauseAV = timer

        def _collectTimers(timers: 'list[Timer]', now: DateTimeDelta) -> None:

            for timer in timers:
                timer.apply(now)

                if timer.state == STATE_STARTING:
                    self._beginningTimers.append(timer)
                    self.hasEventToPerform = True

                elif timer.state == STATE_ENDING:
                    _collectEndingTimer(timer)
                    self.hasEventToPerform = True

                elif timer.state == STATE_RUNNING:
                    self._runningTimers.append(timer)

                if timer.state in [STATE_STARTING, STATE_RUNNING] and timer.is_fading_timer() \
                        and (self.fader == None or self.fader.current_period.start > timer.current_period.start):
                    self.fader = timer

                if timer.upcoming_event is not None:
                    if self.upcoming_event is None or self.upcoming_event > timer.upcoming_event:
                        self.upcoming_event = timer.upcoming_event
                        self.upcoming_timer = timer

        def _handleNestedStoppingTimer(timerToStop: Timer) -> None:

            def _reset_stop():
                if _stopMediatype in [AUDIO, VIDEO]:
                    self.timerToStopAV = None

                elif _stopMediatype == PICTURE:
                    self.timerToStopSlideshow = None

            if timerToStop:
                _stopMediatype = timerToStop.media_type
                _types_replaced_by_type = get_types_replaced_by_type(
                    _stopMediatype)
                for overlappingTimer in self._runningTimers:
                    if (overlappingTimer.media_type in _types_replaced_by_type
                            and overlappingTimer.is_play_at_start_timer() and overlappingTimer.is_stop_at_end_timer()
                            and timerToStop.current_period.start <= overlappingTimer.current_period.start
                            and timerToStop.current_period.end < overlappingTimer.current_period.end):

                        self._forceResumeResetTypes.extend(
                            _types_replaced_by_type if not timerToStop.is_resuming_timer() else list())

                        if overlappingTimer.priority < timerToStop.priority and timerToStop.is_playing_media_timer() and overlappingTimer.media_type in _types_replaced_by_type:
                            self._beginningTimers.append(overlappingTimer)

                        _reset_stop()

                enclosingTimers = [t for t in self._runningTimers if (t.current_period.start < timerToStop.current_period.start
                                                                      and t.current_period.end > timerToStop.current_period.end)
                                   and t.is_play_at_start_timer() and t.media_type in _types_replaced_by_type]

                if enclosingTimers and not [t for t in enclosingTimers if timerToStop.priority >= t.priority]:
                    _reset_stop()

                elif timerToStop.is_resuming_timer():
                    self._beginningTimers.extend(enclosingTimers)

        def _handleStartingTimers() -> None:

            self._beginningTimers.sort(key=lambda t: t.current_period.start)
            for timer in self._beginningTimers:
                if timer.is_fading_timer():
                    if self.fader and timer is not self.fader:
                        timer.return_vol = self.fader.return_vol
                    elif timer.return_vol == None:
                        timer.return_vol = self._player.getVolume()

                higher_prio_runnings = [running for running in self._runningTimers if running.priority > timer.priority
                                        and running.is_play_at_start_timer() and running.media_type in get_types_replaced_by_type(timer.media_type)]

                if not higher_prio_runnings and timer.is_play_at_start_timer():
                    self._setTimerToPlayAny(timer)

                elif timer.is_stop_at_start_timer():
                    self._setTimerToStopAny(timer)

                elif timer.is_pause_timer():
                    self.timerToPauseAV = timer

        def _handleSystemAction() -> None:

            if not self.timerWithSystemAction or self.timerWithSystemAction.system_action == SYSTEM_ACTION_CEC_STANDBY:
                return

            addon = xbmcaddon.Addon()
            lines = list()
            lines.append(addon.getLocalizedString(32270))
            lines.append(self.timerWithSystemAction.format("$P"))
            lines.append(addon.getLocalizedString(32271))
            abort = xbmcgui.Dialog().yesno(heading="%s: %s" % (addon.getLocalizedString(32256), self.timerWithSystemAction.label),
                                           message="\n".join(lines),
                                           yeslabel=addon.getLocalizedString(
                                               32273),
                                           nolabel=addon.getLocalizedString(
                                               32272),
                                           autoclose=10000)

            if not abort or self.__is_unit_test__:
                self.timerToPlayAV = None
                self.timerToPauseAV = None
                self.timerToUnpauseAV = None
                self.timerToStopAV = self.timerWithSystemAction
                self.timerToPlaySlideshow = None
                self.timerToStopSlideshow = self.timerWithSystemAction
                self.fader = None
                self._forceResumeResetTypes.extend(TYPES)

            else:
                self.timerWithSystemAction = None

        def _sumupEffectivePlayerAction() -> None:

            def _sumUp(timerToPlay: Timer, timerToStop: Timer) -> Timer:

                if timerToPlay:
                    if timerToStop and timerToStop.current_period.end == timerToPlay.current_period.start:
                        self._forceResumeResetTypes.extend(get_types_replaced_by_type(
                            timerToStop.media_type) if not timerToStop.is_resuming_timer() else list())

                    timerToStop = None

                return timerToStop

            if self.timerToPlayAV and PICTURE in get_types_replaced_by_type(self.timerToPlayAV.media_type):
                self.timerToPlaySlideshow = None

            self.timerToStopAV = _sumUp(
                self.timerToPlayAV, self.timerToStopAV)
            self.timerToStopSlideshow = _sumUp(
                self.timerToPlaySlideshow, self.timerToStopSlideshow)

            if self.timerToPlayAV or self.timerToStopAV:
                self.timerToPauseAV = None
                self.timerToUnpauseAV = None

            if self.fader and (self.timerToStopAV == self.fader or self.timerToStopSlideshow == self.fader):
                self.fader = None

        self.reset()

        _collectTimers(timers, now)

        if self.hasEventToPerform:
            _handleNestedStoppingTimer(self.timerToStopAV)
            _handleNestedStoppingTimer(self.timerToStopSlideshow)
            _handleStartingTimers()
            _handleSystemAction()
            _sumupEffectivePlayerAction()

    def _setTimerToStopAny(self, timer: Timer) -> None:

        if timer.media_type == PICTURE:
            self.timerToStopSlideshow = timer

        else:
            self.timerToStopAV = timer

    def getFaderInterval(self) -> float:

        if not self.fader:
            return None

        delta_end_start = abs_time_diff(
            self.fader.current_period.end, self.fader.current_period.start)

        vol_max = self.fader.return_vol if self.fader.fade == FADE_OUT_FROM_CURRENT else self.fader.vol_max
        vol_diff = vol_max - self.fader.vol_min

        return delta_end_start / vol_diff if vol_diff != 0 else None

    def _setTimerToPlayAny(self, timer: Timer) -> None:

        if timer.is_script_timer():
            self.timersToRunScript.append(timer)

        elif timer.media_type == PICTURE:
            self.timerToPlaySlideshow = timer if self.timerToPlaySlideshow is None or self.timerToPlaySlideshow.priority < timer.priority else self.timerToPlaySlideshow

        else:
            self.timerToPlayAV = timer if self.timerToPlayAV is None or self.timerToPlayAV.priority < timer.priority else self.timerToPlayAV

    def fade(self, dtd: DateTimeDelta) -> None:

        if not self.fader:
            return

        delta_now_start = abs_time_diff(
            dtd.td, self.fader.current_period.start)
        delta_end_start = abs_time_diff(
            self.fader.current_period.end, self.fader.current_period.start)
        delta_percent = delta_now_start / delta_end_start

        vol_max = self.fader.return_vol if self.fader.fade == FADE_OUT_FROM_CURRENT else self.fader.vol_max
        vol_diff = vol_max - self.fader.vol_min

        if self.fader.fade == FADE_IN_FROM_MIN:
            _volume = int(round(self.fader.vol_min +
                          vol_diff * delta_percent, 0))
        else:
            _volume = int(round(vol_max - vol_diff * delta_percent, 0))

        self._player.setVolume(_volume)

    def perform(self, now: DateTimeDelta) -> None:

        def _performPlayerAction(_now: DateTimeDelta) -> None:

            if self.timerToPlayAV:
                showNotification(self.timerToPlayAV, msg_id=32280)
                self._player.playTimer(self.timerToPlayAV, _now)

            elif self.timerToStopAV:
                showNotification(self.timerToStopAV, msg_id=32281)
                self._player.resumeFormerOrStop(self.timerToStopAV)

            elif self.timerToPauseAV and not self._player.isPaused():
                showNotification(self.timerToPauseAV, msg_id=32282)
                self._player.pause()

            elif self.timerToUnpauseAV and self._player.isPaused():
                showNotification(self.timerToUnpauseAV, msg_id=32283)
                self._player.pause()

            elif self.fader:
                showNotification(self.fader, msg_id=32284)

            for type in set(self._forceResumeResetTypes):
                self._player.resetResumeStatus(type)

            if not self.timerToPlayAV or self.timerToPlayAV.media_type != VIDEO:
                if self.timerToPlaySlideshow:
                    showNotification(self.timerToPlaySlideshow, msg_id=32286)
                    self._player.playTimer(self.timerToPlaySlideshow, _now)

                elif self.timerToStopSlideshow:
                    showNotification(self.timerToStopSlideshow, msg_id=32287)
                    self._player.resumeFormerOrStop(self.timerToStopSlideshow)

        def _setVolume(dtd: DateTimeDelta) -> None:

            if self.timerWithSystemAction:
                self._player.setVolume(self._player.getDefaultVolume())
                return

            else:
                self.fade(dtd)

            ending_faders = [
                t for t in self._endingTimers if t.is_fading_timer()]
            if ending_faders:
                self._player.setVolume(
                    max(ending_faders, key=lambda t: t.return_vol).return_vol)

        def _consumeSingleRunTimers() -> None:

            def _reset(timers: 'list[Timer]') -> None:

                for timer in timers:
                    if TIMER_WEEKLY not in timer.days:
                        if timer.current_period.start.days in timer.days:
                            timer.days.remove(timer.current_period.start.days)

                        if not timer.days:
                            self.storage.delete_timer(timer.id)
                        else:
                            self.storage.save_timer(timer=timer)

            _reset(self._endingTimers)
            if self.timerWithSystemAction:
                _reset(self._runningTimers)

        def _runScripts() -> None:

            for timer in self.timersToRunScript:
                showNotification(timer, msg_id=32288)
                run_addon(timer.path)

        def _performSystemAction() -> None:

            if not self.timerWithSystemAction:
                pass

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_SHUTDOWN_KODI:
                showNotification(self.timerWithSystemAction, msg_id=32082)
                xbmc.shutdown()

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_QUIT_KODI:
                showNotification(self.timerWithSystemAction, msg_id=32083)
                xbmc.executebuiltin("Quit()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_RESTART_KODI:
                showNotification(self.timerWithSystemAction, msg_id=32094)
                xbmc.executebuiltin("RestartApp()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_STANDBY:
                showNotification(self.timerWithSystemAction, msg_id=32084)
                xbmc.executebuiltin("Suspend()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_HIBERNATE:
                showNotification(self.timerWithSystemAction, msg_id=32085)
                xbmc.executebuiltin("Hibernate()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_POWEROFF:
                showNotification(self.timerWithSystemAction, msg_id=32086)
                xbmc.executebuiltin("Powerdown()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_REBOOT_SYSTEM:
                showNotification(self.timerWithSystemAction, msg_id=32099)
                xbmc.executebuiltin("Reboot()")

            elif self.timerWithSystemAction.system_action == SYSTEM_ACTION_CEC_STANDBY:
                showNotification(self.timerWithSystemAction, msg_id=32093)
                xbmc.executebuiltin("CECStandby()")

        def _adjustState() -> None:

            for t in self._beginningTimers:
                t.state = STATE_RUNNING

            for t in self._endingTimers:
                t.state = STATE_WAITING

        if self.hasEventToPerform:
            _performPlayerAction(now)

        _setVolume(now)

        if self.hasEventToPerform:
            _runScripts()
            _consumeSingleRunTimers()
            _performSystemAction()
            _adjustState()

        self.hasEventToPerform = False

    def reset(self) -> None:

        self._beginningTimers = list()
        self._runningTimers = list()
        self._endingTimers = list()
        self._forceResumeResetTypes = list()

        self.hasEventToPerform = False
        self.upcoming_event = None
        self.upcoming_timer = None

        self.fader = None
        self.timerToPlayAV = None
        self.timerToPauseAV = None
        self.timerToUnpauseAV = None
        self.timerToStopAV = None
        self.timerToPlaySlideshow = None
        self.timerToStopSlideshow = None
        self.timersToRunScript = list()
        self.timerWithSystemAction = None

    def __str__(self) -> str:
        return "SchedulerAction[hasevent=%s, playAV=%s, stopAV=%s, pauseAV=%s, unpauseAV=%s, playSlideshow=%s, stopSlideshow=%s, script=%s, systemaction=%s, fader=%s, next event%s=%s]" % (self.hasEventToPerform,
                                                                                                                                                                                            self.timerToPlayAV,
                                                                                                                                                                                            self.timerToStopAV,
                                                                                                                                                                                            self.timerToPauseAV,
                                                                                                                                                                                            self.timerToUnpauseAV,
                                                                                                                                                                                            self.timerToPlaySlideshow,
                                                                                                                                                                                            self.timerToStopSlideshow,
                                                                                                                                                                                            [str(
                                                                                                                                                                                                s) for s in self.timersToRunScript],
                                                                                                                                                                                            self.timerWithSystemAction,
                                                                                                                                                                                            self.fader,
                                                                                                                                                                                            self.upcoming_event.strftime(
                                                                                                                                                                                                " at %Y-%m-%d %H:%M:%S") if self.upcoming_event else "",
                                                                                                                                                                                            self.upcoming_timer)
