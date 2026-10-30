# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Genre / style / mood slices for Groove's wheel, with album counts, and the "shuffled mix of a slice" action
(the random order is built here; Kodi's shuffle state is never touched).

Counting rules (they match what Kodi itself shows for the same slice):
  genre  albums with at least one song of that genre (song genres, like musicdb://genres/ and the xsp 'genre' rule)
  style  album styles (the album's own field, as the scraper wrote it)
  mood   album moods
Values are taken as the library has them; nothing is merged or renamed."""
import hashlib
import json
import random
import re
from urllib.parse import quote

from . import library

RINGS = ('genre', 'style', 'mood')
SEP = ' / '  # Kodi's default music item separator (advancedsettings <itemseparator>)


def slices(ring, albums, minimum=3):
    """[{value, count, ids, genreid}] for one ring, values with fewer than `minimum` albums dropped."""
    acc = {}
    for a in albums:
        if ring == 'genre':
            vals = {(name, gid) for gid, name in a.get('genres', [])}
        else:
            vals = {(v, None) for v in a.get('styles' if ring == 'style' else 'moods', [])}
        for name, gid in vals:
            s = acc.setdefault(name.lower(), {'value': name, 'genreid': gid, 'ids': [], 'thumbs': []})
            s['ids'].append(a['id'])
            if a.get('thumb'):
                s['thumbs'].append((a['id'], a['thumb']))
    out = []
    for s in acc.values():
        s['count'] = len(set(s['ids']))
        if s['count'] >= minimum:
            out.append(s)
    return out


def covers(s, n=4):
    """n cover URLs for the hub collage: a stable pseudo-random pick (same slice -> same covers between visits)."""
    seed = s['value'].lower()
    picks = sorted(s['thumbs'], key=lambda t: hashlib.md5(('%s|%s' % (seed, t[0])).encode('utf-8')).hexdigest())
    return [t[1] for t in picks[:n]]


def albums_path(ring, value, genreid=None):
    """musicdb:// albums of the slice (opens in MyMusicNav). Genre: the id path musicdb://genres/<id>/-1/ ("-1" = all
    artists, so it lists the genre's albums; no escaping needed for values like R&B/Soul). Style/mood: an exact-token
    xsp (Kodi stores them joined with " / ", so a plain `contains` over-matches: Rock would hit Indie Rock)."""
    if ring == 'genre' and genreid is not None:
        return 'musicdb://genres/%d/-1/' % int(genreid)
    if ring == 'genre':
        rules = {'and': [{'field': 'genre', 'operator': 'is', 'value': [value]}]}
    else:
        f = 'styles' if ring == 'style' else 'moods'
        # albumview stores the list joined with " / ": match the whole value at start, end, middle or alone
        rules = {'or': [{'field': f, 'operator': 'is', 'value': [value]},
                        {'field': f, 'operator': 'startswith', 'value': [value + SEP]},
                        {'field': f, 'operator': 'endswith', 'value': [SEP + value]},
                        {'field': f, 'operator': 'contains', 'value': [SEP + value + SEP]}]}
    xsp = {'type': 'albums', 'rules': rules, 'order': {'direction': 'ascending', 'method': 'artist'}}
    return 'musicdb://albums/?xsp=' + quote(json.dumps(xsp, separators=(',', ':')), safe='')


def find(ring, value, albums):
    v = value.lower()
    for s in slices(ring, albums, minimum=1):
        if s['value'].lower() == v:
            return s
    return None


# ---------------------------------------------------------------- shuffled play
# The random order is built here and queued in that order. Kodi's own shuffle (Player.Open "shuffled": true) is never
# used: it leaves the music playlist's live shuffle state on after the mix ends (FINAL_DEVICE_CHECK 2026-10-21 pass 2),
# so the user's next album would start shuffled. The helper never changes the user's shuffle state.
GENRE_PATH = re.compile(r'^musicdb://genres/(\d+)/(?:-1/){0,2}$')
BATCH = 200          # songs per Playlist.Add after the first one
MAX_DEPTH = 4        # musicdb folders: albums -> songs is depth 1; years/decades xsp -> albums -> songs is 2
MAX_DIRS = 2000      # stop walking a runaway tree


def song_item(entry):
    """Playlist.Item for a Files.GetDirectory / AudioLibrary.GetSongs entry, or None."""
    sid = entry.get('songid') or (entry.get('id') if entry.get('type') == 'song' else None)
    if sid:
        return {'songid': int(sid)}
    if entry.get('file') and entry.get('filetype', 'file') == 'file':
        return {'file': entry['file']}
    return None


def dedupe(items):
    seen, out = set(), []
    for it in items:
        key = json.dumps(it, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def shuffled(items, rng=None):
    """A shuffled copy (every order equally likely, the first song included)."""
    out = list(items)
    (rng or random).shuffle(out)
    return out


def songs_of_genre(genreid):
    """Every song of the genre (song genres, like musicdb://genres/<id>/-1/), singles included."""
    from .common import rpc
    res = rpc('AudioLibrary.GetSongs', {'filter': {'genreid': int(genreid)}, 'includesingles': True}) or {}
    return dedupe(filter(None, (song_item(s) for s in res.get('songs') or [])))


def songs_of_albums(ids):
    from .common import rpc
    out = []
    for i in sorted(set(ids)):
        res = rpc('AudioLibrary.GetSongs', {'filter': {'albumid': int(i)}}) or {}
        out.extend(filter(None, (song_item(s) for s in res.get('songs') or [])))
    return dedupe(out)


def walk(path):
    """(songs, complete) for every song under a musicdb:// (or any music) folder. Genre id paths take one
    AudioLibrary.GetSongs call; anything else is walked with Files.GetDirectory (media=music gives each song its library
    id). complete is False when the MAX_DIRS / MAX_DEPTH budget cut the walk short, so the caller can say so."""
    from .common import rpc
    m = GENRE_PATH.match(path)
    if m:
        return songs_of_genre(m.group(1)), True
    out, seen, todo = [], set(), [(path, 0)]
    complete = True
    while todo:
        d, depth = todo.pop(0)
        if d in seen:
            continue
        if len(seen) >= MAX_DIRS:
            complete = False  # folders left unvisited
            break
        seen.add(d)
        res = rpc('Files.GetDirectory', {'directory': d, 'media': 'music'}) or {}
        for e in res.get('files') or []:
            if e.get('filetype') == 'directory':
                if not e.get('file'):
                    continue
                if depth < MAX_DEPTH:
                    todo.append((e['file'], depth + 1))
                else:
                    complete = False  # a deeper folder is skipped
            else:
                it = song_item(e)
                if it:
                    out.append(it)
    return dedupe(out), complete


def songs_in(path):
    """Every song walk() finds under a folder (the list only)."""
    return walk(path)[0]


def live_shuffle():
    """The playing audio player's shuffle state (True/False), or None when no audio player exists. Read only, for the
    log: the helper never sets it, so a user who turned shuffle on keeps it on and everyone else keeps it off."""
    from .common import rpc
    for p in rpc('Player.GetActivePlayers') or []:
        if p.get('type') == 'audio':
            res = rpc('Player.GetProperties', {'playerid': p.get('playerid', 0), 'properties': ['shuffled']}) or {}
            return res.get('shuffled')
    return None


def start_queue(items):
    """Replace the music queue with `items` in the given order and play from the first one. The first song is queued
    and started before the rest are added (batched), so playback begins at once. No shuffle option is sent.
    Returns True when playback was started."""
    from .common import rpc, log
    if not items:
        return False
    state = live_shuffle()
    rpc('Playlist.Clear', {'playlistid': 0})
    if rpc('Playlist.Add', {'playlistid': 0, 'item': items[0]}) is None:
        return False
    if rpc('Player.Open', {'item': {'playlistid': 0, 'position': 0}}) is None:
        return False
    for i in range(1, len(items), BATCH):
        rpc('Playlist.Add', {'playlistid': 0, 'item': items[i:i + BATCH]})
    log('queued %d songs in random order (live shuffle before: %s, not changed)' % (len(items), state))
    return True


def play_shuffled(path):
    """Play every song under a music folder in a random order, the first song included. Returns True on success."""
    from .common import log
    if not path:
        return False
    items, complete = walk(path)
    ok = start_queue(shuffled(items))
    log('play_shuffled %s: %d songs -> %s%s' % (path, len(items), ok, '' if complete else ' (INCOMPLETE: walk budget)'))
    if ok and not complete:
        notify_incomplete()
    return ok


def notify_incomplete():
    """Tell the user the mix holds only part of the folder (the walk hit MAX_DIRS / MAX_DEPTH)."""
    import xbmcgui
    from .common import localize
    xbmcgui.Dialog().notification(localize(32001), localize(32002), xbmcgui.NOTIFICATION_WARNING, 6000)


def play(ring, value):
    """Replace the music queue with the slice's songs in a random order and play. Returns the number of albums used."""
    from .common import log  # Kodi-only imports kept out of the pure helpers above
    if ring not in RINGS or not value:
        return 0
    s = find(ring, value, library.albums())
    if not s:
        log('play_slice: no albums for %s=%s' % (ring, value))
        return 0
    if ring == 'genre' and s.get('genreid') is not None:
        items = songs_of_genre(s['genreid'])
    else:
        items = songs_of_albums(s['ids'])
    if not start_queue(shuffled(items)):
        log('play_slice %s=%s: nothing played (%d songs)' % (ring, value, len(items)))
        return 0
    log('play_slice %s=%s (%d albums, %d songs)' % (ring, value, s['count'], len(items)))
    return s['count']
