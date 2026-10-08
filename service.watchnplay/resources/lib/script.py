# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Skript-Einstieg: Programme-Menue und Knoepfe in den Einstellungen.

Argumente: connect | disconnect | syncnow (ohne Argument: passendes Menue).
"""

import sys

import xbmcgui

from resources.lib import pairing, util
from resources.lib.api import Api, ApiError
from resources.lib.store import Store


def disconnect(store, confirm=True):
    if confirm and not xbmcgui.Dialog().yesno('WatchNPlay', util.lang(32021)):
        return
    token = store.token
    if token:
        try:
            Api(util.api_base(), util.user_agent(), token).unpair()
        except ApiError as exc:
            # lokal trotzdem trennen; das Geraet laesst sich in der App entfernen
            util.warn('unpair failed: %s' % exc.status)
    store.clear_auth()
    # Warteschlange gehoert zu diesem Konto: auch dann leeren, wenn der Dienst gerade
    # nicht laeuft, sonst ginge sie nach der naechsten Kopplung an ein anderes Konto
    store.clear_queue()
    store.reset_state()
    util.set_status(False)
    util.notify_service('unpaired')
    util.notify(util.lang(32020))


def sync_now():
    util.notify_service('syncnow')
    util.notify(util.lang(32022))


def menu(store):
    user = store.state.get('userName') or store.auth.get('userName') or ''
    choice = xbmcgui.Dialog().select(util.lang(32006) % user, [util.lang(32004), util.lang(32003)])
    if choice == 0:
        sync_now()
    elif choice == 1:
        disconnect(store)


def main(argv):
    store = Store(util.profile_dir())
    arg = argv[1] if len(argv) > 1 else ''
    if arg == 'disconnect':
        if store.token:
            disconnect(store)
        return
    if arg == 'syncnow':
        if store.token:
            sync_now()
        return
    if store.token:
        menu(store)
    else:
        pairing.run(store)
