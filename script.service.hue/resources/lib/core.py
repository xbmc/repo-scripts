#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


import sys
import threading
from datetime import datetime, timedelta


from . import ADDON, AMBI_RUNNING, BRIDGE_SETTINGS_CHANGED, KODIVERSION, ADDONVERSION, TIMERS_DIRTY
from . import lightgroup, ambigroup, settings
from .hue import Hue
from .kodiutils import notification, cache_set, cache_get, log
from .language import get_string as _


def core_dispatcher():
    settings_monitor = settings.SettingsMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        command_args = sys.argv[2:]

        command_handler = CommandHandler(settings_monitor)
        command_handler.handle_command(command, *command_args)
    else:
        service = HueService(settings_monitor)
        service.run()


class CommandHandler:
    def __init__(self, settings_monitor):
        self.settings_monitor = settings_monitor
        self.commands = {
            "discover": self.discover,
            "sceneSelect": self.scene_select,
            "ambiLightSelect": self.ambi_light_select
        }

    def handle_command(self, command, *args):
        log(f"[SCRIPT.SERVICE.HUE] Started with {command}, Kodi: {KODIVERSION}, Addon: {ADDONVERSION}, Python: {sys.version}")
        command_func = self.commands.get(command)

        if command_func:
            command_func(*args)
        else:
            log(f"[SCRIPT.SERVICE.HUE] Unknown command: {command}")
            raise RuntimeError(f"Unknown Command: {command}")

    def discover(self):
        bridge = Hue(self.settings_monitor, discover=True)
        # Open the settings dialog either way so the user can inspect or fix the
        # bridge configuration; the log line distinguishes the two outcomes.
        if bridge.connected:
            log("[SCRIPT.SERVICE.HUE] Found bridge. Opening settings.")
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. Opening settings.")
        ADDON.openSettings()

    def scene_select(self, light_group, action):
        log(f"[SCRIPT.SERVICE.HUE] sceneSelect: light_group: {light_group}, action: {action}")
        bridge = Hue(self.settings_monitor)
        if bridge.connected:
            bridge.configure_scene(light_group, action)
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    def ambi_light_select(self, light_group):
        bridge = Hue(self.settings_monitor)
        if bridge.connected:
            bridge.configure_ambilights(light_group)
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))


class HueService:
    def __init__(self, settings_monitor):
        self.settings_monitor = settings_monitor
        self.bridge = Hue(settings_monitor)
        self.light_groups = []
        self.timers = None
        # The cache is the source of truth for service_enabled — menu.py (plugin
        # process) reads and writes it via cache_get/cache_set. Initialize True
        # so the first cache_get in run() agrees with the default.
        cache_set("service_enabled", True)

    def run(self):
        log(f"[SCRIPT.SERVICE.HUE] Starting Hue Service, Kodi: {KODIVERSION}, Addon: {ADDONVERSION}, Python: {sys.version}")
        self.light_groups = self.initialize_light_groups()
        self.timers = Timers(self.settings_monitor, self.bridge, self)

        if self.bridge.connected:
            self.timers.start()

        # Track the previous state of the service
        prev_service_enabled = True

        while not self.settings_monitor.abortRequested(): # main loop, once per second
            # Update the current state of the service
            service_enabled = cache_get("service_enabled")

            # Check if the bridge settings have changed, if so, reconnect the bridge
            if BRIDGE_SETTINGS_CHANGED.is_set():
                self.bridge.connect()
                BRIDGE_SETTINGS_CHANGED.clear()

            #Process pending action commands
            self._process_action()

            if service_enabled:
                # If the service was previously disabled and is now enabled, activate light groups
                if not prev_service_enabled and self.bridge.connected:
                    self.activate()
            else:
                AMBI_RUNNING.clear()

            # If the bridge gets disconnected, stop the timers
            if not self.bridge.connected and self.timers.is_alive():
                self.timers.stop()

            # If the bridge gets reconnected, restart the timers
            if self.bridge.connected and not self.timers.is_alive():
                self.timers = Timers(self.settings_monitor, self.bridge, self)
                self.timers.start()

            # Update the previous state for the next iteration
            prev_service_enabled = service_enabled

            if self.settings_monitor.waitForAbort(1):
                break

        log("[SCRIPT.SERVICE.HUE] Abort requested...")

    def initialize_light_groups(self):
        # Initialize light groups
        return [
            lightgroup.LightGroup(0, lightgroup.VIDEO, self.settings_monitor, self.bridge),
            lightgroup.LightGroup(1, lightgroup.AUDIO, self.settings_monitor, self.bridge),
            ambigroup.AmbiGroup(3, self.settings_monitor, self.bridge)
        ]

    def activate(self):
        # Activates play action as appropriate for all groups. Used at sunset and when service is re-enabled via Actions.
        log("[SCRIPT.SERVICE.HUE] Activating scenes")

        for g in self.light_groups:
            if ADDON.getSettingBool(f"group{g.light_group_id}_enabled"):
                g.activate()

    def _process_action(self):
        # Retrieve an action command stored in the CACHE.
        action = cache_get("action")

        # Check if the action is not None or not empty
        if action:
            action_action = action[0]
            action_light_group_id = int(action[1]) - 1
            log(f"[SCRIPT.SERVICE.HUE] Action command: {action}, action_action: {action_action}, action_light_group_id: {action_light_group_id}")

            # Run the action
            self.light_groups[action_light_group_id].run_action(action_action)

            # Clear the action from the cache after processing
            cache_set("action", None)


