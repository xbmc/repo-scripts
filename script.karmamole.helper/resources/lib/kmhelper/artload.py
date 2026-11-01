# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read art bytes for an infolabel art URL, the way TMDb Helper does (resources/tmdbhelper/lib/monitor/images.py):
1) Kodi's texture cache (Thumbnails/<h>/<crc>.jpg|png; hash of the unwrapped and of the wrapped URL) - the usual hit,
   because the art is on screen when we ask; 2) the URL through the VFS; 3) a VFS copy into our profile folder."""
import os
import uuid
from urllib.parse import unquote

import xbmc
import xbmcvfs

from .common import PROFILE, log


def usable(url):
    """Skin fallbacks (DefaultAlbumCover.png ...) and empty labels are not art."""
    return bool(url) and not url.startswith('Default') and not url.startswith('special://skin/')


def _read(path):
    try:
        f = xbmcvfs.File(path, 'rb')
        try:
            return bytes(f.readBytes())
        finally:
            f.close()
    except Exception as e:  # noqa: BLE001
        log('read failed %s: %s' % (path, e))
        return b''


def load(url):
    """(bytes, stamp). stamp identifies this version of the image (cached file + size + mtime when the texture cache
    served it), so a replaced cover with the same URL gets a new soft-art file name. (b'', '') when unreadable."""
    inner = unquote(url[len('image://'):]) if url.startswith('image://') else url
    if inner.endswith('/'):
        inner = inner[:-1]
    for key in (inner, url):
        name = xbmc.getCacheThumbName(key)  # 'xxxxxxxx.tbn'
        for ext in ('jpg', 'png'):
            cached = 'special://profile/Thumbnails/%s/%s.%s' % (name[0], name[:-4], ext)
            real = xbmcvfs.translatePath(cached)
            try:
                st = os.stat(real)
            except OSError:
                continue
            data = _read(cached)
            if data:
                return data, '%s|%d|%d' % (cached, st.st_size, int(st.st_mtime))
    for path in (url, inner) if inner != url else (url,):
        data = _read(path)
        if data:
            return data, '%s|%d' % (url, len(data))
    # one temp file per call: the spine worker and the browse loop can both be here at once
    tmp = os.path.join(PROFILE, 'art.%s.tmp' % uuid.uuid4().hex)
    try:
        if not os.path.isdir(PROFILE):
            os.makedirs(PROFILE, exist_ok=True)
        if xbmcvfs.copy(url, tmp):
            with open(tmp, 'rb') as f:
                data = f.read()
            return data, '%s|%d' % (url, len(data))
    except Exception as e:  # noqa: BLE001
        log('copy failed %s: %s' % (url, e))
    finally:
        try:
            os.remove(tmp)
        except OSError:  # never created (copy failed) or already gone
            pass
    return b'', ''
