import os
import time
from datetime import datetime, timedelta

import xbmc
import xbmcgui
import xbmcvfs
from resources.lib.timer import util
from resources.lib.timer.player import Player

CHECK_INTERVAL = 12

TIMERS = 12
SLEEP_TIMER = 0
SNOOZE_TIMER = 1

TIMER_ONCE = [str(i) for i in range(7)]
TIMER_OFF = "25"

TIMER_DAYS_PRESETS = {
    "0": [0],                     # mon
    "1": [1],                     # tue
    "2": [2],                     # wed
    "3": [3],                     # thu
    "4": [4],                     # fri
    "5": [5],                     # sat
    "6": [6],                     # sun
    "7": [0],                     # mons
    "8": [1],                     # tues
    "9": [2],                     # weds
    "10": [3],                    # thus
    "11": [4],                    # fris
    "12": [5],                    # sats
    "13": [6],                    # suns
    "14": [0, 1, 2, 3],           # mon-thu
    "15": [0, 1, 2, 3, 4],        # mon-fri
    "16": [1, 2, 3, 4],           # tue-fri
    "17": [3, 4, 5],              # thu-sat
    "18": [4, 5],                 # fri-sat
    "19": [4, 5, 6],              # fri-sun
    "20": [5, 6],                 # sat-sun
    "21": [5, 6, 0],              # sat-mon
    "22": [6, 0, 1, 2],           # sun-wed
    "23": [6, 0, 1, 2, 3],        # sun-thu
    "24": [0, 1, 2, 3, 4, 5, 6],  # everyday
    "25": []                      # off
}

END_TYPE_NO = "0"
END_TYPE_DURATION = "1"
END_TYPE_TIME = "2"

ACTION_NO = "0"
ACTION_PLAY = "1"
ACTION_START = "2"
ACTION_START_AT_END = "3"
ACTION_STOP = "4"
ACTION_STOP_AT_END = "5"
ACTION_POWERDOWN_AT_END = "6"

FADE_OFF = "0"
FADE_IN_FROM_MIN = "1"
FADE_OUT_FROM_MAX = "2"
FADE_OUT_FROM_CURRENT = "3"


