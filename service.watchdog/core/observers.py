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
from polling_local import PollerObserver_Full as poller_local
from polling_xbmc import PollerObserver_Depth1 as xbmc_depth_1
from polling_xbmc import PollerObserver_Depth2 as xbmc_depth_2
from polling_xbmc import PollerObserver_Full as xbmc_full

try:
    from watchdog.observers.inotify import InotifyObserver as _Observer
except:
    try:
        from watchdog.observers.kqueue import KqueueObserver as _Observer
    except:
        try:
            from watchdog.observers.read_directory_changes import WindowsApiObserver as _Observer
        except:
            _Observer = poller_local

preferred = _Observer
_instances = {}

def get(cls):
    if cls not in _instances:
        _instances[cls] = cls()
    return _instances[cls]
