#      Copyright (C) 2023 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import json
from socket import getfqdn

import requests
import urllib3
import xbmcgui,xbmcvfs
from requests.exceptions import HTTPError, ConnectionError, Timeout

from . import ADDON, TIMEOUT, NOTIFICATION_THRESHOLD, MAX_RETRIES, HueApiError, reporting
from .kodiutils import notification, convert_time, log
from .language import get_string as _
from .mdns_discovery import discover_hue_bridge_mdns


class Hue(object):
    def __init__(self, settings_monitor, discover=False):
        self.scene_data = None

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Old hue bridges use insecure https
        self.session = requests.Session()
        self.session.verify = False

        self.connected: bool = False
        self.devices: dict = None
        self.bridge_id = None
        self.base_url = None
        self.sunset = None
        self.settings_monitor = settings_monitor

        log(f"[SCRIPT.SERVICE.HUE] init: ip: {self.settings_monitor.ip}, key: {self.settings_monitor.key}")
        if discover:
            self.discover()
        elif self.settings_monitor.ip != "" or self.settings_monitor.key != "":
            self.connected = self.connect()
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge IP or user key provided. Bridge not configured.")
            notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)

    def make_api_request(self, method, resource, **kwargs):
        ip_discovered = False
        for attempt in range(MAX_RETRIES):
            url = f"{self.base_url}{resource}"
            if attempt == 0 or ip_discovered:
                log(f"[SCRIPT.SERVICE.HUE] make_request: {method} {url}")
            try:
                response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
                response.raise_for_status()
                return response.json()
            except ConnectionError as x:
                log(f"[SCRIPT.SERVICE.HUE] make_request: ConnectionError: {x}")
                if not ip_discovered:
                    ip_discovered = self._discover_new_ip()
            except HTTPError as x:
                status = x.response.status_code
                text = x.response.text
                if status == 429:
                    log(f"[SCRIPT.SERVICE.HUE] make_request: Too Many Requests: {x}\nResponse: {text}")
                    raise HueApiError(429, text)
                elif status in [401, 403]:
                    log(f"[SCRIPT.SERVICE.HUE] make_request: Unauthorized: {x}\nResponse: {text}")
                    notification(_("Hue Service"), _("Bridge unauthorized, please reconfigure."), icon=xbmcgui.NOTIFICATION_ERROR)
                    ADDON.setSettingString("bridgeUser", "")
                    raise HueApiError(401, text)
                elif status == 404:
                    log(f"[SCRIPT.SERVICE.HUE] make_request: Not Found: {x}\nResponse: {text}")
                    raise HueApiError(404, text)
                elif status == 500:
                    log(f"[SCRIPT.SERVICE.HUE] make_request: Internal Bridge Error: {x}\nResponse: {text}")
                else:
                    log(f"[SCRIPT.SERVICE.HUE] make_request: HTTPError: {x}\nResponse: {text}")
                    reporting.process_exception(f"Response: {text}, Exception: {x}", logging=True)
                    raise HueApiError(status, text)
            except Timeout as x:
                log(f"[SCRIPT.SERVICE.HUE] make_request: Timeout: {x}")
            except json.JSONDecodeError as x:
                log(f"[SCRIPT.SERVICE.HUE] make_request: JSONDecodeError: {x}")
            except requests.RequestException as x:
                log(f"[SCRIPT.SERVICE.HUE] make_request: RequestException: {x}")
                reporting.process_exception(x)
            if attempt == MAX_RETRIES - 1:
                break  # no point waiting after the last attempt
            retry_time = 2 ** attempt
            if attempt >= NOTIFICATION_THRESHOLD:
                notification(_("Hue Service"), _("Connection failed, retrying..."), icon=xbmcgui.NOTIFICATION_WARNING)
            log(f"[SCRIPT.SERVICE.HUE] make_request: Retry in {retry_time}s ({attempt + 1}/{MAX_RETRIES})")
            if self.settings_monitor.waitForAbort(retry_time):
                break
        log(f"[SCRIPT.SERVICE.HUE] make_request: All {MAX_RETRIES} attempts failed")
        return None

    def _make_v1_request(self, method, resource, ip=None, **kwargs):
        if ip is None:
            ip = self.settings_monitor.ip
        url = f"https://{ip}/api/{resource}"
        log(f"[SCRIPT.SERVICE.HUE] _make_v1_request: {method} {url}")
        try:
            response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
            response.raise_for_status()
            return response.json()
        except (ConnectionError, HTTPError, Timeout) as exc:
            log(f"[SCRIPT.SERVICE.HUE] _make_v1_request: {type(exc).__name__}: {exc}")
            return None
        except json.JSONDecodeError as exc:
            log(f"[SCRIPT.SERVICE.HUE] _make_v1_request: JSONDecodeError: {exc}")
            return None

    def _discover_bridge_ip(self):
        log("[SCRIPT.SERVICE.HUE] _discover_bridge_ip: Trying mDNS...")
        ip = discover_hue_bridge_mdns(timeout=2.0)
        if ip:
            log(f"[SCRIPT.SERVICE.HUE] _discover_bridge_ip: mDNS found bridge at {ip}")
            return ip
        log("[SCRIPT.SERVICE.HUE] _discover_bridge_ip: mDNS failed, trying cloud lookup...")
        ip = self._discover_cloud()
        if ip:
            log(f"[SCRIPT.SERVICE.HUE] _discover_bridge_ip: Cloud found bridge at {ip}")
            return ip
        log("[SCRIPT.SERVICE.HUE] _discover_bridge_ip: All discovery methods failed")
        return None

    def _discover_cloud(self):
        log("[SCRIPT.SERVICE.HUE] _discover_cloud: Querying discovery.meethue.com")
        try:
            response = self.session.get("https://discovery.meethue.com/", timeout=TIMEOUT)
            response.raise_for_status()
            result = response.json()
            if result:
                ip = result[0]["internalipaddress"]
                log(f"[SCRIPT.SERVICE.HUE] _discover_cloud: Found bridge at {ip}")
                return ip
            log("[SCRIPT.SERVICE.HUE] _discover_cloud: Empty response")
            return None
        except (ConnectionError, HTTPError, Timeout) as exc:
            log(f"[SCRIPT.SERVICE.HUE] _discover_cloud: {type(exc).__name__}: {exc}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            log(f"[SCRIPT.SERVICE.HUE] _discover_cloud: Parse error: {exc}")
            return None

    def _discover_new_ip(self):
        new_ip = self._discover_bridge_ip()
        if new_ip:
            log(f"[SCRIPT.SERVICE.HUE] _discover_new_ip: Found bridge at {new_ip}")
            ADDON.setSettingString("bridgeIP", new_ip)
            self.base_url = f"https://{new_ip}/clip/v2/resource/"
            return True
        log("[SCRIPT.SERVICE.HUE] _discover_new_ip: Discovery failed")
        return False

    def connect(self):
        log(f"[SCRIPT.SERVICE.HUE] connect: ip: {self.settings_monitor.ip}, key: {self.settings_monitor.key}")
        if self.settings_monitor.ip and self.settings_monitor.key:
            self.base_url = f"https://{self.settings_monitor.ip}/clip/v2/resource/"
            self.session.headers.update({'hue-application-key': self.settings_monitor.key})

            try:
                self.devices = self.make_api_request("GET", "device")
                if not isinstance(self.devices, dict):
                    log(f"[SCRIPT.SERVICE.HUE] connect: Connection error. Setting connected to False. {type(self.devices)}: {self.devices}")
                    notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
                    self.connected = False
                    return False

                self.scene_data = self.make_api_request("GET", "scene")

                self.bridge_id = self.get_device_by_archetype(self.devices, 'bridge_v2')
                if self._check_version():
                    self.connected = True
                    self.update_sunset()
                    log("[SCRIPT.SERVICE.HUE] connect: Connection successful")
                    return True
            except HueApiError as exc:
                # Bridge rejected the request (eg. 401 after a re-pair/reset); treat as a failed connection instead of crashing the service.
                log(f"[SCRIPT.SERVICE.HUE] connect: HueApiError: {exc}")
            log("[SCRIPT.SERVICE.HUE] connect: Connection attempts failed. Setting connected to False")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            self.connected = False
            return False

        log("[SCRIPT.SERVICE.HUE] No bridge IP or user key provided. Bridge not configured.")
        notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
        self.connected = False
        return False

    def discover(self):
        log("[SCRIPT.SERVICE.HUE] Start discover")
        self.connected = False

        progress_bar = xbmcgui.DialogProgress()
        progress_bar.create(_('Searching for bridge...'))
        progress_bar.update(5, _("Discovery started"))

        create_user_attempts = 0
        MAX_CREATE_USER_ATTEMPTS = 1
        while not progress_bar.iscanceled() and not self.settings_monitor.abortRequested():
            progress_bar.update(percent=10, message=_("Searching for bridge..."))
            discovered_ip = self._discover_bridge_ip() or ""

            if not discovered_ip and not progress_bar.iscanceled():
                log("[SCRIPT.SERVICE.HUE] discover: Bridge not found automatically")
                progress_bar.update(percent=10, message=_("Bridge not found"))
                manual_entry = xbmcgui.Dialog().yesno(
                    _("Bridge not found"),
                    _("Bridge not found automatically. Please make sure your bridge is up to date and has access to the internet. [CR]Would you like to enter your bridge IP manually?")
                )
                if not manual_entry:
                    break
                discovered_ip = xbmcgui.Dialog().numeric(3, _("Bridge IP"))
                log(f"[SCRIPT.SERVICE.HUE] discover: Manual entry: {discovered_ip}")

            if not discovered_ip:
                continue

            progress_bar.update(percent=50, message=_("Connecting..."))
            log(f"[SCRIPT.SERVICE.HUE] discover: Attempt connection to {discovered_ip}")
            config = self._make_v1_request("GET", "0/config", ip=discovered_ip)
            log(f"[SCRIPT.SERVICE.HUE] discover: config: {config}")

            if progress_bar.iscanceled():
                break

            if not isinstance(config, dict):
                log("[SCRIPT.SERVICE.HUE] discover: Bridge not reachable, retrying")
                progress_bar.update(percent=10, message=_("Bridge not found[CR]Check your bridge and network."))
                discovered_ip = ""
                if self.settings_monitor.waitForAbort(3):
                    break
                continue

            progress_bar.update(percent=100, message=_("Found bridge: ") + discovered_ip)
            self.settings_monitor.waitForAbort(1)

            bridge_user_created = self._create_user(progress_bar, discovered_ip)

            if progress_bar.iscanceled():
                break

            if bridge_user_created:
                log(f"[SCRIPT.SERVICE.HUE] discover: User created: {bridge_user_created}")
                progress_bar.update(percent=90, message=_("User Found![CR]Saving settings..."))
                ADDON.setSettingString("bridgeIP", discovered_ip)
                ADDON.setSettingString("bridgeUser", bridge_user_created)
                progress_bar.update(percent=100, message=_("Complete!"))
                self.settings_monitor.waitForAbort(5)
                progress_bar.close()
                log("[SCRIPT.SERVICE.HUE] discover: Bridge discovery complete")
                self.connect()
                return

            create_user_attempts += 1
            if create_user_attempts >= MAX_CREATE_USER_ATTEMPTS:
                log(f"[SCRIPT.SERVICE.HUE] discover: Giving up after {create_user_attempts} failed pairing attempts; existing settings preserved")
                progress_bar.update(percent=100, message=_("Bridge connection failed"))

                self.settings_monitor.waitForAbort(3)

                break

            log("[SCRIPT.SERVICE.HUE] discover: User not created, retrying")
            progress_bar.update(percent=10, message=_("Bridge connection failed"))
            discovered_ip = ""
            if self.settings_monitor.waitForAbort(3):
                break

        log("[SCRIPT.SERVICE.HUE] discover: Discovery cancelled or ended")
        progress_bar.update(percent=100, message=_("Cancelled"))
        self.settings_monitor.waitForAbort(1)
        progress_bar.close()

    def _create_user(self, progress_bar, ip):
        log("[SCRIPT.SERVICE.HUE] _create_user: start")

        data = {"devicetype": f"kodi#{getfqdn()}", "generateclientkey": True}

        response = None
        time = 0
        timeout = 90
        last_progress = -1

        while time <= timeout and not self.settings_monitor.abortRequested() and not progress_bar.iscanceled():
            progress = int((time / timeout) * 100)

            if progress != last_progress:
                progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))
                last_progress = progress

            response = self._make_v1_request("POST", "", ip=ip, json=data)
            log(f"[SCRIPT.SERVICE.HUE] _create_user: response at iteration {time}: {response}")

            if response and response[0].get('error', {}).get('type') != 101:
                break

            self.settings_monitor.waitForAbort(1)
            time = time + 1

        if progress_bar.iscanceled():
            return False

        try:
            username = response[0]['success']['username']
            log(f"[SCRIPT.SERVICE.HUE] _create_user: User created: {username}")
            return username
        except (KeyError, TypeError) as exc:
            log(f"[SCRIPT.SERVICE.HUE] _create_user: Username not found: {exc}")
            return False

    def _check_version(self):
        try:
            config = self._make_v1_request("GET", "config")
            log(f"[SCRIPT.SERVICE.HUE] _version_check(): config: {config}")

            swversion_raw = self.search_dict(config, "swversion")
            if swversion_raw is None:
                raise KeyError("swversion not found in config")
            swversion = int(swversion_raw)
            log(f"[SCRIPT.SERVICE.HUE] _version_check(): swversion: {swversion}")
        except (KeyError, ValueError, TypeError) as error:
            log(f"[SCRIPT.SERVICE.HUE] _version_check(): Could not determine bridge version: {error}")
            notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
            return False
        except Exception as exc:
            reporting.process_exception(exc)
            return False

        if swversion >= 1948086000:  # minimum bridge version 1.60
            log(f"[SCRIPT.SERVICE.HUE] connect() software version: {swversion}")
            return True

        notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
        log(f"[SCRIPT.SERVICE.HUE] connect(): Connected! Bridge API too old: {swversion}")
        return False

    def update_sunset(self):
        try:
            geolocation = self.make_api_request("GET", "geolocation")
        except HueApiError as exc:
            log(f"[SCRIPT.SERVICE.HUE] update_sunset(): HueApiError: {exc}")
            geolocation = None
        log(f"[SCRIPT.SERVICE.HUE] update_sunset(): geolocation: {geolocation}")
        if geolocation is None:
            # Request failed; keep the previous sunset if there is one so a transient outage doesn't reset it.
            if self.sunset is not None:
                log(f"[SCRIPT.SERVICE.HUE] update_sunset(): request failed, keeping previous sunset: {self.sunset}")
                return
            log("[SCRIPT.SERVICE.HUE] update_sunset(): request failed and no previous sunset, defaulting to 19:00")
            self.sunset = convert_time("19:00")
            return
        sunset_str = self.search_dict(geolocation, "sunset_time")
        if sunset_str is None or sunset_str == "":
            log("[SCRIPT.SERVICE.HUE] Sunset not found; configure Hue geolocalisation")
            notification(_("Hue Service"), _("Configure Hue Home location to use Sunset time, defaulting to 19:00"), icon=xbmcgui.NOTIFICATION_ERROR)
            self.sunset = convert_time("19:00")
            return

        self.sunset = convert_time(sunset_str)
        log(f"[SCRIPT.SERVICE.HUE] update_sunset(): sunset: {self.sunset}")

    def recall_scene(self, scene_id, duration=400):  # 400 is the default used by Hue, defaulting here for consistency

        log(f"[SCRIPT.SERVICE.HUE] recall_scene(): scene_id: {scene_id}, transition_time: {duration}")

        json_data = {
            "recall": {
                "action": "active",
                "duration": int(duration)  # Hue API requires int
            }
        }
        response = self.make_api_request("PUT", f"scene/{scene_id}", json=json_data)

        log(f"[SCRIPT.SERVICE.HUE] recall_scene(): response: {response}")
        return response

    def configure_scene(self, group_id, action):
        scene = self.select_hue_scene()
        log(f"[SCRIPT.SERVICE.HUE] selected scene: {scene}")
        if scene is not None:
            # setting ID format example: group0_playSceneID
            ADDON.setSettingString(f"group{group_id}_{action}SceneID", scene[0])
            ADDON.setSettingString(f"group{group_id}_{action}SceneName", scene[1])
        ADDON.openSettings()

    def get_scenes_and_areas(self):
        try:
            scenes_data = self.make_api_request("GET", "scene")
            rooms_data = self.make_api_request("GET", "room")
            zones_data = self.make_api_request("GET", "zone")
        except HueApiError as exc:
            log(f"[SCRIPT.SERVICE.HUE] get_scenes_and_areas(): HueApiError: {exc}")
            return None

        # All three requests must have returned data before building the dictionaries
        if not all(isinstance(d, dict) and 'data' in d for d in (scenes_data, rooms_data, zones_data)):
            log("[SCRIPT.SERVICE.HUE] get_scenes_and_areas(): Bridge request failed, no data")
            return None

        # Create dictionaries for rooms and zones
        rooms_dict = {room['id']: room['metadata']['name'] for room in rooms_data['data']}
        zones_dict = {zone['id']: zone['metadata']['name'] for zone in zones_data['data']}

        # Merge rooms and zones into areas
        areas_dict = {**rooms_dict, **zones_dict}
        log(f"[SCRIPT.SERVICE.HUE] get_scenes(): areas_dict: {areas_dict}")
        # Create a dictionary for scenes
        scenes_dict = {}
        for scene in scenes_data['data']:
            scene_id = scene['id']
            scene_name = scene['metadata']['name']
            area_id = scene['group']['rid']

            scenes_dict[scene_id] = {'scene_name': scene_name, 'area_id': area_id}

        return scenes_dict, areas_dict

    def select_hue_scene(self):
        dialog_progress = xbmcgui.DialogProgress()
        dialog_progress.create("Hue Service", "Searching for scenes...")
        log("[SCRIPT.SERVICE.HUE] select_hue_scene: start")

        scenes_and_areas = self.get_scenes_and_areas()
        if scenes_and_areas is None:
            # Bridge unreachable or rejected the request; close the progress dialog instead of leaving it stuck open
            log("[SCRIPT.SERVICE.HUE] select_hue_scene: Can't fetch scenes from bridge")
            dialog_progress.close()
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            return None
        hue_scenes, hue_areas = scenes_and_areas

        area_items = [xbmcgui.ListItem(label=name) for _, name in hue_areas.items()]
        log(f"[SCRIPT.SERVICE.HUE] select_hue_scene: area_items: {area_items}")
        selected_area_index = xbmcgui.Dialog().select("Select Hue area...", area_items)

        if selected_area_index > -1:
            selected_area_id = list(hue_areas.keys())[selected_area_index]
            scene_items = [(scene_id, xbmcgui.ListItem(label=info['scene_name']))
                           for scene_id, info in hue_scenes.items() if info['area_id'] == selected_area_id]

            selected_scene_index = xbmcgui.Dialog().select("Select Hue scene...", [item[1] for item in scene_items])

            if selected_scene_index > -1:
                selected_id, selected_scene_item = scene_items[selected_scene_index]
                selected_scene_name = selected_scene_item.getLabel()
                selected_area_name = area_items[selected_area_index].getLabel()
                selected_name = f"{selected_scene_name} - {selected_area_name}"
                log(f"[SCRIPT.SERVICE.HUE] select_hue_scene: selected: {selected_id}, name: {selected_name}")
                dialog_progress.close()
                return selected_id, selected_name
        log("[SCRIPT.SERVICE.HUE] select_hue_scene: cancelled")
        dialog_progress.close()
        return None

    def configure_ambilights(self, group_id):
        lights = self._select_hue_lights()
        if lights is not None:
            light_names = [light['metadata']['name'] for light in lights]
            color_lights = [light['id'] for light in lights]

            ADDON.setSettingString(f"group{group_id}_Lights", ','.join(color_lights))
            ADDON.setSettingString(f"group{group_id}_LightNames", ', '.join(light_names))
            ADDON.setSettingBool(f"group{group_id}_enabled", True)
            ADDON.openSettings()

    def _select_hue_lights(self):
        hue_lights: dict = self.make_api_request("GET", "light")
        if hue_lights is not None and 'data' in hue_lights:
            items = [xbmcgui.ListItem(label=light['metadata']['name']) for light in hue_lights['data']]
            selected = xbmcgui.Dialog().multiselect(_("Select Hue Lights..."), items)
            if selected:
                return [hue_lights['data'][i] for i in selected]
        return None

    @staticmethod
    def get_device_by_archetype(json_data, archetype):
        for device in json_data['data']:
            if device['product_data']['product_archetype'] == archetype:
                return device['id']
        return None

    @staticmethod
    def get_attribute_value(json_data, device_id, attribute_path):
        for device in json_data['data']:
            if device['id'] == device_id:
                value = device
                for key in attribute_path:
                    value = value.get(key)
                    if value is None:
                        return None
                return value
        return None

    @staticmethod
    def search_dict(d, key):
        if key in d:
            return d[key]
        for k, v in d.items():
            if isinstance(v, dict):
                item = Hue.search_dict(v, key)
                if item is not None:
                    return item
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        item = Hue.search_dict(d, key)
                        if item is not None:
                            return item
