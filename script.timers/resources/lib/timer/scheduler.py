import os
import time
from datetime import datetime, timedelta

import xbmc
import xbmcgui
import xbmcvfs
from resources.lib.timer import util
from resources.lib.timer.player import Player
from resources.lib.timer.timer import (ACTION_POWERDOWN_AT_END,
                                       ACTION_START_AT_END, ACTION_STOP,
                                       END_TYPE_NO, FADE_IN_FROM_MIN,
                                       FADE_OUT_FROM_CURRENT, TIMER_ONCE,
                                       Timer)

CHECK_INTERVAL = 10

TIMERS = 17


class Scheduler(xbmc.Monitor):

    _addon = None
    _addon_dir = None

    _timers = None

    _player = None

    _default_vol = None
    _resume = None
    _powermanagement_displaysoff = 0
    _disabled_powermanagement_displaysoff = False

    def __init__(self, addon):

        super().__init__()
        self._addon = addon
        self._addon_dir = xbmcvfs.translatePath(
            self._addon.getAddonInfo('path'))

        self._player = Player()

        self._timers = [Timer(i) for i in range(TIMERS)]

        self._update()

        util.set_volume(self._default_vol)

    def onSettingsChanged(self):

        if util.isSettingsChangedEvents(self._addon):
            self._update()

    def _update(self):

        for i, timer in enumerate(self._timers):
            self._timers[i] = timer.update_or_replace_from_settings()

        self._default_vol = int("0%s" % self._addon.getSetting("vol_default"))
        self._resume = ("true" == self._addon.getSetting("resume"))
        self._powermanagement_displaysoff = int(
            "0%s" % self._addon.getSetting("powermanagement_displaysoff"))
        self.reset_powermanagement_displaysoff()

    def start(self):

        def _check_timers(t_now):

            td_now = timedelta(hours=t_now.tm_hour,
                               minutes=t_now.tm_min,
                               seconds=t_now.tm_sec,
                               days=t_now.tm_wday)

            beginners, enders, parallels = list(), list(), list()
            stopper = None
            fader = None

            for timer in self._timers:
                period = timer.get_matching_period(td_now)

                if period is not None and not timer.b_active:
                    beginners.append((timer, period[0]))

                elif period is None and timer.b_active:
                    enders.append((timer, td_now - timer.td_duration))

                elif period is not None and timer.is_starting_timer() and timer.is_stopping_timer():
                    parallels.append((timer, period[0]))
                    if stopper == None or period[0] < stopper[1]:
                        stopper = (timer, period[0])

                if period is not None and timer.is_fading_timer():
                    if fader == None or period[0] < fader[1]:
                        fader = (timer, period[0], period[1])

            has_stopped_player = False
            for e in enders:
                has_stopped_player |= _end_timer(timer=e[0], reset_vol=(fader is None),
                                                 stop_player=(not stopper or stopper[1] < e[1]))

            if has_stopped_player:
                beginners.extend(parallels)

            starter = None
            beginners.sort(key=lambda b: b[1])
            for b in beginners:
                starter = b[0] if b[0].is_starting_timer(
                ) else starter

            for b in beginners:
                _begin_timer(
                    timer=b[0],
                    td_now=td_now,
                    start_player=(b[0] == starter),
                    force_return_vol=fader[0].i_return_vol if fader is not None and fader[0] != b[0] else None)

            if fader:
                _fade_timer(timer=fader[0], td_now=td_now,
                            td_start=fader[1], td_end=fader[2])

        def _begin_timer(timer, td_now, force_return_vol=None, start_player=True):

            if timer.is_fading_timer():
                if force_return_vol is not None:
                    timer.i_return_vol = force_return_vol
                else:
                    timer.i_return_vol = util.get_volume(
                        or_default=self._default_vol)

            if start_player and timer.is_starting_timer():
                if self._resume:
                    td_start = util.parse_time(
                        timer.s_start, datetime.today().weekday())
                    delta_now_start = util.abs_time_diff(td_now, td_start)
                    self._player.playWithSeekTime(
                        timer.s_filename, seektime=delta_now_start)
                else:
                    self._player.play(timer.s_filename)

            elif timer.s_action in [ACTION_STOP, ACTION_START_AT_END]:
                self._player.stop()

            if timer.b_notify:
                icon_file = os.path.join(self._addon_dir,
                                         "resources",
                                         "assets", "icon_alarm.png" if timer.s_end_type == END_TYPE_NO else "icon_sleep.png")
                xbmcgui.Dialog().notification(self._addon.getLocalizedString(
                    32100), timer.s_label, icon=icon_file)

            timer.b_active = True

        def _end_timer(timer, reset_vol=True, stop_player=True):

            has_stopped_player = False
            if stop_player and timer.is_stopping_timer():
                self._player.stop()
                has_stopped_player = True

            elif timer.s_action == ACTION_START_AT_END and timer.s_filename != "":
                self._player.play(timer.s_filename)

            if timer.b_notify and timer.s_end_type != END_TYPE_NO:
                xbmcgui.Dialog().notification(self._addon.getLocalizedString(
                    32101), timer.s_label)

            if reset_vol and timer.is_fading_timer():
                xbmc.sleep(3000)
                util.set_volume(timer.i_return_vol)

            timer.b_active = False

            if timer.s_schedule in TIMER_ONCE:
                Timer(timer.i_timer).save_to_settings()

            if timer.s_action == ACTION_POWERDOWN_AT_END:
                xbmc.shutdown()

            return has_stopped_player

        def _fade_timer(timer, td_now, td_start, td_end):

            if not timer.is_fading_timer():
                return

            delta_now_start = util.abs_time_diff(td_now, td_start)
            delta_end_start = util.abs_time_diff(td_end, td_start)
            delta_percent = delta_now_start / delta_end_start

            vol_min = timer.i_vol_min
            vol_max = timer.i_return_vol if timer.s_fade == FADE_OUT_FROM_CURRENT else timer.i_vol_max
            vol_diff = vol_max - vol_min

            if timer.s_fade == FADE_IN_FROM_MIN:
                new_vol = int(vol_min + vol_diff * delta_percent)
            else:
                new_vol = int(vol_max - vol_diff * delta_percent)

            util.set_volume(new_vol)

        while not self.abortRequested():

            t_now = time.localtime()
            _check_timers(t_now)

            if self._powermanagement_displaysoff:
                self._prevent_powermanagement_displaysoff()

            if self.waitForAbort(
                    CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL):
                break

    def _prevent_powermanagement_displaysoff(self):

        if not util.is_fullscreen():
            self._disabled_powermanagement_displaysoff = True
            util.set_powermanagement_displaysoff(0)

        elif self._disabled_powermanagement_displaysoff:
            self.reset_powermanagement_displaysoff()

    def reset_powermanagement_displaysoff(self):

        if self._powermanagement_displaysoff:
            util.set_powermanagement_displaysoff(
                self._powermanagement_displaysoff)
            self._disabled_powermanagement_displaysoff = False
