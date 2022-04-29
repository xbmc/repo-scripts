#      Copyright (C) 2019-2021 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import datetime
import traceback

import requests
import xbmc
import xbmcgui
from qhue import QhueException

from resources.lib import CACHE, ADDON, reporting, hue, ADDONID
from resources.lib.settings import convert_time
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 0
AUDIO = 1


class LightGroup(xbmc.Player):
    def __init__(self, light_group_id, bridge, media_type, initial_state=STATE_STOPPED, video_info_tag=xbmc.InfoTagVideo):
        self.light_group_id = light_group_id
        self.bridge = bridge
        self.enabled = ADDON.getSettingBool(f"group{self.light_group_id}_enabled")

        self.start_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_startBehavior")
        self.start_scene = ADDON.getSettingString(f"group{self.light_group_id}_startSceneID")

        self.pause_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_pauseBehavior")
        self.pause_scene = ADDON.getSettingString(f"group{self.light_group_id}_pauseSceneID")

        self.stop_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_stopBehavior")
        self.stop_scene = ADDON.getSettingString(f"group{self.light_group_id}_stopSceneID")

        self.state = initial_state
        self.media_type = media_type
        self.video_info_tag = video_info_tag
        self.last_media_type = self.media_type
        self.lights = self.bridge.lights
        self.group0 = self.bridge.groups[0]

        super().__init__()

    def __repr__(self):
        return f"light_group_id: {self.light_group_id}, enabled: {self.enabled}, state: {self.state}"

    def onAVStarted(self):
        if self.enabled:
            xbmc.log(
                f"In KodiGroup[{self.light_group_id}], onPlaybackStarted. Group enabled: {self.enabled},startBehavior: {self.start_behavior} , isPlayingVideo: {self.isPlayingVideo()}, isPlayingAudio: {self.isPlayingAudio()}, self.mediaType: {self.media_type},self.playbackType(): {self.playback_type()}")
            self.state = STATE_PLAYING
            self.last_media_type = self.playback_type()

            if self.isPlayingVideo() and self.media_type == VIDEO:  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                try:
                    self.video_info_tag = self.getVideoInfoTag()
                except RuntimeError as exc:
                    xbmc.log(f"[script.service.hue] Get InfoTag Exception: {exc}")
                    reporting.process_exception(exc)
                    return
                # xbmc.log("[script.service.hue] InfoTag: {}".format(self.videoInfoTag))
                if not self.check_video_activation(self.video_info_tag):
                    return
            else:
                self.video_info_tag = None

            if (self.check_active_time() or self.check_already_active(self.start_scene)) and self.check_keep_lights_off_rule(self.start_scene) and self.start_behavior and self.media_type == self.playback_type():
                self.run_action("play")

    def onPlayBackPaused(self):
        if self.enabled:
            xbmc.log(f"[script.service.hue] In KodiGroup[{self.light_group_id}], onPlaybackPaused() , isPlayingVideo: {self.isPlayingVideo()}, isPlayingAudio: {self.isPlayingAudio()}")
            self.state = STATE_PAUSED

            if self.media_type == VIDEO and not self.check_video_activation(
                    self.video_info_tag):  # If video group, check video activation. Otherwise it's audio so we ignore this and continue
                return

            if (self.check_active_time() or self.check_already_active(self.pause_scene)) and self.check_keep_lights_off_rule(self.pause_scene) and self.pause_behavior and self.media_type == self.playback_type():
                self.last_media_type = self.playback_type()
                self.run_action("pause")

    def onPlayBackStopped(self):
        if self.enabled:
            xbmc.log(f"[script.service.hue] In KodiGroup[{self.light_group_id}], onPlaybackStopped() , mediaType: {self.media_type}, lastMediaType: {self.last_media_type} ")
            self.state = STATE_STOPPED

            try:
                if self.media_type == VIDEO and not self.check_video_activation(self.video_info_tag):  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                    return
            except AttributeError:
                xbmc.log("[script.service.hue] No videoInfoTag")

            if (self.check_active_time() or self.check_already_active(self.stop_scene)) and self.check_keep_lights_off_rule(self.stop_scene) and self.stop_behavior and self.media_type == self.last_media_type:
                self.run_action("stop")

    def onPlayBackResumed(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackResumed()".format(self.light_group_id))
        self.onAVStarted()

    def onPlayBackError(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackError()".format(self.light_group_id))
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackEnded()".format(self.light_group_id))
        self.onPlayBackStopped()

    def run_action(self, action):
        if action == "play":
            scene = self.start_scene
        elif action == "pause":
            scene = self.pause_scene
        elif action == "stop":
            scene = self.stop_scene
        else:
            xbmc.log(f"[script.service.hue] Unknown action type: {action}")
            raise RuntimeError
        try:
            self.group0.action(scene=scene)
        except QhueException as exc:
            xbmc.log(f"[script.service.hue] run_action: Hue call fail: {exc.type_id}: {exc.message} {traceback.format_exc()}")
            if "7" in exc.type_id:
                xbmc.log("[script.service.hue] Scene not found")
                hue.notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(exc)

    def activate(self):
        xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. State: {self.state}")
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing.
            xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. playback stopped, doing nothing. ")

    def playback_type(self):
        if self.isPlayingVideo():
            media_type = VIDEO
        elif self.isPlayingAudio():
            media_type = AUDIO
        else:
            media_type = None
        return media_type

    @staticmethod
    def check_active_time():
        service_enabled = CACHE.get(f"{ADDONID}.service_enabled")
        daylight = CACHE.get("script.service.hue.daylight")
        # xbmc.log("[script.service.hue] Schedule: {}, daylightDisable: {}, daylight: {}, startTime: {}, endTime: {}".format(ADDON.getSettingBool("enableSchedule"), ADDON.getSettingBool("daylightDisable"), daylight,
        #           ADDON.getSettingBool("startTime"), ADDON.getSettingBool("endTime")))

        if ADDON.getSettingBool("daylightDisable") and daylight:
            xbmc.log("[script.service.hue] Disabled by daylight")
            return False

        if service_enabled:
            if ADDON.getSettingBool("enableSchedule"):
                start = convert_time(ADDON.getSettingBool("startTime"))
                end = convert_time(ADDON.getSettingBool("endTime"))
                now = datetime.datetime.now().time()
                if (now > start) and (now < end):
                    # xbmc.log("[script.service.hue] Enabled by schedule")
                    return True
                # xbmc.log("[script.service.hue] Disabled by schedule")
                return False
            # xbmc.log("[script.service.hue] Schedule not enabled")
            return True

        # xbmc.log("[script.service.hue] Service disabled")
        return False

    def check_video_activation(self, info_tag):
        try:
            duration = info_tag.getDuration() / 60  # returns seconds, convert to minutes
            media_type = info_tag.getMediaType()
            file_name = info_tag.getFile()
            if not file_name and self.isPlayingVideo():
                file_name = self.getPlayingFile()
            #
            # if not fileName and previousFileName:
            #     fileName = previousFileName
            # elif fileName:
            #     previousFileName = fileName

            # xbmc.log("[script.service.hue] InfoTag contents: duration: {}, mediaType: {}, file: {}".format(duration, mediaType, fileName))
        except (AttributeError, TypeError) as exc:
            xbmc.log("[script.service.hue] Can't read infoTag {exc}")
            return False
        # xbmc.log("Video Activation settings({}): minDuration: {}, Movie: {}, Episode: {}, MusicVideo: {}, PVR : {}, Other: {}".format(self.light_group_id, settings_storage['videoMinimumDuration'], settings_storage['video_enableMovie'],
        #                settings_storage['video_enableEpisode'], settings_storage['video_enableMusicVideo'], settings_storage['video_enablePVR'], settings_storage['video_enableOther']))
        # xbmc.log("[script.service.hue] Video Activation ({}): Duration: {}, mediaType: {}, ispvr: {}".format(self.light_group_id, duration, mediaType, fileName[0:3] == "pvr"))
        if ((duration >= ADDON.getSettingInt("video_MinimumDuration") or file_name[0:3] == "pvr") and
                ((ADDON.getSettingBool("video_Movie") and media_type == "movie") or
                 (ADDON.getSettingBool("video_Episode") and media_type == "episode") or
                 (ADDON.getSettingBool("video_MusicVideo") and media_type == "MusicVideo") or
                 (ADDON.getSettingBool("video_PVR") and file_name[0:3] == "pvr") or
                 (ADDON.getSettingBool("video_Other") and media_type != "movie" and media_type != "episode" and media_type != "MusicVideo" and file_name[0:3] != "pvr"))):
            xbmc.log("[script.service.hue] Video activation: True")
            return True
        xbmc.log("[script.service.hue] Video activation: False")
        return False

    def check_already_active(self, scene):
        if not scene:
            return False

        xbmc.log(f"[script.service.hue] Check if scene light already active, settings: enable {ADDON.getSettingBool('enable_if_already_active')}")
        if ADDON.getSettingBool("enable_if_already_active"):
            try:
                scene_data = self.bridge.scenes[scene]()
                for light in scene_data["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"]:  # one light is on, the scene can be applied
                        # xbmc.log("[script.service.hue] Check if scene light already active: True")
                        return True
                # xbmc.log("[script.service.hue] Check if scene light already active: False")
            except QhueException as exc:
                xbmc.log(f"[script.service.hue] checkAlreadyActive: Hue call fail: {exc.type_id}: {exc.message} {traceback.format_exc()}")
                reporting.process_exception(exc)
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] Requests exception: {exc}")
                hue.notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)

        return False

    def check_keep_lights_off_rule(self, scene):
        if not scene:
            return True

        xbmc.log(f"[script.service.hue] Check if lights should stay off, settings: enable {ADDON.getSettingBool('keep_lights_off')}")
        if ADDON.getSettingBool("keep_lights_off"):
            try:
                scene_data = self.bridge.scenes[scene]()
                for light in scene_data["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"] is False:  # one light is off, the scene should not be applied
                        xbmc.log("[script.service.hue] Check if lights should stay off: True")
                        return False
                xbmc.log("[script.service.hue] Check if lights should stay off: False")
            except QhueException as exc:
                xbmc.log(f"[script.service.hue] checkKeepLightsOffRule: Hue call fail: {exc.type_id}: {exc.message} {traceback.format_exc()}")
                reporting.process_exception(exc)
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] Requests exception: {exc}")
                hue.notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)

        return True
