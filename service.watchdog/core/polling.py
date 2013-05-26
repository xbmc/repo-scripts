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
import time
import xbmc
from functools import partial
from watchdog.observers.api import EventEmitter, BaseObserver
from watchdog.events import DirDeletedEvent, DirCreatedEvent
from main import log
from main import PAUSE_ON_PLAYBACK

def _paused():
  return xbmc.Player().isPlaying() and PAUSE_ON_PLAYBACK

def hidden(path):
  return path.startswith('.')

class SnapshotRootOnly(object):
  def __init__(self, root, get_mtime):
    self._root = root
    self._mtime = get_mtime(root)
  
  def diff(self, other):
    modified = [self._root] if self._mtime != other._mtime else []
    return [], [], modified

class PathSnapsot(object):
  def __init__(self, root, walker):
    self._files = set()
    for dirs, files in walker(root):
      self._files.update(files)
  
  def diff(self, other):
    created = other._files - self._files
    deleted = self._files - other._files
    return created, deleted, []

class SnapshotWithStat(object):
  def __init__(self, root, walker, get_mtime):
    self._dirs = set()
    self._files = set()
    self._stat_info = {}
    for dirs, files in walker(root):
      self._dirs.update(dirs)
      self._files.update(files)
    for path in self._dirs:
      self._stat_info[path] = get_mtime(path)
  
  def diff(self, other):
    created_files = other._files - self._files
    deleted_files = self._files - other._files
    
    created_dirs = other._dirs - self._dirs
    deleted_dirs = self._dirs - other._dirs
    
    modified_dirs = []
    for path in set(self._stat_info) - deleted_dirs - created_dirs:
      if self._stat_info[path] != other._stat_info[path]:
        modified_dirs.append(path)
    return created_files | created_dirs, deleted_files | deleted_dirs, modified_dirs

class Poller(EventEmitter):
  def __init__(self, event_queue, watch, make_snapshot, timeout):
    EventEmitter.__init__(self, event_queue, watch, timeout)
    self._make_snapshot = make_snapshot
    self._snapshot = make_snapshot(self.watch.path)
  
  def queue_events(self, timeout):
    time.sleep(timeout)
    if not _paused():
      new_snapshot = self._make_snapshot(self.watch.path)
      created, deleted, modified = self._snapshot.diff(new_snapshot)
      self._snapshot = new_snapshot
      
      if deleted:
        log("poller: delete event appeared in %s" % deleted)
      if created:
        log("poller: create event appeared in %s" % created)
      if modified and not(deleted or created):
        log("poller: modify event appeared in %s" % modified)
      
      if modified or deleted:
        self.queue_event(DirDeletedEvent(self.watch.path + '*'))
      if modified or created:
        self.queue_event(DirCreatedEvent(self.watch.path + '*'))

class PollingObserverBase(BaseObserver):
  def __init__(self, make_snapshot, polling_interval=1):
    constructor = partial(Poller, make_snapshot=make_snapshot)
    BaseObserver.__init__(self, constructor, polling_interval)
