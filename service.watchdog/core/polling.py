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

import xbmc
import settings
from watchdog.observers.api import EventEmitter
from watchdog.events import FileCreatedEvent, FileDeletedEvent
from utils import log, XBMCInterrupt


def _paused():
    return xbmc.Player().isPlaying() and settings.PAUSE_ON_PLAYBACK


def hidden(path):
    return path.startswith(b'.') or path.startswith(b'_UNPACK')


def file_diff(old, current):
    created = current - old
    deleted = old - current
    return created, deleted


def file_list_from_walk(walker):
    def f(path):
        ret = []
        for dirs, files in walker(path):
            ret.extend(files)
        return ret
    return f


class Poller(EventEmitter):
    polling_interval = -1
    list_files = None

    def __init__(self, event_queue, watch, timeout=1):
        EventEmitter.__init__(self, event_queue, watch, timeout)
        self._snapshot = None

    def take_snapshot(self):
        """Take snapshot of this emitters root path and return changes."""
        if self._snapshot is None:
            self._snapshot = set(self.list_files(self.watch.path))
            return [], []

        new_snapshot = set(self.list_files(self.watch.path))
        diff = file_diff(self._snapshot, new_snapshot)
        self._snapshot = new_snapshot
        return diff

    def is_offline(self):
        """Whether the file system this emitter is watching is offline."""
        return False

    def queue_events(self, timeout):
        if self.stopped_event.wait(self.polling_interval):
            return
        if _paused():
            return
        if self.is_offline():
            return

        files_created, files_deleted = self.take_snapshot()

        for path in files_created:
            self.queue_event(FileCreatedEvent(path))
        for path in files_deleted:
            self.queue_event(FileDeletedEvent(path))

    def run(self):
        try:
            while self.should_keep_running():
                self.queue_events(self.timeout)
        except XBMCInterrupt:
            log("XBMCInterrupt raised")
        except Exception:
            pass


class PollerNonRecursive(Poller):
    get_mtime = None
    list_files = None

    def __init__(self, *args, **kwargs):
        super(PollerNonRecursive, self).__init__(*args, **kwargs)
        self._files = None
        self._mtime = None

    def take_snapshot(self):
        if self._files is None:
            self._mtime = self.get_mtime(self.watch.path)
            self._files = set(self.list_files(self.watch.path))
            return [], []

        # Do fast check of mtime before listing directory
        current_mtime = self.get_mtime(self.watch.path)
        if current_mtime == self._mtime:
            return [], []

        current_files = set(self.list_files(self.watch.path))
        diff = file_diff(self._files, current_files)
        self._mtime = current_mtime
        self._files = current_files
        return diff