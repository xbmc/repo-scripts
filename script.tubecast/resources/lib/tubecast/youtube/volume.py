# -*- coding: utf-8 -*-
import json

from resources.lib.kodi import kodilogging
from resources.lib.tubecast.youtube import kodibrigde

import xbmc


logger = kodilogging.get_logger()


class VolumeMonitor(xbmc.Monitor):

    def __init__(self, youtubecastv1):
        self.youtubecastv1 = youtubecastv1
        self.kodi_volume = kodibrigde.get_kodi_volume()

    def onNotification(self, sender, method, data):
        if self.youtubecastv1.has_client and method == "Application.OnVolumeChanged":
            new_volume = json.loads(data)["volume"]
            if self.kodi_volume != new_volume:
                self.kodi_volume = new_volume
                self.youtubecastv1.set_volume(new_volume)
