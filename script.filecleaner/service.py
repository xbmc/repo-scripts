#!/usr/bin/python
# -*- coding: utf-8 -*-

from xbmc import Monitor

from default import Cleaner
from settings import *
from utils import debug, notify


def autostart():
    """
    Starts the cleaning service.
    """
    cleaner = Cleaner()
    monitor = Monitor()

    service_sleep = 4  # Lower than 4 causes too much stress on resource limited systems such as RPi
    ticker = 0
    delayed_completed = False

    while not monitor.abortRequested():
        if get_setting(service_enabled):
            scan_interval_ticker = get_setting(scan_interval) * 60 / service_sleep
            delayed_start_ticker = get_setting(delayed_start) * 60 / service_sleep

            if delayed_completed and ticker >= scan_interval_ticker:
                results, _ = cleaner.clean_all()
                notify(results)
                ticker = 0
            elif not delayed_completed and ticker >= delayed_start_ticker:
                delayed_completed = True
                results, _ = cleaner.clean_all()
                notify(results)
                ticker = 0

            xbmc.sleep(service_sleep * 1000)
            ticker += 1
        else:
            xbmc.sleep(service_sleep * 1000)

    xbmc.log("Abort requested. Terminating.")
    return


if __name__ == "__main__":
    autostart()
