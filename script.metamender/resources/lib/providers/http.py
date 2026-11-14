"""Shared HTTP helper for provider calls.

Centralizes the outbound request, the User-Agent, the transport limits and
HTTP error classification so every provider fetch handles failures the same
way. Every request goes through ``_send``: one reusable session per host,
no redirects followed, the body streamed under a whole-response deadline and
a size cap.

Classification:
    200             -> parsed JSON (provider_get/post) or text (provider_get_text)
    404            -> None (legitimate "no data found")
    401            -> ApiKeyError (fatal for that provider)
    3xx            -> TransientProviderError (a redirect to a consent or
                      challenge page is not an answer)
    403/408/425/429/5xx -> TransientProviderError (counts toward circuit breaker)
    400            -> TransientProviderError when the caller sets
                      transient_400 (TVDB answers 400 for request problems that
                      are not a "no data" result), else None
    other 4xx      -> None (no data; not a provider failure)
    timeout/conn/deadline/size cap -> TransientProviderError
    malformed JSON -> TransientProviderError

403 is treated as transient because it is how bot-protection layers (e.g. Akamai)
reject automated requests; if that becomes persistent it should trip the breaker
and stop the cycle rather than silently spin through the whole library.

Logging:
    Request bodies and headers are never logged. Exception text from requests
    can embed a URL, and is redacted before it enters a raised error.
    Uses the caller's logger; events use the caller's domain via `label`.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any, NoReturn
from urllib.parse import urlsplit

import requests

from resources.lib.constants import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_DEADLINE_SEC,
    HTTP_MAX_BODY_BYTES,
    HTTP_READ_TIMEOUT,
    METAMENDER_USER_AGENT,
)
from resources.lib.utils import ApiKeyError, TransientProviderError, _redact

_HEADERS = {"User-Agent": METAMENDER_USER_AGENT}
_CHUNK_BYTES = 65536

# One session per host keeps connections alive across a scan's many calls to
# the same provider. Kodi runs the service in one interpreter for its whole
# life, so the cache lives as long as the add-on.
_SESSIONS: dict[str, requests.Session] = {}


class _TransportLimit(requests.RequestException):
    """The response broke the deadline or the size cap; handled like any
    other transport failure."""


class _Response:
    """A fully read response: status, body bytes and the declared encoding."""

    def __init__(self, status_code: int, body: bytes, encoding: str | None) -> None:
        self.status_code = status_code
        self.body = body
        self.encoding = encoding or "utf-8"

    def json(self) -> Any:
        return json.loads(self._decode("strict"))

    @property
    def text(self) -> str:
        return self._decode("replace")

    def _decode(self, errors: str) -> str:
        try:
            return self.body.decode(self.encoding, errors=errors)
        except LookupError:
            # A charset Python does not know: the providers all send UTF-8.
            return self.body.decode("utf-8", errors=errors)


def _session_for(url: str) -> requests.Session:
    host = urlsplit(url).netloc.lower()
    session = _SESSIONS.get(host)
    if session is None:
        session = _SESSIONS[host] = requests.Session()
    return session


def _send(
    url: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    read_timeout: float = HTTP_READ_TIMEOUT,
) -> _Response:
    """Perform one request and read its body under the transport limits.

    Raises requests.RequestException (including _TransportLimit) on any
    transport failure; the caller classifies it.
    """
    started = time.monotonic()
    resp = _session_for(url).request(
        method, url, params=params, json=json_body, headers=_merge_headers(headers),
        timeout=(HTTP_CONNECT_TIMEOUT, read_timeout), allow_redirects=False,
        stream=True,
    )
    # A read blocks until a whole chunk or the end arrives, and the read
    # timeout only bounds the gap between bytes, so a trickling body would
    # outlive any check between chunks. A watchdog closes the response at the
    # deadline, which ends the blocked read.
    remaining = max(0.0, HTTP_DEADLINE_SEC - (time.monotonic() - started))
    expired = threading.Event()

    def _expire() -> None:
        expired.set()
        # close() alone does not wake a recv already blocked in another
        # thread; shutting the socket down does. urllib3 keeps the socket on
        # its connection (1.26 and 2.x alike); without it, close() still ends
        # the read at the next byte.
        sock = getattr(getattr(resp.raw, "_connection", None), "sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        resp.close()

    watchdog = threading.Timer(remaining, _expire)
    watchdog.daemon = True
    watchdog.start()
    try:
        chunks: list[bytes] = []
        size = 0
        try:
            for chunk in resp.iter_content(_CHUNK_BYTES):
                size += len(chunk)
                if size > HTTP_MAX_BODY_BYTES:
                    raise _TransportLimit(
                        "response larger than {} bytes".format(HTTP_MAX_BODY_BYTES))
                if time.monotonic() - started > HTTP_DEADLINE_SEC:
                    raise _TransportLimit(
                        "response slower than {} s".format(HTTP_DEADLINE_SEC))
                chunks.append(chunk)
        except Exception as exc:
            if expired.is_set():
                raise _TransportLimit(
                    "response slower than {} s".format(HTTP_DEADLINE_SEC)) from exc
            raise
        if expired.is_set():
            raise _TransportLimit("response slower than {} s".format(HTTP_DEADLINE_SEC))
        return _Response(resp.status_code, b"".join(chunks), resp.encoding)
    finally:
        watchdog.cancel()
        resp.close()


def provider_get(
    url: str,
    logger: Any,
    label: str,
    params: dict[str, Any] | None = None,
    provider: str = "",
    timeout: float = HTTP_READ_TIMEOUT,
    headers: dict[str, str] | None = None,
    transient_400: bool = False,
) -> dict[str, Any] | None:
    """GET a provider URL and classify the outcome.

    Returns parsed JSON on 200, None on 404. Raises ApiKeyError on 401 and
    TransientProviderError on 3xx/429/5xx/timeout/connection/malformed-JSON,
    and on 400 when `transient_400` is set. `headers` are merged over the
    default User-Agent. `label` is used as the log event domain (e.g.
    "tmdb.movie"); `timeout` is the read timeout.
    """
    try:
        resp = _send(url, params=params, headers=headers, read_timeout=timeout)
    except requests.RequestException as exc:
        _raise_transport_error(logger, label, exc)
    return _classify(resp, logger, label, provider, transient_400)


def provider_get_text(
    url: str,
    logger: Any,
    label: str,
    params: dict[str, Any] | None = None,
    provider: str = "",
    headers: dict[str, str] | None = None,
) -> str | None:
    """GET a page and return its text on 200; every other outcome is
    classified exactly like provider_get."""
    try:
        resp = _send(url, params=params, headers=headers)
    except requests.RequestException as exc:
        _raise_transport_error(logger, label, exc)
    return _classify(resp, logger, label, provider, False, as_text=True)


def provider_post(
    url: str,
    logger: Any,
    label: str,
    json_body: dict[str, Any],
    provider: str = "",
    timeout: float = HTTP_READ_TIMEOUT,
    headers: dict[str, str] | None = None,
    transient_400: bool = False,
) -> dict[str, Any] | None:
    """POST a JSON body to a provider URL; classified exactly like provider_get."""
    try:
        resp = _send(
            url, method="POST", json_body=json_body, headers=headers, read_timeout=timeout,
        )
    except requests.RequestException as exc:
        _raise_transport_error(logger, label, exc)
    return _classify(resp, logger, label, provider, transient_400)


def _merge_headers(extra: dict[str, str] | None) -> dict[str, str]:
    merged = dict(_HEADERS)
    if extra:
        merged.update(extra)
    return merged


def _raise_transport_error(logger: Any, label: str, exc: Exception) -> NoReturn:
    # Deliberate warning() not exception(): this fires on every transient
    # failure (429/timeout/conn reset), so a stack trace per occurrence
    # would be log noise. The error= kwarg carries the cause.
    cause = _redact(str(exc))
    logger.warning(
        "Transient request failure",
        event="{}.transient".format(label),
        error=cause,
    )
    raise TransientProviderError(cause)


def _classify(
    resp: Any, logger: Any, label: str, provider: str, transient_400: bool,
    as_text: bool = False,
) -> Any:
    """Map a response to parsed JSON (or text), None, or a raised provider error."""
    status = resp.status_code
    if status == 200:
        if as_text:
            return resp.text
        try:
            return resp.json()
        except ValueError:
            # Deliberate warning() not exception(): malformed JSON is a
            # transient provider hiccup that can recur; a stack trace per
            # occurrence would be log noise.
            logger.warning(
                "Malformed JSON",
                event="{}.transient".format(label),
            )
            raise TransientProviderError("malformed json")
    if status == 404:
        logger.debug(
            "No data found (404)",
            event="{}.nodata".format(label),
        )
        return None
    if status == 401:
        raise ApiKeyError(provider or label)
    if 300 <= status < 400:
        logger.warning(
            "Redirect not followed",
            event="{}.redirect".format(label),
            status_code=status,
        )
        raise TransientProviderError("http {}".format(status), status=status)
    # 403 (bot block), 408 (request timeout), 425 (too early), 429 (rate limit)
    # and all 5xx are transient: they should count toward the breaker.
    if status in (403, 408, 425, 429) or status >= 500 or (
        status == 400 and transient_400
    ):
        logger.warning(
            "Transient HTTP status",
            event="{}.transient".format(label),
            status_code=status,
        )
        raise TransientProviderError("http {}".format(status), status=status)
    # Other 4xx: treat as no data (not retryable as a provider failure)
    logger.warning(
        "Unexpected status, treating as no data",
        event="{}.nodata".format(label),
        status_code=status,
    )
    return None
