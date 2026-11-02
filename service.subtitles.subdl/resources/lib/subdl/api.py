"""Client for SubDL's public subtitle API (https://api.subdl.com).

Standard library only: Kodi's Python has no pip. Nothing here imports a Kodi module,
so the tests run it on any Python 3.8 or later.

Every failure leaves as a SubDLError whose ``kind`` picks the message the viewer
sees. Error details never carry the API key, a URL or anything about the video,
because Kodi logs end up pasted into public forum threads.
"""

from __future__ import annotations

import email.utils
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import timezone
from typing import Callable, Dict, Optional, Tuple

API_BASE = "https://api.subdl.com"
DOWNLOAD_BASE = "https://dl.subdl.com"
#: Where viewers create a free key and see their usage and plans.
PANEL_URL = "https://subdl.com/panel/api"
SEARCH_PATH = "/api/v1/subtitles"
ACCOUNT_PATH = "/api/v1/me"
DOWNLOAD_PREFIXES = ("/subtitle/", "/mobile/")
#: SubDL's API knows this client name: the first search tags the key as a Kodi key.
CLIENT = "kodi"
PAGE_SIZE = 30  # the API's maximum subs_per_page

TIMEOUT_S = 20.0
MAX_WAIT_S = 8.0  # longest Retry-After worth waiting for while the viewer watches
MAX_JSON_BYTES = 16 * 1024 * 1024  # season packs list every file they hold
MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024


class SubDLError(Exception):
    MISSING_KEY = "missing_key"
    INVALID_KEY = "invalid_key"
    DAILY_LIMIT = "daily_limit"  # the key's daily search quota
    DOWNLOAD_LIMIT = "download_limit"  # the key's daily download quota
    BUSY = "busy"  # per-minute limit or overload that outlasted the retries
    NOT_FOUND = "not_found"
    NETWORK = "network"
    FAILED = "failed"

    def __init__(self, kind: str, detail: str = "", status: Optional[int] = None,
                 retry_after: Optional[float] = None) -> None:
        super().__init__("%s (%s)" % (kind, detail) if detail else kind)
        self.kind = kind
        self.detail = detail
        self.status = status
        self.retry_after = retry_after


