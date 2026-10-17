#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
#
# This file is part of Cloud Drive Common Module for Kodi
#
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

# Requests from the download service to the provider over kept-open connections. A player opens a file many times
# in a row (probing, seeking), and a new HTTPS connection costs about 0.1 s (Google) to 0.3 s (Microsoft) each time.

import http.client
import re
import ssl
import threading
import time
import urllib.parse


_REDIRECTS = (301, 302, 303, 307, 308)
# Raised when a kept-open connection was closed by the server in the meantime: the request is sent again on a new one.
_STALE = (http.client.RemoteDisconnected, http.client.BadStatusLine, BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


class ConnectionPool(object):
    MAX_IDLE_PER_HOST = 4
    IDLE_SECONDS = 30

    def __init__(self):
        self._idle = {}
        self._lock = threading.Lock()
        self._context = ssl.create_default_context()

    def get(self, key):
        """A kept-open connection for (scheme, host, port), or a new one. Returns (connection, reused)."""
        now = time.time()
        with self._lock:
            idle = self._idle.get(key, [])
            while idle:
                connection, since = idle.pop()
                if now - since < self.IDLE_SECONDS:
                    return connection, True
                connection.close()
        scheme, host, port = key
        if scheme == 'https':
            return http.client.HTTPSConnection(host, port, timeout=30, context=self._context), False
        return http.client.HTTPConnection(host, port, timeout=30), False

    def release(self, key, connection, response):
        """Keeps the connection if its response was read completely and the server keeps it open."""
        if response.isclosed() and not response.will_close:
            with self._lock:
                idle = self._idle.setdefault(key, [])
                if len(idle) < self.MAX_IDLE_PER_HOST:
                    idle.append((connection, time.time()))
                    return
        connection.close()

    def clear(self):
        with self._lock:
            for idle in self._idle.values():
                for connection, _ in idle:
                    connection.close()
            self._idle = {}


pool = ConnectionPool()


def fetch(url, headers, max_redirects=3):
    """
    GET url with headers, following redirects (Authorization only goes to the same host). Returns (key, connection,
    response); hand them back with pool.release(key, connection, response) after reading the response.
    """
    headers = dict(headers)
    for _ in range(max_redirects + 1):
        parts = urllib.parse.urlsplit(url)
        key = (parts.scheme, parts.hostname, parts.port)
        path = (parts.path or '/') + ('?' + parts.query if parts.query else '')
        for attempt in (1, 2):
            connection, reused = pool.get(key)
            try:
                connection.request('GET', path, headers=headers)
                response = connection.getresponse()
                break
            except _STALE:
                connection.close()
                if not reused or attempt == 2:
                    raise
        location = response.getheader('Location')
        if response.status in _REDIRECTS and location:
            response.read()
            pool.release(key, connection, response)
            new_url = urllib.parse.urljoin(url, location)
            if urllib.parse.urlsplit(new_url).netloc != parts.netloc:
                headers = dict((k, v) for k, v in headers.items() if k.lower() != 'authorization')
            url = new_url
            continue
        return key, connection, response
    raise http.client.HTTPException('Too many redirects: %s' % urllib.parse.urlsplit(url).netloc)


def parse_range(value):
    """'bytes=a-b' or 'bytes=a-' to (a, b or None). None for anything else (multiple ranges, suffix ranges)."""
    match = re.match(r'^bytes=(\d+)-(\d*)$', (value or '').strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


def parse_content_range(value):
    """'bytes a-b/total' to (a, b, total), or None (also when the total is unknown)."""
    match = re.match(r'^bytes (\d+)-(\d+)/(\d+)$', (value or '').strip())
    return tuple(int(g) for g in match.groups()) if match else None
