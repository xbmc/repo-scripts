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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import xbmc
import json
import time
from utils import is_url, rpc, log


def _split_path(path):
    sep = '/' if is_url(path) else os.sep
    folder, filename = path.rsplit(sep, 1)
    return folder + sep, filename


def _rpc_remove_video(media_type, media_id):
    method = "VideoLibrary.Remove%s" % media_type
    params = {'%sid' % media_type: media_id}
    response = rpc(method, **params)
    if response.get('result') != 'OK':
        log("[rpc] failed to remove %s with id %s. response: %s"
            % (media_type, media_id, json.dumps(response, indent=4)), xbmc.LOGERROR)
        return False
    return True


def _remove_video(path, filename):
    params = {
        'properties': ['file'],
        'filter': {
            'and': [
                {'operator': 'is', 'field': 'path', 'value': path},
                {'operator': 'is', 'field': 'filename', 'value': filename}
            ]
        }
    }

    movies = rpc('VideoLibrary.GetMovies', **params).get('result', {}).get('movies', [])
    if movies:
        return _rpc_remove_video('movie', movies[0]['movieid'])

    episodes = rpc('VideoLibrary.GetEpisodes', **params).get('result', {}).get('episodes', [])
    if episodes:
        return _rpc_remove_video('episode', episodes[0]['episodeid'])

    return False


def remove_video(path):
    start = time.time()
    foldername, filename = _split_path(path)
    if _remove_video(foldername, filename):
        t = time.time() - start
        log("[videolibrary] successfully removed '%r' from database in %.0f ms." % (path, t*1000))
    else:
        log("[videolibrary] No media with path '%r' and name '%r' in database" % (foldername, filename))
