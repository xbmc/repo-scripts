# -*- coding: utf-8 -*-
import datetime

import xbmc
import simplecache
import xbmcgui

from resources.lib.qhue import QhueException

from requests import ConnectTimeout

from resources.lib.kodisettings import convert_time
from resources.lib import logger, cache, reporting
from . import ADDON
from .kodisettings import settings_storage
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 1
AUDIO = 2
ALL_MEDIA = 3


class KodiGroup(xbmc.Player):
    def __init__(self):

        super(xbmc.Player, self).__init__()

    def loadSettings(self):
        logger.debug("KodiGroup Load settings for group: {}".format(self.kgroupID))
        self.enabled = ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))

        self.startBehavior = ADDON.getSettingBool("group{}_startBehavior".format(self.kgroupID))
        self.startScene = ADDON.getSettingString("group{}_startSceneID".format(self.kgroupID))

        self.pauseBehavior = ADDON.getSettingBool("group{}_pauseBehavior".format(self.kgroupID))
        self.pauseScene = ADDON.getSettingString("group{}_pauseSceneID".format(self.kgroupID))

        self.stopBehavior = ADDON.getSettingBool("group{}_stopBehavior".format(self.kgroupID))
        self.stopScene = ADDON.getSettingString("group{}_stopSceneID".format(self.kgroupID))

    def setup(self, bridge, kgroupID, flash=False, mediaType=VIDEO):
        if not hasattr(self, "state"):
            self.state = STATE_STOPPED
        self.bridge = bridge
        self.mediaType = mediaType

        self.lights = bridge.lights
        self.kgroupID = kgroupID

        self.loadSettings()

        self.groupResource = bridge.groups[0]

        if flash:
            self.flash()

    def flash(self):
        logger.debug("in KodiGroup Flash")
        try:
            self.groupResource.action(alert="select")
        except QhueException() as exc:
            logger.debug("Hue Error: {}".format(exc))
            reporting.process_exception(exc)
        except ConnectTimeout as exc:
            logger.debug("Hue Error: {}".format(exc))


    def onAVStarted(self):
        if self.enabled:
            logger.debug(
                "In KodiGroup[{}], onPlaybackStarted. Group enabled: {},startBehavior: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(
                    self.kgroupID, self.enabled, self.startBehavior, self.isPlayingVideo(), self.isPlayingAudio(),
                    self.mediaType, self.playbackType()))
            self.state = STATE_PLAYING
            settings_storage['lastMediaType'] = self.playbackType()

            if self.isPlayingVideo() and self.mediaType == VIDEO:  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                try:
                    self.videoInfoTag = self.getVideoInfoTag()
                except Exception as exc:
                    logger.debug("Get InfoTag Exception: {}".format(exc))
                    reporting.process_exception(exc)
                    return
                logger.debug("InfoTag: {}".format(self.videoInfoTag))
                if not self.checkVideoActivation(self.videoInfoTag):
                    return
            else:
                self.videoInfoTag = None

            if (self.checkActiveTime() or self.checkAlreadyActive(self.startScene)) and self.checkKeepLightsOffRule(self.startScene) and self.startBehavior and self.mediaType == self.playbackType():
                self.run_play()

    def onPlayBackStopped(self):
        if self.enabled:
            logger.debug("In KodiGroup[{}], onPlaybackStopped() , mediaType: {}, lastMediaType: {} ".format(self.kgroupID, self.mediaType, settings_storage['lastMediaType']))
            self.state = STATE_STOPPED

            try:
                if self.mediaType == VIDEO and not self.checkVideoActivation(
                        self.videoInfoTag):  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                    return
            except AttributeError:
                logger.debug("No videoInfoTag")

            if (self.checkActiveTime() or self.checkAlreadyActive(self.stopScene)) and self.checkKeepLightsOffRule(self.stopScene) and self.stopBehavior and self.mediaType == settings_storage['lastMediaType']:
                self.run_stop()

    def onPlayBackPaused(self):
        if self.enabled:
            logger.debug(
                "In KodiGroup[{}], onPlaybackPaused() , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID,
                                                                                                       self.isPlayingVideo(),
                                                                                                       self.isPlayingAudio()))
            self.state = STATE_PAUSED

            if self.mediaType == VIDEO and not self.checkVideoActivation(
                    self.videoInfoTag):  # If video group, check video activation. Otherwise it's audio so we ignore this and continue
                return
                
            if (self.checkActiveTime() or self.checkAlreadyActive(self.pauseScene)) and self.checkKeepLightsOffRule(self.pauseScene) and self.pauseBehavior and self.mediaType == self.playbackType():
                settings_storage['lastMediaType'] = self.playbackType()
                self.run_pause()

    def onPlayBackResumed(self):
        logger.debug("In KodiGroup[{}], onPlaybackResumed()".format(self.kgroupID))
        self.onAVStarted()

    def onPlayBackError(self):
        logger.debug("In KodiGroup[{}], onPlaybackError()".format(self.kgroupID))
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        logger.debug("In KodiGroup[{}], onPlaybackEnded()".format(self.kgroupID))
        self.onPlayBackStopped()

    def run_play(self):
        try:
            self.groupResource.action(scene=self.startScene)
        except QhueException as e:
            logger.debug("onAVStarted: Hue call fail: {}".format(e))
            if e.args[0][0] == 7:
                logger.debug("Scene not found")
                xbmcgui.Dialog().notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(e)


    def run_pause(self):
        try:
            xbmc.sleep(500)  # sleep for any left over ambilight calls to complete first.
            self.groupResource.action(scene=self.pauseScene)
            logger.debug("In KodiGroup[{}], onPlaybackPaused() Pause scene activated")
        except QhueException as e:
            logger.debug("onPlaybackStopped: Hue call fail: {}".format(e))
            if e.args[0][0] == 7:
                logger.debug("Scene not found")
                xbmcgui.Dialog().notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(e)

    def run_stop(self):
        try:
            xbmc.sleep(100)  # sleep for any left over ambilight calls to complete first.
            self.groupResource.action(scene=self.stopScene)
            logger.debug("In KodiGroup[{}], onPlaybackStop() Stop scene activated")
        except QhueException as e:
            logger.debug("onPlaybackStopped: Hue call fail: {}".format(e))
            if e.args[0][0] == 7:
                logger.debug("Scene not found")
                xbmcgui.Dialog().notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(e)

    def activate(self):
        logger.debug("Activate group [{}]. State: {}".format(self.kgroupID, self.state))
        xbmc.sleep(200)
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing.
            logger.debug("Activate group [{}]. playback stopped, doing nothing. ".format(self.kgroupID))

    def playbackType(self):
        if self.isPlayingVideo():
            mediaType = VIDEO
        elif self.isPlayingAudio():
            mediaType = AUDIO
        else:
            mediaType = None
        return mediaType

    def checkActiveTime(self):
        service_enabled = cache.get("script.service.hue.service_enabled")
        daylight = cache.get("script.service.hue.daylight")
        logger.debug(
            "Schedule: {}, daylightDiable: {}, daylight: {}, startTime: {}, endTime: {}".format(
                settings_storage['enableSchedule'],
                settings_storage['daylightDisable'],
                daylight,
                settings_storage['startTime'],
                settings_storage['endTime']))

        if settings_storage['daylightDisable'] and daylight:
            logger.debug("Disabled by daylight")
            return False

        if service_enabled:
            if settings_storage['enableSchedule']:
                start = convert_time(settings_storage['startTime'])
                end = convert_time(settings_storage['endTime'])
                now = datetime.datetime.now().time()
                if (now > start) and (now < end):
                    logger.debug("Enabled by schedule")
                    return True
                logger.debug("Disabled by schedule")
                return False
            logger.debug("Schedule not enabled")
            return True
        else:
            logger.debug("Service disabled")
            return False

    def checkVideoActivation(self, infoTag):
        try:
            duration = infoTag.getDuration() / 60  # returns seconds, convert to minutes
            mediaType = infoTag.getMediaType()
            fileName = infoTag.getFile()
            if not fileName and self.isPlayingVideo():
                fileName = self.getPlayingFile()

            if not fileName and settings_storage['previousFileName']:
                fileName = settings_storage['previousFileName']
            elif fileName:
                settings_storage['previousFileName'] = fileName

            logger.debug(
                "InfoTag contents: duration: {}, mediaType: {}, file: {}".format(duration, mediaType, fileName))
        except AttributeError:
            logger.debug("Can't read infoTag")
            return False
        logger.debug(
            "Video Activation settings({}): minDuration: {}, Movie: {}, Episode: {}, MusicVideo: {}, PVR : {}, Other: {}".
                format(self.kgroupID, settings_storage['videoMinimumDuration'], settings_storage['video_enableMovie'],
                       settings_storage['video_enableEpisode'],
                       settings_storage['video_enableMusicVideo'], 
                       settings_storage['video_enablePVR'],
                       settings_storage['video_enableOther']))
        logger.debug("Video Activation ({}): Duration: {}, mediaType: {}, ispvr: {}".format(self.kgroupID, duration, mediaType, fileName[0:3] == "pvr"))
        if ((duration >= settings_storage['videoMinimumDuration'] or fileName[0:3] == "pvr") and
                ((settings_storage['video_enableMovie'] and mediaType == "movie") or
                 (settings_storage['video_enableEpisode'] and mediaType == "episode") or
                 (settings_storage['video_enableMusicVideo'] and mediaType == "MusicVideo") or
                 (settings_storage['video_enablePVR'] and fileName[0:3] == "pvr") or
                 (settings_storage['video_enableOther'] and mediaType != "movie" and mediaType != "episode" and mediaType != "MusicVideo" and fileName[0:3] != "pvr"))):
            logger.debug("Video activation: True")
            return True
        logger.debug("Video activation: False")
        return False

    def checkAlreadyActive(self, scene):
        if not scene:
            return False

        logger.debug("Check if scene light already active, settings: enable {}".format(settings_storage['enable_if_already_active']))
        if settings_storage['enable_if_already_active']:
            try:
                sceneData = self.bridge.scenes[scene]()
                for light in sceneData["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"] == True: # one light is on, the scene can be applied
                        logger.debug("Check if scene light already active: True")
                        return True
                logger.debug("Check if scene light already active: False")
            except QhueException as e:
                logger.debug("checkAlreadyActive: Hue call fail: {}".format(e))

        return False
    
    def checkKeepLightsOffRule(self, scene):
        if not scene:
            return True

        logger.debug("Check if lights should stay off, settings: enable {}".format(settings_storage['keep_lights_off']))
        if settings_storage['keep_lights_off']:
            try:
                sceneData = self.bridge.scenes[scene]()
                for light in sceneData["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"] == False: # one light is off, the scene should not be applied
                        logger.debug("Check if lights should stay off: True")
                        return False
                logger.debug("Check if lights should stay off: False")
            except QhueException as e:
                logger.debug("checkKeepLightsOffRule: Hue call fail: {}".format(e))

        return True
                
