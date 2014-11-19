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
from watchdog.observers.api import BaseObserver
from watchdog.observers.api import ObservedWatch
from polling_local import LocalPoller
from polling_xbmc import VFSPoller
from utils import encode_path, is_url


try:
    from watchdog.observers.inotify import InotifyEmitter as NativeEmitter
except:
    try:
        from watchdog.observers.kqueue import KqueueEmitter as NativeEmitter
    except:
        try:
            from watchdog.observers.read_directory_changes import WindowsApiEmitter as NativeEmitter
        except:
            NativeEmitter = LocalPoller


class MultiEmitterObserver(BaseObserver):
    def __init__(self):
        BaseObserver.__init__(self, None)

    @property
    def paths(self):
        return [w.path for w in self._watches]

    def schedule(self, event_handler, path, emitter_cls=None):
        with self._lock:
            watch = ObservedWatch(path, True)
            emitter = emitter_cls(self.event_queue, watch, self.timeout)
            if self.is_alive():
                emitter.start()
            self._add_handler_for_watch(event_handler, watch)
            self._add_emitter(emitter)
            self._watches.add(watch)
            return watch


def select_emitter(path):
    import xbmcvfs
    import settings
    from utils import log

    if is_url(path) and xbmcvfs.exists(path):
        return VFSPoller

    if os.path.exists(encode_path(path)):
        if settings.POLLING:
            return LocalPoller
        if _is_remote_filesystem(path):
            log("select_observer: path <%s> identified as remote filesystem" % path)
            return LocalPoller
        return NativeEmitter

    raise IOError("No such directory: '%s'" % path)


def _is_remote_filesystem(path):
    from utils import log
    from watchdog.utils import platform
    if not platform.is_linux():
        return False

    remote_fs_types = ['cifs', 'smbfs', 'nfs', 'nfs4']
    escaped_path = encode_path(path.rstrip('/').replace(' ', '\\040'))
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                _, mount_point, fstype = line.split()[:3]
                if mount_point == escaped_path:
                    log("[fstype] type is \"%s\" '%s' " % (fstype, path.decode('utf-8')))
                    return fstype in remote_fs_types
        log("[fstype] path not in /proc/mounts '%s' " % escaped_path.decode('utf-8'))
        return False

    except (IOError, ValueError) as e:
        log("[fstype] failed to read /proc/mounts. %s, %s" % (type(e), e))
        return False