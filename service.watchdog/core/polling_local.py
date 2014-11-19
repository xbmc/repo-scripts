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
import settings
from functools import partial
from polling import Poller, PollerNonRecursive, file_list_from_walk, hidden
from utils import encode_path, decode_path


def _walk(path):
    path = encode_path(path)
    for root, dirs, files in os.walk(path):
        if dirs or files:
            for d in dirs:
                if hidden(d):
                    dirs.remove(d)
            dirs = (decode_path(os.path.join(root, d)) for d in dirs)
            files = (decode_path(os.path.join(root, f)) for f in files if not hidden(f))
            yield dirs, files


def _list_files(root):
    root = encode_path(root)
    paths = [os.path.join(root, name) for name in os.listdir(root) if not hidden(name)]
    return [decode_path(path) for path in paths if not os.path.isdir(path)]


def _get_mtime(path):
    return os.stat(encode_path(path)).st_mtime


class _Recursive(Poller):
    polling_interval = 1
    list_files = partial(file_list_from_walk(_walk))


class _NonRecursive(PollerNonRecursive):
    polling_interval = 1
    list_files = partial(_list_files)
    get_mtime = partial(_get_mtime)

LocalPoller = _Recursive if settings.RECURSIVE else _NonRecursive