class Scheduler(xbmc.Monitor):

    addon = None
    addon_dir = None

    player = None

    _timer_state = {
        "t_now": None,
        "td_now": None,
        "i_default_vol": 100,
        "timers": [
            {
                "i_timer": 0,
                "s_schedule": TIMER_OFF,
                "days": [],
                "s_label": "",
                "s_start": "00:00",
                "s_end_type": END_TYPE_NO,
                "s_end": "00:00",
                "s_duration": "00:00",
                "td_duration": None,
                "s_action": ACTION_NO,
                "s_filename": "",
                "s_fade": FADE_OFF,
                "i_vol_min": 0,
                "i_vol_max": 100,
                "i_return_vol": 100,
                "periods": [],
                "b_in_period": False,
                "b_active": False,
                "b_notify": True
            }] * TIMERS
    }

    def __init__(self, addon):

        super().__init__()
        self.addon = addon
        self.addon_dir = xbmcvfs.translatePath(addon.getAddonInfo('path'))

        self.player = Player()

        self._timer_state["i_default_vol"] = int(
            self.addon.getSetting("vol_default"))

        xbmc.executebuiltin("SetVolume(%i)" %
                            self._timer_state["i_default_vol"])

        self._update()

    def start(self):

        while not self.abortRequested():

            t_now = time.localtime()
            if self.waitForAbort(
                    CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL):
                break

            self.check_timers()

    def onSettingsChanged(self):

        if util.isSettingsChangedEvents(self.addon):
            self._update()
            xbmcgui.Dialog().notification(self.addon.getLocalizedString(
                32027), self.addon.getLocalizedString(32028))

    def _update(self):

        self._set_now()
        timers = self._timer_state["timers"]
        for i in range(len(timers)):

            s_label = self.addon.getSetting("timer_%i_label" % i)

            s_action = self.addon.getSetting("timer_%i_action" % i)

            s_fade = self.addon.getSetting("timer_%i_fade" % i)

            i_vol_min = int("0%s" % self.addon.getSetting(
                "timer_%i_vol_min" % i))

            i_vol_max = int("0%s" % self.addon.getSetting(
                "timer_%i_vol_max" % i))

            s_filename = self.addon.getSetting("timer_%i_filename" % i)

            s_schedule = self.addon.getSetting("timer_%i" % i)

            s_start = self.addon.getSetting("timer_%i_start" % i)

            s_end_type = self.addon.getSetting("timer_%i_end_type" % i)

            s_end = self.addon.getSetting("timer_%i_end" % i)

            s_duration = self.addon.getSetting("timer_%i_duration" % i)

            td_duration = util.parse_time(s_duration)

            b_notify = ("true" == self.addon.getSetting("timer_%i_notify" % i))

            periods = list()
            for i_day in TIMER_DAYS_PRESETS[s_schedule]:
                td_start = util.parse_time(s_start, i_day)
                td_end = self._build_end_time(td_start,
                                              s_end_type,
                                              td_duration,
                                              s_end)

                periods.append({
                    "td_start": td_start,
                    "td_end": td_end
                })

            timers[i] = {
                "i_timer": i,
                "s_schedule": s_schedule,
                "days": TIMER_DAYS_PRESETS[s_schedule],
                "s_label": s_label,
                "s_start": s_start,
                "s_end_type": s_end_type,
                "s_end": s_end,
                "s_duration": s_duration,
                "td_duration": td_duration,
                "s_action": s_action,
                "s_filename": s_filename,
                "s_fade": s_fade,
                "i_vol_min": i_vol_min,
                "i_vol_max": i_vol_max,
                "periods": periods,
                "b_in_period": False,
                "b_active": False,
                "b_notify": b_notify
            }

    def _set_now(self, t_now=None):

        if t_now == None:
            t_now = time.localtime()

        td_now = timedelta(hours=t_now.tm_hour,
                           minutes=t_now.tm_min,
                           seconds=t_now.tm_sec,
                           days=t_now.tm_wday)

        self._timer_state["t_now"] = t_now
        self._timer_state["td_now"] = td_now

        return t_now, td_now

    def _build_end_time(self, td_start, s_end_type, td_duration, s_end):

        if s_end_type == END_TYPE_DURATION:
            td_end = td_start + td_duration

        elif s_end_type == END_TYPE_TIME:
            td_end = util.parse_time(s_end, td_start.days)

            if td_end < td_start:
                td_end += timedelta(days=1)

        else:  # END_TYPE_NO
            td_end = td_start + timedelta(seconds=CHECK_INTERVAL)

        return td_end

    def _start_action(self, timer, td_now):

        try:
            _result = util.json_rpc("Application.GetProperties", {
                "properties": ["volume"]})
            timer["i_return_vol"] = _result["volume"]

        except:
            xbmc.log(
                "jsonrpc call failed in order to get current volume: Application.GetProperties", xbmc.LOGERROR)
            timer["i_return_vol"] = int(self.addon.getSetting("vol_default"))

        if timer["s_fade"] == FADE_OUT_FROM_CURRENT and timer["s_end_type"] != END_TYPE_NO:
            pass

        elif timer["s_fade"] == FADE_OUT_FROM_MAX and timer["s_end_type"] != END_TYPE_NO:
            xbmc.executebuiltin("SetVolume(%i)" % timer["i_vol_max"])

        elif timer["s_fade"] == FADE_IN_FROM_MIN and timer["s_end_type"] != END_TYPE_NO:
            xbmc.executebuiltin("SetVolume(%i)" % timer["i_vol_min"])

        if timer["s_action"] in [ACTION_PLAY, ACTION_START] and timer["s_filename"] != "":
            if self.addon.getSetting("resume") == "true":
                td_start = util.parse_time(
                    timer["s_start"], datetime.today().weekday())
                delta_now_start = util.abs_time_diff(td_now, td_start)
                self.player.playWithSeekTime(
                    timer["s_filename"], seektime=delta_now_start)
            else:
                self.player.play(timer["s_filename"])

        elif timer["s_action"] in [ACTION_STOP, ACTION_START_AT_END]:
            self.player.stop()

        if timer["b_notify"]:
            icon_file = os.path.join(self.addon_dir,
                                     "resources",
                                     "assets", "icon_alarm.png" if timer["s_end_type"] == END_TYPE_NO else "icon_sleep.png")
            xbmcgui.Dialog().notification(self.addon.getLocalizedString(
                32100), timer["s_label"], icon=icon_file)

        timer["b_active"] = True

    def _stop_action(self, timer):

        if timer["s_action"] in [ACTION_PLAY, ACTION_STOP_AT_END]:
            self.player.stop()

        elif timer["s_action"] == ACTION_START_AT_END and timer["s_filename"] != "":
            self.player.play(timer["s_filename"])

        if timer["b_notify"] and timer["s_end_type"] != END_TYPE_NO:
            xbmcgui.Dialog().notification(self.addon.getLocalizedString(
                32101), timer["s_label"])

        if timer["s_schedule"] in TIMER_ONCE:
            timer["s_schedule"] == TIMER_OFF
            self.addon.setSetting("timer_%i" % timer["i_timer"], TIMER_OFF)

        if timer["s_fade"] != FADE_OFF and timer["s_end_type"] != END_TYPE_NO:
            xbmc.sleep(3000)
            reset_vol = timer["i_return_vol"]
            xbmc.executebuiltin("SetVolume(%s)" % reset_vol)

        timer["b_active"] = False

        if timer["s_action"] in [ACTION_POWERDOWN_AT_END]:
            xbmc.shutdown()

    def _fade(self, timer, td_now, td_start, td_end):

        if timer["s_fade"] == FADE_OFF or timer["s_end_type"] == END_TYPE_NO:
            return

        delta_now_start = util.abs_time_diff(td_now, td_start)
        delta_end_start = util.abs_time_diff(td_end, td_start)
        delta_percent = delta_now_start / delta_end_start

        vol_min = timer["i_vol_min"]
        vol_max = timer["i_return_vol"] if timer["s_fade"] == FADE_OUT_FROM_CURRENT else timer["i_vol_max"]
        vol_diff = vol_max - vol_min

        if timer["s_fade"] == FADE_IN_FROM_MIN:
            new_vol = int(vol_min + vol_diff * delta_percent)
        else:
            new_vol = int(vol_max - vol_diff * delta_percent)

        try:
            _result = util.json_rpc("Application.GetProperties",
                                    {"properties": ["volume"]})
            current_vol = _result["volume"]
            if current_vol != new_vol:
                xbmc.executebuiltin("SetVolume(%i)" % new_vol)

        except:
            xbmc.log(
                "jsonrpc call failed in order to get current volume: Application.GetProperties", xbmc.LOGERROR)
            xbmc.executebuiltin("SetVolume(%i)" % new_vol)

    def _check_period(self, timer, td_now):

        for period in timer["periods"]:

            in_period = period["td_start"] <= td_now < period["td_end"]
            if in_period:
                timer["b_in_period"] = True
                return in_period, period["td_start"], period["td_end"]

        timer["b_in_period"] = False
        return False, None, None

    def check_timers(self, t_now=None):

        t_now, td_now = self._set_now(t_now)

        starters, stoppers = list(), list()

        timers = self._timer_state["timers"]
        for timer in timers:
            in_period, td_start, td_end = self._check_period(timer, td_now)

            if in_period and not timer["b_active"]:
                starters.append(timer)

            elif not in_period and timer["b_active"]:
                stoppers.append(timer)

            elif in_period:  # fade
                self._fade(timer, td_now, td_start, td_end)

        for t in starters:
            self._start_action(t, td_now)

        for t in stoppers:
            self._stop_action(t)
