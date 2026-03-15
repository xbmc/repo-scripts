# -*- coding: utf-8 -*-
# Copyright (c) 2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

import threading

import xbmc
import xbmcaddon

import lib.helpers
import lib.monitor

try:
    import lib.server
    __server_available__ = True
except ImportError:
    __server_available__ = False

__addon__ = xbmcaddon.Addon()
__server__ = None


def server_available():
    if not __server_available__ and __addon__.getSetting("enabled") == "true":
        lib.helpers.display_error_message(32200)
    return __server_available__

def restart_server():
    """Restart the REST API.
    """
    if not server_available():
        return

    global __server__
    stop_server()

    if __addon__.getSetting("enabled") != "true":
        return


    port = int(__addon__.getSetting("port"))
    address = __addon__.getSetting("address")
    __server__ = threading.Thread(target=lib.server.init_server, args=(port, address))
    __server__.start()
    # wait one second and make sure the server has started
    xbmc.sleep(1000)
    if not __server__.is_alive():
        __server__.join()
        lib.helpers.display_error_message(32201)
        __server__ = None
    else:
        lib.helpers.display_message(32300, " {}:{}".format(address,port))

def refresh_addon():
    global __addon__
    __addon__ = xbmcaddon.Addon()
    return __addon__

def stop_server():
    """Stop the REST API."""
    if not server_available():
        return

    global __server__
    if __server__:
        lib.server.stop_server()
        __server__.join()
        lib.helpers.display_message(32301)
    __server__ = None

def run():
    monitor = lib.monitor.ProjectorMonitor()
    restart_server()

    monitor.waitForAbort()

    lib.helpers.log("Shutting down addon")
    stop_server()
    monitor.cleanup()
    if __addon__.getSetting("at_shutdown") == "true":
        lib.commands.stop(final_shutdown=True)
