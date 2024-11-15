#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


from threading import Thread
from concurrent.futures import ThreadPoolExecutor

import xbmc
import xbmcgui
from PIL import Image

from . import ADDON, MINIMUM_COLOR_DISTANCE, imageprocess, lightgroup
from . import PROCESS_TIMES, reporting, AMBI_RUNNING
from .kodiutils import notification, log
from .language import get_string as _
from .lightgroup import STATE_STOPPED, STATE_PAUSED, STATE_PLAYING, VIDEO
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(lightgroup.LightGroup):
    def __init__(self, light_group_id, settings_monitor, bridge):

        self.bridge = bridge
        self.light_group_id = light_group_id
        self.settings_monitor = settings_monitor
        super().__init__(light_group_id, VIDEO, self.settings_monitor, self.bridge)

        self.capacity_error_count = 0
        self.saved_light_states = {}
        self.ambi_lights = {}

        self.image_process = imageprocess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)  # Gamut doesn't matter for this usage




        # convert MS to seconds

    def onAVStarted(self):
        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled", False)

        if getattr(self.settings_monitor, f"group{self.light_group_id}_enabled", False) and self.bridge.connected:
            self._get_lights()
        else:
            return

        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")


        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] onPlaybackStarted. media_type: {self.media_type} == playback_type: {self._playback_type()}")
        if self.media_type == self._playback_type() and self._playback_type() == VIDEO:
            try:
                self.info_tag = self.getVideoInfoTag()
            except (AttributeError, TypeError) as x:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup{self.light_group_id}: OnAV Started: Can't read infoTag")
                reporting.process_exception(x)
        else:
            self.info_tag = None

        if self.activation_check.validate():
            log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Running Play action")

            # Start the Ambi loop
            ambi_loop_thread = Thread(target=self._ambi_loop, name="_ambi_loop", daemon=True)
            ambi_loop_thread.start()

    def onPlayBackStopped(self):
        # always stop ambilight even if group is disabled or it'll run forever
        log(f"[SCRIPT.SERVICE.HUE] In ambiGroup[{self.light_group_id}], onPlaybackStopped()")
        self.state = STATE_STOPPED
        AMBI_RUNNING.clear()

    def onPlayBackPaused(self):
        # always stop ambilight even if group is disabled or it'll run forever
        log(f"[SCRIPT.SERVICE.HUE] In ambiGroup[{self.light_group_id}], onPlaybackPaused()")
        self.state = STATE_PAUSED
        AMBI_RUNNING.clear()

    def _ambi_loop(self):
        AMBI_RUNNING.set()
        executor = ThreadPoolExecutor(max_workers=len(self.ambi_lights) * 2)
        cap = xbmc.RenderCapture()
        cap_image = bytes
        log("[SCRIPT.SERVICE.HUE] _ambiLoop started")
        aspect_ratio = cap.getAspectRatio()

        # These settings require restarting ambilight video to update:
        capture_size_x = getattr(self.settings_monitor, f"group{self.light_group_id}_capture_size")
        transition_time = getattr(self.settings_monitor, f"group{self.light_group_id}_transition_time")
        min_bri = getattr(self.settings_monitor, f"group{self.light_group_id}_min_bri")
        max_bri = getattr(self.settings_monitor, f"group{self.light_group_id}_max_bri")
        saturation = getattr(self.settings_monitor, f"group{self.light_group_id}_saturation")
        update_interval = getattr(self.settings_monitor, f"group{self.light_group_id}_update_interval")

        capture_size_y = int(capture_size_x / aspect_ratio)
        expected_capture_size = capture_size_x * capture_size_y * 4  # size * 4 bytes - RGBA

        log(f"[SCRIPT.SERVICE.HUE] aspect_ratio: {aspect_ratio}, Capture Size: ({capture_size_x}, {capture_size_y}), expected_capture_size: {expected_capture_size}")

        cap.capture(capture_size_x, capture_size_y)  # start the capture process https://github.com/xbmc/xbmc/pull/8613#issuecomment-165699101

        for L in list(self.ambi_lights):
            self.ambi_lights[L].update(prev_xy=(0.0001, 0.0001))

        while not self.settings_monitor.abortRequested() and AMBI_RUNNING.is_set() and self.bridge.connected:  # loop until kodi tells add-on to stop or video playing flag is unset.
            try:

                cap_image = cap.getImage()  # timeout to wait for OS in ms, default 1000

                if cap_image is None or len(cap_image) < expected_capture_size:
                    log("[SCRIPT.SERVICE.HUE] capImage is none or < expected. captured: {}, expected: {}".format(len(cap_image), expected_capture_size))
                    self.settings_monitor.waitForAbort(0.25)  # pause before trying again
                    continue  # no image captured, try again next iteration
                image = Image.frombytes("RGBA", (capture_size_x, capture_size_y), bytes(cap_image), "raw", "BGRA", 0, 1)  # Kodi always returns a BGRA image.

            except ValueError:
                log(f"[SCRIPT.SERVICE.HUE] capImage: {len(cap_image)}")
                log("[SCRIPT.SERVICE.HUE] Value Error")
                self.settings_monitor.waitForAbort(0.25)
                continue  # returned capture is smaller than expected, but this happens when player is stopping so fail silently. give up this loop.

            colors = self.image_process.img_avg(image, min_bri, max_bri, saturation)
            for L in list(self.ambi_lights):
                executor.submit(self._update_hue_rgb, colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], L, colors['bri'], transition_time)

            self.settings_monitor.waitForAbort(update_interval)  # seconds

        executor.shutdown(wait=False) #stop _update_hue_rgb thread(s)

        if not self.settings_monitor.abortRequested():  # ignore writing average process time if Kodi is shutting down
            average_process_time = self._perf_average(PROCESS_TIMES)
            log(f"[SCRIPT.SERVICE.HUE] Average process time: {average_process_time}")
            ADDON.setSettingString("average_process_time", str(average_process_time))
            log("[SCRIPT.SERVICE.HUE] _ambiLoop stopped")

    def _update_hue_rgb(self, r, g, b, light, bri, transition_time):
        gamut = self.ambi_lights[light].get('gamut')
        prev_xy = self.ambi_lights[light].get('prev_xy')

        if gamut == "A":
            xy = self.converterA.rgb_to_xy(r, g, b)
        elif gamut == "B":
            xy = self.converterB.rgb_to_xy(r, g, b)
        else:
            xy = self.converterC.rgb_to_xy(r, g, b)

        xy = round(xy[0], 4), round(xy[1], 4)  # Hue has a max precision of 4 decimal points
        distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(prev_xy[0], prev_xy[1]))  # only update hue if XY changed enough

        if distance > MINIMUM_COLOR_DISTANCE:
            request_body = {
                'type': 'light',
                'on': {
                    'on': True
                },
                'dimming': {
                    'brightness': bri
                },
                'color': {
                    'xy': {
                        'x': xy[0],
                        'y': xy[1]
                    }
                },
                'dynamics': {
                    'duration': int(transition_time)
                }
            }
            response = self.bridge.make_api_request('PUT', f'light/{light}', json=request_body)

            if response is not None:
                self.ambi_lights[light].update(prev_xy=xy)
            elif response == 429 or response == 500:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] _update_hue_rgb: {response}: Too Many Requests. Aborting request.")
                self.bridge_capacity_error()
                notification(_("Hue Service"), _("Bridge overloaded, stopping ambilight"), icon=xbmcgui.NOTIFICATION_ERROR)
            elif response == 404:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Not Found")
                AMBI_RUNNING.clear()
                notification(header=_("Hue Service"), message=_(f"ERROR: Light not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)
                AMBI_RUNNING.clear()  # shut it down
            else:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] RequestException Hue call fail")
                AMBI_RUNNING.clear()  # shut it down
                reporting.process_exception(response)

    def bridge_capacity_error(self):
        self.capacity_error_count = self.capacity_error_count + 1  # increment counter
        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Bridge capacity error count: {self.capacity_error_count}")
        if self.capacity_error_count > 50 and self.settings_monitor.show500errors:
            AMBI_RUNNING.clear()  # shut it down
            stop_showing_error = xbmcgui.Dialog().yesno(_("Hue Bridge over capacity"), _("The Hue Bridge is over capacity. Increase refresh rate or reduce the number of Ambilights."), yeslabel=_("Do not show again"), nolabel=_("Ok"))
            if stop_showing_error:
                ADDON.setSettingBool("show500Error", False)
            self.capacity_error_count = 0

    @staticmethod
    def _get_light_gamut(bridge, light):
        gamut = "C"  # default
        light_data = bridge.make_api_request("GET", f"light/{light}")
        if light_data == 404:
            log(f"[SCRIPT.SERVICE.HUE] _get_light_gamut: Light[{light}] not found or ID invalid")
            return 404
        elif light_data is not None and 'data' in light_data:
            for item in light_data['data']:
                if 'color' in item and 'gamut_type' in item['color']:
                    gamut = item['color']['gamut_type']
        if gamut not in ["A", "B", "C"]:
            gamut = "C"  # default to C if unknown gamut type
        return gamut

    @staticmethod
    def _perf_average(process_times):
        process_times = list(process_times)
        size = len(process_times)
        total = 0
        if size > 0:
            for x in process_times:
                total += x
            average_process_time = int(total / size * 1000)
            return f"{average_process_time} ms"
        return _("Unknown")

    def _get_and_save_light_states(self):
        response = self.bridge.make_api_request('GET', 'lights')
        if response is not None and 'data' in response:
            states = {}
            for light in response['data']:
                states[light['id']] = {
                    'on': light['on']['on'],
                    'brightness': light['dimming']['brightness'],
                    'color': light['color']['xy'],
                    'color_temperature': light['color_temperature']['mirek'] if 'mirek' in light['color_temperature'] else None,
                    'dynamics': light['dynamics']['status'],
                    'dynamics_speed': light['dynamics']['speed'],
                    'effects': light['effects']['status'],
                }
            return states
        else:
            log(f"[SCRIPT.SERVICE.HUE] Failed to get light states.")
            return None

    def _resume_all_light_states(self, states):
        for light_id, state in states.items():
            data = {
                "type": "light",
                "on": {"on": state['on']},
                "dimming": {"brightness": state['brightness']},
                "color": {"xy": state['color']},
                "dynamics": {
                    "status": state['dynamics'],
                    "speed": state['dynamics_speed']
                },
                "effects": {"status": state['effects']}
            }
            if state['color_temperature'] is not None:
                data["color_temperature"] = {"mirek": state['color_temperature']}
            response = self.bridge.make_api_request('PUT', f'lights/{light_id}', json=data)
            if response is not None:
                log(f"[SCRIPT.SERVICE.HUE] Light[{light_id}] state resumed successfully.")
            else:
                log(f"[SCRIPT.SERVICE.HUE] Failed to resume Light[{light_id}] state.")

    def _get_lights(self):
        index = 0
        lights = getattr(self.settings_monitor, f"group{self.light_group_id}_lights")
        if len(lights) > 0:
            for L in lights:
                gamut = self._get_light_gamut(self.bridge, L)
                if gamut == 404:
                    notification(header=_("Hue Service"), message=_(f"ERROR: Light not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)
                    AMBI_RUNNING.clear()
                    ADDON.setSettingString(f"group{self.light_group_id}_Lights", "-1")
                    ADDON.setSettingString(f"group{self.light_group_id}_LightNames", _("Not selected"))
                else:
                    light = {L: {'gamut': gamut, 'prev_xy': (0, 0), "index": index}}
                    self.ambi_lights.update(light)
                    index = index + 1
        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Lights: {self.ambi_lights}")