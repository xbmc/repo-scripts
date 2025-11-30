import datetime
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.wellbeing.player import Player

CHECK_INTERVAL = 10

OFF = 0
AUDIO_VIDEO = 1
VIDEO = 2

NOTIFY_OFF = 0
NOTIFY_1M = 1
NOTIFY_5M = 2
NOTIFY_15M = 3
NOTIFY_HOURLY = 4

TIME_1M = 60
TIME_5M = 300
TIME_15M = 900
TIME_20M = 1200
TIME_30M = 1800
TIME_1H = 3600
TIME_2H = 7200

SECONDS_PER_DAY = 86400

AUTO_STOP_INTERVAL = [None, TIME_15M, TIME_20M, TIME_30M, TIME_1H]


class Wellbeing(xbmc.Monitor):

    def __init__(self) -> None:

        self._changed = .0

        self._addon = xbmcaddon.Addon()
        self._player = Player()

        self._wday: int = -1
        self._ignoreLimit: bool = False
        self._ignoreRestPeriod: int = -1

        self._limitation: int = OFF
        self._limits: list = list()

        self._restperiods: list = list()
        self._restfrom: list = list()
        self._restto: list = list()

        self._autostopInterval: int = 0

        self._notification: int = NOTIFY_HOURLY

        self._password: str = ""

        self._icon: str = os.path.join(xbmcvfs.translatePath(self._addon.getAddonInfo('path')),
                                       "resources",
                                       "assets", "icon.png")

        self._sum: int = self._addon.getSettingInt("sum") if self._addon.getSetting(
            "date") == datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d") else 0

        self.onSettingsChanged()

    def onSettingsChanged(self) -> None:

        ts = time.time()
        if self._changed + 1 > ts:
            return
        self._changed = ts

        limits = list()
        restperiods = list()
        restfrom = list()
        restto = list()
        for d in range(7):
            limits.append(self._timeformat_to_seconds(
                self._addon.getSetting("limit_%i" % d)))
            restperiods.append(self._addon.getSettingInt("restperiod_%i" % d))
            restfrom.append(self._timeformat_to_seconds(
                self._addon.getSetting("restfrom_%i" % d)))
            restto.append(self._timeformat_to_seconds(
                self._addon.getSetting("restto_%i" % d)))

        self._limits = limits
        self._restperiods = restperiods
        self._restfrom = restfrom
        self._restto = restto

        self._notification = self._addon.getSettingInt("notification")

        self._wday = time.localtime().tm_wday
        self._ignoreLimit = False
        self._ignoreRestPeriod = -1

        sum = self._addon.getSettingInt("sum")
        if sum < 0:
            self._sum = 0
            self._addon.setSettingInt("sum", 0)

        limit = self._addon.getSetting("limit")
        if limit:
            self._limits[self._wday] = self._timeformat_to_seconds(limit)
            self._addon.setSetting("limit", "")

        self._password = self._addon.getSettingString("password")

        self._autostopInterval = AUTO_STOP_INTERVAL[self._addon.getSettingInt(
            "autostop")]

        self._limitation = self._addon.getSettingInt("limitation")
        if self._limitation != OFF:
            left = self._get_time_left(time.localtime())
            s1 = self._addon.getLocalizedString(32040) % (self._format_seconds(self._sum + 59),
                                                          self._addon.getLocalizedString(32013 if self._limitation == VIDEO else 32012))
            s2 = self._addon.getLocalizedString(
                32041) % self._format_seconds(left)
            xbmcgui.Dialog().notification(self._addon.getLocalizedString(
                32000), "%s. %s" % (s1, s2), icon=self._icon)

    def _notify(self, msgId):

        xbmcgui.Dialog().notification(self._addon.getLocalizedString(
            32000), self._addon.getLocalizedString(msgId), icon=self._icon)

    def _get_time_left(self, t_now: time.struct_time) -> int:

        limit = self._limits[t_now.tm_wday]
        left = limit - self._sum
        return max(0, left)

    def _timeformat_to_seconds(self, stime: str) -> int:

        hh_mm = stime.split(":")
        return int(hh_mm[0]) * TIME_1H + int(hh_mm[1]) * TIME_1M

    def _format_seconds(self, secs: int) -> str:

        return "%02i:%02i" % (secs // TIME_1H, (secs % TIME_1H) // TIME_1M)

    def _stopAndAskForReactivation(self) -> bool:

        self._player.pause()

        password = xbmcgui.Dialog().input(heading=self._addon.getLocalizedString(
            32035), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT, autoclose=60000)
        if password != self._password:
            self._notify(32036)
            self._player.stop()
            return False

        else:
            self._notify(32037)
            self._player.pause()
            return True

    def _handleLimit(self, t_now: time.struct_time, _interval: int) -> bool:

        if self._limitation == VIDEO and not self._player.isPlayingVideo():
            return False

        reached = False
        self._sum += _interval

        left = self._get_time_left(t_now)
        if not self._ignoreLimit and left <= 0:
            reached = True
            self._notify(32034)
            if self._stopAndAskForReactivation():
                self._ignoreLimit = True

        elif self._notification >= NOTIFY_1M and left > TIME_1M - _interval and left <= TIME_1M:
            self._notify(32033)

        elif self._notification >= NOTIFY_5M and left > TIME_5M - _interval and left <= TIME_5M:
            self._notify(32032)

        elif self._notification >= NOTIFY_15M and left > TIME_15M - _interval and left <= TIME_15M:
            self._notify(32031)

        elif self._notification == NOTIFY_HOURLY and self._sum % TIME_1H < _interval:
            s1 = self._addon.getLocalizedString(32040) % (self._format_seconds(self._sum + 59 - _interval),
                                                          self._addon.getLocalizedString(32013 if self._limitation == VIDEO else 32012))

            s2 = self._addon.getLocalizedString(32041) % self._format_seconds(
                left) if left <= TIME_2H and not self._ignoreLimit else ""

            xbmcgui.Dialog().notification(self._addon.getLocalizedString(
                32000), "%s. %s" % (s1, s2), icon=self._icon)

        return reached

    def _handleRestPeriod(self, t_now: time.struct_time) -> bool:

        def _handleEnteringRestPeriod():

            self._notify(32080)
            return self._stopAndAskForReactivation()

        def _handleAutostop() -> None:

            if not xbmcgui.Dialog().yesno(heading="%s - %s" % (self._addon.getLocalizedString(32000), self._addon.getLocalizedString(32004)), message=self._addon.getLocalizedString(32008), autoclose=60000):
                self._player.stop()

        entered = False
        secs_in_day = t_now.tm_sec + t_now.tm_min * TIME_1M + t_now.tm_hour * TIME_1H
        if self._restperiods[t_now.tm_wday] \
            and secs_in_day >= self._restfrom[self._wday] \
            and (self._restperiods[t_now.tm_wday] == AUDIO_VIDEO
                 or self._restperiods[t_now.tm_wday] == VIDEO and self._player.isPlayingVideo()):

            entered = True
            if self._ignoreRestPeriod != t_now.tm_wday * 2 + 1:
                if _handleEnteringRestPeriod():
                    self._ignoreRestPeriod = t_now.tm_wday * 2 + 1

            elif self._autostopInterval and (secs_in_day - self._restfrom[self._wday]) % self._autostopInterval < CHECK_INTERVAL:
                _handleAutostop()

        elif self._restperiods[(t_now.tm_wday - 1) % 7] \
            and secs_in_day < self._restto[self._wday] \
            and (self._restperiods[(t_now.tm_wday - 1) % 7] == AUDIO_VIDEO
                 or self._restperiods[(t_now.tm_wday - 1) % 7] == VIDEO and self._player.isPlayingVideo()):

            entered = True
            if self._ignoreRestPeriod != t_now.tm_wday * 2:
                if _handleEnteringRestPeriod():
                    self._ignoreRestPeriod = t_now.tm_wday * 2

            elif self._autostopInterval and (secs_in_day + SECONDS_PER_DAY - self._restfrom[(t_now.tm_wday - 1) % 7]) % self._autostopInterval < CHECK_INTERVAL:
                _handleAutostop()

        return entered

    def start(self) -> None:

        while not self.abortRequested():

            t_now = time.localtime()
            if t_now.tm_wday != self._wday:
                self._wday = time.localtime().tm_wday
                self._sum = 0
                self._ignoreLimit = False
                self._ignoreRestPeriod = -1

            _interval = CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL

            self._player.isPlaying() and not self._player.isPaused() \
                and not self._handleLimit(t_now, _interval) \
                and not self._handleRestPeriod(t_now)

            if self.waitForAbort(_interval):
                break

        self.saveUsageToSettings()

    def saveUsageToSettings(self) -> None:

        self._addon.setSetting("date", datetime.datetime.strftime(
            datetime.datetime.now(), "%Y-%m-%d"))
        self._addon.setSettingInt("sum", self._sum)
