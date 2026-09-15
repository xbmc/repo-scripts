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
# the whole daily request allowance in one cycle. Reaching it means the list
# returned is INCOMPLETE, which the caller is told about rather than left to
# guess (see ``Result.complete``).
MAX_PAGES = 3

# Outcomes the caller can act on without catching exceptions.
OK = "ok"
NO_KEY = "no_key"
BUDGET_SPENT = "budget_spent"
UNAUTHORIZED = "unauthorized"
UPGRADE_REQUIRED = "upgrade_required"
RATE_LIMITED = "rate_limited"
NOT_FOUND = "not_found"
TRANSPORT_ERROR = "transport_error"
BAD_RESPONSE = "bad_response"
HTTP_ERROR = "http_error"


class Result:
    """A request outcome. Truthy only when the call actually returned data.

    ``complete`` answers a question the caller cannot answer for itself: is
    this the whole list, or only as much of it as could be read? A list that
    stopped at the page cap, lost a page to an error, or ran out of request
    budget part-way through looks exactly like a shorter list, and something
    that infers a match has finished from its absence must not be handed one
    without being told.

    A result that is not OK carries no list at all, so it is never complete
    whatever the caller asked for. That is the safe answer rather than the
    vacuous one: a future caller that reads ``complete`` before checking the
    status gets "do not trust this", not "this is everything".
    """

    __slots__ = ("status", "payload", "detail", "complete")

    def __init__(self, status, payload=None, detail="", complete=True):
        self.status = status
        self.payload = payload
        self.detail = detail
        self.complete = bool(complete) and status == OK

    def __bool__(self):
        return self.status == OK

    def __repr__(self):
        return (f"Result({self.status!r}, detail={self.detail!r}, "
                f"complete={self.complete!r})")


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

    def __init__(self, api_key, log=None, opener=None, base_url=BASE_URL,
                 budget=None):
        self._api_key = (api_key or "").strip()
        self._log = log or (lambda message: None)
        # Injectable so the transport can be exercised without a network.
        self._opener = opener or urllib.request.urlopen
        self._base_url = base_url.rstrip("/")
        # The day's request budget, if the caller wants one enforced. Anything
        # with a ``take()`` that returns False when the day is spent will do,
        # which keeps this module free of Kodi and of the file it lives in.
        self._budget = budget

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

        Whenever the list returned is only part of the live list, the result
        is marked ``complete=False``. That happens when a page after the first
        failed, when the page cap was reached with more still to come, when
        the request budget ran out mid-pagination, or when a page arrived in an
        envelope this add-on cannot read. All of them are indistinguishable
        from a short list by length alone, and :mod:`resources.lib.changes`
        infers a finished match from absence, so the distinction has to be
        carried.

        "Cannot read" is judged strictly, against the documented envelope: the
        body is an object, ``data`` is an array, ``meta`` is an object and
        ``meta.has_more`` is a boolean (schema ``ListMeta``, which declares
        ``has_more`` non-nullable and says to read it "rather than comparing
        count to limit"). Anything else and the add-on does not know whether
        another page exists -- which is the same as not knowing whether a
        match is missing -- so the list is reported incomplete. An empty live
        list is ``"data": []``, not an absent ``data``, so nothing normal is
        caught by this.
        """
        bounded = max(1, min(int(limit), MAX_PAGE_SIZE))
        gathered = []
        offset = 0
        complete = True

        for page in range(MAX_PAGES):
            result = self._get("/matches", {
                "status": "live", "limit": bounded, "offset": offset})
            if not result:
                if page == 0:
                    return result
                return Result(OK, {"data": gathered}, complete=False)

            page_data, has_more = self._page_of(result.payload)
            if page_data is None:
                complete = False
                break
            gathered.extend(page_data)

            if has_more is not True:
                # False means the list ended here. None means the envelope did
                # not say, and an unanswered question is not a "no".
                complete = has_more is False
                break
            offset += bounded
        else:
            self._log(f"live list still had more after {MAX_PAGES} pages; "
                      "using what was read, marked incomplete")
            complete = False

        return Result(OK, {"data": gathered}, complete=complete)

    def _page_of(self, payload):
        """Split one list page into ``(matches, has_more)``.

        :returns: ``(None, None)`` when the page is not the documented
            envelope at all, so nothing can be read from it; otherwise the
            match dicts it holds and ``meta.has_more`` as a bool, or None for
            ``has_more`` when the envelope did not state it.
        """
        if not isinstance(payload, dict):
            self._log("live list arrived in an unrecognised envelope; "
                      "treating the list as incomplete")
            return None, None

        data = payload.get("data")
        if not isinstance(data, list):
            self._log("live list page has no readable `data` array; "
                      "treating the list as incomplete")
            return None, None

        meta = payload.get("meta")
        has_more = meta.get("has_more") if isinstance(meta, dict) else None
        if not isinstance(has_more, bool):
            self._log("live list page did not state `meta.has_more`; "
                      "treating the list as incomplete")
            has_more = None

        return [item for item in data if isinstance(item, dict)], has_more

    def match(self, match_id):
        """``GET /matches/{matchId}`` -- full detail for one match."""
        quoted = urllib.parse.quote(str(match_id), safe="")
        return self._get(f"/matches/{quoted}")

    def _get(self, path, params=None):
        if not self._api_key:
            # Nothing to report and nothing to log: no key is a configuration
            # state, not a failure.
            return Result(NO_KEY)

        if self._budget is not None and not self._budget.take():
            # The day's allowance is gone. Sending this anyway would earn a
            # 429 and spend the provider's count on nothing, so it is not
            # sent: no socket is opened below this line.
            self._log(f"{path} not sent: the daily request budget is spent")
            return Result(BUDGET_SPENT, detail="daily request budget spent")

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
