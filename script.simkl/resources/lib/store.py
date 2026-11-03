#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The JSON files in the add-on profile: the login identity, the import state and the history queue. One reader, one
atomic writer."""

import json
import os

import xbmcvfs

from resources.lib import utils

IDENTITY = 'identity.json'
IMPORT_STATE = 'import_state.json'
QUEUE = 'queue.json'
HISTORY = 'history.json'
SEARCH = 'search.json'


def path(name):
    if not xbmcvfs.exists(utils.PROFILE):
        xbmcvfs.mkdirs(utils.PROFILE)
    return os.path.join(utils.PROFILE, name)


def read(name, default):
    """A file that exists but cannot be read raises: caching a default over it would write an empty state back."""
    try:
        with open(path(name), 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        utils.error('cannot read %s: %s' % (name, exc))
        raise


def write(name, data):
    """Written to a temporary file, forced to disk and renamed over the old one, so a power cut leaves either version."""
    target = path(name)
    temporary = target + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def quarantine(name):
    """Moves an unreadable file aside (name.corrupt) so a fresh one can take its place; the old one stays for a look."""
    try:
        os.replace(path(name), path(name) + '.corrupt')
        utils.error('%s was unreadable and was moved to %s.corrupt' % (name, name))
    except OSError as exc:
        utils.error('cannot move %s aside: %s' % (name, exc))
