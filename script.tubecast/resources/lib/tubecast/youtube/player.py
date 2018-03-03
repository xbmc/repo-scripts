# -*- coding: utf-8 -*-
from resources.lib.kodi import kodilogging

import xbmc


monitor = xbmc.Monitor()
logger = kodilogging.get_logger()


class CastPlayer(xbmc.Player):
    def __init__(self, youtubecastv1):
        self.youtubecastv1 = youtubecastv1
        self.from_yt = False # auxiliar variable to know if the request came from the youtube background thread
        self.playing = False
        self.video_id = None
        self.ctt = None
        self.list_id = None
        self.current_index = None

    def setInfo(self, video_id, ctt, list_id, current_index):
        self.video_id = video_id
        self.ctt = ctt
        self.list_id = list_id
        self.current_index = current_index

    def play_from_youtube(self, url):
        self.from_y = True
        self.play(url)

    @staticmethod
    def getPlayingStatusCode():
        return 2 if xbmc.getInfoLabel('Player.Paused') else 1

    def onPlayBackStarted(self):
        self.from_yt = False
        self.playing = True
        self.youtubecastv1.report_playback_started(self.video_id, int(self.getTime()), self.ctt, self.list_id, self.current_index)
        while not monitor.abortRequested():
            if self.playing:
                try:
                    self.youtubecastv1.report_playing_time(self.getPlayingStatusCode(), int(self.getTime()), int(self.getTotalTime()))
                except Exception as e:
                    logger.error(e)
                    logger.debug("Probably playback was stopped but we still have a request")
                    self.youtubecastv1.report_playback_ended()
                    self.playing = False
            monitor.waitForAbort(5)

    def onPlayBackResumed(self):
        self.playing = True
        self.youtubecastv1.report_playing_time(self.getPlayingStatusCode(), int(self.getTime()), int(self.getTotalTime()))

    def onPlayBackPaused(self):
        self.playing = False
        self.youtubecastv1.pause(int(self.getTime()), int(self.getTotalTime()))

    def onPlaybackEnded(self):
        self.playing = False
        if not self.from_yt:
            self.youtubecastv1.report_playback_ended()

    def onPlayBackSeek(self, time, seekOffset):
        self.youtubecastv1.report_playing_time(self.getPlayingStatusCode(), int(self.getTime()), int(self.getTotalTime()))

    def onPlayBackStopped(self):
        self.onPlaybackEnded()
