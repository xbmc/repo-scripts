# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""plugin://script.karmamole.helper/ routes.

  plugin://script.karmamole.helper/                              = ?info=rings
  plugin://script.karmamole.helper/?info=rings[&min=3]          the rings that have slices (Genre, Style, Mood)
  plugin://script.karmamole.helper/?info=wheel&ring=genre|style|mood[&min=3][&sort=name|count]
  plugin://script.karmamole.helper/?action=play_slice&ring=R&value=V   (RunPlugin) replace the queue, play shuffled
"""
import sys
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcgui
import xbmcplugin

from . import library, wheel
from .common import ADDON_ID, localize
from .features import allowed

BASE = 'plugin://%s/' % ADDON_ID
RING_LABEL = {'genre': 515, 'style': 176, 'mood': 175}  # Kodi core strings: Genre, Styles, Moods


def url(**kw):
    return BASE + '?' + urlencode(kw)


def _int(v, default):
    try:
        return max(1, int(v))
    except (TypeError, ValueError):
        return default


def list_rings(handle, params):
    minimum = _int(params.get('min'), 3)
    albums = library.albums()
    items = []
    for ring in wheel.RINGS:
        sl = wheel.slices(ring, albums, minimum)
        if not sl:
            continue
        covered = len({i for s in sl for i in s['ids']})
        li = xbmcgui.ListItem(xbmc.getLocalizedString(RING_LABEL[ring]), str(len(sl)), offscreen=True)
        li.setProperty('Groove.Ring', ring)
        li.setProperty('Groove.Count', str(len(sl)))
        li.setProperty('Groove.Albums', str(covered))
        li.setArt({'icon': 'DefaultMusicGenres.png'})
        items.append((url(info='wheel', ring=ring, min=minimum), li, True))
    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.setContent(handle, 'genres')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def list_wheel(handle, params):
    ring = params.get('ring', 'genre')
    if ring not in wheel.RINGS:
        ring = 'genre'
    minimum = _int(params.get('min'), 3)
    sl = wheel.slices(ring, library.albums(), minimum)
    if params.get('sort') == 'count':
        sl.sort(key=lambda s: (-s['count'], s['value'].lower()))
    else:
        sl.sort(key=lambda s: s['value'].lower())
    mix = localize(32001)  # English fallback: see common.STRINGS_EN (Kodi skips strings of copy-installed add-ons)
    items = []
    for s in sl:
        path = wheel.albums_path(ring, s['value'], s.get('genreid'))
        play = url(action='play_slice', ring=ring, value=s['value'])
        li = xbmcgui.ListItem(s['value'], str(s['count']), path=path, offscreen=True)
        cov = wheel.covers(s)
        if cov:
            li.setArt({'thumb': cov[0], 'icon': cov[0]})
        for n, c in enumerate(cov, 1):
            li.setProperty('Groove.Cover%d' % n, c)
        li.setProperty('Groove.Ring', ring)
        li.setProperty('Groove.Value', s['value'])
        li.setProperty('Groove.Count', str(s['count']))
        li.setProperty('Groove.AlbumsPath', path)
        li.setProperty('Groove.PlayPath', play)
        if s.get('genreid') is not None:
            li.setProperty('Groove.GenreID', str(s['genreid']))
        li.addContextMenuItems([(mix, 'RunPlugin(%s)' % play)])
        items.append((path, li, True))
    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.setContent(handle, 'genres')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def main():
    handle = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip('-').isdigit() else -1
    params = dict(parse_qsl(sys.argv[2].lstrip('?'))) if len(sys.argv) > 2 else {}
    if not allowed('wheel'):  # the running skin didn't ask: an empty listing (not an error), no play
        if handle >= 0:
            xbmcplugin.endOfDirectory(handle, succeeded=params.get('action') != 'play_slice', cacheToDisc=False)
        return
    if params.get('action') == 'play_slice':
        wheel.play(params.get('ring', ''), params.get('value', ''))
        if handle >= 0:
            xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    if params.get('info') == 'wheel':
        list_wheel(handle, params)
    else:
        list_rings(handle, params)

