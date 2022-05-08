#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import json
import traceback
from datetime import timedelta
from json import JSONDecodeError
from socket import getfqdn

import requests
import xbmc
import xbmcgui
import qhue

from resources.lib import ADDON, QHUE_TIMEOUT, SETTINGS_CHANGED, reporting, CONNECTED
from resources.lib import ADDONID, CACHE

from .language import get_string as _
from qhue import QhueException
from .settings import validate_settings


def create_hue_scene(bridge):
    xbmc.log("[script.service.hue] In kodiHue createHueScene")
    scenes = bridge.scenes

    xbmcgui.Dialog().ok(heading=_("Create New Scene"), message=_("Adjust lights to desired state in the Hue App to save as new scene.[CR]Set a fade time in seconds, or 0 for an instant transition."))

    scene_name = xbmcgui.Dialog().input(_("Scene Name"))

    if scene_name:
        try:
            transition_time = int(xbmcgui.Dialog().numeric(0, _("Fade Time (Seconds)"), defaultt="10")) * 10  # yes, default with two ts. *10 to convert secs to msecs
        except ValueError:
            transition_time = 0

        if transition_time > 65534:  # hue uses uint16 for transition time, so set a max
            transition_time = 65534
        selected = select_hue_lights(bridge)

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


def delete_hue_scene(bridge):
    xbmc.log("[script.service.hue] In kodiHue deleteHueScene")
    scene = select_hue_scene(bridge)
    if scene is not None:
        confirm = xbmcgui.Dialog().yesno(heading=_("Delete Hue Scene"), message=_(f"Are you sure you want to delete this scene:[CR][B]{scene[1]}[/B]"))
        if confirm:
            scenes = bridge.scenes
            try:
                result = scenes[scene[0]](http_method='delete')
            except QhueException as exc:
                xbmc.log(f"[script.service.hue]: Delete Hue Scene QhueException: {exc.type_id}: {exc.message} {traceback.format_exc()}")
                notification(_("Hue Service"), _("ERROR: Scene not deleted") + f"[CR]{exc.message}")
            # xbmc.log(f"[script.service.hue] In kodiHue createHueGroup. Res: {result}")
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue]: Delete Hue Scene requestsException: {result} {exc}")
                notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            if result[0]["success"]:
                notification(_("Hue Service"), _("Scene deleted"))
            else:
                xbmc.log(f"[script.service.hue] Scene not deleted: {result}")
                notification(_("Hue Service"), _("ERROR: Scene not deleted"))


def _discover_nupnp():
    xbmc.log("[script.service.hue] In kodiHue discover_nupnp()")
    try:
        req = requests.get('https://discovery.meethue.com/')
        result = req.json()
    except requests.RequestException as error:
        xbmc.log(f"[script.service.hue] Nupnp failed: {error}")
        return None
    except JSONDecodeError as error:
        xbmc.log(f"[script.service.hue] Nupnp failed: {error}, req: {req}")
        reporting.process_exception(req, "critical", req)
        return None

    bridge_ip = None
    if result:
        bridge_ip = result[0]["internalipaddress"]
    return bridge_ip


def discover_bridge(monitor):
    xbmc.log("[script.service.hue] Start bridgeDiscover")
    # Create new config if none exists. Returns success or fail as bool
    ADDON.setSettingString("bridgeIP", "")
    ADDON.setSettingString("bridgeUser", "")
    CONNECTED.clear()

    progress_bar = xbmcgui.DialogProgress()
    progress_bar.create(_('Searching for bridge...'))
    progress_bar.update(5, _("Discovery started"))

    complete = False
    while not progress_bar.iscanceled() and not complete and not monitor.abortRequested():

        progress_bar.update(percent=10, message=_("N-UPnP discovery..."))
        bridge_ip = _discover_nupnp()

        if _connection_test(bridge_ip):
            progress_bar.update(percent=100, message=_("Found bridge: ") + bridge_ip)
            monitor.waitForAbort(1)

            bridge_user = _create_user(monitor, bridge_ip, progress_bar)

            if bridge_user:
                xbmc.log(f"[script.service.hue] User created: {bridge_user}")
                progress_bar.update(percent=90, message=_("User Found![CR]Saving settings..."))

                ADDON.setSettingString("bridgeIP", bridge_ip)
                ADDON.setSettingString("bridgeUser", bridge_user)

                CONNECTED.set()
                progress_bar.update(percent=100, message=_("Complete!"))
                monitor.waitForAbort(5)
                progress_bar.close()
                xbmc.log("[script.service.hue] Bridge discovery complete")
                return True

            xbmc.log(f"[script.service.hue] User not created, received: {bridge_user}")
            progress_bar.update(percent=100, message=_("User not found[CR]Check your bridge and network."))
            monitor.waitForAbort(5)
            complete = True
            progress_bar.close()

        else:
            progress_bar.update(percent=100, message=_("Bridge not found[CR]Check your bridge and network."))
            xbmc.log("[script.service.hue] Bridge not found, check your bridge and network")
            monitor.waitForAbort(5)
            complete = True
            progress_bar.close()

    if progress_bar.iscanceled():
        xbmc.log("[script.service.hue] Bridge discovery cancelled by user")
        progress_bar.update(100, _("Cancelled"))
        progress_bar.close()


