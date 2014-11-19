# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import time
import traceback
import threading
import xbmc
import xbmcgui
import utils
import settings
import emitters
import videolibrary
from utils import escape_param, log
from itertools import repeat
from watchdog.events import FileSystemEventHandler
from watchdog.utils.compat import Event
from emitters import MultiEmitterObserver


class XBMCIF(threading.Thread):
    """Wrapper around the builtins to make sure no two commands a executed at
    the same time (xbmc will cancel previous if not finished)
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self._stop_event = Event()
        self._cmd_queue = utils.OrderedSetQueue()

    def stop(self):
        self._stop_event.set()
        self._cmd_queue.put("stop")  # unblock wait

    def queue_scan(self, library, path=None):
        if path:
            cmd = "UpdateLibrary(%s,%s)" % (library, escape_param(path))
        else:
            cmd = "UpdateLibrary(%s)" % library
        self._cmd_queue.put(cmd)

    def queue_clean(self, library):
        self._cmd_queue.put("CleanLibrary(%s)" % library)

    def queue_remove(self, library, path=None):
        if settings.REMOVAL_ENABLED:
            if settings.PER_FILE_REMOVE and path and library == 'video':
                videolibrary.remove_video(path)
            else:
                self._cmd_queue.put("CleanLibrary(%s)" % library)

    def run(self):
        player = xbmc.Player()
        while True:
            self._cmd_queue.wait()
            if self._stop_event.wait(settings.SCAN_DELAY):
                return
            while player.isPlaying():
                self._stop_event.wait(1)
            if self._stop_event.is_set():
                return

            # Remove item right before it's executed so that any duplicates of
            # this commands gets flushed from the queue.
            cmd = self._cmd_queue.get_nowait()
            log("[xbmcif] executing builtin: '%s'" % cmd)
            xbmc.executebuiltin(cmd.encode('utf-8'))

            # wait for scan to start. we need a timeout or else we a screwed
            # if we missed it.
            # TODO: replace this crap with Monitor callbacks in Helix
            log("[xbmcif] waiting for scan/clean start..")
            timeout = 3000
            while not xbmc.getCondVisibility('Library.IsScanning') \
                    and not self._stop_event.is_set():
                xbmc.sleep(100)
                timeout -= 100
                if timeout <= 0:
                    log("[xbmcif] wait for scan/clean timed out.")
                    break
            log("[xbmcif] scan/clean started.")
            log("[xbmcif] waiting for scan/clean end..")

            # wait for scan to end
            while xbmc.getCondVisibility('Library.IsScanning') \
                    and not self._stop_event.is_set():
                xbmc.sleep(100)
            log("[xbmcif] scan/clean ended.")


class EventHandler(FileSystemEventHandler):
    """
    Handles raw incoming events for single root path and library,
    and queues scan/clean commands to the xbmcif singleton.
    """

    def __init__(self, library, path, xbmcif):
        FileSystemEventHandler.__init__(self)
        self.library = library
        self.path = path
        self.xbmcif = xbmcif
        self.supported_media = '|' + xbmc.getSupportedMedia(library).decode('utf-8') + '|'

    def on_created(self, event):
        if not event.is_directory and not self._can_skip(event, event.src_path):
            # TODO: remove this hack when fixed in xbmc
            if settings.FORCE_GLOBAL_SCAN and self.library == 'video':
                self.xbmcif.queue_scan(self.library)
            else:
                self.xbmcif.queue_scan(self.library, self.path)

    def on_deleted(self, event):
        if not event.is_directory and not self._can_skip(event, event.src_path):
            self.xbmcif.queue_remove(self.library, event.src_path)

    def on_moved(self, event):
        self.on_deleted(event)
        if not self._can_skip(event, event.dest_path):
            # TODO: remove this hack when fixed in xbmc
            if settings.FORCE_GLOBAL_SCAN and self.library == 'video':
                self.xbmcif.queue_scan(self.library)
            else:
                self.xbmcif.queue_scan(self.library, self.path)

    def on_any_event(self, event):
        log("[event] <%s> <%r>" % (event.event_type, event.src_path))

    def _is_hidden(self, path):
        sep = '/' if utils.is_url(self.path) else os.sep
        relpath = path[len(self.path):] if path.startswith(self.path) else path
        for part in relpath.split(sep):
            if part.startswith('.') or part.startswith('_UNPACK'):
                return True
        return False

    def _can_skip(self, event, path):
        if not path:
            return False
        if self._is_hidden(path):
            log("[event] skipping <%s> <%r>" % (event.event_type, path))
            return True
        if not event.is_directory:
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            if self.supported_media.find('|%s|' % ext) == -1:
                log("[event] skipping <%s> <%r>" % (event.event_type, path))
                return True
        return False


def main():
    progress = xbmcgui.DialogProgressBG()
    progress.create("Watchdog starting. Please wait...")

    if settings.STARTUP_DELAY > 0:
        log("waiting for user delay of %d seconds" % settings.STARTUP_DELAY)
        msg = "Delaying startup by %d seconds."
        progress.update(0, message=msg % settings.STARTUP_DELAY)
        start = time.time()
        while time.time() - start < settings.STARTUP_DELAY:
            xbmc.sleep(100)
            if xbmc.abortRequested:
                progress.close()
                return

    sources = []
    video_sources = settings.VIDEO_SOURCES
    sources.extend(zip(repeat('video'), video_sources))
    log("video sources %s" % video_sources)

    music_sources = settings.MUSIC_SOURCES
    sources.extend(zip(repeat('music'), music_sources))
    log("music sources %s" % music_sources)

    xbmcif = XBMCIF()
    if settings.CLEAN_ON_START:
        if video_sources:
            xbmcif.queue_clean('video')
        if music_sources:
            xbmcif.queue_clean('music')

    if settings.SCAN_ON_START:
        if video_sources:
            xbmcif.queue_scan('video')
        if music_sources:
            xbmcif.queue_scan('video')

    observer = MultiEmitterObserver()
    observer.start()  # start so emitters are started on schedule

    for i, (libtype, path) in enumerate(sources):
        progress.update((i+1)/len(sources)*100, message="Setting up %s" % path)
        try:
            emitter_cls = emitters.select_emitter(path)
        except IOError:
            log("not watching <%s>. does not exist" % path)
            continue
        finally:
            if xbmc.abortRequested:
                break

        eh = EventHandler(libtype, path, xbmcif)
        try:
            observer.schedule(eh, path=path, emitter_cls=emitter_cls)
            log("watching <%s> using %s" % (path, emitter_cls))
        except Exception:
            traceback.print_exc()
            log("failed to watch <%s>" % path)
        finally:
            if xbmc.abortRequested:
                break

    xbmcif.start()
    progress.close()
    log("initialization done")

    if settings.SHOW_STATUS_DIALOG:
        watching = ["Watching '%s'" % path for _, path in sources
                    if path in observer.paths]
        not_watching = ["Not watching '%s'" % path for _, path in sources
                        if path not in observer.paths]
        dialog = xbmcgui.Dialog()
        dialog.select('Watchdog status', watching + not_watching)

    if xbmc.__version__ >= '2.19.0':
        monitor = xbmc.Monitor()
        monitor.waitForAbort()
    else:
        while not xbmc.abortRequested:
            xbmc.sleep(100)

    log("stopping..")
    observer.stop()
    xbmcif.stop()
    observer.join()
    xbmcif.join()

if __name__ == "__main__":
    main()
