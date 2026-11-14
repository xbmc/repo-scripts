#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The focused list item as the payload the service's context actions take: from sys.listitem (context menu) or from
the ListItem.* info labels (RunScript from a skin or a keymap). Kept free of the service's own imports: both callers
are short-lived scripts."""

import base64
import json

import xbmc
import xbmcgui

ADDON_ID = 'script.simkl'
ID_KEYS = ('imdb', 'tmdb', 'tvdb', 'anidb', 'mal', 'anilist', 'simkl')
# where an add-on puts the show's ids on its episode items, as for a playback (README): the JSON property, else flat ones
IDS_PROPERTIES = ('script.simkl.ids', 'script.trakt.ids')
SHOW_PREFIX = 'tvshow.'
SHOW_ID_PROPERTIES = tuple(SHOW_PREFIX + key + '_id' for key in ID_KEYS)


def notify_service(action, payload=None):
    """Hands an action to the running service: NotifyAll(script.simkl, <action>, {"data": base64 JSON}). The item
    travels with its own notification (a shared window property would be overwritten by the next action before the
    service read it); base64 keeps Kodi's builtin parser from splitting the JSON at its commas."""
    data = '' if payload is None else ', {"data": "%s"}' % base64.b64encode(json.dumps(payload).encode('utf-8')).decode('ascii')
    xbmc.executebuiltin('NotifyAll(%s, %s%s)' % (ADDON_ID, action, data))


def toast(addon, text):
    xbmcgui.Dialog().notification('Simkl', text, addon.getAddonInfo('icon'), 5000, False)


def refusal(payload, action, pick=False):
    """The string the service would answer this action with, said before any pick: an episode outside the library whose
    show the add-on did not name (nothing of it can reach Simkl); a rating pick for a library movie Kodi has as
    unwatched (Simkl files a rated movie as watched); Plan to watch for a library movie Kodi has as watched (Simkl would
    take it out of the watched list). None when nothing stands in the way."""
    if payload.get('dbtype') == 'episode' and int(payload.get('dbid') or 0) <= 0 and not payload.get('show_ids'):
        return 32271
    if action == 'ctx_rate' and pick and unwatched_movie(payload):
        return 32299
    if action == 'ctx_plantowatch' and watched_movie(payload):
        return 32314
    return None


def _movie_playcount(payload):
    """Kodi's play count of the library movie a row is about; None for any other row, or without an answer (the service
    decides then)."""
    if payload.get('dbtype') != 'movie' or int(payload.get('dbid') or 0) <= 0:
        return None
    request = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params': {'movieid': int(payload['dbid']), 'properties': ['playcount']}, 'id': 1}
    try:
        details = ((json.loads(xbmc.executeJSONRPC(json.dumps(request))) or {}).get('result') or {}).get('moviedetails') or {}
    except ValueError:
        return None
    return int(details.get('playcount') or 0) if 'playcount' in details else None


def unwatched_movie(payload):
    return _movie_playcount(payload) == 0


def watched_movie(payload):
    return (_movie_playcount(payload) or 0) > 0


def _usable(ids):
    """The Simkl ids of a {name: id} object, as the service normalises them (utils.ids_from, which this module cannot
    import): names case-insensitive, with or without an _id suffix, values that are set and real."""
    usable = {}
    if not isinstance(ids, dict):
        return usable
    for raw, value in ids.items():
        key = str(raw).lower()
        if key.endswith('_id'):
            key = key[:-3]
        value = str(value or '').strip()
        if key in ID_KEYS and value and value != '0':
            usable[key] = value
    return usable


def _show_ids(read):
    """The show's ids an add-on put on its episode item: the first id property holding Simkl ids (one with only trakt
    ids does not count), else the flat tvshow.*_id ones; read(name) is the property's value."""
    for name in IDS_PROPERTIES:
        try:
            ids = _usable(json.loads(read(name) or 'null'))
        except ValueError:
            ids = {}
        if ids:
            return ids
    return _usable({name[len(SHOW_PREFIX):]: read(name) for name in SHOW_ID_PROPERTIES})


