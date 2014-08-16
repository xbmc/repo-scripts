'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import os
import traceback
import threading
import pykka
import xbmc
import xbmcgui
import utils
import settings
from utils import escape_param, log, notify
from itertools import repeat
from watchdog.events import FileSystemEventHandler

SUPPORTED_MEDIA = '|' + xbmc.getSupportedMedia('video') + \
                  '|' + xbmc.getSupportedMedia('music') + '|'


class XBMCActor(pykka.ThreadingActor):
    """ Messaging interface to xbmc's executebuiltin calls """

    @staticmethod
    def _xbmc_is_busy():
        xbmc.sleep(100) # visibility cant be immediately trusted. Give xbmc time to render
        return ((xbmc.Player().isPlaying() and settings.PAUSE_ON_PLAYBACK)
            or xbmc.getCondVisibility('Library.IsScanning')
            or xbmc.getCondVisibility('Window.IsActive(10101)'))

    def scan(self, library, path):
        """ Tell xbmc to scan. Returns immediately when scanning has started. """
        while self._xbmc_is_busy():
            pass
        log("scanning %s (%s)" % (path, library))
        if library == 'video' and settings.FORCE_GLOBAL_SCAN:
            xbmc.executebuiltin("UpdateLibrary(video)")
        else:
            xbmc.executebuiltin("UpdateLibrary(%s,%s)" % (library, escape_param(path)))

    def clean(self, library, path=None):
        """ Tell xbmc to clean. Returns immediately when scanning has started. """
        while self._xbmc_is_busy():
            pass
        log("cleaning %s library" % library)
        xbmc.executebuiltin("CleanLibrary(%s)" % library)


class EventHandler(threading.Thread, FileSystemEventHandler):
    """
    Handles raw incoming events for single root path and library
    and forward scan/clean commands to the xbmc actor singleton.

    Commands are skipped base on settings and the path the event comes from.
    Additionally, 'batches' of events that occur before cleaning/scanning has
    started are accumulated into one call.
    """

    def __init__(self, library, path, xbmc_actor):
        threading.Thread.__init__(self)
        FileSystemEventHandler.__init__(self)
        self.library = library
        self.path = path
        self.xbmc = xbmc_actor
        self.stop_event = threading.Event()
        self.new_event = threading.Event()
        self.clean_event = threading.Event()
        self.scan_event = threading.Event()

    def on_created(self, event):
        if not self._can_skip(event, event.src_path):
            self.scan_event.set()
            self.new_event.set()

    def on_deleted(self, event):
        if settings.CLEAN and not self._can_skip(event, event.src_path):
            self.clean_event.set()
            self.new_event.set()

    def on_moved(self, event):
        self.on_deleted(event)
        if not self._can_skip(event, event.dest_path):
            self.scan_event.set()
            self.new_event.set()

    def on_any_event(self, event):
        log("<%s> <%s>" % (event.event_type, event.src_path))

    @staticmethod
    def _is_hidden(path):
        dirs = path.split(os.sep)
        for d in dirs:
            if d.startswith('.') or d.startswith('_UNPACK'):
                return True
        return False

    def _can_skip(self, event, path):
        if not path:
            return False
        relpath = path[len(self.path):] if path.startswith(self.path) else path
        if self._is_hidden(relpath):
            log("skipping <%s> <%s>" % (event.event_type, path))
            return True
        if not event.is_directory:
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            if SUPPORTED_MEDIA.find('|%s|' % ext) == -1:
                log("skipping <%s> <%s>" % (event.event_type, path))
                return True
        return False

    def stop(self):
        self.stop_event.set()
        self.new_event.set()

    def run(self):
        while True:
            self.new_event.wait()
            if self.stop_event.wait(settings.SCAN_DELAY):
                return

            if self.clean_event.is_set():
                self.xbmc.clean(self.library, self.path)
                self.clean_event.clear()

            if self.stop_event.is_set():
                return

            if self.scan_event.is_set():
                self.xbmc.scan(self.library, self.path)
                # Scan started. All events occurring from here on out may not
                # be picked up by scanner and will require a new scan.
                self.scan_event.clear()


def main():
    progress = xbmcgui.DialogProgressBG()
    progress.create("Watchdog starting. Please wait...")

    if settings.STARTUP_DELAY > 0:
        log("waiting for user delay of %d seconds" % settings.STARTUP_DELAY)
        msg = "Delaying startup by %d seconds."
        progress.update(0, message=msg % settings.STARTUP_DELAY)
        xbmc.sleep(settings.STARTUP_DELAY * 1000)
        if xbmc.abortRequested:
            return

    sources = []
    video_sources = settings.VIDEO_SOURCES
    sources.extend(zip(repeat('video'), video_sources))
    log("video sources %s" % video_sources)

    music_sources = settings.MUSIC_SOURCES
    sources.extend(zip(repeat('music'), music_sources))
    log("music sources %s" % music_sources)

    if not sources:
        notify("Nothing to watch", "No media source found")

    xbmc_actor = XBMCActor.start().proxy()
    threads = []
    for i, (libtype, path) in enumerate(sources):
        progress.update((i+1)/len(sources)*100, message="Setting up %s" % path)
        try:
            fs_path, observer = utils.select_observer(path)
        except IOError:
            log("not watching <%s>. does not exist" % path)
            notify("Could not find path", path)
            continue
        event_handler = EventHandler(libtype, path, xbmc_actor)
        event_handler.start()
        threads.append(event_handler)
        try:
            observer.schedule(event_handler, path=fs_path, recursive=settings.RECURSIVE)
            if not observer.is_alive():
                observer.start()
                threads.append(observer)
            log("watching <%s> using %s" % (path, observer))
        except Exception:
            traceback.print_exc()
            log("failed to watch <%s>" % path)
            notify("Failed to watch %s" % path, "See log for details")

    progress.close()
    log("initialization done")

    while not xbmc.abortRequested:
        xbmc.sleep(100)
    for i, th in enumerate(threads):
        try:
            log("stopping thread %d of %d" % (i+1, len(threads)))
            th.stop()
        except Exception:
            traceback.print_exc()
    xbmc_actor.stop()

if __name__ == "__main__":
    main()
