"""Kodi player bridge: every callback is a one-line post to the dispatcher.

Kodi pumps Player callbacks sequentially, so anything slow here delays
every subsequent callback for this addon. This class therefore holds no
logic: no logging, no settings reads, no state. Translation to typed
events and all decisions happen in dispatcher handlers.
"""

import xbmc

from resources.lib.aome.app import events


class PlayerBridge(xbmc.Player):
    def __init__(self, dispatcher):
        super().__init__()
        self._dispatcher = dispatcher

    def onAVStarted(self):
        self._dispatcher.post(events.PlaybackStarted())

    def onAVChange(self):
        self._dispatcher.post(events.AvChanged())

    def onPlayBackStopped(self):
        self._dispatcher.post(events.PlaybackStopped())

    def onPlayBackEnded(self):
        self._dispatcher.post(events.PlaybackEnded())

    def onPlayBackPaused(self):
        self._dispatcher.post(events.Paused())

    def onPlayBackResumed(self):
        self._dispatcher.post(events.Resumed())

    def onPlayBackSeek(self, time, seekOffset):
        self._dispatcher.post(events.SeekOccurred(time_ms=time,
                                                  offset_ms=seekOffset))

    def onPlayBackSeekChapter(self, chapter):
        self._dispatcher.post(events.SeekChapter(chapter=chapter))

    def onPlayBackSpeedChanged(self, speed):
        self._dispatcher.post(events.SpeedChanged(speed=speed))
