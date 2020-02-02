# -*- coding: utf-8 -*-
import xbmc

from resources.lib.kodi.utils import get_setting_as_bool
from resources.lib.tubecast.chromecast import Chromecast
from resources.lib.tubecast.kodicast import Kodicast, generate_uuid
from resources.lib.tubecast.ssdp import SSDPserver

monitor = xbmc.Monitor()


def run():
    generate_uuid()

    # Start HTTP server
    chromecast = Chromecast(monitor)
    chromecast_addr = chromecast.start()

    # Start SSDP service
    if get_setting_as_bool('enable-ssdp'):
        ssdp_server = SSDPserver()
        ssdp_server.start(chromecast_addr, interfaces=Kodicast.interfaces)

    while not monitor.abortRequested():
        monitor.waitForAbort(1)

    # Abort services
    if get_setting_as_bool('enable-ssdp'):
        ssdp_server.shutdown()
    chromecast.abort()
