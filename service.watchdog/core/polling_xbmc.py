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

import xbmcvfs
import settings
from functools import partial
from polling import Poller, PollerNonRecursive, file_list_from_walk, hidden
from utils import raise_if_aborted


def _walk(path):
    raise_if_aborted()
    dirs, files = xbmcvfs.listdir(path)
    # xbmcvfs bug: sometimes return invalid utf-8 encoding. we only care about
    # finding changed paths so it's ok to ignore here.
    dirs = [path + _.decode('utf-8', 'ignore') for _ in dirs if not hidden(_)]
    files = [path + _.decode('utf-8', 'ignore') for _ in files if not hidden(_)]
    yield dirs, files
    for d in dirs:
        for dirs, files in _walk(d + '/'):
            yield dirs, files


def _list_files(path):
    dirs, files = xbmcvfs.listdir(path)
    return [path + '/' + f.decode('utf-8', 'ignore') for f in files if not hidden(f)]


def _get_mtime(path):
    return xbmcvfs.Stat(path).st_mtime()


class _Recursive(Poller):
    polling_interval = settings.POLLING_INTERVAL
    list_files = partial(file_list_from_walk(_walk))

    def is_offline(self):
        # Since path is always a media source, it's unlikely the user would
        # delete it. Assume it's offline if it doesn't exist.
        return not xbmcvfs.exists(self.watch.path)


class _NonRecursive(PollerNonRecursive):
    polling_interval = 1
    list_files = partial(_list_files)
    get_mtime = partial(_get_mtime)

VFSPoller = _Recursive if settings.RECURSIVE else _NonRecursive