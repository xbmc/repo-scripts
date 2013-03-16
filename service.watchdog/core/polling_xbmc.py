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
import xbmcvfs
from functools import partial
from polling import *

def _join_path(base, lst):
  return [ os.path.join(base, _) for _ in lst if not hidden(_) ]

def _walker_recursive(top):
  dirs, files = xbmcvfs.listdir(top) #returns utf-8 encoded str
  dirs = _join_path(top, dirs)
  files = _join_path(top, files)
  yield dirs, files
  for d in dirs:
    for dirs, files in _walker_recursive(d):
      yield dirs, files

def _walker_depth_1(top):
  dirs, files = xbmcvfs.listdir(top) #returns utf-8 encoded str
  yield _join_path(top, dirs), _join_path(top, files)

def _get_mtime(path):
  return xbmcvfs.Stat(path).st_mtime()

class PollerObserver_Depth1(PollingObserverBase):
  def __init__(self):
    make_snapshot = partial(SnapshotRootOnly, get_mtime=_get_mtime)
    PollingObserverBase.__init__(self, make_snapshot, polling_interval=2)

class PollerObserver_Depth2(PollingObserverBase):
  def __init__(self):
    make_snapshot = partial(SnapshotWithStat, walker=_walker_depth_1, get_mtime=_get_mtime)
    PollingObserverBase.__init__(self, make_snapshot, polling_interval=4)

class PollerObserver_Full(PollingObserverBase):
  def __init__(self):
    make_snapshot = partial(PathSnapsot, walker=_walker_recursive)
    PollingObserverBase.__init__(self, make_snapshot, polling_interval=4)
