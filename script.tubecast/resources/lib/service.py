# -*- coding: utf-8 -*-
from resources.lib.kodi import kodilogging
from resources.lib.kodi.utils import get_setting_as_bool
from resources.lib.tubecast.chromecast import Chromecast
from resources.lib.tubecast.kodicast import Kodicast, generate_uuid
from resources.lib.tubecast.ssdp import SSDPserver

import xbmc


logger = kodilogging.get_logger()
monitor = xbmc.Monitor()


def run():
    generate_uuid()
    # Start SSDP service
    if get_setting_as_bool('enable-ssdp'):
        ssdp_server = SSDPserver()
        ssdp_server.start(interfaces=Kodicast.interfaces)
    # Start HTTP server
    chromecast = Chromecast(monitor)
    chromecast.start()

    while not monitor.abortRequested():
        monitor.waitForAbort(1)

    # Abort services
    if get_setting_as_bool('enable-ssdp'):
        ssdp_server.shutdown()
    chromecast.abort()
