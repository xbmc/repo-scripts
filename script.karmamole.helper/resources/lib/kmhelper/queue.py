# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Up next reordering on the music playlist (id 0).

Positions are OFFSETS from the playing song, the same numbering as MusicPlayer.offset(N): 1 = next song. The playing
song (offset 0) and the history before it are never touched. A move is a chain of adjacent Playlist.Swap calls (Kodi
posts each swap to the app thread in order, PlaylistOperations.cpp), so the songs in between shift by one, like
lifting a record out of the stack and sliding it back in elsewhere."""
import xbmc

from .common import log, rpc, set_prop

MUSIC = 0


def _current():
    """(position of the playing song in playlist 0, playlist size). Position -1 when no music plays."""
    size = (rpc('Playlist.GetProperties', {'playlistid': MUSIC, 'properties': ['size']}) or {}).get('size', 0)
    pos = -1
    for p in rpc('Player.GetActivePlayers') or []:
        if p.get('type') == 'audio':
            r = rpc('Player.GetProperties', {'playerid': p['playerid'], 'properties': ['playlistid', 'position']})
            if r and r.get('playlistid') == MUSIC:
                pos = r.get('position', -1)
    return pos, size


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def move(src, dst):
    src, dst = _int(src), _int(dst)
    if src is None or dst is None or src < 1 or dst < 1 or src == dst:
        log('queue_move ignored: from=%s to=%s' % (src, dst), xbmc.LOGWARNING)
        return False
    cur, size = _current()
    if cur < 0:  # music stopped before the action ran: offsets have no anchor, touch nothing
        log('queue_move ignored: no music playing (from=%d to=%d)' % (src, dst), xbmc.LOGWARNING)
        return False
    a, b = cur + src, cur + dst
    if a >= size or b >= size:
        log('queue_move out of range: from=%d to=%d (playing %d of %d)' % (src, dst, cur, size), xbmc.LOGWARNING)
        return False
    step = 1 if b > a else -1
    for i in range(a, b, step):
        rpc('Playlist.Swap', {'playlistid': MUSIC, 'position1': i, 'position2': i + step})
    set_prop('Groove.Queue.Moved', dst)  # the skin can put focus back on the moved card
    log('queue_move %d -> %d' % (src, dst))
    return True


def remove(offset):
    off = _int(offset)
    if off is None or off < 1:
        return False
    cur, size = _current()
    if cur < 0:  # music stopped before the action ran: offset 1 would be the first song of the queue
        log('queue_remove ignored: no music playing (offset=%d)' % off, xbmc.LOGWARNING)
        return False
    pos = cur + off
    if pos >= size:
        return False
    rpc('Playlist.Remove', {'playlistid': MUSIC, 'position': pos})
    log('queue_remove %d' % off)
    return True
