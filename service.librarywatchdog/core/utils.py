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



import os
import re
import sys
import xbmc
import xbmcgui
import json
from urllib.parse import unquote
from threading import Condition

monitor = xbmc.Monitor()

def log(msg, level=xbmc.LOGDEBUG):
    from . import settings
    xbmc.log(("[" + settings.ADDON_ID + "] " + msg), level)


def is_url(path):
    return re.match(r'^[A-z]+://', path) is not None


def escape_param(s):
    escaped = s.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + escaped + '"'


def rpc(method, **params):
    params = json.dumps(params)
    query = b'{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method.encode(), params.encode())
    return json.loads(xbmc.executeJSONRPC(query.decode()), encoding='utf-8')


def _split_multipaths(paths):
    ret = []
    for path in paths:
        if path.startswith("multipath://"):
            subpaths = path.split("multipath://")[1].split('/')
            subpaths = [unquote(path) for path in subpaths if path != ""]
            ret.extend(subpaths)
        else:
            ret.append(path)
    return ret


def get_media_sources(media_type):
    response = rpc('Files.GetSources', media=media_type)
    paths = [s['file'] for s in response.get('result', {}).get('sources', [])]
    paths = _split_multipaths(paths)
    return [path for path in paths if not path.startswith('upnp://')]


class OrderedSetQueue(object):
    """Queue with no repetition. Since we only have one consumer thread, this
    is simplified version."""

    def __init__(self):
        self.queue = []
        self.not_empty = Condition()

    def size(self):
        return len(self.queue)

    def put(self, item):
        self.not_empty.acquire()
        try:
            if item in self.queue:
                return
            self.queue.append(item)
            self.not_empty.notify()
        finally:
            self.not_empty.release()

    def get_nowait(self):
        self.not_empty.acquire()
        try:
            return self.queue.pop(0)
        finally:
            self.not_empty.release()

    def wait(self):
        """Wait for item to become available."""
        self.not_empty.acquire()
        try:
            while len(self.queue) == 0:
                self.not_empty.wait()
        finally:
            self.not_empty.release()


class XBMCInterrupt(Exception):
    pass


def raise_if_aborted():
    if monitor.abortRequested():
        raise XBMCInterrupt
