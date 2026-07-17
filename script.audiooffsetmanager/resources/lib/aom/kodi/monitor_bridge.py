"""Kodi monitor bridge: settings-change callback posts to the dispatcher.

Also serves as the service's abort monitor (the runtime blocks on
``waitForAbort()`` of this instance). Zero logic, like the player bridge.
"""

import xbmc

from resources.lib.aom.app import events


class MonitorBridge(xbmc.Monitor):
    def __init__(self, dispatcher):
        super().__init__()
        self._dispatcher = dispatcher

    def onSettingsChanged(self):
        self._dispatcher.post(events.SettingsChanged())