def pick_rating(addon, label, current=0, skip=False):
    """A pick of 10 down to 1, or 0 to remove the rating; None when cancelled. The current rating is preselected; skip
    adds a first "Not now" entry, preselected when there is no rating, so a stray OK changes nothing."""
    current = int(current or 0)
    offset = 1 if skip else 0
    options = ([addon.getLocalizedString(32300)] if skip else []) + [str(n) for n in range(10, 0, -1)] + [addon.getLocalizedString(32276)]
    preselect = offset + 10 - current if 1 <= current <= 10 else (0 if skip else -1)
    choice = xbmcgui.Dialog().select('%s: %s' % (addon.getLocalizedString(32275), label), options, preselect=preselect)
    if choice < offset:
        return None
    index = choice - offset
    return 0 if index == 10 else 10 - index


def rating_subject(payload):
    """What a rating from this row is about: the show of an episode or a season row (Simkl rates no episodes), else the
    item itself; and its current Kodi rating where that is the item's own."""
    dbtype = payload.get('dbtype')
    label = (payload.get('showtitle') if dbtype in ('episode', 'season', 'tvshow') else payload.get('label')) or payload.get('label') or ''
    return label, payload.get('userrating') if dbtype in ('movie', 'tvshow') else 0


def _unique_id(item, tag, key):
    try:
        return tag.getUniqueID(key)
    except AttributeError:
        pass
    try:
        return item.getUniqueID(key)
    except AttributeError:
        return ''


def from_listitem(item):
    tag = item.getVideoInfoTag()
    ids = {}
    for key in ID_KEYS:
        value = str(_unique_id(item, tag, key) or '').strip()
        if value and value != '0':
            ids[key] = value
    try:
        dbid = int(tag.getDbId())
    except (AttributeError, ValueError, TypeError):
        dbid = int(xbmc.getInfoLabel('ListItem.DBID') or 0)
    try:
        dbtype = (tag.getMediaType() or '').lower()
    except AttributeError:
        dbtype = ''
    try:
        path = item.getPath()
    except AttributeError:
        path = ''
    try:
        userrating = int(tag.getUserRating())
    except (AttributeError, ValueError, TypeError):
        userrating = _label_int('ListItem.UserRating')
    return {
        'dbtype': dbtype or xbmc.getInfoLabel('ListItem.DBTYPE').lower(),
        'dbid': dbid,
        'ids': ids,
        'show_ids': _show_ids(item.getProperty),
        'userrating': userrating,
        'season': tag.getSeason(),
        'number': tag.getEpisode(),
        'showtitle': tag.getTVShowTitle(),
        'title': tag.getTitle() or item.getLabel(),
        'year': tag.getYear(),
        'label': item.getLabel(),
        'file': path or xbmc.getInfoLabel('ListItem.FilenameAndPath'),
    }


def _label_int(name):
    try:
        return int(xbmc.getInfoLabel(name) or 0)
    except ValueError:
        return 0


def from_infolabels():
    """The item under the cursor of the current list, the only view RunScript has of it."""
    ids = {}
    for key in ID_KEYS:
        value = xbmc.getInfoLabel('ListItem.UniqueID(%s)' % key).strip()
        if value and value != '0':
            ids[key] = value
    season = xbmc.getInfoLabel('ListItem.Season').strip()
    return {
        'dbtype': xbmc.getInfoLabel('ListItem.DBTYPE').lower(),
        'dbid': _label_int('ListItem.DBID'),
        'ids': ids,
        'show_ids': _show_ids(lambda name: xbmc.getInfoLabel('ListItem.Property(%s)' % name)),
        'userrating': _label_int('ListItem.UserRating'),
        # a special's season is 0; only an unknown one is -1 (season 1 to Simkl)
        'season': int(season) if season.isdigit() else -1,
        'number': _label_int('ListItem.Episode'),
        'showtitle': xbmc.getInfoLabel('ListItem.TVShowTitle'),
        'title': xbmc.getInfoLabel('ListItem.Title') or xbmc.getInfoLabel('ListItem.Label'),
        'year': _label_int('ListItem.Year'),
        'label': xbmc.getInfoLabel('ListItem.Label'),
        'file': xbmc.getInfoLabel('ListItem.FilenameAndPath'),
    }
