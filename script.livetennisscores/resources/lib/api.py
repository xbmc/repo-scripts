"""Live Tennis API client for script.livetennisscores.

Standard library only -- ``urllib.request`` rather than ``requests`` -- so the
add-on declares no dependency beyond ``xbmc.python``.

Endpoints used, both on the provider's FREE tier:

* ``GET /matches?status=live``  -- the live list, with each match's latest score
* ``GET /matches/{matchId}``    -- one match in full

Confirmed against https://docs.livetennisapi.com/llms.txt and
https://docs.livetennisapi.com/openapi.yaml (retrieved 2026-09-12):
the base URL, the ``X-API-Key`` header, ``status=live`` being free while
``status=completed`` requires a paid plan, and the ``{"data": [...],
"meta": {...}}`` envelope.

The key is read from add-on settings by the caller and is sent only as a
request header. It is never placed in the URL (the provider also accepts
``?token=``, but URLs reach logs, history and referrers) and never logged.
"""

import http.client
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.livetennisapi.com/api/public/v1"
USER_AGENT = "Kodi script.livetennisscores/1.0.0"

# Kept under the five seconds Kodi allows a service to finish in after it
# signals abort: a longer socket timeout can leave the service inside a stalled
# read when Kodi wants to shut down, and Kodi then force-kills it and logs an
# error. A slow network costs a skipped cycle, which is recoverable; being
# force-killed is not.
TIMEOUT_SECONDS = 4

# The API's maximum page size. Asking for the largest page makes one request
# cover the live list in every realistic case instead of silently truncating
# it at a smaller default.
MAX_PAGE_SIZE = 200

# Hard cap on pages fetched per poll, so a pathological `has_more` cannot spend
# the whole daily request allowance in one cycle.
MAX_PAGES = 3

# Outcomes the caller can act on without catching exceptions.
OK = "ok"
NO_KEY = "no_key"
UNAUTHORIZED = "unauthorized"
UPGRADE_REQUIRED = "upgrade_required"
RATE_LIMITED = "rate_limited"
NOT_FOUND = "not_found"
TRANSPORT_ERROR = "transport_error"
BAD_RESPONSE = "bad_response"
HTTP_ERROR = "http_error"


class Result:
    """A request outcome. Truthy only when the call actually returned data."""

    __slots__ = ("status", "payload", "detail")

    def __init__(self, status, payload=None, detail=""):
        self.status = status
        self.payload = payload
        self.detail = detail

    def __bool__(self):
        return self.status == OK

    def __repr__(self):
        return f"Result({self.status!r}, detail={self.detail!r})"


def _status_for_code(code):
    if code == 401:
        return UNAUTHORIZED
    if code == 403:
        return UPGRADE_REQUIRED
    if code == 429:
        return RATE_LIMITED
    if code in (404, 410):
        return NOT_FOUND
    return HTTP_ERROR


class Client:
    """Reads the two free endpoints and never raises at the call site."""

    def __init__(self, api_key, log=None, opener=None, base_url=BASE_URL):
        self._api_key = (api_key or "").strip()
        self._log = log or (lambda message: None)
        # Injectable so the transport can be exercised without a network.
        self._opener = opener or urllib.request.urlopen
        self._base_url = base_url.rstrip("/")

    @property
    def has_key(self):
        return bool(self._api_key)

    def live_matches(self, limit=MAX_PAGE_SIZE):
        """``GET /matches?status=live``, following pagination.

        The response envelope's ``meta.has_more`` is the documented way to know
        another page exists ("Read this rather than comparing count to limit"),
        so it is followed rather than assuming one page holds everything. In
        practice the first page does, because it asks for the largest size the
        API allows; the loop exists so a busy day is not silently truncated.

        A failure on the first page is returned as that failure. A failure
        part-way through is returned as OK with the pages gathered so far --
        an incomplete list is better than none, and treating it as a total
        failure would look to the caller like every match had finished.
        """
        bounded = max(1, min(int(limit), MAX_PAGE_SIZE))
        gathered = []
        offset = 0

        for page in range(MAX_PAGES):
            result = self._get("/matches", {
                "status": "live", "limit": bounded, "offset": offset})
            if not result:
                return result if page == 0 else Result(OK, {"data": gathered})

            payload = result.payload if isinstance(result.payload, dict) else {}
            data = payload.get("data")
            gathered.extend(item for item in (data or []) if isinstance(item, dict))

            meta = payload.get("meta")
            meta = meta if isinstance(meta, dict) else {}
            if meta.get("has_more") is not True:
                break
            offset += bounded
        else:
            self._log(f"live list still had more after {MAX_PAGES} pages; "
                      "using what was read")

        return Result(OK, {"data": gathered})

    def match(self, match_id):
        """``GET /matches/{matchId}`` -- full detail for one match."""
        quoted = urllib.parse.quote(str(match_id), safe="")
        return self._get(f"/matches/{quoted}")

    def _get(self, path, params=None):
        if not self._api_key:
            # Nothing to report and nothing to log: no key is a configuration
            # state, not a failure.
            return Result(NO_KEY)

        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        request = urllib.request.Request(url, method="GET")
        request.add_header("X-API-Key", self._api_key)
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", USER_AGENT)

        try:
            with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = _status_for_code(error.code)
            # The path is safe to log; the key is a header, so it is not in it.
            self._log(f"{path} returned HTTP {error.code} ({status})")
            return Result(status, detail=f"HTTP {error.code}")
        except urllib.error.URLError as error:
            self._log(f"{path} could not be reached: {error.reason}")
            return Result(TRANSPORT_ERROR, detail=str(error.reason))
        except (socket.timeout, TimeoutError):
            self._log(f"{path} timed out after {TIMEOUT_SECONDS}s")
            return Result(TRANSPORT_ERROR, detail="timeout")
        except http.client.HTTPException as error:
            # A truncated or malformed response. These do NOT subclass OSError,
            # so without this clause they would escape to the service loop.
            self._log(f"{path} gave a malformed response: {type(error).__name__}")
            return Result(TRANSPORT_ERROR, detail=type(error).__name__)
        except OSError as error:
            self._log(f"{path} failed: {error}")
            return Result(TRANSPORT_ERROR, detail=str(error))

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            self._log(f"{path} returned a body that is not JSON: {error}")
            return Result(BAD_RESPONSE, detail="unparseable body")

        return Result(OK, payload=payload)
