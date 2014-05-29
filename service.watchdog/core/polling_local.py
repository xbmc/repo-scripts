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
from functools import partial
from polling import *

def _walker_recursive(top):
    for root, dirs, files in os.walk(top):
        if dirs or files:
            for d in dirs:
                if hidden(d):
                    dirs.remove(d)
            dirs = (os.path.join(root, _)  for _ in dirs)
            files = (os.path.join(root, _) for _ in files if not hidden(_))
            yield dirs, files

def _walker_depth_1(top):
    names = [ os.path.join(top, name) for name in os.listdir(top) if not hidden(name)]
    dirs = [ name for name in names if os.path.isdir(name) ]
    files = [ name for name in names if not os.path.isdir(name) ]
    yield dirs, files

def _get_mtime(path):
    return os.stat(path).st_mtime

class PollerObserver_Depth1(PollingObserverBase):
    def __init__(self):
        make_snapshot = partial(SnapshotRootOnly, get_mtime=_get_mtime)
        PollingObserverBase.__init__(self, make_snapshot, polling_interval=1)

class PollerObserver_Depth2(PollingObserverBase):
    def __init__(self):
        make_snapshot = partial(SnapshotWithStat, walker=_walker_depth_1, get_mtime=_get_mtime)
        PollingObserverBase.__init__(self, make_snapshot, polling_interval=1)

class PollerObserver_Full(PollingObserverBase):
    def __init__(self):
        make_snapshot = partial(PathSnapshot, walker=_walker_recursive)
        PollingObserverBase.__init__(self, make_snapshot, polling_interval=1)
