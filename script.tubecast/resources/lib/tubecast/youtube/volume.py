# -*- coding: utf-8 -*-
import json
import threading

import xbmc

from resources.lib.tubecast.youtube import kodibrigde


class VolumeMonitor(xbmc.Monitor):

    def __init__(self, cast):
        super(VolumeMonitor, self).__init__()
        self.cast = cast
        self.kodi_volume = kodibrigde.get_kodi_volume()

        self.thread = None

    def onNotification(self, sender, method, data):
        if self.cast.has_client and method == "Application.OnVolumeChanged":
            new_volume = json.loads(data)["volume"]
            if self.kodi_volume != new_volume:
                self.kodi_volume = new_volume
                self.cast.report_volume(new_volume)

    def start(self):
        self.thread = threading.Thread(name="VolumeMonitor", target=self.__run)
        self.thread.start()

    def __run(self):
        while self.cast.has_client and not self.abortRequested():
            self.waitForAbort(1)
