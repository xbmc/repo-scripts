#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


import xbmc
import xbmcgui

from . import ADDON, BRIDGE_SETTINGS_CHANGED
from .language import get_string as _
from .kodiutils import convert_time, notification, log


class SettingsMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self.ip = ADDON.getSetting("bridgeIP")
        self.key = ADDON.getSetting("bridgeUser")

        self.reload_settings()

    def onSettingsChanged(self):
        self.reload_settings()

    def reload_settings(self):
        log("[SCRIPT.SERVICE.HUE] Reloading settings...")
        old_ip = self.ip
        old_key = self.key

        # bridge
        self.ip = ADDON.getSetting("bridgeIP")
        self.key = ADDON.getSetting("bridgeUser")

        # If IP or key has changed, set flag so core loop knows to try reconnecting
        if (old_ip != self.ip or old_key != self.key) and self.ip and self.key:
            log(f"[SCRIPT.SERVICE.HUE] SettingsMonitor: Bridge settings changed: {self.ip} and {self.key}")
            BRIDGE_SETTINGS_CHANGED.set()

        self.show500error = ADDON.getSettingBool("show500Error")

        # scheduling settings

        self.daylight_disable = ADDON.getSettingBool("daylightDisable")
        self.force_on_sunset = ADDON.getSettingBool("forceOnSunset")
        self.morning_time = convert_time(ADDON.getSettingString("morningTime"))
        self.sunset_offset = ADDON.getSettingNumber("sunsetOffset")

        self.schedule_enabled = ADDON.getSettingBool("enableSchedule")
        self.schedule_start = convert_time(ADDON.getSettingString("startTime"))
        self.schedule_end = convert_time(ADDON.getSettingString("endTime"))

        # video activation settings
        self.minimum_duration = ADDON.getSettingInt("video_MinimumDuration")
        self.movie_setting = ADDON.getSettingBool("video_Movie")
        self.episode_setting = ADDON.getSettingBool("video_Episode")
        self.music_video_setting = ADDON.getSettingBool("video_MusicVideo")
        self.pvr_setting = ADDON.getSettingBool("video_PVR")
        self.other_setting = ADDON.getSettingBool("video_Other")
        self.skip_time_check_if_light_on = ADDON.getSettingBool('enable_if_already_active')
        self.skip_scene_if_all_off = ADDON.getSettingBool('keep_lights_off')

        # light group 0 (Video)
        self.group0_enabled = ADDON.getSettingBool("group0_enabled")

        self.group0_play_enabled = ADDON.getSettingBool("group0_playBehavior")
        self.group0_play_scene = ADDON.getSettingString("group0_playSceneID")
        self.group0_play_transition = int(ADDON.getSettingNumber("group0_playTransition") * 1000)  # Hue API v2 expects milliseconds (int), but we use seconds (float) in the settings because its precise enough and more user-friendly

        self.group0_pause_enabled = ADDON.getSettingBool("group0_pauseBehavior")
        self.group0_pause_scene = ADDON.getSettingString("group0_pauseSceneID")
        self.group0_pause_transition = int(ADDON.getSettingNumber("group0_pauseTransition") * 1000)

        self.group0_stop_enabled = ADDON.getSettingBool("group0_stopBehavior")
        self.group0_stop_scene = ADDON.getSettingString("group0_stopSceneID")
        self.group0_stop_transition = int(ADDON.getSettingNumber("group0_stopTransition") * 1000)

        # light group 1 (Music)
        self.group1_enabled = ADDON.getSettingBool("group1_enabled")

        self.group1_play_enabled = ADDON.getSettingBool("group1_playBehavior")
        self.group1_play_scene = ADDON.getSettingString("group1_playSceneID")
        self.group1_play_transition = int(ADDON.getSettingNumber("group1_playTransition") * 1000)  # Hue API v2 expects milliseconds (int), but we use seconds (float) in the settings because its precise enough and more user-friendly

        self.group1_pause_enabled = ADDON.getSettingBool("group1_pauseBehavior")
        self.group1_pause_scene = ADDON.getSettingString("group1_pauseSceneID")
        self.group1_pause_transition = int(ADDON.getSettingNumber("group1_pauseTransition") * 1000)

        self.group1_stop_enabled = ADDON.getSettingBool("group1_stopBehavior")
        self.group1_stop_scene = ADDON.getSettingString("group1_stopSceneID")
        self.group1_stop_transition = int(ADDON.getSettingNumber("group1_stopTransition") * 1000)

        # light group 3 / ambigroup
        self.group3_enabled = ADDON.getSettingBool("group3_enabled")
        self.group3_lights = ADDON.getSettingString("group3_Lights")
        self.group3_transition_time = int(ADDON.getSettingInt("group3_TransitionTime"))  # Stored as ms in Kodi settings.
        self.group3_min_bri = ADDON.getSettingInt("group3_MinBrightness")
        self.group3_max_bri = ADDON.getSettingInt("group3_MaxBrightness")
        self.group3_saturation = ADDON.getSettingNumber("group3_Saturation")
        self.group3_capture_size = ADDON.getSettingInt("group3_CaptureSize")
        self.group3_resume_state = ADDON.getSettingBool("group3_ResumeState")
        self.group3_resume_transition = ADDON.getSettingInt("group3_ResumeTransition") * 10  # convert seconds to multiple of 100ms
        self.group3_update_interval = ADDON.getSettingInt("group3_Interval") / 1000

        if self.group3_update_interval == 0: #Never allow a 0 value for update interval
            self.group3_update_interval = 0.1

        self.group3_lights = self.group3_lights.split(",") #split lights on comma

        log("[SCRIPT.SERVICE.HUE] SettingsMonitor: Settings loaded, validating")

        self._validate_schedule()
        self._validate_ambilight()

    def _validate_ambilight(self):
        log(f"[SCRIPT.SERVICE.HUE] Validate ambilight config. Enabled: {self.group3_enabled}, Lights: {type(self.group3_lights)} : {self.group3_lights}")
        if self.group3_enabled:
            if self.group3_lights == ["-1"]:
                ADDON.setSettingBool('group3_enabled', False)
                log('[SCRIPT.SERVICE.HUE] _validate_ambilights: No ambilights selected')
                notification(_('Hue Service'), _('No lights selected for Ambilight.'), icon=xbmcgui.NOTIFICATION_ERROR)

    def _validate_schedule(self):
        log(f"[SCRIPT.SERVICE.HUE] Validate schedule. Schedule Enabled: {self.schedule_enabled}, Start time: {self.schedule_start}, End time: {self.schedule_end}")
        if self.schedule_enabled:
            if self.schedule_start > self.schedule_end:  # checking if start time is after the end time
                ADDON.setSettingBool('EnableSchedule', False)
                log('[SCRIPT.SERVICE.HUE] _validate_schedule: Start time is after end time, schedule disabled')
                notification(_('Hue Service'), _('Invalid start or end time, schedule disabled'), icon=xbmcgui.NOTIFICATION_ERROR)
