# -*- coding: utf-8 -*-
# Copyright (c) 2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

import datetime
import threading

import xbmc

import lib.commands
import lib.helpers
import lib.service

class ProjectorMonitor(xbmc.Monitor):
    """Subclass of xbmc.Monitor that restarts the twisted web server on
    configuration changes, and starting library updates if configured.
    """

    def __init__(self, *args, **kwargs):
        self._update_lock_ = threading.Lock()
        self._ongoing_updates_ = set()
        self._update_timer_ = None
        self._ss_activation_timer_ = None
        self._last_power_command_ = datetime.datetime.fromtimestamp(0)
        self._addon_ = lib.service.refresh_addon()
        if self._addon_.getSetting("at_start") == "true":
            lib.commands.start()


    def update_libraries(self):
        """Called by the timer to start a new library update if the projector
        is still offline and configuration is set to allow regular library
        updates.
        """
        power_status = lib.commands.report()["power"]
        if not power_status \
                and self._addon_.getSetting("lib_update") == "true" \
                and self._addon_.getSetting("update_again") == "true":
            if self._addon_.getSetting("update_music") == "true":
                xbmc.executebuiltin('UpdateLibrary(music)')
            if self._addon_.getSetting("update_video") == "true":
                xbmc.executebuiltin('UpdateLibrary(video)')
        
    def cleanup(self):
        """Remove any lingering timer before exit"""
        if self._ss_activation_timer_:
            self._ss_activation_timer_.cancel()
    
        with self._update_lock_:
            if self._update_timer_:
                self._update_timer_.cancel()
                self._update_timer_ = None

    def onScreensaverActivated(self):
        if self._addon_.getSetting("at_ss_start") == "true":
            delay = int(self._addon_.getSetting("at_ss_start_delay"))
            lib.helpers.log("Screensaver activated, scheduling projector shutdown")
            self._ss_activation_timer_ = threading.Timer(delay, lib.commands.stop)
            self._last_power_command_ = datetime.datetime.now() + datetime.timedelta(seconds=delay)
            self._ss_activation_timer_.start()

    def onScreensaverDeactivated(self):
        if self._ss_activation_timer_:
            lib.helpers.log("Screensaver deactivated, aborting any scheduled projector shutdown")
            self._ss_activation_timer_.cancel()

        if self._addon_.getSetting("at_ss_shutdown") == "true":
            min_turnaround = int(self._addon_.getSetting("min_turnaround"))
            time_since_stop = datetime.datetime.now() - self._last_power_command_
            if time_since_stop.days == 0 and time_since_stop.seconds < min_turnaround:
                lib.helpers.log("Screensaver deactivated too soon, will sleep a while before starting projector")
                monitor.waitForAbort((min_turnaround-time_since_stop.seconds)*1000)
            lib.helpers.log("Screensaver deactivated, starting projector")
            lib.commands.start()

    def onSettingsChanged(self):
        self._addon_ = lib.service.refresh_addon()

        if self._addon_.getSetting("enabled") == "true":
            lib.service.restart_server()
        else:
            lib.service.stop_server()

    def onCleanStarted(self, library):
        self.onScanStarted(library)

    def onCleanFinished(self, library):
        self.onScanFinished(library)
    
    def onScanStarted(self, library):
        self.cleanup()
        with self._update_lock_:
            self._ongoing_updates_.add(library)
        return library

    def onScanFinished(self, library):
        self.cleanup()
        with self._update_lock_:
            self._ongoing_updates_.discard(library)
            if len(self._ongoing_updates_) == 0 \
                    and self._addon_.getSetting("lib_update") == "true" \
                    and self._addon_.getSetting("update_again") == "true":
                self._update_timer_ = threading.Timer(
                        int(self._addon_.getSetting("update_again_at"))*60,
                        self.update_libraries)
                self._update_timer_.start()
        return library

