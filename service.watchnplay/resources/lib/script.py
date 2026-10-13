# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Skript-Einstieg: Programme-Menue und Knoepfe in den Einstellungen.

Argumente: connect | disconnect | syncnow (ohne Argument: passendes Menue).
"""

import sys

import xbmc
import xbmcgui

from resources.lib import pairing, util
from resources.lib.api import Api, ApiError
from resources.lib.store import Store


def _confirm(message):
    """Ja/Nein mit Fokus auf Ja: mit der Fernbedienung bestaetigt OK sonst 'Nein', und das
    Trennen wirkt wie kaputt (Betreiber 13.10.2026, Shield). Kodi 19 kennt defaultbutton nicht."""
    dialog = xbmcgui.Dialog()
    try:
        return dialog.yesno('WatchNPlay', message, defaultbutton=xbmcgui.DLG_YESNO_YES_BTN)
    except (TypeError, AttributeError):
        return dialog.yesno('WatchNPlay', message)


def _forget(store):
    """Lokal trennen. Jeder Schritt einzeln: scheitert einer (Datei gerade vom Dienst
    geschrieben), darf die Anzeige trotzdem nicht auf 'verbunden' stehen bleiben."""
    for step in (store.clear_auth, store.clear_queue, store.reset_state):
        try:
            step()
        except OSError as exc:
            util.warn('disconnect step failed: %s' % exc)
    util.set_status(False)
    util.notify_service('unpaired')


def disconnect(store, confirm=True):
    if confirm and not _confirm(util.lang(32021)):
        return False
    token = store.token
    if token:
        try:
            Api(util.api_base(), util.user_agent(), token).unpair()
        except ApiError as exc:
            # lokal trotzdem trennen; das Geraet laesst sich in der App entfernen
            util.warn('unpair failed: %s' % exc.status)
    _forget(store)
    util.notify(util.lang(32020))
    return True


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


def _reopen_settings():
    """Knopf in den Einstellungen gedrueckt (die Seite schliesst dabei): danach wieder
    oeffnen, damit der neue Stand sichtbar ist statt einer leeren Rueckkehr."""
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % util.ADDON_ID)


def main(argv):
    store = Store(util.profile_dir())
    arg = argv[1] if len(argv) > 1 else ''
    if arg in ('disconnect', 'syncnow') and not store.token:
        # Seite zeigte noch 'verbunden', die Verbindung ist aber schon weg (in der App
        # entfernt): Anzeige richtigstellen statt nichts zu tun
        _forget(store)
        util.notify(util.lang(32020))
        _reopen_settings()
        return
    if arg == 'disconnect':
        disconnect(store)
        _reopen_settings()
        return
    if arg == 'syncnow':
        sync_now()
        return
    if arg == 'connect':
        if not store.token:
            pairing.run(store)
        _reopen_settings()
        return
    if store.token:
        menu(store)
    else:
        pairing.run(store)