def _connection_test(bridge_ip):
    b = qhue.Resource(f"http://{bridge_ip}/api", requests.session())
    try:
        api_version = b.config()['apiversion']
    except QhueException as error:
        xbmc.log(f"[script.service.hue] Connection test failed.  {error.type_id}: {error.message} {traceback.format_exc()}")
        reporting.process_exception(error)
        return False
    except requests.RequestException as error:
        xbmc.log(f"[script.service.hue] Connection test failed.  {error}")
        return False
    except KeyError as error:
        notification(_("Hue Service"), _(f"Bridge API: {api_version}, update your bridge"), icon=xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"[script.service.hue] in ConnectionTest():  Connected! Bridge too old: {api_version}, error: {error}")
        return False

    api_split = api_version.split(".")

    if api_version and int(api_split[0]) >= 1 and int(api_split[1]) >= 38:  # minimum bridge version 1.38
        xbmc.log(f"[script.service.hue] Bridge Found! Hue API version: {api_version}")
        return True

    notification(_("Hue Service"), _(f"Bridge API: {api_version}, update your bridge"), icon=xbmcgui.NOTIFICATION_ERROR)
    xbmc.log(f"[script.service.hue] in ConnectionTest():  Connected! Bridge too old: {api_version}")
    return False


def _user_test(bridge_ip, bridge_user):
    xbmc.log("[script.service.hue] in ConnectionTest() Attempt initial connection")
    b = qhue.Bridge(bridge_ip, bridge_user, timeout=QHUE_TIMEOUT)
    try:
        zigbee = b.config()['zigbeechannel']
    except (requests.RequestException, qhue.QhueException, KeyError):
        return False

    if zigbee:
        xbmc.log(f"[script.service.hue] Hue User Authorized. Bridge Zigbee Channel: {zigbee}")
        return True
    return False


def _discover_bridge_ip():
    # discover hue bridge IP silently for non-interactive discovery / bridge IP change.
    xbmc.log("[script.service.hue] In discoverBridgeIP")
    bridge_ip = _discover_nupnp()
    if _connection_test(bridge_ip):
        return bridge_ip

    return False


def _create_user(monitor, bridge_ip, progress_bar=False):
    xbmc.log("[script.service.hue] In createUser")
    # devicetype = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn())  # Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    req = requests
    res = 'link button not pressed'
    time = 0
    timeout = 90
    progress = 0

    if progress_bar:
        progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))  # press link button on bridge

    while 'link button not pressed' in res and time <= timeout and not monitor.abortRequested() and not progress_bar.iscanceled():
        # xbmc.log(f"[script.service.hue] In create_user: abortRequested: {str(monitor.abortRequested())}, timer: {time}")

        if progress_bar:
            progress_bar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))  # press link button on bridge

        try:
            req = requests.post(f'http://{bridge_ip}/api', data=data)
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] requests exception: {exc}")
            return False

        res = req.text
        monitor.waitForAbort(1)
        time = time + 1
        progress = int((time / timeout) * 100)

    res = req.json()
    xbmc.log(f"[script.service.hue] json response: {res}, content: {req.content}")

    try:
        username = res[0]['success']['username']
        return username
    except requests.RequestException as exc:
        xbmc.log(f"[script.service.hue] Username Requests exception: {exc}")
        return False
    except KeyError as exc:
        xbmc.log(f"[script.service.hue] Username not found: {exc}")
        return False


