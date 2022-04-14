import xbmc
import xbmcaddon
from resources.lib.player.player import Player
from resources.lib.timer.scheduleraction import SchedulerAction
from resources.lib.timer.timer import Timer
from resources.lib.utils import datetime_utils, settings_utils, system_utils

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
        self._player.set_default_volume(_default_volume)
        self._player.set_volume(_default_volume)
        self._timers = [Timer(i) for i in range(TIMERS)]

        self._update()

    def onSettingsChanged(self) -> None:

        if settings_utils.isSettingsChangedEvents():
            self._update()

    def _update(self) -> None:

        for i, timer in enumerate(self._timers):
            self._timers[i], changed = timer.update_or_replace_from_settings()
            if changed:
                self._player.reset_resume_of_timer(self._timers[i])

        addon = xbmcaddon.Addon()
        self._player.set_seek_delayed_timer(
            addon.getSettingBool("resume"))

        self._player.set_default_volume(addon.getSettingInt("vol_default"))

        self._powermanagement_displaysoff = addon.getSettingInt(
            "powermanagement_displaysoff")
        self._windows_unlock = addon.getSettingBool("windows_unlock")
        self.reset_powermanagement_displaysoff()

    def _prevent_powermanagement_displaysoff(self) -> None:

        if not system_utils.is_fullscreen():
            self._disabled_powermanagement_displaysoff = True
            system_utils.set_powermanagement_displaysoff(0)

        elif self._disabled_powermanagement_displaysoff:
            self.reset_powermanagement_displaysoff()

    def reset_powermanagement_displaysoff(self) -> None:

        if self._powermanagement_displaysoff:
            system_utils.set_powermanagement_displaysoff(
                self._powermanagement_displaysoff)
            self._disabled_powermanagement_displaysoff = False

    def start(self) -> None:

        prev_windows_unlock = False
        action = SchedulerAction(self._player)
        while not self.abortRequested():

            t_now, td_now = datetime_utils.get_now()

            action.initFromTimers(timers=self._timers,
                                  now=td_now)
            action.perform()
            action.reset()

            if self._windows_unlock != prev_windows_unlock:
                prev_windows_unlock = system_utils.set_windows_unlock(
                    self._windows_unlock)

            if self._powermanagement_displaysoff:
                self._prevent_powermanagement_displaysoff()

            if self.waitForAbort(
                    CHECK_INTERVAL - t_now.tm_sec % CHECK_INTERVAL):
                break
