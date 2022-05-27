import xbmc
import xbmcaddon
from resources.lib.player.player import Player
from resources.lib.timer.scheduleraction import SchedulerAction
from resources.lib.timer.timer import Timer
from resources.lib.utils.datetime_utils import get_now
from resources.lib.utils.settings_utils import isSettingsChangedEvents
from resources.lib.utils.system_utils import (is_fullscreen,
                                              set_powermanagement_displaysoff,
                                              set_windows_unlock)

CHECK_INTERVAL = 10

TIMERS = 17


class Scheduler(xbmc.Monitor):

    _timers = None
    _player = None

    _powermanagement_displaysoff = 0
    _disabled_powermanagement_displaysoff = False
    _windows_unlock = False

    def __init__(self) -> None:

        super().__init__()

        self._player = Player()
        _default_volume = xbmcaddon.Addon().getSettingInt("vol_default")
        self._player.setDefaultVolume(_default_volume)
        self._player.setVolume(_default_volume)
        self._timers = [Timer(i) for i in range(TIMERS)]

        self._update()

    def onSettingsChanged(self) -> None:

        if isSettingsChangedEvents():
            self._update()

    def _update(self) -> None:

        for i, timer in enumerate(self._getTimers()):
            self._timers[i], changed = timer.update_or_replace_from_settings()
            if changed:
                self._player.resetResumeOfTimer(self._timers[i])

        addon = xbmcaddon.Addon()
        self._player.setSeekDelayedTimer(
            addon.getSettingBool("resume"))

        self._player.setDefaultVolume(addon.getSettingInt("vol_default"))

        self._powermanagement_displaysoff = addon.getSettingInt(
            "powermanagement_displaysoff")
        self._windows_unlock = addon.getSettingBool("windows_unlock")
        self.resetPowermanagementDisplaysoff()

    def _getTimers(self) -> 'list[Timer]':

        return self._timers

    def _preventPowermanagementDisplaysoff(self) -> None:

        if not is_fullscreen():
            self._disabled_powermanagement_displaysoff = True
            set_powermanagement_displaysoff(0)

        elif self._disabled_powermanagement_displaysoff:
            self.resetPowermanagementDisplaysoff()

    def resetPowermanagementDisplaysoff(self) -> None:

        if self._powermanagement_displaysoff:
            set_powermanagement_displaysoff(
                self._powermanagement_displaysoff)
            self._disabled_powermanagement_displaysoff = False

    def start(self) -> None:

        prev_windows_unlock = False
        action = SchedulerAction(self._player)
        while not self.abortRequested():

            t_now, td_now = get_now()

            action.initFromTimers(timers=self._timers,
                                  now=td_now)
            action.perform()
            action.reset()

            if self._windows_unlock != prev_windows_unlock:
                prev_windows_unlock = set_windows_unlock(
                    self._windows_unlock)

            if self._powermanagement_displaysoff:
                self._preventPowermanagementDisplaysoff()

            if self.waitForAbort(
                    CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL):
                break
