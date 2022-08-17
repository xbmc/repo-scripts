#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import json
import sys
from datetime import timedelta

import requests
import xbmc

from resources.lib import ADDON, CACHE, SETTINGS_CHANGED, ADDONID, AMBI_RUNNING
from resources.lib import ambigroup, lightgroup, kodiutils, hueconnection
from resources.lib.hueconnection import HueConnection
from resources.lib.language import get_string as _
from resources.lib.kodiutils import validate_settings, notification


def core():
    kodiutils.validate_settings()
    monitor = HueMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        _commands(monitor, command)
    else:
        _service(monitor)


def _commands(monitor, command):
    xbmc.log(f"[script.service.hue] Started with {command}")

    if command == "discover":
        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=True)
        if hue_connection.connected:
            xbmc.log("[script.service.hue] Found bridge. Starting service.")
            ADDON.openSettings()
            _service(monitor)
        else:
            ADDON.openSettings()

    elif command == "createHueScene":
        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.create_hue_scene()
        else:
            xbmc.log("[script.service.hue] No bridge found. createHueScene cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.delete_hue_scene()
        else:
            xbmc.log("[script.service.hue] No bridge found. deleteHueScene cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=light_group,action  / sceneSelect=0,play
        light_group = sys.argv[2]
        action = sys.argv[3]
        # xbmc.log(f"[script.service.hue] sceneSelect: light_group: {light_group}, action: {action}")

        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.configure_scene(light_group, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=light_group_id
        light_group = sys.argv[2]
        # xbmc.log(f"[script.service.hue] ambiLightSelect light_group_id: {light_group}")

        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=False)  # don't rediscover, proceed silently  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.configure_ambilights(light_group)
        else:
            xbmc.log("[script.service.hue] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        xbmc.log(f"[script.service.hue] Unknown command: {command}")
        raise RuntimeError(f"Unknown Command: {command}")


def _service(monitor):
    hue_connection = HueConnection(monitor, silent=ADDON.getSettingBool("disableConnectionMessage"), discover=False)
    service_enabled = CACHE.get(f"{ADDONID}.service_enabled")

    if hue_connection.connected:
        light_groups = [lightgroup.LightGroup(0, hue_connection, lightgroup.VIDEO),
                        lightgroup.LightGroup(1, hue_connection, lightgroup.AUDIO),
                        ambigroup.AmbiGroup(3, hue_connection)]

        connection_retries = 0
        timer = 60
        daylight = hue_connection.get_daylight()
        new_daylight = daylight

        CACHE.set(f"{ADDONID}.daylight", daylight)
        CACHE.set(f"{ADDONID}.service_enabled", True)
        # xbmc.log("[script.service.hue] Core service starting. Connected: {}".format(CONNECTED))

        while hue_connection.connected and not monitor.abortRequested():

            # check if service was just re-enabled and if so activate groups
            prev_service_enabled = service_enabled
            service_enabled = CACHE.get(f"{ADDONID}.service_enabled")
            if service_enabled and not prev_service_enabled:
                activate(light_groups)

            # if service disabled, stop ambilight._ambi_loop thread
            if not service_enabled:
                AMBI_RUNNING.clear()

            # process cached waiting commands
            action = CACHE.get(f"{ADDONID}.action")
            if action:
                _process_actions(action, light_groups)

            # reload groups if settings changed, but keep player state
            if SETTINGS_CHANGED.is_set():
                light_groups = [lightgroup.LightGroup(0, hue_connection, lightgroup.VIDEO, initial_state=light_groups[0].state, video_info_tag=light_groups[0].video_info_tag),
                                lightgroup.LightGroup(1, hue_connection, lightgroup.AUDIO, initial_state=light_groups[1].state, video_info_tag=light_groups[1].video_info_tag),
                                ambigroup.AmbiGroup(3, hue_connection, initial_state=light_groups[2].state, video_info_tag=light_groups[2].video_info_tag)]
                SETTINGS_CHANGED.clear()

            # every minute, check for sunset & connection
            if timer > 59:
                timer = 0
                # check connection to Hue hue_connection and fetch daylight status
                try:
                    if connection_retries > 0:
                        hue_connection.connect_bridge(silent=True)
                        if hue_connection.connected:
                            new_daylight = hue_connection.get_daylight()
                            connection_retries = 0
                    else:
                        new_daylight = hue_connection.get_daylight()
                except (requests.RequestException, ConnectionError) as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 10:
                        xbmc.log(f"[script.service.hue] Bridge Connection Error. Attempt: {connection_retries}/10 : {error}")
                        notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60
                    else:
                        xbmc.log(f"[script.service.hue] Bridge Connection Error. Attempt: {connection_retries}/10. Shutting down : {error}")
                        notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        hue_connection.connected = False

                # check if sunset took place
                if new_daylight != daylight:
                    xbmc.log(f"[script.service.hue] Daylight change. current: {daylight}, new: {new_daylight}")
                    daylight = new_daylight

                    CACHE.set(f"{ADDONID}.daylight", daylight)
                    if not daylight and service_enabled:
                        xbmc.log("[script.service.hue] Sunset activate")
                        activate(light_groups)
            timer += 1
            monitor.waitForAbort(1)
        xbmc.log("[script.service.hue] Process exiting...")
        return
    xbmc.log("[script.service.hue] No connected hue_connection, exiting...")
    return


def _process_actions(action, light_groups):
    # process an action command stored in the cache.
    action_action = action[0]
    action_light_group_id = int(action[1]) - 1
    xbmc.log(f"[script.service.hue] Action command: {action}, action_action: {action_action}, action_light_group_id: {action_light_group_id}")
    light_groups[action_light_group_id].run_action(action_action)

    CACHE.set(f"{ADDONID}.action", None)


class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        # xbmc.log("[script.service.hue] Settings changed")
        validate_settings()
        SETTINGS_CHANGED.set()

    def onNotification(self, sender, method, data):
        if sender == ADDONID:
            xbmc.log(f"[script.service.hue] Notification received: method: {method}, data: {data}")

            if method == "Other.disable":
                xbmc.log("[script.service.hue] Notification received: Disable")
                CACHE.set(f"{ADDONID}.service_enabled", False)

            if method == "Other.enable":
                xbmc.log("[script.service.hue] Notification received: Enable")
                CACHE.set(f"{ADDONID}.service_enabled", True)

            if method == "Other.actions":
                json_loads = json.loads(data)

                light_group_id = json_loads['group']
                action = json_loads['command']
                xbmc.log(f"[script.service.hue] Action Notification: group: {light_group_id}, command: {action}")
                CACHE.set("script.service.hue.action", (action, light_group_id), expiration=(timedelta(seconds=5)))


def activate(light_groups):
    """
    Activates play action as appropriate for all groups. Used at sunset and when service is re-enabled via Actions.
    """
    xbmc.log(f"[script.service.hue] Activating scenes: light_groups: {light_groups}")

    for g in light_groups:
        xbmc.log(f"[script.service.hue] in activate g: {g}, light_group_id: {g.light_group_id}")
        if ADDON.getSettingBool(f"group{g.light_group_id}_enabled"):
            g.activate()
