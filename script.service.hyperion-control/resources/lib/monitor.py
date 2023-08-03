"""Observable monitor."""
from __future__ import annotations

import xbmc

from resources.lib.interfaces import Observer


class XBMCMonitor(xbmc.Monitor):
    """xbmc monitor class."""

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

    def onSettingsChanged(self) -> None:
        """Settings changed event."""
        self.notify_observers("updateSettings")

    def onScreensaverActivated(self) -> None:
        """Screensaver activated event."""
        self.notify_observers("screensaver")

    def onScreensaverDeactivated(self) -> None:
        """Screensaver deactivated event."""
        self.notify_observers("menu")
