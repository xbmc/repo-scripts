# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""A small cached index of the music library's albums, shared by the wheel plugin and the spine builder.

The cache (addon_data/script.karmamole.helper/library.json) is keyed by a library signature from
AudioLibrary.GetProperties, so it is rebuilt only after the library changes (scan, clean, edit)."""
import json
import os

from .common import PROFILE, log, rpc, write_json, read_json

SIG_PROPS = ['albumslastadded', 'albumsmodified', 'songslastadded', 'songsmodified', 'librarylastupdated',
             'librarylastcleaned', 'genreslastadded']
ALBUM_PROPS = ['title', 'displayartist', 'year', 'style', 'mood', 'songgenres', 'art', 'thumbnail']
CACHE = os.path.join(PROFILE, 'library.json')
VERSION = 1


def signature():
    r = rpc('AudioLibrary.GetProperties', {'properties': SIG_PROPS})
    return json.dumps(r, sort_keys=True) if r else ''


def _thumb(a):
    art = a.get('art') or {}
    return art.get('thumb') or a.get('thumbnail') or ''


def albums(sig=None):
    """[{id, title, artist, year, thumb, genres: [[genreid, name]], styles, moods}] for every library album."""
    sig = sig if sig is not None else signature()
    cached = read_json(CACHE, {})
    if sig and cached.get('v') == VERSION and cached.get('sig') == sig:
        return cached.get('albums', [])
    r = rpc('AudioLibrary.GetAlbums', {'properties': ALBUM_PROPS})
    if r is None:  # a failed request is not an empty library: cache nothing, so the next call asks again
        log('library index: AudioLibrary.GetAlbums failed, not cached')
        return []
    out = []
    for a in r.get('albums', []):
        out.append({
            'id': a.get('albumid'),
            'title': a.get('title') or a.get('label') or '',
            'artist': a.get('displayartist') or '',
            'year': a.get('year') or 0,
            'thumb': _thumb(a),
            'genres': [[g.get('genreid'), g.get('title') or ''] for g in (a.get('songgenres') or [])
                       if g.get('title')],
            'styles': [s for s in (a.get('style') or []) if s],
            'moods': [m for m in (a.get('mood') or []) if m],
        })
    if sig:
        try:
            write_json(CACHE, {'v': VERSION, 'sig': sig, 'albums': out})
        except OSError as e:
            log('library cache not written: %s' % e)
    log('library index: %d albums' % len(out))
    return out