class Timers(threading.Thread):
    """Background thread that fires once at morning_time and once at sunset+offset.

    The thread sleeps via xbmc.Monitor.waitForAbort, which is the only Kodi-sanctioned
    way to wait in service code: xbmc.sleep / threading.Event.wait would block Kodi's
    shutdown. waitForAbort can only be woken by Kodi abort, however, so we slice the
    wait into short chunks (_wait_chunked) to stay responsive to stop() and to
    settings changes signalled via TIMERS_DIRTY.
    """

    # Slice length for the chunked wait. Picks the worst-case latency for
    # observing stop() / TIMERS_DIRTY; 1s matches the main service loop cadence
    # and is negligibly more expensive than a single long waitForAbort.
    _WAIT_CHUNK_SECONDS = 1.0

    def __init__(self, settings_monitor, bridge, hue_service):
        self.settings_monitor = settings_monitor
        self.bridge = bridge
        self.hue_service = hue_service
        self.stop_timers = threading.Event()  # Flag to stop the thread

        # Daemon=True so an in-flight bridge.update_sunset() HTTP call inside
        # _run_morning() doesn't hold Kodi's shutdown open: the chunked wait
        # observes abort within ~1s, but a request that is already mid-flight
        # has to finish (or hit its retry timeout) before the thread can check
        # anything. Daemon threads are killed by the interpreter on exit, so
        # the worst case is a torn-down HTTP call — which is fine, since the
        # state being updated (sunset time) is recomputed on next service start.
        super().__init__(daemon=True)

    def run(self):
        # Establish the daytime cache before entering the loop so other components
        # querying it before the first event fires get a correct answer.
        self._set_daytime()
        self._task_loop()

    def stop(self):
        # Cooperative stop: observed by _wait_chunked within _WAIT_CHUNK_SECONDS.
        self.stop_timers.set()

    def _run_morning(self):
        cache_set("daytime", True)
        # Sunset shifts day to day, so refresh it from the bridge here.
        # update_sunset() performs HTTP I/O and can't be cancelled mid-request;
        # the thread is a daemon so a Kodi shutdown during this call won't hang
        # the host process.
        self.bridge.update_sunset()
        log(f"[SCRIPT.SERVICE.HUE] run_morning(): new sunset: {self.bridge.sunset}")

    def _run_sunset(self):
        log("[SCRIPT.SERVICE.HUE] run_sunset(): Sunset.")
        cache_set("daytime", False)
        if self.settings_monitor.force_on_sunset:
            self.hue_service.activate()

    def _compute_sun_events(self, now):
        """Return (next_morning_dt, next_sunset_dt) as full datetimes, both >= now.

        Anchoring against today's date and rolling forward by one day if the
        event has already passed lets _task_loop measure remaining time to the
        next occurrence with a simple subtraction. Reads timing values live from
        settings_monitor so that updates take effect on the next iteration
        without any snapshot to keep in sync.
        """
        today = now.date()
        morning_dt = datetime.combine(today, self.settings_monitor.morning_time)
        sunset_dt = (
            datetime.combine(today, self.bridge.sunset)
            + timedelta(minutes=self.settings_monitor.sunset_offset)
        )
        if morning_dt <= now:
            morning_dt += timedelta(days=1)
        if sunset_dt <= now:
            sunset_dt += timedelta(days=1)
        return morning_dt, sunset_dt

    def _set_daytime(self):
        """Cache whether we are currently inside the daylight window.

        Compares full datetimes rather than naked time() values: a large positive
        sunset_offset can push sunset past midnight, in which case dropping the
        date component would invert the inequality (e.g. now=22:00 is NOT
        < sunset_with_offset.time()=00:30, even though we're clearly still
        before that sunset).
        """
        now = datetime.now()
        today = now.date()

        morning_dt = datetime.combine(today, self.settings_monitor.morning_time)
        sunset_dt = (
            datetime.combine(today, self.bridge.sunset)
            + timedelta(minutes=self.settings_monitor.sunset_offset)
        )

        daytime = morning_dt <= now < sunset_dt
        cache_set("daytime", daytime)
        log(
            f"[SCRIPT.SERVICE.HUE] _set_daytime(): now={now}, "
            f"morning={morning_dt}, sunset(+offset)={sunset_dt}, daytime={daytime}"
        )

    def _wait_chunked(self, total_seconds):
        """Sleep up to total_seconds, returning early on abort, stop, or settings change.

        Returns one of:
            "abort"   - Kodi requested abort; caller should exit the thread.
            "stop"    - Timers.stop() was called.
            "dirty"   - TIMERS_DIRTY was set; caller should recompute and re-sleep.
            "timeout" - The full duration elapsed; the scheduled event is due.

        See class docstring for why this slices waitForAbort instead of issuing
        a single long call.
        """
        remaining = total_seconds
        while remaining > 0:
            chunk = min(self._WAIT_CHUNK_SECONDS, remaining)
            if self.settings_monitor.waitForAbort(chunk):
                return "abort"
            if self.stop_timers.is_set():
                return "stop"
            if TIMERS_DIRTY.is_set():
                # Consume the flag here so the next iteration's wait starts
                # clean; the caller is responsible for recomputing.
                TIMERS_DIRTY.clear()
                return "dirty"
            remaining -= chunk
        return "timeout"

    def _task_loop(self):
        while not self.settings_monitor.abortRequested() and not self.stop_timers.is_set():
            now = datetime.now()
            morning_dt, sunset_dt = self._compute_sun_events(now)

            time_to_morning = (morning_dt - now).total_seconds()
            time_to_sunset = (sunset_dt - now).total_seconds()
            morning_is_next = time_to_morning < time_to_sunset
            wait_seconds = time_to_morning if morning_is_next else time_to_sunset

            log(
                f"[SCRIPT.SERVICE.HUE] Timers: now={now}, "
                f"next morning={morning_dt} ({time_to_morning:.0f}s), "
                f"next sunset={sunset_dt} ({time_to_sunset:.0f}s); "
                f"waiting for {'morning' if morning_is_next else 'sunset'}"
            )

            result = self._wait_chunked(wait_seconds)

            if result in ("abort", "stop"):
                break
            if result == "dirty":
                # Timing settings changed mid-wait. Refresh the daytime cache
                # against the new values and re-enter the loop to recompute
                # which event is next and how long until it fires.
                self._set_daytime()
                continue
            # result == "timeout": the scheduled event is due now.
            if morning_is_next:
                self._run_morning()
            else:
                self._run_sunset()

        log("[SCRIPT.SERVICE.HUE] Timers stopped")
