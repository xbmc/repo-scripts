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
import sys
import xbmc
import xbmcvfs
import xbmcgui
import subprocess
import simplejson as json
from urllib import unquote


def log(msg):
    import settings
    xbmc.log("%s: %s" % (settings.ADDON_ID, msg), xbmc.LOGDEBUG)


def escape_param(s):
    escaped = s.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + escaped + '"'


def notify(msg1, msg2):
    import settings
    if settings.SHOW_NOTIFICATIONS:
        dialog = xbmcgui.Dialog()
        dialog.notification("Watchdog: %s" % msg1, msg2,
                            xbmcgui.NOTIFICATION_WARNING, 2000)


def rpc(method, **params):
    params = json.dumps(params)
    query = '{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, params)
    return json.loads(xbmc.executeJSONRPC(query))


def select_observer(path):
    # path assumed to be utf-8 encoded string
    import settings
    import observers
    if os.path.exists(path):
        if settings.POLLING:
            return path, observers.get(observers.poller_local)
        elif _is_remote_filesystem(path):
            log("select_observer: path <%s> identified as remote filesystem" % path)
            return path, observers.get(observers.poller_local)
        return path, observers.get(observers.preferred)

    # try using fs encoding
    fsenc = sys.getfilesystemencoding()
    if fsenc:
        try:
            path_alt = path.decode('utf-8').encode(fsenc)
        except UnicodeEncodeError:
            path_alt = None
        if path_alt and os.path.exists(path_alt):
            if settings.POLLING:
                return path_alt, observers.get(observers.poller_local)
            return path_alt, observers.get(observers.preferred)

    if xbmcvfs.exists(path):
        cls = [observers.xbmc_depth_1, observers.xbmc_depth_2,
               observers.xbmc_full][settings.POLLING_METHOD]
        return path, observers.get(cls)
    raise IOError("No such directory: '%s'" % path)


def _is_remote_filesystem(path):
    from watchdog.utils import platform
    REMOTE_FSTYPES = '|cifs|smbfs|nfs|nfs4|'
    if platform.is_linux():
        try:
            df = subprocess.Popen(['df', '--output=fstype', path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = df.communicate()
            if df.returncode == 0:
                fstype = stdout.rstrip('\n').split('\n')[1]
                log("df. fstype of <%s> is %s" % (path, fstype))
                return fstype and REMOTE_FSTYPES.find('|%s|' % fstype) != -1
            else:
                log("df returned %d, %s" % (df.returncode, stderr))
        except Exception as e:
            log("df failed. %s, %s" % (type(e), e))
    return False


def get_media_sources(media_type):
    response = rpc("Files.GetSources", media=media_type)
    ret = []
    if response.has_key('result'):
        if response['result'].has_key('sources'):
            paths = [e['file'] for e in response['result']['sources']]
            for path in paths:
                #split and decode multipaths
                if path.startswith("multipath://"):
                    for e in path.split("multipath://")[1].split('/'):
                        if e != "":
                            ret.append(unquote(e).encode('utf-8'))
                elif not path.startswith("upnp://"):
                    ret.append(path.encode('utf-8'))
    return ret
