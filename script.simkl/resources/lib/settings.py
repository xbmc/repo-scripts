#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Typed access to the add-on settings. The login identity (tokens and account) lives in identity.json in the profile,
not in the Kodi settings: a setting written while the add-on's own settings dialog is open goes to the dialog instead
of the service, and every xbmcaddon instance keeps its own copy, so a multi-key identity could tear or revert there.
Keys that survive from 3.x keep their ids so nothing is lost on upgrade."""

import re
import threading

from resources.lib import store, utils

TOKEN = 'token'
REFRESH_TOKEN = 'refresh_token'
TOKEN_EXPIRES = 'token_expires'
TOKEN_SCOPE = 'token_scope'
ACCOUNT_ID = 'account_id'
ACCOUNT_NAME = 'account_name'
ACCOUNT_PLAN = 'account_plan'
IDENTITY_KEYS = (TOKEN, REFRESH_TOKEN, TOKEN_EXPIRES, TOKEN_SCOPE, ACCOUNT_ID, ACCOUNT_NAME, ACCOUNT_PLAN)

ACCOUNT_STATUS = 'account_status'
# 0 = not connected, 1 = old sign-in, 2 = new sign-in: the settings page shows Log in / Reconnect / Log out by it
LOGIN_STATE = 'login_state'
LAST_NUDGE = 'last_nudge'
LOGIN_HINT_SHOWN = 'login_hint_shown'
MIGRATED = 'migrated_v4'
AUTOSCROBBLE_LEGACY = 'autoscrobble'

SCROBBLE_MOVIES = 'scrobble_movies'
SCROBBLE_SHOWS = 'scrobble_shows'
THRESHOLD = 'scr-pct'
MIN_LENGTH = 'min-length'
BUBBLE = 'bubble'
RATE_PROMPT = 'rate_prompt'
ALLOW_REWATCH = 'allow_rewatch'
SYNC_MARKS = 'sync_marks'
SYNC_RATINGS = 'sync_ratings'

AUTO_IMPORT = 'auto_import'
AUTO_IMPORT_HOURS = 'auto_import_hours'
IMPORT_STATUS = 'import_status'
IMPORT_MISSING = 'import_missing'
IMPORT_RATINGS = 'import_ratings'
CONTINUE_WATCHING = 'continue_watching'

EXCLUDE_LIVETV = 'exclude_livetv'
EXCLUDE_HTTP = 'exclude_http'
EXCLUDE_PLUGIN = 'exclude_plugin'
EXCLUDED_PATH_SLOTS = 5

DEBUG = 'debug'
LOG_PATH = 'log_path'

V2_PREFIX = 'simkl_at_'
THRESHOLD_MIN = 50

_identity = None
_identity_lock = threading.Lock()


def _identity_state():
    """The identity dict, loaded once; the first start of 4.0 moves the 3.x pin-flow token out of the Kodi settings."""
    global _identity
    if _identity is not None:
        return _identity
    with _identity_lock:
        if _identity is not None:
            return _identity
        try:
            data = store.read(store.IDENTITY, None)
        except Exception:
            # a file that is there but cannot be read: logged out for this run, the file is left for the next start
            data = {}
        state = {key: '' for key in IDENTITY_KEYS}
        if isinstance(data, dict):
            for key in IDENTITY_KEYS:
                state[key] = str(data.get(key) or '')
        else:
            legacy = utils.addon().getSetting(TOKEN)
            if legacy:
                state[TOKEN] = legacy
            # the 3.x token leaves the Kodi settings only once identity.json holds it
            if _write_identity(state) and legacy:
                utils.addon().setSetting(TOKEN, '')
        _identity = state
        return state


def _write_identity(state):
    try:
        store.write(store.IDENTITY, state)
        return True
    except OSError as exc:
        utils.error('cannot write the login identity: %s' % exc)
        return False


def get(key, default=''):
    value = _identity_state().get(key, '') if key in IDENTITY_KEYS else utils.addon().getSetting(key)
    return value if value != '' else default


def get_bool(key, default=False):
    value = get(key).lower()
    if value in ('true', 'false'):
        return value == 'true'
    return default


def get_int(key, default=0):
    try:
        return int(float(get(key)))
    except ValueError:
        return default


def put(key, value):
    if value is True or value is False:
        value = 'true' if value else 'false'
    value = '' if value is None else str(value)
    if key in IDENTITY_KEYS:
        put_identity({key: value})
    else:
        utils.addon().setSetting(key, value)


def put_identity(values, write=True):
    """Several identity keys in one atomic write; True once the file holds them. write=False only sets the memory copy,
    to put back what the file still holds after a failed write."""
    state = _identity_state()
    with _identity_lock:
        for key, value in values.items():
            state[key] = '' if value is None else str(value)
        return _write_identity(state) if write else True


def token():
    return get(TOKEN)


def logged_in():
    return token() != ''


def is_v2(value):
    return value.startswith(V2_PREFIX)


def account_id():
    return get(ACCOUNT_ID)


def is_pro():
    return get(ACCOUNT_PLAN).lower() in ('pro', 'vip')


def tracked(kind):
    """Whether playbacks and marks of this kind (movie, else episode/show) go to Simkl: the switch per type."""
    return get_bool(SCROBBLE_MOVIES if kind == 'movie' else SCROBBLE_SHOWS, True)


def threshold():
    return min(100, max(THRESHOLD_MIN, get_int(THRESHOLD, 70)))


def min_length_seconds():
    return max(0, get_int(MIN_LENGTH, 5)) * 60


def excluded_paths():
    paths = []
    for slot in range(1, EXCLUDED_PATH_SLOTS + 1):
        if not get_bool('exclude_path%d_on' % slot):
            continue
        path = get('exclude_path%d' % slot)
        if path:
            # matched as a prefix: the separator keeps "D:\Movies" from covering "D:\Movies2"
            paths.append(path if path.endswith(('/', '\\')) else path + ('\\' if '\\' in path else '/'))
    return paths


def _stored_setting(key):
    """A value as written in the profile's settings.xml (Kodi drops an out-of-range value at load, so the API never
    shows it); None when the file or the key is not there."""
    try:
        with open(store.path('settings.xml'), 'r', encoding='utf-8') as handle:
            text = handle.read()
    except OSError:
        return None
    match = re.search(r'<setting id="%s"(?: value="([^"]*)")?[^>]*>(?:([^<]*)</setting>)?' % re.escape(key), text)
    if not match:
        return None
    return (match.group(1) if match.group(1) is not None else match.group(2) or '').strip()


def migrate():
    """3.x had one tracking switch; 4.0 has one per type. A 3.x threshold below the new minimum is lifted to it. 3.x
    applied its minimum length in seconds under a label that said minutes: a stored value over 30 is taken as seconds.
    Runs once."""
    if get_bool(MIGRATED):
        return
    stored = _stored_setting(THRESHOLD)
    # read raw as well: 4.0 declares the minimum length 0..600, so Kodi answers the default for a 3.x value above that
    raw = _stored_setting(MIN_LENGTH)
    if utils.addon().getSetting(AUTOSCROBBLE_LEGACY).lower() == 'false':
        put(SCROBBLE_MOVIES, False)
        put(SCROBBLE_SHOWS, False)
    try:
        if stored is not None and int(float(stored)) < THRESHOLD_MIN:
            put(THRESHOLD, THRESHOLD_MIN)
    except ValueError:
        pass
    try:
        minutes = int(float(raw))
    except (TypeError, ValueError):
        minutes = get_int(MIN_LENGTH, 5)
    if minutes > 30:
        put(MIN_LENGTH, min(600, max(1, int(round(minutes / 60.0)))))
    put(MIGRATED, True)
