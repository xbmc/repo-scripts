# SPDX-License-Identifier: GPL-2.0-only
"""HTTP for library sync: upload, queue and ack, one attempt each.

The engine decides retries, backoff and what an error means (plan Task 14); this module only
makes one request and says plainly what came back. Paths are relative to the paired webhook
URL (CrossWatch serves sync under /webhook/kodiwatcher/sync/v1), so a CrossWatch behind a
reverse proxy at a sub-path works the same way the webhook does.

The token goes in X-CrossWatch-Token and the device id in X-CrossWatch-Device, never in the
query: sync endpoints refuse ?token= (contract), and a query string ends up in proxy logs.
Redirects are not followed, so the token is never sent anywhere but the paired host.

Every CrossWatch reply carries "ok". Anything else, a proxy login page, a captive portal, a
proxy's own error page, is not CrossWatch answering: SyncError.from_crosswatch is False and
the contract's error actions (stop on 401, pause on 403, ...) must not be taken on it. A
proxy's 413 is the one status worth acting on, because only a smaller request gets through.

Log events: none; the engine logs outcomes with the endpoint and status.
"""
from __future__ import annotations

import gzip
import json
import math
import socket
import ssl
import threading
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from resources.lib.constants import HTTP_TIMEOUT_SECONDS, SHUTDOWN_HTTP_TIMEOUT_SECONDS
from resources.lib.reporter import open_connection, target_of
from resources.lib.sync.constants import BACKOFF_SECONDS, CONNECT_TIMEOUT_SECONDS, MAX_REQUEST_BYTES

# A queue page of 1000 changes is well under this; a bigger answer is not CrossWatch's.
MAX_REPLY_BYTES = 8 * 1024 * 1024


class SyncError(Exception):
    """A sync request that didn't succeed.

    status is the HTTP status, or 0 when no answer arrived. code is CrossWatch's error code
    when from_crosswatch is True; otherwise one of the add-on's own:
    - "not_crosswatch": something else answered (a proxy, a portal);
    - "no_sync": the paired server answered 404, so it has no sync endpoints (a CrossWatch
      without library sync, or a paired URL with the wrong path);
    - "network": no answer, nothing known to have arrived;
    - "lost_reply": the request went out and the answer was lost, so it may have arrived;
    - "certificate": the HTTPS certificate was refused;
    - "request_too_large": the add-on would have sent more than MAX_REQUEST_BYTES;
    - "reply_too_large", "invalid_request": the reply or the request couldn't be handled.
    retryable says whether the same request may simply be sent again later; retry_after is
    seconds from a Retry-After header, or None.
    """

    def __init__(
        self,
        status: int,
        code: str,
        retryable: bool,
        retry_after: float | None = None,
        *,
        from_crosswatch: bool = False,
    ) -> None:
        super().__init__(f"{status} {code}")
        self.status = status
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
        self.from_crosswatch = from_crosswatch


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        # An HTTP date is legal too; the engine's own backoff covers that case.
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    # Only ever from a proxy (CrossWatch sends none on sync), so never longer than our own
    # longest backoff.
    return min(seconds, float(BACKOFF_SECONDS[-1]))


