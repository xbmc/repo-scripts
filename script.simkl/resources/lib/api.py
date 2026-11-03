#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The HTTP client. POST for writes, timeouts, one client id per token generation, typed errors, no token in any log line."""

import contextlib
import http.client
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from resources.lib import settings, utils

# Two client ids. A Simkl token only resolves under the app that minted it: tokens stored by 3.x belong to the old
# pin-flow app and keep working under it, a device-flow login belongs to the OAuth 2 app.
CLIENT_LEGACY = '62a587ec2a82dbed02c6ab48b923d72e775cb1096d2de60d04502413e36ef100'
CLIENT_V2 = '84e2976d62b915ce6becdfcbccb78d5e3a2cab7e1de2314d1557bcee8ff06131'
SCOPE = 'media:read media:write'
BASE = 'https://api.simkl.com'
TIMEOUT = 30
TIMEOUT_LONG = 300
CHUNK = 65536
# Simkl's rule: at most one write per second, from whichever thread sends it
POST_GAP = 1.0
# a short limit (429 rate_limit, or 400 RATE_LIMIT: the per-user write lock of up to 20 s) is tried again after this;
# the daily quota (429 user_limit_exceeded / app_limit_exceeded) carries Retry-After, the seconds to the next reset
RATE_RETRY = 5
QUOTA_WAIT = 3600
QUOTA_ERRORS = ('user_limit_exceeded', 'app_limit_exceeded')


class ApiError(Exception):
    def __init__(self, status, error='', message='', data=None, retry_after=None):
        self.status = status
        self.error = error
        self.message = message
        self.data = data
        self.retry_after = retry_after
        super().__init__('HTTP %s %s %s' % (status, error, message))

    @property
    def transport(self):
        return self.status == 0

    @property
    def quota(self):
        return self.status == 429 and self.error in QUOTA_ERRORS

    @property
    def rate_limited(self):
        return (self.status == 429 and not self.quota) or (self.status == 400 and self.error.upper() == 'RATE_LIMIT')

    @property
    def retryable(self):
        return self.transport or self.rate_limited or self.quota or self.status >= 500


