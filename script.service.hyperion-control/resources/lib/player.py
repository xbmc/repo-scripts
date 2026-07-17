"""Observable player."""
from __future__ import annotations

import xbmc

from resources.lib.interfaces import Observer


class Player(xbmc.Player):
    """xbmc player class."""

    def __init__(self) -> None:
        super().__init__()
        self._observers: list[Observer] = []

    def register_observer(self, observer: Observer) -> None:
        """Register an observer to the events."""
        self._observers.append(observer)

    def notify_observers(self, command: str) -> None:
        """Sends the command to the observers."""
        for observer in self._observers:
            observer.notify(command)

    def onPlayBackPaused(self) -> None:
        """Playback paused event."""
        self.notify_observers("pause")

    def onPlayBackResumed(self) -> None:
        """Playback resumed event."""
        self._play_handler()

    def onAVStarted(self) -> None:
        """Audio or Video started event."""
        self._play_handler()

    def onPlayBackStopped(self) -> None:
        """Playback stopped event."""
        self.notify_observers("menu")

    def onPlayBackEnded(self) -> None:
        """Playback end event."""
        self.notify_observers("menu")

    def _play_handler(self) -> None:
        command = "playAudio" if self.isPlayingAudio() else "playVideo"
        self.notify_observers(command)
