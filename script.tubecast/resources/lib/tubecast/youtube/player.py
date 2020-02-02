# -*- coding: utf-8 -*-
import xbmc

from resources.lib.kodi import kodilogging

monitor = xbmc.Monitor()
logger = kodilogging.get_logger("player")

STATUS_PLAYING = 1
STATUS_PAUSED = 2
STATUS_LOADING = 3
STATUS_STOPPED = 4


class CastPlayer(xbmc.Player):
    def __init__(self, cast):  # type: (YoutubeCastV1) -> None
        super(CastPlayer, self).__init__()
        self.cast = cast
        # auxiliary variable to know if the request came from the youtube background thread
        self.from_yt = False

    def play_from_youtube(self, url):  # type: (str) -> None
        self.from_yt = True
        self.play(url)

    @property
    def status_code(self):  # type: () -> int
        if xbmc.getCondVisibility("Player.Paused"):
            return STATUS_PAUSED

        if self.isPlaying():
            return STATUS_PLAYING

        return STATUS_STOPPED

    @property
    def playing(self):  # type: () -> bool
        """Whether the player is currently playing.

        This is different from `isPlaying` in that it returns `False` if the
        player is paused or otherwise not actively playing.
        """
        return xbmc.getCondVisibility("Player.Playing")

    def __should_report(self):  # type: () -> bool
        return self.cast.has_client and self.from_yt

    def __report_state_change(self, status_code=None):
        if not self.__should_report():
            return

        if status_code is None:
            status_code = self.status_code

        self.cast.report_state_change(status_code, int(self.getTime()), int(self.getTotalTime()))

    def onPlayBackStarted(self):
        if not self.__should_report():
            return

        self.cast.report_now_playing()

        while self.isPlaying() and self.__should_report() and not monitor.abortRequested():
            self.__report_state_change()
            monitor.waitForAbort(5)

    def onPlayBackResumed(self):
        self.__report_state_change()

    def onPlayBackPaused(self):
        self.__report_state_change()

    def onPlayBackEnded(self):
        if self.__should_report():
            self.cast.report_playback_ended()

        self.from_yt = False

    def onPlayBackSeek(self, time, seek_offset):
        self.__report_state_change(status_code=STATUS_LOADING)

    def onPlayBackStopped(self):
        if self.__should_report():
            self.cast.report_playback_stopped()
