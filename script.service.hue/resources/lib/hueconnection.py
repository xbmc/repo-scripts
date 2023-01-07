#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import json
import traceback
from json import JSONDecodeError
from socket import getfqdn

import qhue
import requests
import xbmc
import xbmcgui
from qhue import QhueException

from resources.lib import ADDON, QHUE_TIMEOUT, reporting
from resources.lib.kodiutils import notification
from .language import get_string as _


class HueConnection(object):
    def __init__(self, monitor, silent=True, discover=False):
        self.bridge = None
        self.bridge_ip = ADDON.getSettingString("bridgeIP")
        self.bridge_user = ADDON.getSettingString("bridgeUser")
        self.monitor = monitor
        self.connected = False

        if discover:
            self.discover_bridge()
        else:
            self.connect_bridge(silent)

    def connect_bridge(self, silent=False):

        xbmc.log(f"[script.service.hue] in connect_bridge() with settings: bridgeIP: {self.bridge_ip}, bridgeUser: {self.bridge_user}")

        if self.bridge_ip and self.bridge_user:
            if not self._check_version():
                xbmc.log("[script.service.hue] in connect_bridge(): Bridge not responding to connection test, attempt finding a new bridge IP.")

                if self._discover_bridge_ip():
                    xbmc.log(f"[script.service.hue] in connect_bridge(): New IP found: {self.bridge_ip}. Saving")
                    ADDON.setSettingString("bridgeIP", self.bridge_ip)
                else:
                    xbmc.log("[script.service.hue] Bridge not found")
                    notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
                    self.connected = False
                    return

            xbmc.log("[script.service.hue] in Connect(): Checking User")
            if self._check_user():
                bridge = qhue.Bridge(self.bridge_ip, self.bridge_user, timeout=QHUE_TIMEOUT)
                self.connected = True
                self.bridge = bridge
                xbmc.log(f"[script.service.hue] Successfully connected to Hue Bridge: {self.bridge_ip}")
                if not silent:
                    notification(_("Hue Service"), _("Hue connected"), sound=False)
                return
            else:
                xbmc.log("[script.service.hue] Bridge not responding")
                notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
                self.connected = False

        else:
            xbmc.log("[script.service.hue] Bridge not configured")
            notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
            self.connected = False

    def discover_bridge(self):
        xbmc.log("[script.service.hue] Start bridgeDiscover")
        # Create new config if none exists. Returns success or fail as bool
        ADDON.setSettingString("bridgeIP", "")
        ADDON.setSettingString("bridgeUser", "")
        self.bridge_ip = ""
        self.bridge_user = ""

        self.connected = False

        progress_bar = xbmcgui.DialogProgress()
        progress_bar.create(_('Searching for bridge...'))
        progress_bar.update(5, _("Discovery started"))

        complete = False
        while not progress_bar.iscanceled() and not complete and not self.monitor.abortRequested():

            progress_bar.update(percent=10, message=_("N-UPnP discovery..."))
            bridge_ip_found = self._discover_nupnp()

            if not bridge_ip_found and not progress_bar.iscanceled():
                manual_entry = xbmcgui.Dialog().yesno(_("Bridge not found"),
                                                      _("Bridge not found automatically. Please make sure your bridge is up to date and has access to the internet. [CR]Would you like to enter your bridge IP manually?"))
                if manual_entry:
                    self.bridge_ip = xbmcgui.Dialog().numeric(3, _("Bridge IP"))

            if self.bridge_ip:
                progress_bar.update(percent=50, message=_("Connecting..."))
                if self._check_version() and self._check_bridge_model() and not progress_bar.iscanceled():
                    progress_bar.update(percent=100, message=_("Found bridge: ") + self.bridge_ip)
                    self.monitor.waitForAbort(1)

                    bridge_user_created = self._create_user(progress_bar)

                    if bridge_user_created:
                        xbmc.log(f"[script.service.hue] User created: {self.bridge_user}")
                        progress_bar.update(percent=90, message=_("User Found![CR]Saving settings..."))

                        ADDON.setSettingString("bridgeIP", self.bridge_ip)
                        ADDON.setSettingString("bridgeUser", self.bridge_user)

                        progress_bar.update(percent=100, message=_("Complete!"))
                        self.monitor.waitForAbort(5)
                        progress_bar.close()
                        xbmc.log("[script.service.hue] Bridge discovery complete")
                        self.connect_bridge(True)
                        return True

                    elif progress_bar.iscanceled():
                        xbmc.log("[script.service.hue] Cancelled 2")
                        complete = True
                        progress_bar.update(percent=100, message=_("Cancelled"))
                        progress_bar.close()

                    else:
                        xbmc.log(f"[script.service.hue] User not created, received: {self.bridge_user}")
                        progress_bar.update(percent=100, message=_("User not found[CR]Check your bridge and network."))
                        self.monitor.waitForAbort(5)
                        complete = True
                        progress_bar.close()
                        return
                elif progress_bar.iscanceled():
                    xbmc.log("[script.service.hue] Cancelled 3")
                    complete = True
                    progress_bar.update(percent=100, message=_("Cancelled"))
                    progress_bar.close()
                else:
                    progress_bar.update(percent=100, message=_("Bridge not found[CR]Check your bridge and network."))
                    xbmc.log("[script.service.hue] Bridge not found, check your bridge and network")
                    self.monitor.waitForAbort(5)
                    complete = True
                    progress_bar.close()

            xbmc.log("[script.service.hue] Cancelled 4")
            complete = True
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

        if progress_bar.iscanceled():
            xbmc.log("[script.service.hue] Bridge discovery cancelled by user 5")
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

    def _discover_bridge_ip(self):
        # discover hue bridge IP silently for non-interactive discovery / bridge IP change.
        xbmc.log("[script.service.hue] In discoverBridgeIP")
        if self._discover_nupnp():
            if self._check_version():
                return True
        return False

    def _discover_nupnp(self):
        xbmc.log("[script.service.hue] In kodiHue discover_nupnp()")
        try:
            req = requests.get('https://discovery.meethue.com/')
            result = req.json()
        except requests.RequestException as error:
            xbmc.log(f"[script.service.hue] Nupnp failed: {error}")
            return None
        except (JSONDecodeError, json.JSONDecodeError) as error:  # when discovery.meethue.com returns empty JSON or 429
            xbmc.log(f"[script.service.hue] Nupnp failed: {error}, req: {req}")
            return None

        bridge_ip = None
        if result:
            try:
                bridge_ip = result[0]["internalipaddress"]
            except KeyError:
                xbmc.log("[script.service.hue] Nupnp: No IP found in response")
                return None
        self.bridge_ip = bridge_ip
        return True

    def _check_bridge_model(self):
        bridge = qhue.Bridge(self.bridge_ip, None, timeout=QHUE_TIMEOUT)
        model = ""

        try:
            bridge_config = bridge.config()
            model = bridge_config["modelid"]
        except QhueException as exc:
            xbmc.log(f"[script.service.hue] Exception: checkBridgeModel {exc.type_id}: {exc.message} {traceback.format_exc()}")
            reporting.process_exception(exc)
            return None
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] Requests exception: {exc}")
            notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            return None

        if model == "BSB002":
            xbmc.log(f"[script.service.hue] Bridge model OK: {model}")
            return True
        xbmc.log(f"[script.service.hue] Unsupported bridge model: {model}")
        xbmcgui.Dialog().ok(_("Unsupported Hue Bridge"), _("Hue Bridge V1 (Round) is unsupported. Hue Bridge V2 (Square) is required."))
        return None

    def _check_version(self):
        b = qhue.Bridge(self.bridge_ip, None, timeout=QHUE_TIMEOUT)
        try:
            api_version = b.config()['apiversion']
        except QhueException as error:
            xbmc.log(f"[script.service.hue] Version check connection failed.  {error.type_id}: {error.message} {traceback.format_exc()}")
            reporting.process_exception(error)
            return False
        except requests.RequestException as error:
            xbmc.log(f"[script.service.hue] Version check connection failed.  {error}")
            return False
        except KeyError as error:
            notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
            xbmc.log(f"[script.service.hue] in _version_check():  Connected! Bridge too old: {api_version}, error: {error}")
            return False

        api_split = api_version.split(".")

        if api_version and int(api_split[0]) >= 1 and int(api_split[1]) >= 38:  # minimum bridge version 1.38
            xbmc.log(f"[script.service.hue] Bridge Found! Hue API version: {api_version}")
            return True

        notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"[script.service.hue] in _connection_test():  Connected! Bridge too old: {api_version}")
        return False

    def _check_user(self):
        xbmc.log("[script.service.hue] in user_test() Attempt initial connection")
        b = qhue.Bridge(self.bridge_ip, self.bridge_user, timeout=QHUE_TIMEOUT)
        try:
            zigbee = b.config()['zigbeechannel']
        except (requests.RequestException, qhue.QhueException, KeyError):
            return False

        if zigbee:
            xbmc.log(f"[script.service.hue] Hue User Authorized. Bridge Zigbee Channel: {zigbee}")
            return True
        return False

    def _create_user(self, progress_bar):
        xbmc.log("[script.service.hue] In createUser")
        # devicetype = 'kodi#'+getfqdn()
        data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn())  # Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

        req = requests
        res = 'link button not pressed'
        time = 0
        timeout = 90
        progress = 0

        progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))  # press link button on bridge

        while 'link button not pressed' in res and time <= timeout and not self.monitor.abortRequested() and not progress_bar.iscanceled():
            # xbmc.log(f"[script.service.hue] In create_user: abortRequested: {str(monitor.abortRequested())}, timer: {time}")

            progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))  # press link button on bridge

            try:
                req = requests.post(f'http://{self.bridge_ip}/api', data=data)
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] requests exception: {exc}")
                return False

            res = req.text
            self.monitor.waitForAbort(1)
            time = time + 1
            progress = int((time / timeout) * 100)

        if progress_bar.iscanceled():
            return False

        try:
            res = req.json()
            xbmc.log(f"[script.service.hue] json response: {res}, content: {req.content}")
            username = res[0]['success']['username']
            self.bridge_user = username
            return True
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] Username Requests exception: {exc}")
            return False
        except KeyError as exc:
            xbmc.log(f"[script.service.hue] Username not found: {exc}")
            return False

    def configure_scene(self, group_id, action):
        scene = self.select_hue_scene()
        if scene is not None:
            # group0_startSceneID
            ADDON.setSettingString(f"group{group_id}_{action}SceneID", scene[0])
            ADDON.setSettingString(f"group{group_id}_{action}SceneName", scene[1])
            ADDON.openSettings()

    def configure_ambilights(self, group_id):
        lights = self.select_hue_lights()
        light_names = []
        color_lights = []
        if lights is not None:
            for L in lights:
                light_names.append(self._get_light_name(L))
                color_lights.append(L)

            ADDON.setSettingString(f"group{group_id}_Lights", ','.join(color_lights))
            ADDON.setSettingString(f"group{group_id}_LightNames", ', '.join(light_names))
            ADDON.setSettingBool(f"group{group_id}_enabled", True)
            ADDON.openSettings()

    def create_hue_scene(self):
        xbmc.log("[script.service.hue] In kodiHue createHueScene")
        scenes = self.bridge.scenes

        xbmcgui.Dialog().ok(heading=_("Create New Scene"), message=_("Adjust lights to desired state in the Hue App to save as new scene.[CR]Set a fade time in seconds, or 0 for an instant transition."))

        scene_name = xbmcgui.Dialog().input(_("Scene Name"))

        if scene_name:
            try:
                transition_time = int(xbmcgui.Dialog().numeric(0, _("Fade Time (Seconds)"), defaultt="10")) * 10  # yes, default with two ts. *10 to convert secs to msecs
            except ValueError:
                transition_time = 0

            if transition_time > 65534:  # hue uses uint16 for transition time, so set a max
                transition_time = 65534
            selected = self.select_hue_lights()

            if selected:
                try:
                    result = scenes(lights=selected, name=scene_name, recycle=False, type='LightScene', http_method='post', transitiontime=transition_time)
                    # xbmc.log("[script.service.hue] In kodiHue createHueScene. Res: {}".format(res))
                except QhueException as exc:
                    xbmc.log(f"[script.service.hue]: Delete Hue Scene QhueException: {exc.type_id}: {exc.message} {traceback.format_exc()}")
                    notification(_("Hue Service"), _("ERROR: Scene not created") + f"[CR]{exc.message}")
                # xbmc.log(f"[script.service.hue] In kodiHue createHueGroup. Res: {result}")
                except requests.RequestException as exc:
                    xbmc.log(f"[script.service.hue]: Delete Hue Scene requestsException: {result} {exc}")
                    notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)

                if result[0]["success"]:
                    xbmcgui.Dialog().ok(heading=_("Create New Scene"), message=_("Scene successfully created![CR]You may now assign your scene to player actions."))
                else:
                    xbmcgui.Dialog().ok(_("Error"), _("ERROR: Scene not created"))
        else:
            xbmcgui.Dialog().ok(_("Error"), _("ERROR: Scene not created"))

    def delete_hue_scene(self):
        xbmc.log("[script.service.hue] In kodiHue deleteHueScene")
        scene = self.select_hue_scene()
        if scene is not None:
            confirm = xbmcgui.Dialog().yesno(heading=_("Delete Hue Scene"), message=_("Are you sure you want to delete this scene:") + f"[CR][B]{scene[1]}[/B]")
            if confirm:
                scenes = self.bridge.scenes
                try:
                    result = scenes[scene[0]](http_method='delete')
                except QhueException as exc:
                    xbmc.log(f"[script.service.hue]: Delete Hue Scene QhueException: {exc.type_id}: {exc.message} {traceback.format_exc()}")
                    notification(_("Hue Service"), _("ERROR: Scene not deleted") + f"[CR]{exc.message}")
                    # xbmc.log(f"[script.service.hue] In kodiHue createHueGroup. Res: {result}")
                    return
                except requests.RequestException as exc:
                    xbmc.log(f"[script.service.hue]: Delete Hue Scene requestsException: {result} {exc}")
                    notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
                    return

                if result[0]["success"]:
                    notification(_("Hue Service"), _("Scene deleted"))
                else:
                    xbmc.log(f"[script.service.hue] Scene not deleted: {result}")
                    notification(_("Hue Service"), _("ERROR: Scene not deleted"))

    def select_hue_lights(self):
        try:
            hue_lights = self.bridge.lights()
        except QhueException as exc:
            xbmc.log(f"[script.service.hue]: Select Hue Lights QhueException: {exc.type_id}: {exc.message} {traceback.format_exc()}")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            return None
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] Requests exception: {exc}")
            notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            return None

        items = []
        index = []
        light_ids = []

        for light in hue_lights:
            h_light = hue_lights[light]
            h_light_name = h_light['name']

            # xbmc.log("[script.service.hue] In selectHueGroup: {}, {}".format(hgroup,name))
            index.append(light)
            items.append(xbmcgui.ListItem(label=h_light_name))

        selected = xbmcgui.Dialog().multiselect(_("Select Hue Lights..."), items)
        if selected:
            # id = index[selected]
            for s in selected:
                light_ids.append(index[s])

        xbmc.log(f"[script.service.hue] light_ids: {light_ids}")

        if light_ids:
            return light_ids
        return None

    def select_hue_scene(self):
        xbmc.log("[script.service.hue] In selectHueScene{}")

        try:
            hue_scenes = self.bridge.scenes()
        except QhueException as exc:
            xbmc.log(f"[script.service.hue]: Select Hue Lights QhueException: {exc.type_id}: {exc.message} {traceback.format_exc()}")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            reporting.process_exception(exc)
            return None
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] Requests exception: {exc}")
            notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            return None

        items = []
        index = []
        selected_id = -1

        for scene in hue_scenes:

            h_scene = hue_scenes[scene]
            h_scene_name = h_scene['name']

            if h_scene['version'] == 2 and h_scene["recycle"] is False and h_scene["type"] == "LightScene":
                index.append(scene)
                items.append(xbmcgui.ListItem(label=h_scene_name))

        selected = xbmcgui.Dialog().select("Select Hue scene...", items)
        if selected > -1:
            selected_id = index[selected]
            h_scene_name = hue_scenes[selected_id]['name']
            xbmc.log(f"[script.service.hue] In selectHueScene: selected: {selected}")

        if selected > -1:
            return selected_id, h_scene_name
        return None

    def get_daylight(self):
        try:
            daylight = self.bridge.sensors['1']()['state']['daylight']
        except QhueException as exc:
            xbmc.log(f"[script.service.hue]: Get Daylight Qhue Exception: {exc.type_id}: {exc.message} {traceback.format_exc()}")
            reporting.process_exception(exc)
            return
        return daylight

    def _get_light_name(self, light):
        try:
            name = self.bridge.lights()[light]['name']
        except (qhue.QhueException, requests.RequestException) as exc:
            xbmc.log(f"[script.service.hue] getLightName Qhue Exception: {exc} {traceback.format_exc()}")
            return None

        if name is None:
            return None
        return name
