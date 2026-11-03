#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Kodi plumbing shared by every module: add-on handle, logging, toasts, JSON-RPC, dates."""

import calendar
import json
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.simkl'
_addon = xbmcaddon.Addon(ADDON_ID)
ADDON_VERSION = _addon.getAddonInfo('version')
ADDON_PATH = _addon.getAddonInfo('path')
ICON = _addon.getAddonInfo('icon')
PROFILE = xbmcvfs.translatePath(_addon.getAddonInfo('profile'))
KODI_VERSION = xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]

STAMP = '%Y-%m-%dT%H:%M:%SZ'
KODI_DATE = '%Y-%m-%d %H:%M:%S'
_YEAR_2000 = 946684800

# the add-on's own lines go out at DEBUG (Kodi's rule for add-ons); with the debug setting on they go out at INFO so
# they show without Kodi's debug mode. Warnings and errors always show
VERBOSE = False


def addon():
    return _addon


def kodi_log_path():
    return xbmcvfs.translatePath('special://logpath/kodi.log')


def reload_addon():
    global _addon
    _addon = xbmcaddon.Addon(ADDON_ID)


def log(message):
    xbmc.log('[%s] %s' % (ADDON_ID, message), xbmc.LOGINFO if VERBOSE else xbmc.LOGDEBUG)


def warn(message):
    xbmc.log('[%s] %s' % (ADDON_ID, message), xbmc.LOGWARNING)


def error(message):
    xbmc.log('[%s] %s' % (ADDON_ID, message), xbmc.LOGERROR)


def get_str(string_id):
    return _addon.getLocalizedString(string_id)


def notify(message, title='Simkl', time_ms=5000):
    xbmcgui.Dialog().notification(title, message, ICON, time_ms, False)


def jsonrpc(method, params=None):
    request = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params is not None:
        request['params'] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        warn('JSON-RPC %s failed: %s' % (method, response['error']))
        return None
    return response.get('result')


def jsonrpc_batch(calls):
    """calls: list of (method, params); the answers come back aligned with the calls, None when Kodi refused the whole batch."""
    if not calls:
        return []
    request = [{'jsonrpc': '2.0', 'method': method, 'params': params, 'id': index} for index, (method, params) in enumerate(calls)]
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if not isinstance(response, list):
        warn('JSON-RPC batch failed: %s' % (response.get('error') if isinstance(response, dict) else response))
        return None
    by_id = {answer.get('id'): answer for answer in response if isinstance(answer, dict)}
    return [by_id.get(index, {'error': 'no answer'}) for index in range(len(calls))]


def utc_stamp(ts=None):
    return time.strftime(STAMP, time.gmtime(time.time() if ts is None else ts))


def parse_stamp(value):
    """Simkl date -> epoch seconds; None for a missing date or Simkl's 'unknown' sentinel (before 2000). The fixed
    2026-10-25T20:00:00Z shape is sliced (an import parses one per episode); anything else goes through strptime."""
    if not value:
        return None
    text = str(value)
    try:
        if len(text) == 20 and text[4] == '-' and text[10] == 'T' and text[19] == 'Z':
            ts = calendar.timegm((int(text[0:4]), int(text[5:7]), int(text[8:10]), int(text[11:13]), int(text[14:16]), int(text[17:19]), 0, 0, 0))
        else:
            ts = calendar.timegm(time.strptime(text, STAMP))
    except (ValueError, TypeError, OverflowError):
        return None
    return ts if ts > _YEAR_2000 else None


def kodi_date_to_ts(value):
    """Kodi's lastplayed/dateadded are local wall time."""
    if not value:
        return None
    try:
        return time.mktime(time.strptime(value, KODI_DATE))
    except (ValueError, OverflowError):
        return None


def ts_to_kodi_date(ts):
    return time.strftime(KODI_DATE, time.localtime(ts))


def format_duration(seconds):
    seconds = max(0, int(seconds))
    if seconds >= 120:
        return get_str(32237).format(seconds // 60)
    return get_str(32238).format(seconds)


ID_KEYS = ('imdb', 'tmdb', 'tvdb', 'anidb', 'mal', 'anilist', 'simkl')


def ids_from(uniqueid):
    """A Kodi uniqueid dict, or any {name: id} object an add-on hands over, -> the Simkl id keys that are set and real.
    Names are taken case-insensitively and with or without an _id suffix (tmdb, TMDB, tmdb_id)."""
    ids = {}
    if not isinstance(uniqueid, dict):
        return ids
    for raw, value in uniqueid.items():
        key = str(raw).lower()
        if key.endswith('_id'):
            key = key[:-3]
        value = str(value or '').strip()
        if key in ID_KEYS and value and value != '0':
            ids[key] = value
    return ids
