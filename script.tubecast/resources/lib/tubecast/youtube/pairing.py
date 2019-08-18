# -*- coding: utf-8 -*-
import time

from .app import YoutubeCastV1

from resources.lib.kodi.utils import get_string

from xbmc import Monitor

from xbmcgui import DialogProgress


def generate_pairing_code():
    monitor = Monitor()
    progress = DialogProgress()
    progress.create(get_string(32000), get_string(32001))
    chromecast = YoutubeCastV1()
    pairing_code = chromecast.pair()

    i = 0
    progress.update(i, get_string(32002), pairing_code)
    start_time = time.time()
    while not monitor.abortRequested() and not chromecast.has_client and not progress.iscanceled() and not (time.time() - start_time) > (60 * 1):
        i += 10
        if i > 100:
            i = 0
        progress.update(i, get_string(32002), pairing_code)
        monitor.waitForAbort(2)
    progress.close()
