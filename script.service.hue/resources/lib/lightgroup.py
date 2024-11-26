#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.
import inspect
from datetime import datetime

import xbmc
import xbmcgui

from . import ADDON, reporting
from .kodiutils import notification, cache_get, log
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 0
AUDIO = 1


class LightGroup(xbmc.Player):
    def __init__(self, light_group_id, media_type, settings_monitor, bridge=None):
        self.light_group_id = light_group_id
        self.state = STATE_STOPPED
        self.media_type = media_type
        self.info_tag = None
        self.last_media_type = self.media_type
        self.settings_monitor = settings_monitor

        self.activation_check = ActivationChecker(self)
        self.bridge = bridge

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Initialized {self}")

        super().__init__()

    def onAVStarted(self):

        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        play_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_play_enabled")
        play_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_play_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not play_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] play action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        else:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStarted. play_behavior: {play_enabled}, media_type: {self.media_type} == playback_type: {self._playback_type()}")
            if self.media_type == self._playback_type() and self._playback_type() == VIDEO:
                try:
                    self.info_tag = self.getVideoInfoTag()
                except (AttributeError, TypeError) as x:
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup{self.light_group_id}: OnAV Started: Can't read VideoInfoTag")
                    reporting.process_exception(x)
            elif play_enabled and self.media_type == self._playback_type() and self._playback_type() == AUDIO:
                try:
                    self.info_tag = self.getMusicInfoTag()
                except (AttributeError, TypeError) as x:
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup{self.light_group_id}: OnAV Started: Can't read AudioInfoTag")
                    reporting.process_exception(x)

            if self.activation_check.validate(play_scene):
                contents = inspect.getmembers(self.info_tag)
                log(f"[SCRIPT.SERVICE.HUE] Start InfoTag: {contents}")

                #log(f"[SCRIPT.SERVICE.HUE] InfoTag: {self.info_tag}, {self.info_tag.getDuration()}")
                log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Play action")
                self.run_action("play")

    def onPlayBackPaused(self):
        self.state = STATE_PAUSED
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        pause_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_enabled")
        pause_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackPaused. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not pause_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Pause action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        else:

            if self.media_type == self._playback_type():
                if self.activation_check.validate(pause_scene):
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Pause action")
                    self.run_action("pause")

    def onPlayBackStopped(self):
        self.state = STATE_STOPPED
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        stop_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_enabled")
        stop_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStopped. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not stop_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Pause action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        else:
            if self.media_type == self.last_media_type or self.media_type == self._playback_type():

                if self.activation_check.validate(stop_scene):
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Stop action")
                    self.run_action("stop")

    def onPlayBackResumed(self):
        # log("[SCRIPT.SERVICE.HUE] In LightGroup[{}], onPlaybackResumed()".format(self.light_group_id))
        self.onAVStarted()

    def onPlayBackError(self):
        # log("[SCRIPT.SERVICE.HUE] In LightGroup[{}], onPlaybackError()".format(self.light_group_id))
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        # log("[SCRIPT.SERVICE.HUE] In LightGroup[{}], onPlaybackEnded()".format(self.light_group_id))
        self.onPlayBackStopped()

    def run_action(self, action):
        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}], run_action({action})")
        service_enabled = cache_get("service_enabled")

        if service_enabled and self.bridge.connected:
            if action == "play":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_play_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_play_transition")

            elif action == "pause":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_transition")

            elif action == "stop":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_transition")

            else:
                log(f"[SCRIPT.SERVICE.HUE] Unknown action type: {action}")
                raise RuntimeError
            try:
                if self.bridge.recall_scene(scene, duration) == 404:  # scene not found, clear settings and display error message
                    ADDON.setSettingBool(f"group{self.light_group_id}_{action}Behavior", False)
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneName", "Not Selected")
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneID", "-1")
                    log(f"[SCRIPT.SERVICE.HUE] Scene {scene} not found - group{self.light_group_id}_{action}Behavior ")
                    notification(header=_("Hue Service"), message=_("ERROR: Scene not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)


                else:
                    log(f"[SCRIPT.SERVICE.HUE] Scene {scene} recalled")

            except Exception as exc:
                reporting.process_exception(exc)
        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] run_action({action}), service_enabled: {service_enabled}, bridge_connected: {self.bridge.connected}")

    def activate(self):
        log(f"[SCRIPT.SERVICE.HUE] Activate group [{self.light_group_id}]. State: {self.state}")
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing. eg. Don't turn lights on when stopped
            log(f"[SCRIPT.SERVICE.HUE] Activate group [{self.light_group_id}]. playback stopped, doing nothing. ")

    def _playback_type(self):
        if self.isPlayingVideo():
            media_type = VIDEO
        elif self.isPlayingAudio():
            media_type = AUDIO
        else:
            media_type = None
        return media_type


class ActivationChecker:
    def __init__(self, light_group: LightGroup):
        self.settings_monitor = light_group.settings_monitor
        self.light_group = light_group
        self.light_group_id = light_group.light_group_id

    def _video_activation_rules(self):
        # fetch settings
        minimum_duration = self.settings_monitor.minimum_duration

        movie_setting = self.settings_monitor.movie_setting
        episode_setting = self.settings_monitor.episode_setting
        music_video_setting = self.settings_monitor.music_video_setting
        pvr_setting = self.settings_monitor.pvr_setting
        other_setting = self.settings_monitor.other_setting

        # Fetch video info tag
        info_tag = self.light_group.info_tag
        # Get duration in minutes
        duration = info_tag.getDuration() / 60
        # Get media type and file name
        media_type = info_tag.getMediaType()
        file_name = info_tag.getFile()
        if not file_name and self.light_group.isPlayingVideo():
            file_name = self.light_group.getPlayingFile()

        # Check if file is a PVR file
        is_pvr = file_name[0:3] == "pvr"

        # Log settings and values
        log(f"[SCRIPT.SERVICE.HUE] _video_activation_rules settings:   minimum_duration: {minimum_duration}, movie_setting: {movie_setting}, episode_setting: {episode_setting}, music_video_setting: {music_video_setting}, pvr_setting: {pvr_setting}, other_setting: {other_setting}")
        log(f"[SCRIPT.SERVICE.HUE] _video_activation_rules values: duration: {duration}, is_pvr: {is_pvr}, media_type: {media_type}, file_name: {file_name}")

        # Check if media type matches settings
        media_type_match = ((movie_setting and media_type == "movie") or
                            (episode_setting and media_type == "episode") or
                            (music_video_setting and media_type == "MusicVideo") or
                            (pvr_setting and is_pvr) or
                            (other_setting and media_type not in ["movie", "episode", "MusicVideo"] and not is_pvr))

        if duration >= minimum_duration and media_type_match:
            log("[SCRIPT.SERVICE.HUE] _video_activation_rules activation: True")
            return True

        log("[SCRIPT.SERVICE.HUE] _video_activation_rules activation: False")
        return False

    def _is_within_schedule(self):
        # Check if daylight disable setting is on
        if self.settings_monitor.daylight_disable:
            # Fetch daytime status
            daytime = cache_get("daytime")
            # Check if it's daytime
            if daytime:
                log("[SCRIPT.SERVICE.HUE] Disabled by daytime")
                return False

        schedule_enabled = self.settings_monitor.schedule_enabled
        schedule_start = self.settings_monitor.schedule_start
        schedule_end = self.settings_monitor.schedule_end

        # Check if schedule setting is enabled
        if schedule_enabled:
            log(f"[SCRIPT.SERVICE.HUE] Schedule enabled: {schedule_enabled}, start: {schedule_start}, end: {schedule_end}")
            log(f"[SCRIPT.SERVICE.HUE] Schedule enabled: {schedule_enabled}, start: {schedule_start}, end: {schedule_end}")
            # Check if current time is within start and end times
            if schedule_start < datetime.now().time() < schedule_end:
                log("[SCRIPT.SERVICE.HUE] _is_within_schedule: True, Enabled by schedule")
                return True
            else:
                log("[SCRIPT.SERVICE.HUE] _is_within_schedule. False, Not within schedule")
                return False

        # If schedule is not enabled, always return True
        log("[SCRIPT.SERVICE.HUE] _is_within_schedule: True, Schedule not enabled")
        return True

    def _check_any_lights_on(self, scene_id, all_light_states):
        """ Checks if ANY light in the current scene is on"""

        # Find the current scene from the scene data
        current_scene = next((scene for scene in self.light_group.bridge.scene_data['data'] if scene['id'] == scene_id), None)
        if not current_scene:
            log("[SCRIPT.SERVICE.HUE] _is_scene_already_active: Current scene not found in scene data")
            return False

        # Check if any light in the current scene is on
        for action in current_scene['actions']:
            light_id = action['target']['rid']
            light_state = next((state for state in all_light_states['data'] if state['id'] == light_id), None)
            if light_state and 'on' in light_state and light_state['on']['on']:
                log(f"[SCRIPT.SERVICE.HUE] _is_scene_already_active: Light {light_id} in the scene is on")
                return True

        log("[SCRIPT.SERVICE.HUE] _is_scene_already_active: No lights in the scene are on")
        return False

    def _check_all_lights_off(self, scene_id, all_light_states):
        """ Checks if ALL the lights in the given scene are off"""
        # Find the current scene from the scene data
        current_scene = next((scene for scene in self.light_group.bridge.scene_data['data'] if scene['id'] == scene_id), None)
        if not current_scene:
            log("[SCRIPT.SERVICE.HUE] _is_any_light_off: Current scene not found in scene data")
            return False

        # Check if any light in the current scene is on
        for action in current_scene['actions']:
            light_id = action['target']['rid']
            light_state = next((state for state in all_light_states['data'] if state['id'] == light_id), None)
            if light_state and 'on' in light_state and light_state['on']['on']:
                log(f"[SCRIPT.SERVICE.HUE] _check_all_lights_off: Light {light_id} in the scene is on")
                return True
        log(f"[SCRIPT.SERVICE.HUE] _check_all_lights_off: All in scene {scene_id} are off")
        return False

    def validate(self, scene=None):
        # fetch settings

        skip_time_check_if_light_on = self.settings_monitor.skip_time_check_if_light_on
        skip_scene_if_all_off = self.settings_monitor.skip_scene_if_all_off

        log(f"[SCRIPT.SERVICE.HUE] Validate Activation LightGroup[{self.light_group_id}] Scene: {scene}, media_type: {self.light_group.media_type}, skip_time_check_if_light_on: {skip_time_check_if_light_on}, skip_scene_if_all_off: {skip_scene_if_all_off}")

        all_light_states = None
        if scene and (skip_time_check_if_light_on or skip_scene_if_all_off):
            # Fetch all light states
            all_light_states = self.light_group.bridge.make_api_request("GET", "light")
            # log(f"[SCRIPT.SERVICE.HUE] validate: all_light_states {all_light_states}")

        if self.light_group.media_type == VIDEO and scene:
            # Check video activation rules with a Scene
            if skip_scene_if_all_off and not self._check_all_lights_off(scene, all_light_states):
                log("[SCRIPT.SERVICE.HUE] Validate video: All lights are off, not activating scene")
                return False
            elif (skip_time_check_if_light_on and self._check_any_lights_on(scene, all_light_states)) and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate video: Some lights are on, skipping schedule check")
                return True
            elif self._is_within_schedule() and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate video: Scene selected, within schedule and video activation rules, activate")
                return True

            log("[SCRIPT.SERVICE.HUE] Validate Video: No valid checks passed, not activating scene")
            return False

        elif self.light_group.media_type == VIDEO:
            # if no scene is set, use the default activation. This is the case for ambilight.
            if self._is_within_schedule() and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate Video: No scene selected, within schedule and video activation rules: activate")
                return True
            else:
                log("[SCRIPT.SERVICE.HUE] Validate Video: No scene selected, not within schedule or activation rules, ignoring")
                return False

        elif self.light_group.media_type == AUDIO and scene:
            # Check audio activation rules
            if skip_scene_if_all_off and not skip_scene_if_all_off(scene, all_light_states):
                log("[SCRIPT.SERVICE.HUE] Validate Audio: All lights are off, not activating scene")
                return False
            elif (skip_time_check_if_light_on and self._check_any_lights_on(scene, all_light_states)):
                log("[SCRIPT.SERVICE.HUE] Validate Audio: A light in the scene is on, activating scene")
                return True
            elif self._is_within_schedule():
                log("[SCRIPT.SERVICE.HUE] Validate Audio: Within schedule, activating scene")
                return True
            log("[SCRIPT.SERVICE.HUE] Validate Audio: Checks not passed, not activating")
            return False
