#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The Simkl entry of the context menu: one select dialog for the focused movie, show, season or episode. The choice
goes to the running service, which owns the queue and the account."""

import json
import os
import sys

import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import focus

ADDON_ID = 'script.simkl'
ACTIONS =(('ctx_mark', 32250), ('ctx_unmark', 32251), ('ctx_plantowatch', 32252), ('ctx_rate', 32275), ('import_check', 32253))


def _logged_in(addon):
    """The service keeps the login in identity.json; before its first run the 3.x token setting is the only trace."""
    try:
        with open(os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'identity.json'), 'r', encoding='utf-8') as handle:
            return bool((json.load(handle) or {}).get('token'))
    except (OSError, ValueError):
        return bool(addon.getSetting('token'))


def _kodi_marks_reach_simkl(addon, payload):
    """Kodi's own Mark as watched / unwatched on a library item already goes to Simkl while the marks switch and the
    tracking of the item's type are on; the Simkl entries for marks then only matter for files outside the library and
    add-on items, which Kodi never reports, and for a type whose tracking is off."""
    tracked = 'scrobble_movies' if payload.get('dbtype') == 'movie' else 'scrobble_shows'
    return int(payload.get('dbid') or 0) > 0 and addon.getSetting('sync_marks').lower() != 'false' and addon.getSetting(tracked).lower() != 'false'


def _actions(addon, payload):
    """The entries for this row. Where Kodi's own mark already reaches Simkl the Simkl marks are left out, except
    "Remove from Simkl history" on a season or a show: Kodi's own unmark of those is never sent (a burst, which the
    queue drops). Plan to watch is left out for a library movie Kodi has as watched: Simkl would take it out of the
    watched list."""
    reach = _kodi_marks_reach_simkl(addon, payload)
    whole = payload.get('dbtype') in ('season', 'tvshow')
    planned = not focus.watched_movie(payload)
    return [entry for entry in ACTIONS
            if (entry[0] not in ('ctx_mark', 'ctx_unmark') or not reach or (entry[0] == 'ctx_unmark' and whole))
            and (entry[0] != 'ctx_plantowatch' or planned)]


def main():
    addon = xbmcaddon.Addon(ADDON_ID)
    if not _logged_in(addon):
        focus.toast(addon, addon.getLocalizedString(32224))
        return
    payload = focus.from_listitem(sys.listitem)
    actions = _actions(addon, payload)
    choice = xbmcgui.Dialog().select('Simkl', [addon.getLocalizedString(string_id) for _, string_id in actions])
    if choice < 0:
        return
    action = actions[choice][0]
    refused = None if action == 'import_check' else focus.refusal(payload, action, pick=action == 'ctx_rate')
    if refused:
        # what the service would refuse anyway, said before a pick
        focus.toast(addon, addon.getLocalizedString(refused).format(focus.rating_subject(payload)[0]))
        return
    if action == 'ctx_rate':
        label, current = focus.rating_subject(payload)
        payload['rating'] = focus.pick_rating(addon, label, current)
        if payload['rating'] is None:
            return
    focus.notify_service(action, None if action == 'import_check' else payload)


if __name__ == '__main__':
    main()