def configure_scene(bridge, group_id, action):
    scene = select_hue_scene(bridge)
    if scene is not None:
        # group0_startSceneID
        ADDON.setSettingString(f"group{group_id}_{action}SceneID", scene[0])
        ADDON.setSettingString(f"group{group_id}_{action}SceneName", scene[1])
        ADDON.openSettings()


def configure_ambilights(bridge, group_id):
    lights = select_hue_lights(bridge)
    light_names = []
    color_lights = []
    if lights is not None:
        for L in lights:
            light_names.append(_get_light_name(bridge, L))
            color_lights.append(L)

        ADDON.setSettingString(f"group{group_id}_Lights", ','.join(color_lights))
        ADDON.setSettingString(f"group{group_id}_LightNames", ', '.join(light_names))
        ADDON.setSettingBool(f"group{group_id}_enabled", True)
        ADDON.openSettings()


def _get_light_name(bridge, L):
    try:
        name = bridge.lights()[L]['name']
    except (qhue.QhueException, requests.RequestException) as exc:
        xbmc.log(f"[script.service.hue] getLightName Qhue Exception: {exc} {traceback.format_exc()}")
        return None

    if name is None:
        return None
    return name


def select_hue_lights(bridge):
    try:
        hue_lights = bridge.lights()
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


def select_hue_scene(bridge):
    xbmc.log("[script.service.hue] In selectHueScene{}")

    try:
        hue_scenes = bridge.scenes()
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


def get_daylight(bridge):
    try:
        daylight = bridge.sensors['1']()['state']['daylight']
    except QhueException as exc:
        xbmc.log(f"[script.service.hue]: Get Daylight Qhue Exception: {exc.type_id}: {exc.message} {traceback.format_exc()}")
        reporting.process_exception(exc)
        return
    return daylight


def activate(light_groups, ambi_group=None):
    """
    Activates play action as appropriate for all groups. Used at sunset and when service is re-nabled via Actions.
    """
    xbmc.log(f"[script.service.hue] Activating scenes: light_groups: {light_groups} ambigroup: {ambi_group}")

    for g in light_groups:
        xbmc.log(f"[script.service.hue] in activate g: {g}, light_group_id: {g.light_group_id}")
        if ADDON.getSettingBool(f"group{g.light_group_id}_enabled"):
            g.activate()

    if ADDON.getSettingBool("group3_enabled") and ambi_group:
        ambi_group.activate()


def connect_bridge(silent=False):
    bridge_ip = ADDON.getSettingString("bridgeIP")
    bridge_user = ADDON.getSettingString("bridgeUser")
    xbmc.log(f"[script.service.hue] in Connect() with settings: bridgeIP: {bridge_ip}, bridgeUser: {bridge_user}")

    if bridge_ip and bridge_user:
        if not _connection_test(bridge_ip):
            xbmc.log("[script.service.hue] in Connect(): Bridge not responding to connection test, attempt finding a new bridge IP.")
            bridge_ip = _discover_bridge_ip()
            if bridge_ip:
                xbmc.log(f"[script.service.hue] in Connect(): New IP found: {bridge_ip}. Saving")
                ADDON.setSettingString("bridgeIP", bridge_ip)
            else:
                xbmc.log("[script.service.hue] Bridge not found")
                notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
                CONNECTED.clear()
                return None

        xbmc.log("[script.service.hue] in Connect(): Checking User")
        if _user_test(bridge_ip, bridge_user):
            bridge = qhue.Bridge(bridge_ip, bridge_user, timeout=QHUE_TIMEOUT)
            CONNECTED.set()
            xbmc.log(f"[script.service.hue] Successfully connected to Hue Bridge: {bridge_ip}")
            if not silent:
                notification(_("Hue Service"), _("Hue connected"), sound=False)
            return bridge
        else:
            xbmc.log("[script.service.hue] Bridge not responding")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            CONNECTED.clear()
            return None

    else:
        xbmc.log("[script.service.hue] Bridge not configured")
        notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
        CONNECTED.clear()
        return None


def check_bridge_model(bridge):
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
    if model == "BSB002":
        xbmc.log(f"[script.service.hue] Bridge model OK: {model}")
        return True
    xbmc.log(f"[script.service.hue] Unsupported bridge model: {model}")
    xbmcgui.Dialog().ok(_("Unsupported Hue Bridge"), _("Hue Bridge V1 (Round) is unsupported. Hue Bridge V2 (Square) is required."))
    return None


def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=False):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


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