class SyncClient:
    """One instance per paired URL and token.

    The constructor raises reporter.InvalidWebhookUrl for a URL the webhook would refuse too.
    cancel() may be called from another thread to end a request in flight at shutdown.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        device_id: str,
        abort: threading.Event,
        connection_factory: Callable[..., Any] | None = None,
        timeout: float = HTTP_TIMEOUT_SECONDS,
    ) -> None:
        target = target_of(base_url)
        self._scheme, self._host, self._port = target.scheme, target.host, target.port
        # The paired URL's path without its query, with the sync path appended.
        self._base = target.path.split("?", 1)[0].rstrip("/") + "/sync/v1/"
        self._headers = {
            "X-CrossWatch-Token": token,
            "X-CrossWatch-Device": device_id,
            "Accept": "application/json",
        }
        self._abort = abort
        self._factory = connection_factory or open_connection
        self._timeout = timeout
        self._lock = threading.Lock()
        self._live: Any = None

    def upload(self, body: bytes) -> dict[str, Any]:
        """body is the JSON of one upload request; it is sent gzip-compressed."""
        compressed = gzip.compress(body)
        if len(compressed) > MAX_REQUEST_BYTES:
            # Checked here, where the gzip happens, so the limit lives in one place.
            raise SyncError(0, "request_too_large", False)
        return self._request("POST", "upload", compressed)

    def queue(self, viewer_id: str, after: int, limit: int = 500) -> dict[str, Any]:
        query = urlencode({"viewer_id": viewer_id, "after": after, "limit": limit})
        return self._request("GET", f"queue?{query}", None)

    def ack(self, viewer_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        body = json.dumps({"version": 1, "viewer_id": viewer_id, "results": results}).encode("utf-8")
        return self._request("POST", "queue/ack", gzip.compress(body))

    def cancel(self) -> None:
        """End a request in flight now. close() alone doesn't wake a thread blocked reading
        the answer; shutting the socket down does, at once."""
        with self._lock:
            connection = self._live
        sock = getattr(connection, "sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _request(self, method: str, endpoint: str, body: bytes | None) -> dict[str, Any]:
        headers = dict(self._headers)
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Encoding"] = "gzip"
        # After abort, Kodi kills the interpreter within 5 s, so a request then gets the
        # short timeout the reporter uses too.
        timeout = SHUTDOWN_HTTP_TIMEOUT_SECONDS if self._abort.is_set() else self._timeout
        try:
            connection = self._factory(self._scheme, self._host, self._port, min(timeout, CONNECT_TIMEOUT_SECONDS))
        except Exception as exc:
            raise SyncError(0, "network", True) from exc
        with self._lock:
            self._live = connection
        try:
            try:
                connection.connect()
            except ssl.SSLCertVerificationError as exc:
                raise SyncError(0, "certificate", True) from exc
            except Exception as exc:
                raise SyncError(0, "network", True) from exc
            # An abort during the connect missed cancel(), which had no socket to shut.
            connection.sock.settimeout(SHUTDOWN_HTTP_TIMEOUT_SECONDS if self._abort.is_set() else timeout)
            try:
                connection.request(method, self._base + endpoint, body=body, headers=headers)
            except UnicodeEncodeError as exc:
                # A token or device id that can't go in a header: the same every time.
                raise SyncError(0, "invalid_request", False) from exc
            except ssl.SSLCertVerificationError as exc:
                raise SyncError(0, "certificate", True) from exc
            except Exception as exc:
                raise SyncError(0, "network", True) from exc
            try:
                response = connection.getresponse()
                status = int(getattr(response, "status", 0) or 0)
                raw = response.read(MAX_REPLY_BYTES + 1)
                retry_after = _retry_after(response.getheader("Retry-After"))
            except ssl.SSLCertVerificationError as exc:
                raise SyncError(0, "certificate", True) from exc
            except Exception as exc:
                raise SyncError(0, "lost_reply", True) from exc
        finally:
            with self._lock:
                self._live = None
            try:
                connection.close()
            except Exception:
                pass
        if len(raw) > MAX_REPLY_BYTES:
            raise SyncError(status, "reply_too_large", False)
        return _judge(status, raw, retry_after)


def _judge(status: int, raw: bytes, retry_after: float | None) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else None
    except (ValueError, UnicodeDecodeError, RecursionError):
        parsed = None
    if not isinstance(parsed, dict) or "ok" not in parsed:
        if status == 404 and isinstance(parsed, dict) and "detail" in parsed:
            # CrossWatch's web framework answering a path it doesn't serve.
            raise SyncError(status, "no_sync", False, retry_after)
        # A proxy or portal in CrossWatch's place: worth trying again later, whatever its
        # status, except a 413, which only a smaller request gets past.
        raise SyncError(status, "not_crosswatch", status != 413, retry_after)
    if 200 <= status < 300 and parsed.get("ok") is True:
        return parsed
    found = parsed.get("error")
    error: dict[str, Any] = found if isinstance(found, dict) else {}
    code = str(error.get("code") or "unknown")
    retryable = error.get("retryable") is True or status in (429, 503) or status >= 500
    raise SyncError(status, code, retryable, retry_after, from_crosswatch=True)
