import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.player.player import Player
from resources.lib.timer import storage
from resources.lib.timer.scheduleraction import SchedulerAction
from resources.lib.timer.timer import END_TYPE_DURATION, END_TYPE_TIME, Timer
from resources.lib.utils.datetime_utils import get_now, parse_datetime_str
from resources.lib.utils.settings_utils import (is_settings_changed_events,
                                                save_timer_from_settings)
from resources.lib.utils.system_utils import (is_fullscreen,
                                              set_powermanagement_displaysoff,
                                              set_windows_unlock)

CHECK_INTERVAL = 10


class Scheduler(xbmc.Monitor):

    _timers = None
    _player = None
    _pause_from = None
    _pause_until = None
    _offset = 0

    _powermanagement_displaysoff = 0
    _disabled_powermanagement_displaysoff = False
    _windows_unlock = False

    def __init__(self) -> None:

        super().__init__()

        self._player = Player()
        _default_volume = xbmcaddon.Addon().getSettingInt("vol_default")
        self._player.setDefaultVolume(_default_volume)
        self._player.setVolume(_default_volume)

        storage.release_lock()

        self._update()

    def onSettingsChanged(self) -> None:

        if is_settings_changed_events():
            save_timer_from_settings()
            self._update()

    def _update(self) -> None:

        def _has_changed(former_timer: Timer, timer_from_storage: Timer) -> 'tuple[bool,bool]':

            restart = False
            changed = (former_timer.days != timer_from_storage.days)
            changed |= (former_timer.start != timer_from_storage.start)
            changed |= (former_timer.end_type != timer_from_storage.end_type)
            if former_timer.end_type == END_TYPE_DURATION:
                changed |= (former_timer.duration !=
                            timer_from_storage.duration)
            elif former_timer.end_type == END_TYPE_TIME:
                changed |= (former_timer.end != timer_from_storage.end)

            changed |= (former_timer.system_action !=
                        timer_from_storage.system_action)

            changed |= (former_timer.media_action !=
                        timer_from_storage.media_action)
            if former_timer._is_playing_media_timer():
                restart |= (former_timer.path != timer_from_storage.path)
                changed |= (former_timer.path != timer_from_storage.path)
                changed |= (former_timer.media_type !=
                            timer_from_storage.media_type)
                changed |= (former_timer.repeat != timer_from_storage.repeat)
                changed |= (former_timer.shuffle != timer_from_storage.shuffle)
                changed |= (former_timer.resume != timer_from_storage.resume)

            changed |= (former_timer.fade != timer_from_storage.fade)
            if former_timer.is_fading_timer():
                changed |= (former_timer.vol_min != timer_from_storage.vol_min)
                changed |= (former_timer.vol_max != timer_from_storage.vol_max)

            return changed, restart

        def _update_from_storage(scheduled_timers: 'list[Timer]') -> 'list[Timer]':

            for timer in scheduled_timers:

                former_timer = [
                    t for t in self._getTimers() if t.id == timer.id]
                if not former_timer:
                    continue

                timer.active = former_timer[0].active
                timer.return_vol = former_timer[0].return_vol

                changed, restart = _has_changed(
                    former_timer=former_timer[0], timer_from_storage=timer)

                if timer.active and restart:
                    timer.active = False

                if changed:
                    self._player.resetResumeOfTimer(timer=former_timer[0])

        scheduled_timers = storage.get_scheduled_timers()

        if self._timers:
            _update_from_storage(scheduled_timers)

            ids = [t.id for t in scheduled_timers]
            removed_timers = list([t for t in self._timers if t.id not in ids])
            for removed_timer in removed_timers:
                self._player.resetResumeOfTimer(timer=removed_timer)

        self._timers = scheduled_timers

        addon = xbmcaddon.Addon()
        self._player.setSeekDelayedTimer(addon.getSettingBool("resume"))
        self._player.setDefaultVolume(addon.getSettingInt("vol_default"))

        self._offset = -addon.getSettingInt("offset")

        _now = get_now()[0]
        _pause_from = parse_datetime_str("%s %s" % (addon.getSetting(
            "pause_date_from"), addon.getSetting("pause_time_from")))
        _pause_until = parse_datetime_str("%s %s" % (addon.getSetting(
            "pause_date_until"), addon.getSetting("pause_time_until")))

        self._pause_from = _pause_from if _now < _pause_until else None
        self._pause_until = _pause_until if _now < _pause_until else None

        self._windows_unlock = addon.getSettingBool("windows_unlock")
        self._powermanagement_displaysoff = addon.getSettingInt(
            "powermanagement_displaysoff")
        self.reset_powermanagement_displaysoff()

    def _getTimers(self) -> 'list[Timer]':

        return self._timers

    def start(self) -> None:

        prev_windows_unlock = False

        action = SchedulerAction(self._player)
        while not self.abortRequested():

            dt_now, td_now = get_now(offset=self._offset)

            if self._pause_from and self._pause_until and dt_now >= self._pause_from and dt_now < self._pause_until:

                pass

            else:

                if self._pause_until and dt_now >= self._pause_until:
                    self._pause_from = None
                    self._pause_until = None
                    addon = xbmcaddon.Addon()
                    xbmcgui.Dialog().notification(addon.getLocalizedString(
                        32027), addon.getLocalizedString(32166))

                action.initFromTimers(timers=self._timers, now=td_now)
                action.perform()
                action.reset()

            if self._windows_unlock != prev_windows_unlock:
                prev_windows_unlock = set_windows_unlock(self._windows_unlock)

            if self._powermanagement_displaysoff:
                self._prevent_powermanagement_displaysoff()

            if self.waitForAbort(
                    CHECK_INTERVAL - td_now.seconds % CHECK_INTERVAL):
                break

    def _prevent_powermanagement_displaysoff(self) -> None:

        if is_fullscreen() and self._disabled_powermanagement_displaysoff:
            self.reset_powermanagement_displaysoff()

        elif not is_fullscreen() and not self._disabled_powermanagement_displaysoff:
            self._disabled_powermanagement_displaysoff = True
            set_powermanagement_displaysoff(0)

    def reset_powermanagement_displaysoff(self) -> None:

        if self._powermanagement_displaysoff:
            set_powermanagement_displaysoff(
                self._powermanagement_displaysoff)
            self._disabled_powermanagement_displaysoff = False