class Api:
    def __init__(self):
        self.user_agent = '%s/%s Kodi/%s' % (utils.ADDON_ID, utils.ADDON_VERSION, utils.KODI_VERSION)
        self.client_params = urllib.parse.urlencode({'app-name': utils.ADDON_ID, 'app-version': utils.ADDON_VERSION, 'kodi-version': utils.KODI_VERSION})
        # set at shutdown: a request still in flight gives up at its next chunk instead of holding Kodi's exit
        self.abort = False
        self._post_lock = threading.Lock()
        self._last_post = 0.0
        # a daily quota holds every call with that token until the reset Simkl named: nothing leaves the box meanwhile
        self.quota_until = 0.0
        self.quota_error = ''
        self.quota_token = None

    @staticmethod
    def client_id(token):
        if token and not settings.is_v2(token):
            return CLIENT_LEGACY
        return CLIENT_V2

    @contextlib.contextmanager
    def _post_slot(self):
        """One write at a time, the next starting a second after the previous one was answered (its headers), so the
        server never sees two inside a second whatever the connections did; the lock keeps the sender, a sign-in poll
        and a token renewal on the importer's thread from writing together."""
        with self._post_lock:
            wait = self._last_post + POST_GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                yield
            finally:
                self._last_post = time.monotonic()

    def request(self, method, path, body=None, token=None, timeout=TIMEOUT, client_id=None):
        """Returns (status, parsed body). Raises ApiError(0) on a transport failure, and on a 2xx/3xx whose body is not
        JSON (an uncaught server error answers an empty 200): such an answer proves nothing about what the server did,
        so callers retry it like a dropped connection. A literal null body is a legitimate empty answer. An HTTP error
        status is returned, whatever its body."""
        return self._request(method, path, body, token, timeout, client_id)[:2]

    def _request(self, method, path, body=None, token=None, timeout=TIMEOUT, client_id=None):
        """(status, parsed body, Retry-After in seconds or None)."""
        client = client_id or self.client_id(token)
        # the client id travels in the URL as well as in the header: Simkl's developer statistics are keyed on the query string
        url = BASE + path + ('&' if '?' in path else '?') + self.client_params + '&client_id=' + client
        headers = {
            'simkl-api-key': client,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': self.user_agent,
        }
        if token:
            headers['Authorization'] = 'Bearer ' + token
        # Simkl URL-decodes the body before parsing it, so a literal % followed by two hex digits (a file name a dav
        # source stores percent-encoded) would change on the way in; escaped as \u0025 it is the same JSON and survives
        data = json.dumps(body).replace('%', '\\u0025').encode('utf-8') if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        retry_after = None
        try:
            # a write holds the slot until the server answered its headers; the body is read outside it, so a long
            # answer holds no other write
            with self._post_slot() if method == 'POST' else contextlib.nullcontext():
                response = urllib.request.urlopen(req, timeout=timeout)
            with response:
                status = response.getcode()
                chunks = []
                while not self.abort:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    chunks.append(chunk)
                if self.abort:
                    raise ApiError(0, 'transport', 'shutdown')
                raw = b''.join(chunks)
        except urllib.error.HTTPError as exc:
            status = exc.code
            value = str((exc.headers or {}).get('Retry-After') or '').strip()
            retry_after = int(value) if value.isdigit() else None
            try:
                raw = exc.read()
            except (OSError, http.client.HTTPException) as err:
                # without the body the status says nothing final (a 400 may be RATE_LIMIT): retried like a dropped connection
                utils.warn('%s %s: HTTP %s whose body could not be read: %s' % (method, path.split('?')[0], status, err))
                raise ApiError(0, 'transport', 'truncated answer')
        except (urllib.error.URLError, http.client.HTTPException, socket.timeout, ssl.SSLError, OSError, ValueError) as exc:
            utils.warn('%s %s: %s' % (method, path.split('?')[0], exc))
            raise ApiError(0, 'transport', str(exc))

        text = raw.decode('utf-8', 'replace').strip()
        parsed = None
        if text and text != 'null':
            try:
                parsed = json.loads(text)
            except ValueError:
                if status < 400:
                    utils.warn('%s %s: HTTP %s with a body that is not JSON' % (method, path.split('?')[0], status))
                    raise ApiError(0, 'transport', 'malformed answer')
        elif not text and status < 400 and status != 204:
            utils.warn('%s %s: HTTP %s with an empty body' % (method, path.split('?')[0], status))
            raise ApiError(0, 'transport', 'empty answer')
        utils.log('%s %s -> %s' % (method, path.split('?')[0], status))
        return status, parsed, retry_after

    def call(self, method, path, body=None, token=None, timeout=TIMEOUT):
        """Like request, but an error status raises ApiError with the server's error code and message. Under a daily
        quota every call with that token fails here, without a request, until the reset; a renewal, a login or a public
        call (no token) is not held."""
        if token and token == self.quota_token and time.time() < self.quota_until:
            raise ApiError(429, self.quota_error, 'daily limit reached', retry_after=int(self.quota_until - time.time()) + 1)
        status, data, retry_after = self._request(method, path, body, token, timeout)
        if status < 400:
            return data
        error = message = ''
        if isinstance(data, dict):
            error = str(data.get('error') or data.get('code') or '')
            message = str(data.get('message') or data.get('error_description') or '')
        exc = ApiError(status, error, message, data, retry_after)
        if exc.quota and token:
            self.quota_token = token
            self.quota_error = error
            self.quota_until = time.time() + (retry_after or QUOTA_WAIT)
            utils.warn('Simkl\'s daily limit is reached (%s): no request until the reset, in %d s' % (error, retry_after or QUOTA_WAIT))
        raise exc
