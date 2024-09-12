#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


import sys
import threading
from datetime import datetime, timedelta, date

import xbmc

from . import ADDON, AMBI_RUNNING, BRIDGE_SETTINGS_CHANGED
from . import lightgroup, ambigroup, settings
from .hue import Hue
from .kodiutils import notification, cache_set, cache_get, log
from .language import get_string as _


def core():
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
        log(f"[SCRIPT.SERVICE.HUE] Started with {command}, Python: {sys.version}")
        command_func = self.commands.get(command)

        if command_func:
            command_func(*args)
        else:
            log(f"[SCRIPT.SERVICE.HUE] Unknown command: {command}")
            raise RuntimeError(f"Unknown Command: {command}")

    def discover(self):
        bridge = Hue(self.settings_monitor, discover=True)
        if bridge.connected:
            log("[SCRIPT.SERVICE.HUE] Found bridge. Opening settings.")
            ADDON.openSettings()

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
        self.service_enabled = True
        cache_set("service_enabled", True)

    def run(self):
        log(f"[SCRIPT.SERVICE.HUE] Starting Hue Service, Python: {sys.version}")
        self.light_groups = self.initialize_light_groups()
        self.timers = Timers(self.settings_monitor, self.bridge, self)

        if self.bridge.connected:
            self.timers.start()

        # Track the previous state of the service
        prev_service_enabled = self.service_enabled

        while not self.settings_monitor.abortRequested(): # main loop, once per second
            # Update the current state of the service
            self.service_enabled = cache_get("service_enabled")

            # Check if the bridge settings have changed, if so, reconnect the bridge
            if BRIDGE_SETTINGS_CHANGED.is_set():
                self.bridge.connect()
                BRIDGE_SETTINGS_CHANGED.clear()

            #Process pending action commands
            self._process_action()

            if self.service_enabled:
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
            prev_service_enabled = self.service_enabled

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
        log(f"[SCRIPT.SERVICE.HUE] Activating scenes")

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
    def __init__(self, settings_monitor, bridge, hue_service):
        self.settings_monitor = settings_monitor
        self.bridge = bridge
        self.hue_service = hue_service
        self.morning_time = self.settings_monitor.morning_time
        self.stop_timers = threading.Event()  # Flag to stop the thread

        super().__init__()

    def run(self):
        self._set_daytime()
        self._task_loop()

    def stop(self):
        self.stop_timers.set()

    def _run_morning(self):
        cache_set("daytime", True)
        self.bridge.update_sunset()
        log(f"[SCRIPT.SERVICE.HUE] run_morning(): new sunset: {self.bridge.sunset}")

    def _run_sunset(self):
        log(f"[SCRIPT.SERVICE.HUE] in run_sunset(): Sunset. ")
        cache_set("daytime", False)
        if self.settings_monitor.force_on_sunset:
            self.hue_service.activate()


    def _set_daytime(self):
        now = datetime.now()
        log(f"[SCRIPT.SERVICE.HUE] _set_daytime(): Morning Time: {self.morning_time}, Now: {now.time()}, bridge.sunset: {self.bridge.sunset}, Sunset offset: {self.settings_monitor.sunset_offset}")

        # Convert self.bridge.sunset to a datetime object by combining it with today's date
        sunset_datetime = datetime.combine(datetime.today(), self.bridge.sunset)

        # Apply the sunset offset
        sunset_with_offset = sunset_datetime + timedelta(minutes=self.settings_monitor.sunset_offset)

        # Compare times
        if self.morning_time <= now.time() < sunset_with_offset.time():
            daytime=True
        else:
            daytime = False
        cache_set("daytime", daytime)
        log(f"[SCRIPT.SERVICE.HUE] in _set_daytime(): Sunset with offset: {sunset_with_offset}, Daytime: {daytime} ")

    def _task_loop(self):

        while not self.settings_monitor.abortRequested() and not self.stop_timers.is_set(): #todo: Update timers if sunset offset changes.

            now = datetime.now() #+ timedelta(seconds=5)
            today = date.today()

            morning_datetime = datetime.combine(today, self.settings_monitor.morning_time)
            # Convert self.bridge.sunset to a datetime object and apply the sunset offset
            sunset_datetime = datetime.combine(today, self.bridge.sunset) + timedelta(minutes=self.settings_monitor.sunset_offset)

            if sunset_datetime < now:
                sunset_datetime += timedelta(days=1)
            if morning_datetime < now:
                morning_datetime += timedelta(days=1)

            time_to_sunset = (sunset_datetime - now).total_seconds()
            time_to_morning = (morning_datetime - now).total_seconds()

            # Log the calculated times
            log(f"[SCRIPT.SERVICE.HUE] Time to sunset: {time_to_sunset}, Time to morning: {time_to_morning}")

            # Determine which event is next based on the time calculations
            if time_to_morning < time_to_sunset:
                # Morning is next
                log(f"[SCRIPT.SERVICE.HUE] Timers: Morning is next. wait_time: {time_to_morning}")
                if self.settings_monitor.waitForAbort(time_to_morning):
                    break
                self._run_morning()
            else:
                # Sunset is next
                log(f"[SCRIPT.SERVICE.HUE] Timers: Sunset is next. wait_time: {time_to_sunset}")
                if self.settings_monitor.waitForAbort(time_to_sunset):
                    break
                self._run_sunset()
        log("[SCRIPT.SERVICE.HUE] Timers stopped")

    @staticmethod
    def _time_until(current, target):
        # Calculates remaining time from current to target
        now = datetime(1, 1, 1, current.hour, current.minute, current.second)
        then = datetime(1, 1, 1, target.hour, target.minute, target.second)
        return (then - now).seconds