class Response:
    def __init__(self, status: int, headers, body: bytes) -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self._json: Optional[dict] = None

    def header(self, name: str) -> str:
        return (self.headers.get(name) if self.headers is not None else None) or ""

    def json(self) -> dict:
        """The body as a JSON object, or {} when it is not one."""
        if self._json is None:
            try:
                data = json.loads(self.body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                data = None
            self._json = data if isinstance(data, dict) else {}
        return self._json


Transport = Callable[[urllib.request.Request, float, int], Response]


def is_subdl_url(url: str) -> bool:
    """True for https addresses on subdl.com and its subdomains, nothing else."""
    try:
        split = urllib.parse.urlsplit(url)
        host = (split.hostname or "").lower()
        port = split.port
    except ValueError:
        return False
    return (split.scheme == "https" and port in (None, 443)
            and (host == "subdl.com" or host.endswith(".subdl.com")))


def strip_api_key(url: str) -> str:
    """The address without its api_key parameter.

    Search results come back with the key in every download address. Those
    addresses travel through Kodi's plugin URLs, which Kodi writes to its log.
    """
    split = urllib.parse.urlsplit(url or "")
    if not split.query:
        return url or ""
    kept = [(key, value) for key, value in urllib.parse.parse_qsl(split.query, keep_blank_values=True)
            if key.lower() != "api_key"]
    return urllib.parse.urlunsplit(split._replace(query=urllib.parse.urlencode(kept)))


def is_download_path(path: str) -> bool:
    path = strip_api_key(path or "")
    if path.startswith("/"):
        path = DOWNLOAD_BASE + path
    return is_subdl_url(path) and urllib.parse.urlsplit(path).path.startswith(DOWNLOAD_PREFIXES)


def download_url(path: str, api_key: str) -> str:
    """The full dl.subdl.com address for a download path from a search result.

    The key goes back on as the api_key parameter, the form SubDL documents and
    returns itself, so the download counts against the viewer's own key.
    """
    if not is_download_path(path):
        raise SubDLError(SubDLError.FAILED, "not a SubDL download address")
    url = strip_api_key(path)
    if url.startswith("/"):
        url = DOWNLOAD_BASE + url
    if api_key:
        url += ("&" if urllib.parse.urlsplit(url).query else "?") + urllib.parse.urlencode({"api_key": api_key})
    return url


def parse_retry_after(value: str, now: float) -> Optional[float]:
    """Seconds to wait from a Retry-After header: delta-seconds or an HTTP date."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, when.timestamp() - now)


def filename_from_disposition(value: str) -> str:
    """The file name in a Content-Disposition header, or ""."""
    match = re.search(r"filename\*\s*=\s*([\w-]*)'[^']*'([^;]+)", value or "", re.I)
    if match:
        try:
            return urllib.parse.unquote(match.group(2).strip().strip('"'), encoding=match.group(1) or "utf-8")
        except LookupError:
            return urllib.parse.unquote(match.group(2).strip().strip('"'))
    match = re.search(r'filename\s*=\s*"([^"]*)"', value or "", re.I) or re.search(
        r"filename\s*=\s*([^;]+)", value or "", re.I)
    return match.group(1).strip() if match else ""


def is_title_miss(body: dict) -> bool:
    """SubDL answered, but found no film or show for that request."""
    return body.get("status") is False and "find" in str(body.get("error") or "").lower()


class _SubDLRedirectsOnly(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to an https subdl.com host, refusing it before it is sent.

    urllib follows every redirect by default, so a check on where a request ended up
    would come after the request elsewhere had already been made.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_subdl_url(newurl):
            fp.close()
            raise SubDLError(SubDLError.FAILED, "redirect away from subdl.com refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read(stream, limit: int, headers) -> bytes:
    chunks = []
    size = 0
    while True:
        chunk = stream.read(min(65536, limit + 1 - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise SubDLError(SubDLError.FAILED, "response too large")
    data = b"".join(chunks)
    if headers is not None and (headers.get("Content-Encoding") or "").lower() == "gzip":
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        data = decoder.decompress(data, limit + 1)
        if len(data) > limit or decoder.unconsumed_tail:
            raise SubDLError(SubDLError.FAILED, "response too large")
    return data


def urllib_transport(request: urllib.request.Request, timeout: float, limit: int) -> Response:
    opener = urllib.request.build_opener(_SubDLRedirectsOnly())
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        try:
            body = _read(error, min(limit, MAX_ERROR_BYTES), error.headers) if error.fp else b""
        except SubDLError:
            body = b""
        finally:
            error.close()
        return Response(error.code, error.headers, body)
    with response:
        return Response(response.status, response.headers, _read(response, limit, response.headers))


#: Connection failures, timeouts, resets and broken gzip. HTTP errors are answers.
_NETWORK_ERRORS = (OSError, http.client.HTTPException, zlib.error, EOFError)
_RETRYABLE = ("rate_limit", "service_busy")


class SubDLClient:
    def __init__(self, api_key: str, user_agent: str, transport: Optional[Transport] = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.time,
                 log: Optional[Callable[[str], None]] = None, timeout: float = TIMEOUT_S) -> None:
        self.api_key = (api_key or "").strip()
        self.user_agent = user_agent
        self.transport = transport or urllib_transport
        self.sleep = sleep
        self.clock = clock
        self.log = log or (lambda message: None)
        self.timeout = timeout

    def _require_key(self) -> None:
        if not self.api_key:
            raise SubDLError(SubDLError.MISSING_KEY)

    def search(self, params: Dict[str, str]) -> dict:
        """One page of search results.

        The body comes back as SubDL sent it, also when SubDL found no title for the
        request (``is_title_miss``), so the caller can try its next way of asking.
        """
        self._require_key()
        query = {key: str(value) for key, value in params.items() if value not in (None, "")}
        query.update(api_key=self.api_key, client=CLIENT)
        response = self._send("search", API_BASE + SEARCH_PATH, query, "application/json", MAX_JSON_BYTES)
        body = response.json()
        if response.status == 200:
            if body.get("status") is True or is_title_miss(body):
                return body
            raise SubDLError(SubDLError.FAILED, _code(body) or "unexpected answer", 200)
        raise self._error(response, body)

    def account(self) -> dict:
        """The key's account, plan and today's usage (does not use up a search)."""
        self._require_key()
        response = self._send("account", API_BASE + ACCOUNT_PATH, {"api_key": self.api_key},
                              "application/json", MAX_ERROR_BYTES)
        body = response.json()
        if response.status == 200 and body.get("status") is True:
            return body
        raise self._error(response, body)

    def download(self, path: str) -> Tuple[bytes, str]:
        """The bytes behind a download path, and the file name SubDL gives them."""
        self._require_key()
        response = self._send("download", download_url(path, self.api_key), None, "*/*", MAX_DOWNLOAD_BYTES)
        if response.status == 200 and response.body:
            return response.body, filename_from_disposition(response.header("Content-Disposition"))
        raise self._error(response, response.json())

    def _send(self, label: str, url: str, query: Optional[Dict[str, str]], accept: str,
              limit: int) -> Response:
        """GET with retries. ``label`` is all the log ever learns about the request."""
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": accept,
            "Accept-Encoding": "gzip",
        })
        for attempt in range(3):
            try:
                response = self.transport(request, self.timeout, limit)
            except SubDLError:
                raise
            except _NETWORK_ERRORS as error:
                self.log("%s: %s" % (label, type(error).__name__))
                if attempt == 0:
                    self.sleep(1.0)
                    continue
                raise SubDLError(SubDLError.NETWORK, type(error).__name__)
            self.log("%s: HTTP %d" % (label, response.status))
            wait = self._retry_wait(response)
            if wait is None or attempt == 2:
                return response
            self.sleep(wait)
        return response  # pragma: no cover - the loop always returns or raises

    def _retry_wait(self, response: Response) -> Optional[float]:
        """Seconds to wait before asking again, or None when asking again won't help."""
        if response.status == 429:
            if _code(response.json()) not in _RETRYABLE:
                return None  # a daily limit: no point asking again today
        elif response.status not in (502, 503, 504):
            return None
        wait = self._retry_after(response)
        if wait is None:
            return 2.0
        return max(0.5, wait) if wait <= MAX_WAIT_S else None

    def _retry_after(self, response: Response) -> Optional[float]:
        wait = parse_retry_after(response.header("Retry-After"), self.clock())
        if wait is None:
            try:
                wait = float(response.json().get("retryAfterSeconds"))
            except (TypeError, ValueError):
                wait = None
        return wait

    def _error(self, response: Response, body: dict) -> SubDLError:
        status = response.status
        code = _code(body)
        if code == "daily_limit":
            return SubDLError(SubDLError.DAILY_LIMIT, code, status)
        if code in ("api_download_limit_exceeded", "download_limit_exceeded"):
            return SubDLError(SubDLError.DOWNLOAD_LIMIT, code, status, self._retry_after(response))
        if status == 403 or code == "not_authorized":
            return SubDLError(SubDLError.INVALID_KEY, code or "HTTP 403", status)
        if status == 429 or status in (502, 503, 504):
            return SubDLError(SubDLError.BUSY, code or "HTTP %d" % status, status, self._retry_after(response))
        if status == 404 or code == "subtitle_not_found":
            return SubDLError(SubDLError.NOT_FOUND, code or "HTTP 404", status)
        return SubDLError(SubDLError.FAILED, code or "HTTP %d" % status, status)


def _code(body: dict) -> str:
    """The machine-readable error code in a SubDL error body ("daily_limit"), or ""."""
    error = body.get("error")
    if isinstance(error, dict):  # API v2 envelope, should one ever come back
        error = error.get("code")
    return error if isinstance(error, str) and len(error) <= 64 else ""
