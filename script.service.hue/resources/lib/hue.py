#      Copyright (C) 2023 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import json
from socket import getfqdn
from urllib.parse import urljoin

import requests
import urllib3
import xbmcgui
from requests.exceptions import HTTPError, ConnectionError, Timeout

from . import ADDON, TIMEOUT, NOTIFICATION_THRESHOLD, MAX_RETRIES, reporting
from .kodiutils import notification, convert_time, log
from .language import get_string as _


class Hue(object):
    def __init__(self, settings_monitor, discover=False):
        self.scene_data = None
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Old hue bridges use insecure https

        self.session = requests.Session()
        self.session.verify = False

        self.connected: bool = False
        self.devices: dict = None
        self.bridge_id = None
        self.retries = 0
        self.max_retries = 5
        self.max_timeout = 5
        self.base_url = None
        self.sunset = None
        self.settings_monitor = settings_monitor

        log(f"[SCRIPT.SERVICE.HUE] v2 init: ip: {self.settings_monitor.ip}, key: {self.settings_monitor.key}")
        if discover:
            self.discover()
        elif self.settings_monitor.ip != "" or self.settings_monitor.key != "":
            self.connected = self.connect()
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge IP or user key provided. Bridge not configured.")
            notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def make_api_request(self, method, resource, discovery=False, **kwargs):
        # Discovery and account creation not yet supported on API V2. This flag uses a V1 URL and supports new IPs.
        if discovery:
            log(f"[SCRIPT.SERVICE.HUE] v2 make_request: discovery mode. DiscoveredIP: {self.discoveredIP}")
        for attempt in range(MAX_RETRIES):
            # Prepare the URL for the request
            log(f"[SCRIPT.SERVICE.HUE] v2 ip: {self.settings_monitor.ip}, key: {self.settings_monitor.key}")
            base_url = self.base_url if not discovery else f"http://{self.discoveredIP}/api/"
            url = urljoin(base_url, resource)
            #log(f"[SCRIPT.SERVICE.HUE] v2 make_request: base_url: {base_url}, url: {url}, method: {method}, kwargs: {kwargs}")
            try:
                # Make the request
                response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
                response.raise_for_status()
                return response.json()
            except ConnectionError as x:
                # If a ConnectionError occurs, try to handle a new IP, except in discovery mode
                log(f"[SCRIPT.SERVICE.HUE] v2 make_request: ConnectionError: {x}")
                if self._discover_new_ip() and not discovery:
                    # If handling a new IP is successful, retry the request
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: New IP handled successfully. Retrying request.")
                    continue
                else:
                    # If handling a new IP fails, abort the request
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Failed to handle new IP. Aborting request.")
                    return None

            except HTTPError as x:
                # Handle HTTP errors
                if x.response.status_code == 429:
                    # If a 429 status code is received, abort and log an error
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Too Many Requests: {x} \nResponse: {x.response.text}")
                    return 429
                elif x.response.status_code in [401, 403]:
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Unauthorized: {x}\nResponse: {x.response.text}")
                    notification(_("Hue Service"), _("Bridge unauthorized, please reconfigure."), icon=xbmcgui.NOTIFICATION_ERROR)
                    ADDON.setSettingString("bridgeUser", "")
                    return 401
                elif x.response.status_code == 404:
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Not Found: {x}\nResponse: {x.response.text}")
                    return 404
                elif x.response.status_code == 500:
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Internal Bridge Error: {x}\nResponse: {x.response.text}")
                    return 500
                else:
                    log(f"[SCRIPT.SERVICE.HUE] v2 make_request: HTTPError: {x}\nResponse: {x.response.text}")
                    reporting.process_exception(f"Response: {x.response.text}, Exception: {x}", logging=True)
                    return x.response.status_code
            except (Timeout, json.JSONDecodeError) as x:
                log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Timeout/JSONDecodeError: Response: {x.response}\n{x}")
            except requests.RequestException as x:
                # Report other kinds of RequestExceptions
                log(f"[SCRIPT.SERVICE.HUE] v2 make_request: RequestException: {x}")
                reporting.process_exception(x)
            # Calculate the retry time and log the retry attempt
            retry_time = 2 ** attempt
            if retry_time >= 7 and attempt >= NOTIFICATION_THRESHOLD:
                notification(_("Hue Service"), _("Connection failed, retrying..."), icon=xbmcgui.NOTIFICATION_WARNING)
            log(f"[SCRIPT.SERVICE.HUE] v2 make_request: Retry in {retry_time} seconds, retry {attempt + 1}/{MAX_RETRIES}...")
            if self.settings_monitor.waitForAbort(retry_time):
                break
        # If all attempts fail, log the failure and set connected to False
        log(f"[SCRIPT.SERVICE.HUE] v2 make_request: All attempts failed after {MAX_RETRIES} retries. Setting connected to False")
        self.connected = False
        return None

    def _discover_new_ip(self):
        if self._discover_nupnp():
            log(f"[SCRIPT.SERVICE.HUE] v2 _discover_and_handle_new_ip: discover_nupnp SUCCESS, bridge IP: {self.settings_monitor.ip}")
            # TODO:  add new discovery methods here
            ADDON.setSettingString("bridgeIP", self.discoveredIP)
            if self.connect():
                log(f"[SCRIPT.SERVICE.HUE] v2 _discover_and_handle_new_ip: connect SUCCESS")
                return True
        log(f"[SCRIPT.SERVICE.HUE] v2 _discover_and_handle_new_ip: discover_nupnp FAIL, bridge IP: {self.settings_monitor.ip}")
        return False

    def connect(self):
        log(f"[SCRIPT.SERVICE.HUE] v2 connect: ip: {self.settings_monitor.ip}, key: {self.settings_monitor.key}")
        if self.settings_monitor.ip and self.settings_monitor.key:
            self.base_url = f"https://{self.settings_monitor.ip}/clip/v2/resource/"
            self.session.headers.update({'hue-application-key': self.settings_monitor.key})

            self.devices = self.make_api_request("GET", "device")
            if not isinstance(self.devices, dict):
                log(f"[SCRIPT.SERVICE.HUE] v2 connect: Connection error. Setting connected to False.  {type(self.devices)} :  {self.devices}")
                self.connected = False
                return False

            self.scene_data = self.make_api_request("GET", "scene")

            self.bridge_id = self.get_device_by_archetype(self.devices, 'bridge_v2')
            if self._check_version():
                self.connected = True
                self.update_sunset()
                log(f"[SCRIPT.SERVICE.HUE] v2 connect: Connection successful")
                return True
            log(f"[SCRIPT.SERVICE.HUE] v2 connect: Connection attempts failed. Setting connected to False")
            self.connected = False
            return False

        log("[SCRIPT.SERVICE.HUE] No bridge IP or user key provided. Bridge not configured.")
        notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
        return False

    def discover(self):
        log("[SCRIPT.SERVICE.HUE] v2 Start discover")
        # Reset settings
        self.discoveredIP = ""
        self.key = ""
        self.connected = False

        ADDON.setSettingString("bridgeIP", "")
        ADDON.setSettingString("bridgeUser", "")

        progress_bar = xbmcgui.DialogProgress()
        progress_bar.create(_('Searching for bridge...'))
        progress_bar.update(5, _("Discovery started"))

        complete = False
        while not progress_bar.iscanceled() and not complete and not self.settings_monitor.abortRequested():

            progress_bar.update(percent=10, message=_("N-UPnP discovery..."))
            # Try to discover the bridge using N-UPnP
            ip_discovered = self._discover_nupnp()

            if not ip_discovered and not progress_bar.iscanceled():
                # If the bridge was not found, ask the user to enter the IP manually
                log("[SCRIPT.SERVICE.HUE] v2 discover: Bridge not found automatically")
                progress_bar.update(percent=10, message=_("Bridge not found"))
                manual_entry = xbmcgui.Dialog().yesno(_("Bridge not found"), _("Bridge not found automatically. Please make sure your bridge is up to date and has access to the internet. [CR]Would you like to enter your bridge IP manually?")
                                                      )
                if manual_entry:
                    self.discoveredIP = xbmcgui.Dialog().numeric(3, _("Bridge IP"))
                    log(f"[SCRIPT.SERVICE.HUE] v2 discover: Manual entry: {self.discoveredIP}")

            if self.discoveredIP:
                progress_bar.update(percent=50, message=_("Connecting..."))
                # Set the base URL for the API
                self.base_url = f"https://{self.discoveredIP}/clip/v2/resource/"
                # Try to connect to the bridge
                log(f"[SCRIPT.SERVICE.HUE] v2 discover: Attempt connection")
                config = self.make_api_request("GET", "0/config", discovery=True)  # bypass some checks in discovery mode, and use Hue API V1 until Philipps provides a V2 method
                log(f"[SCRIPT.SERVICE.HUE] v2 discover: config: {config}")
                if config is not None and isinstance(config, dict) and not progress_bar.iscanceled():
                    progress_bar.update(percent=100, message=_("Found bridge: ") + self.discoveredIP)
                    self.settings_monitor.waitForAbort(1)

                    # Try to create a user
                    bridge_user_created = self._create_user(progress_bar)

                    if bridge_user_created:
                        log(f"[SCRIPT.SERVICE.HUE] v2 discover: User created: {bridge_user_created}")
                        progress_bar.update(percent=90, message=_("User Found![CR]Saving settings..."))

                        # Save the IP and user key to the settings
                        ADDON.setSettingString("bridgeIP", self.discoveredIP)
                        ADDON.setSettingString("bridgeUser", bridge_user_created)

                        progress_bar.update(percent=100, message=_("Complete!"))
                        self.settings_monitor.waitForAbort(5)
                        progress_bar.close()
                        log("[SCRIPT.SERVICE.HUE] v2 discover: Bridge discovery complete")
                        self.connect()
                        return

                    elif progress_bar.iscanceled():
                        log("[SCRIPT.SERVICE.HUE] v2 discover: Discovery cancelled by user")
                        progress_bar.update(percent=100, message=_("Cancelled"))
                        progress_bar.close()

                    else:
                        log(f"[SCRIPT.SERVICE.HUE] v2 discover: User not created, received: {self.settings_monitor.key}")
                        progress_bar.update(percent=100, message=_("User not found[CR]Check your bridge and network."))
                        self.settings_monitor.waitForAbort(5)
                        progress_bar.close()
                        return
                elif progress_bar.iscanceled():
                    log("[SCRIPT.SERVICE.HUE] v2 discover: Discovery cancelled by user")

                    progress_bar.update(percent=100, message=_("Cancelled"))
                    progress_bar.close()
                else:
                    progress_bar.update(percent=100, message=_("Bridge not found[CR]Check your bridge and network."))
                    log("[SCRIPT.SERVICE.HUE] v2 discover: Bridge not found, check your bridge and network")
                    self.settings_monitor.waitForAbort(5)
                    progress_bar.close()

            log("[SCRIPT.SERVICE.HUE] v2 discover: Discovery process complete")
            complete = True
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

        if progress_bar.iscanceled():
            log("[SCRIPT.SERVICE.HUE] v2 discover: Bridge discovery cancelled by user")
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

    def _create_user(self, progress_bar):
        # Log start of user creation
        log("[SCRIPT.SERVICE.HUE] v2 _create_user: In createUser")

        # Prepare data for POST request
        data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn())

        time = 0
        timeout = 90
        progress = 0
        last_progress = -1

        # Loop until timeout, user cancellation, or settings_monitor abort request
        while time <= timeout and not self.settings_monitor.abortRequested() and not progress_bar.iscanceled():
            progress = int((time / timeout) * 100)

            # Update progress bar if progress has changed
            if progress != last_progress:
                progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))
                last_progress = progress

            response = self.make_api_request("POST", "", discovery=True, data=data)
            log(f"[SCRIPT.SERVICE.HUE] v2 _create_user: response at iteration {time}: {response}")

            # Break loop if link button has been pressed
            if response and response[0].get('error', {}).get('type') != 101:
                break

            self.settings_monitor.waitForAbort(1)
            time = time + 1

        if progress_bar.iscanceled():
            return False

        try:
            # Extract and save username from response
            username = response[0]['success']['username']

            log(f"[SCRIPT.SERVICE.HUE] v2 _create_user: User created: {username}")
            return username
        except (KeyError, TypeError) as exc:
            log(f"[SCRIPT.SERVICE.HUE] v2 _create_user: Username not found: {exc}")
            return False

    def _check_version(self):
        try:
            software_version = self.get_attribute_value(self.devices, self.bridge_id, ['product_data', 'software_version'])
            api_split = software_version.split(".")
        except KeyError as error:
            notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
            log(f"[SCRIPT.SERVICE.HUE] v2 _version_check():  Connected! Bridge too old: {software_version}, error: {error}")
            return False
        except Exception as exc:
            reporting.process_exception(exc)
            return False

        if int(api_split[0]) >= 1 and int(api_split[1]) >= 60:  # minimum bridge version 1.60
            log(f"[SCRIPT.SERVICE.HUE] v2 connect() software version: {software_version}")
            return True

        notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
        log(f"[SCRIPT.SERVICE.HUE] v2 connect():  Connected! Bridge API too old: {software_version}")
        return False

    def update_sunset(self):
        geolocation = self.make_api_request("GET", "geolocation")
        log(f"[SCRIPT.SERVICE.HUE] v2 update_sunset(): geolocation: {geolocation}")
        sunset_str = self.search_dict(geolocation, "sunset_time")
        if sunset_str is None or sunset_str == "":
            log(f"[SCRIPT.SERVICE.HUE] Sunset not found; configure Hue geolocalisation")
            notification(_("Hue Service"), _("Configure Hue Home location to use Sunset time, defaulting to 19:00"), icon=xbmcgui.NOTIFICATION_ERROR)
            self.sunset = convert_time("19:00")
            return

        self.sunset = convert_time(sunset_str)
        log(f"[SCRIPT.SERVICE.HUE] v2 update_sunset(): sunset: {self.sunset}")

    def recall_scene(self, scene_id, duration=400):  # 400 is the default used by Hue, defaulting here for consistency

        log(f"[SCRIPT.SERVICE.HUE] v2 recall_scene(): scene_id: {scene_id}, transition_time: {duration}")

        json_data = {
            "recall": {
                "action": "active",
                "duration": int(duration)  # Hue API requires int
            }
        }
        response = self.make_api_request("PUT", f"scene/{scene_id}", json=json_data)

        log(f"[SCRIPT.SERVICE.HUE] v2 recall_scene(): response: {response}")
        return response

    def configure_scene(self, group_id, action):
        scene = self.select_hue_scene()
        log(f"[SCRIPT.SERVICE.HUE] v2 selected scene: {scene}")
        if scene is not None:
            # setting ID format example: group0_playSceneID
            ADDON.setSettingString(f"group{group_id}_{action}SceneID", scene[0])
            ADDON.setSettingString(f"group{group_id}_{action}SceneName", scene[1])
        ADDON.openSettings()

    def get_scenes_and_areas(self):
        scenes_data = self.make_api_request("GET", "scene")
        rooms_data = self.make_api_request("GET", "room")
        zones_data = self.make_api_request("GET", "zone")

        # Create dictionaries for rooms and zones
        rooms_dict = {room['id']: room['metadata']['name'] for room in rooms_data['data']}
        zones_dict = {zone['id']: zone['metadata']['name'] for zone in zones_data['data']}

        # Merge rooms and zones into areas
        areas_dict = {**rooms_dict, **zones_dict}
        log(f"[SCRIPT.SERVICE.HUE] v2 get_scenes(): areas_dict: {areas_dict}")
        # Create a dictionary for scenes
        scenes_dict = {}
        for scene in scenes_data['data']:
            scene_id = scene['id']
            scene_name = scene['metadata']['name']
            area_id = scene['group']['rid']

            scenes_dict[scene_id] = {'scene_name': scene_name, 'area_id': area_id}

        # dict_items = "\n".join([f"{key}: {value}" for key, value in scenes_dict.items()])
        # log(f"[SCRIPT.SERVICE.HUE] v2 get_scenes(): scenes_dict:\n{dict_items}")

        return scenes_dict, areas_dict

    def select_hue_scene(self):
        dialog_progress = xbmcgui.DialogProgress()
        dialog_progress.create("Hue Service", "Searching for scenes...")
        log("[SCRIPT.SERVICE.HUE] V2 selectHueScene{}")

        hue_scenes, hue_areas = self.get_scenes_and_areas()

        area_items = [xbmcgui.ListItem(label=name) for _, name in hue_areas.items()]
        log(f"[SCRIPT.SERVICE.HUE] V2 selectHueScene: area_items: {area_items}")
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
                log(f"[SCRIPT.SERVICE.HUE] V2 selectHueScene: selected: {selected_id}, name: {selected_name}")
                dialog_progress.close()
                return selected_id, selected_name
        log("[SCRIPT.SERVICE.HUE] V2 selectHueScene: cancelled")
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

    def _discover_nupnp(self):
        log("[SCRIPT.SERVICE.HUE] v2 _discover_nupnp:")
        result: dict = self.make_api_request('GET', 'https://discovery.meethue.com/')
        if result is None or isinstance(result, int):
            log(f"[SCRIPT.SERVICE.HUE] v2 _discover_nupnp: make_request failed, result: {result}")
            return None

        bridge_ip = None
        if result:
            try:
                bridge_ip = result[0]["internalipaddress"]
            except KeyError:
                log("[SCRIPT.SERVICE.HUE] v2 _discover_nupnp: No IP found in response")
                return None
        self.discoveredIP = bridge_ip
        return True

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
