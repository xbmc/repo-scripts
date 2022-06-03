import datetime
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

CHECK_INTERVAL = 10

OFF = 0
AUDIO_VIDEO = 1
VIDEO = 2


class Wellbeing(xbmc.Monitor):

    _player = None
    _addon = None
    _icon = None

    _sum = 0
    _wday = -1
    _ignoreLimit = False
    _ignoreRestPeriod = -1

    _limitation = OFF
    _limits = list()

    _restperiods = list()
    _restfrom = list()
    _restto = list()

    _password = ""

    def __init__(self) -> None:

        self._addon = xbmcaddon.Addon()
        self._player = xbmc.Player()

        self._icon = os.path.join(xbmcvfs.translatePath(self._addon.getAddonInfo('path')),
                                  "resources",
                                  "assets", "icon.png")

        if self._addon.getSetting("date") == datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d"):
            self._sum = self._addon.getSettingInt("sum")

        self.onSettingsChanged()

    def onSettingsChanged(self) -> None:

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

        self._wday = time.localtime().tm_wday
        self._ignoreLimit = False
        self._ignoreRestPeriod = -1

        self._password = self._addon.getSettingString("password")

        self._limitation = self._addon.getSettingInt("limitation")
        if self._limitation != OFF:
            left = self._get_time_left(time.localtime())
            xbmcgui.Dialog().notification(self._addon.getLocalizedString(
                32000), self._addon.getLocalizedString(32040) % (self._format_seconds(left),
                                                                 self._addon.getLocalizedString(32013 if self._limitation == VIDEO else 32012)),
                icon=self._icon)

    def _notify(self, msgId):

        xbmcgui.Dialog().notification(self._addon.getLocalizedString(
            32000), self._addon.getLocalizedString(msgId), icon=self._icon)

    def _get_time_left(self, t_now: time.struct_time) -> int:

        limit = self._limits[t_now.tm_wday]
        left = limit - self._sum
        return max(0, left)

    def _timeformat_to_seconds(self, stime: str) -> int:

        hh_mm = stime.split(":")
        return int(hh_mm[0]) * 3600 + int(hh_mm[1]) * 60

    def _format_seconds(self, secs: int) -> str:

        return "%02i:%02i" % (secs // 3600, (secs % 3600) // 60)

    def _stopAndAskForReactivation(self) -> bool:

        self._getPlayer().pause()

        password = xbmcgui.Dialog().input(heading=self._addon.getLocalizedString(
            32035), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT, autoclose=60000)
        if password != self._password:
            self._notify(32036)
            self._getPlayer().stop()
            return False

        else:
            self._notify(32037)
            self._getPlayer().pause()
            return True

    def _handleLimit(self, t_now: time.struct_time, _interval: int) -> None:

        if self._limitation == VIDEO and not self._getPlayer().isPlayingVideo():
            return

        self._sum += _interval

        if self._ignoreLimit:
            return

        left = self._get_time_left(t_now)
        if left > 900 - _interval and left <= 900:
            self._notify(32031)

        elif left > 300 - _interval and left <= 300:
            self._notify(32032)

        elif left > 60 - _interval and left <= 60:
            self._notify(32033)

        elif left <= 0:
            self._notify(32034)
            if self._stopAndAskForReactivation():
                self._ignoreLimit = True

    def _handleRestPeriod(self, t_now: time.struct_time) -> None:

        def _handle():

            self._notify(32080)
            return self._stopAndAskForReactivation()

        min_in_day = t_now.tm_min * 60 + t_now.tm_hour * 3600
        if (self._restperiods[t_now.tm_wday] and min_in_day >= self._restfrom[self._wday] and self._ignoreRestPeriod != t_now.tm_wday * 2 + 1):

            if (self._restperiods[t_now.tm_wday] == AUDIO_VIDEO
                    or self._restperiods[t_now.tm_wday] == VIDEO and self._getPlayer().isPlayingVideo()):

                if _handle():
                    self._ignoreRestPeriod = t_now.tm_wday * 2 + 1

        elif (self._restperiods[(t_now.tm_wday - 1) % 7] and min_in_day < self._restto[self._wday] and self._ignoreRestPeriod != t_now.tm_wday * 2):

            if (self._restperiods[(t_now.tm_wday - 1) % 7] == AUDIO_VIDEO
                    or self._restperiods[(t_now.tm_wday - 1) % 7] == VIDEO and self._getPlayer().isPlayingVideo()):

                if _handle():
                    self._ignoreRestPeriod = t_now.tm_wday * 2

    def start(self) -> None:

        while not self.abortRequested():

            t_now = time.localtime()
            if t_now.tm_wday != self._wday:
                self._wday = time.localtime().tm_wday
                self._sum = 0
                self._ignoreLimit = False
                self._ignoreRestPeriod = -1

            _interval = CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL

            if self._getPlayer().isPlaying():
                self._handleRestPeriod(t_now)
                self._handleLimit(t_now, _interval)

            if self.waitForAbort(_interval):
                break

        self.saveUsageToSettings()

    def _getPlayer(self) -> xbmc.Player:

        return self._player

    def saveUsageToSettings(self) -> None:

        self._addon.setSetting("date", datetime.datetime.strftime(
            datetime.datetime.now(), "%Y-%m-%d"))
        self._addon.setSettingInt("sum", self._sum)
