# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Duenner HTTP-Client fuer /api/kodi (nur stdlib)."""

import json
import socket
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

# Kurz halten: Kodi wartet beim Beenden nur wenige Sekunden auf den Dienst
TIMEOUT = 10
# Abgleich von bis zu 500 Titeln braucht auf dem Server laenger
LIBRARY_TIMEOUT = 20
# Kopplungsdialog: blockiert waehrenddessen die Fernbedienung
POLL_TIMEOUT = 6
# Nur das verwirft einen Stapel: der Server hat genau diesen Inhalt abgelehnt
DROP_CODES = ('KODI_BAD_ITEMS', 'KODI_BAD_PLAYS')


class ApiError(Exception):
    """Nicht wiederholbarer Fehler (400 mit KODI_BAD_*): Daten verwerfen statt endlos zu senden."""

    def __init__(self, status, body=None):
        Exception.__init__(self, 'HTTP %s' % status)
        self.status = status
        self.body = body or {}
        # Token der Anfrage (None = ohne Anmeldung oder nicht bekannt)
        self.token = None


class Unauthorized(ApiError):
    """401: Geraet in der App entfernt, Token ungueltig."""


class ProRequired(ApiError):
    """402 PRO_REQUIRED."""


class Retryable(ApiError):
    """Alles andere (408/409/429/5xx/Netz, aber auch unerwartete 4xx wie 403 von einer
    Firewall oder 404 bei einem Server-Rollback): spaeter erneut versuchen, Warteschlange
    behalten. Verworfen wird nur, was der Server inhaltlich ablehnt (DROP_CODES).

    Dazu 503 KODI_DISABLED: Betreiber-Schalter fuer dieses Konto aus, nur warten.
    """

    @property
    def kodi_disabled(self):
        return self.status == 503 and (self.body or {}).get('code') == 'KODI_DISABLED'


def classify(status, body):
    if status == 401:
        return Unauthorized(status, body)
    if status == 402:
        return ProRequired(status, body)
    if status == 400 and (body or {}).get('code') in DROP_CODES:
        return ApiError(status, body)
    return Retryable(status, body)


class Api(object):
    def __init__(self, base, user_agent, token=None, opener=None):
        self.base = base.rstrip('/')
        self.user_agent = user_agent
        self.token = token
        self._open = opener or urlrequest.urlopen

    def _request(self, method, path, body=None, auth=True, timeout=TIMEOUT):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if auth:
            if not self.token:
                raise Unauthorized(401, {'code': 'NO_TOKEN'})
            headers['Authorization'] = 'Bearer %s' % self.token
        req = urlrequest.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            resp = self._open(req, timeout=timeout)
            try:
                status = resp.getcode()
                raw = resp.read()
            finally:
                resp.close()
        except HTTPError as err:
            try:
                parsed = json.loads(err.read().decode('utf-8') or '{}')
            except Exception:
                parsed = {}
            exc = classify(err.code, parsed if isinstance(parsed, dict) else {})
            # mit welchem Token die Anfrage lief: ein 401 fuer ein altes Token betrifft
            # keine inzwischen neue Kopplung (sync._handle)
            exc.token = self.token if auth else None
            raise exc
        except (URLError, socket.timeout, OSError) as err:
            raise Retryable(0, {'error': str(err)})
        if status == 204 or not raw:
            return {}
        try:
            parsed = json.loads(raw.decode('utf-8'))
        except ValueError:
            raise Retryable(status, {'error': 'invalid json'})
        return parsed if isinstance(parsed, dict) else {}

    # --- oeffentlich ---
    def pair_start(self, name, platform, kodi_version, addon_version):
        return self._request('POST', '/pair/start', {
            'name': name, 'platform': platform,
            'kodiVersion': kodi_version, 'addonVersion': addon_version,
        }, auth=False)

    def pair_poll(self, poll_token):
        return self._request('POST', '/pair/poll', {'pollToken': poll_token}, auth=False,
                             timeout=POLL_TIMEOUT)

    # --- Geraet ---
    def status(self):
        return self._request('GET', '/status')

    def library(self, items, full):
        """Antwort: mark, unmark, backSync, version (Gesehen-Stand nach diesem Abgleich)."""
        return self._request('POST', '/library', {'items': items, 'full': bool(full)},
                             timeout=LIBRARY_TIMEOUT)

    def plays(self, plays, min_percent=None):
        body = {'plays': plays}
        if min_percent is not None:
            body['minPercent'] = min_percent
        return self._request('POST', '/plays', body)

    def unpair(self):
        return self._request('POST', '/unpair')
