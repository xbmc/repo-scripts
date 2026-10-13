# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Kopplung: Code + QR auf dem Fernseher, Bestaetigung in App oder Web. Nichts zu tippen."""

import os
import time

import xbmc
import xbmcgui

from . import util
from .api import Api, ApiError, Retryable

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_SELECT_ITEM = 7
ACTION_MOUSE_LEFT_CLICK = 100

TEXT = 'FFFFFFFF'
MUTED = 'FFA0A0AA'
DARK = 'FF050506'


def _media(name):
    return os.path.join(util.addon_path(), 'resources', 'media', name)


class PairingDialog(xbmcgui.WindowDialog):
    """Programmatisch gebaut, unabhaengig vom Skin (Koordinaten 1280x720)."""

    def __init__(self):
        xbmcgui.WindowDialog.__init__(self)
        self.closed = False
        white = _media('white.png')
        # abgedunkelter Hintergrund + Panel
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, white, colorDiffuse='CC000000'))
        self.addControl(xbmcgui.ControlImage(170, 100, 940, 520, white, colorDiffuse='FF15151A'))
        self.title = xbmcgui.ControlLabel(220, 135, 520, 44, util.lang(32002), font='font30_title', textColor=TEXT)
        self.text = xbmcgui.ControlTextBox(220, 195, 500, 96, font='font13', textColor=MUTED)
        self.code = xbmcgui.ControlLabel(220, 300, 520, 90, '', font='font45', textColor=TEXT)
        self.countdown = xbmcgui.ControlLabel(220, 400, 520, 30, '', font='font12', textColor=MUTED)
        self.web = xbmcgui.ControlLabel(220, 440, 520, 30, '', font='font12', textColor=MUTED)
        self.qr_bg = xbmcgui.ControlImage(760, 160, 300, 300, white, colorDiffuse='FFFFFFFF')
        self.qr = xbmcgui.ControlImage(770, 170, 280, 280, '', aspectRatio=0)
        self.cancel = xbmcgui.ControlButton(
            220, 520, 220, 56, util.lang(32013),
            focusTexture=_media('button_focus.png'), noFocusTexture=_media('button_nofocus.png'),
            alignment=0x00000002 | 0x00000004, font='font13',
            textColor=TEXT, focusedColor=DARK)
        for c in (self.title, self.text, self.code, self.countdown, self.web, self.qr_bg, self.qr, self.cancel):
            self.addControl(c)
        self.text.setText(util.lang(32010))
        self.code.setLabel(util.lang(32024))

    def show(self):
        xbmcgui.WindowDialog.show(self)
        # manche Kodi-Versionen setzen den Fokus erst nach show() (Fernbedienung)
        self.setFocus(self.cancel)

    def set_code(self, res):
        self.code.setLabel(util.format_code(res.get('code')))
        self.qr.setImage(res.get('qrImageUrl') or '', False)
        verify = util.strip_scheme(res.get('verifyUrl') or 'https://watch-n-play.com/kodi')
        self.web.setLabel(util.lang(32011) % verify)

    def set_countdown(self, seconds):
        self.countdown.setLabel(util.lang(32012) % util.format_countdown(seconds))

    def set_hint(self, text):
        self.countdown.setLabel(text)

    def _is_cancel(self, control_id):
        try:
            return control_id == self.cancel.getId()
        except RuntimeError:
            return False

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close_dialog()
        elif aid in (ACTION_SELECT_ITEM, ACTION_MOUSE_LEFT_CLICK):
            # Kodi meldet den Klick nicht immer per onControl (Fernbedienung, Touch)
            try:
                focused = self.getFocusId()
            except RuntimeError:
                focused = 0
            if self._is_cancel(focused):
                self.close_dialog()

    def onControl(self, control):
        # Vergleich ueber die ID: Kodi reicht nicht unbedingt dasselbe Objekt weiter
        if control is not None and self._is_cancel(control.getId()):
            self.close_dialog()

    def close_dialog(self):
        self.closed = True
        self.close()


def _start(api):
    return api.pair_start(util.device_name(), util.platform(), util.kodi_version(), util.addon_version())


def _discard(token):
    """Bestaetigung kam nach dem Abbrechen an: Geraet beim Server gleich wieder abmelden,
    damit in der App kein verwaistes Geraet stehen bleibt."""
    util.log('pairing confirmed after cancel, device removed again')
    try:
        Api(util.api_base(), util.user_agent(), token).unpair()
    except ApiError as exc:
        util.warn('unpair after cancel failed: %s' % exc.status)


def _error_dialog(exc):
    msg = util.lang(32016) if getattr(exc, 'status', 0) == 429 else util.lang(32017)
    xbmcgui.Dialog().ok('WatchNPlay', msg)


def run(store):
    """Zeigt den Kopplungsdialog. True, wenn gekoppelt."""
    api = Api(util.api_base(), util.user_agent())
    monitor = xbmc.Monitor()
    # Dialog sofort zeigen ("Code wird angefordert..."), nicht erst nach der Anfrage
    dlg = PairingDialog()
    dlg.show()
    try:
        res = _start(api)
    except ApiError as exc:
        util.warn('pair/start failed: %s' % exc.status)
        dlg.close_dialog()
        del dlg
        _error_dialog(exc)
        return False
    if dlg.closed:
        del dlg
        return False
    dlg.set_code(res)
    result = None
    try:
        expires = time.time() + int(res.get('expiresIn') or 600)
        interval = max(2, int(res.get('interval') or 5))
        next_poll = time.time() + interval
        poll_token = res.get('pollToken')
        while not dlg.closed and not monitor.abortRequested():
            now = time.time()
            renew = now >= expires
            if not renew:
                dlg.set_countdown(expires - now)
            if not renew and now >= next_poll:
                next_poll = now + interval
                try:
                    poll = api.pair_poll(poll_token)
                except Retryable as exc:
                    if exc.status == 429:
                        interval = min(interval * 2, 30)
                    next_poll = now + interval
                    poll = {}
                except ApiError as exc:
                    util.warn('pair/poll failed: %s' % exc.status)
                    poll = {}
                status = poll.get('status')
                if status == 'confirmed' and poll.get('token'):
                    # Abbrechen waehrend der Anfrage: Kodi liefert den Klick erst beim
                    # naechsten Warten aus, also kurz warten und dann pruefen
                    if monitor.waitForAbort(0.1) or dlg.closed:
                        _discard(poll['token'])
                        break
                    result = poll
                    break
                if status == 'expired':
                    renew = True
            if renew:
                # abgelaufen: automatisch neuer Code
                dlg.set_hint(util.lang(32015))
                try:
                    res = _start(api)
                except ApiError as exc:
                    util.warn('pair/start (renew) failed: %s' % exc.status)
                    dlg.close_dialog()
                    _error_dialog(exc)
                    break
                dlg.set_code(res)
                expires = time.time() + int(res.get('expiresIn') or 600)
                interval = max(2, int(res.get('interval') or 5))
                next_poll = time.time() + interval
                poll_token = res.get('pollToken')
            monitor.waitForAbort(0.25)
    finally:
        if not dlg.closed:
            dlg.close_dialog()
        del dlg

    if not result:
        return False
    user = result.get('userName') or ''
    # Warteschlange eines frueher gekoppelten Kontos nicht unter dem neuen senden
    store.clear_queue()
    store.set_auth(result['token'], user, bool(result.get('backSync')))
    util.set_status(True, user, None)
    util.notify(util.lang(32014) % user)
    util.notify_service('paired')
    util.log('paired with WatchNPlay')
    return True
