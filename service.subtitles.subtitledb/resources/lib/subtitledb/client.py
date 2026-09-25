"""HTTP client for the SubtitleDB open API.

Standard library only. Kodi ships its own Python with no pip, Bazarr pins its
dependency tree, and neither is a place to add a package: ``urllib`` is what both
already have. The web bindings use ``fetch`` for the same reason.

The API takes no key and no account, so there is nothing to configure but the base
URL, which exists only so a test can point it somewhere else.
"""

from __future__ import annotations

import gzip
import http.client
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass

DEFAULT_API_BASE = "https://api.thesubtitledb.org"

RETRY_BASE_S = 0.3
MAX_BACKOFF_S = 8.0


class SubtitleDbError(Exception):
    """Any failure that reached the API and came back not-OK."""

    def __init__(self, message: str, status: int | None = None, body: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body or {}

    @property
    def fallthrough(self) -> bool:
        """404 and 400 mean "this rung does not apply", not "give up"."""
        return self.status in (400, 404)


#: A connection that failed, timed out or broke off mid-body, and a body that does not
#: decompress. OSError covers URLError, timeouts and resets; HTTPError is caught first.
_BROKEN = (OSError, http.client.HTTPException, EOFError, zlib.error)


class _OurHostsOnly(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to one of our hosts, and refuses it before it is sent.

    urllib follows every redirect by default, so checking where a request ended up
    would come after the request to somewhere else had already been made.
    """

    def __init__(self, api_base: str) -> None:
        self.api_base = api_base

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _ours(newurl, self.api_base):
            fp.close()
            raise SubtitleDbError("redirected off our hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass
class Client:
    api_base: str = DEFAULT_API_BASE
    #: Sent as a query parameter, not a header: identifies the plugin in our logs.
    client: str = "subtitledb-plugin"
    timeout: float = 15.0
    retries: int = 2
    user_agent: str = "subtitledb-plugin/0.1 (+https://thesubtitledb.org)"

    def __post_init__(self) -> None:
        self.api_base = self.api_base.rstrip("/")

    # ---- requests ---------------------------------------------------------

    def _url(self, path: str, params: dict | None = None) -> str:
        query = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        query["client"] = self.client
        return "%s%s?%s" % (self.api_base, path, urllib.parse.urlencode(query))

    def _open(self, url: str, accept: str):
        req = urllib.request.Request(url, method="GET")  # noqa: S310 - _url builds it
        req.add_header("Accept", accept)
        req.add_header("Accept-Encoding", "gzip")
        req.add_header("User-Agent", self.user_agent)
        opener = urllib.request.build_opener(_OurHostsOnly(self.api_base))
        return opener.open(req, timeout=self.timeout)

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        """Honour Retry-After, else exponential backoff with full jitter.

        The jitter is not decoration: a media server scanning a library asks about
        many files at once, and un-jittered backoff marches all of them into the
        next wall together.
        """
        if retry_after:
            try:
                return min(float(retry_after), MAX_BACKOFF_S)
            except ValueError:
                pass
        return random.random() * min(RETRY_BASE_S * (2**attempt), MAX_BACKOFF_S)  # noqa: S311

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self._url(path, params)
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with self._open(url, "application/json") as res:
                    raw = _read(res)
            except urllib.error.HTTPError as err:
                body = {}
                try:
                    body = json.loads(err.read().decode("utf-8"))
                except Exception:
                    pass
                message = body.get("message") or body.get("error") or err.reason
                # 4xx other than 429 will say the same thing however many times we ask.
                if err.code < 500 and err.code != 429:
                    raise SubtitleDbError(str(message), err.code, body) from err
                last = SubtitleDbError(str(message), err.code, body)
                if attempt < self.retries:
                    time.sleep(self._backoff(attempt, err.headers.get("Retry-After")))
                continue
            except _BROKEN as err:
                last = SubtitleDbError("cannot reach %s: %s" % (self.api_base, err))
                if attempt < self.retries:
                    time.sleep(self._backoff(attempt, None))
                continue
            try:
                return json.loads(raw.decode("utf-8"))
            except ValueError as err:
                raise SubtitleDbError("the API sent something that is not JSON") from err
        raise last if last else SubtitleDbError("request failed")

    # ---- lookup verbs -----------------------------------------------------
    #
    # One identifier in, the whole title back as a single bundle. tmdb is the headline
    # key; by-imdb sits beside it, first-class and the same bundle shape, because media
    # servers identify content by IMDb id. by-title resolves free text server-side, so
    # no ranked list of titles ever crosses the wire. Every verb takes the same paging
    # and lang/format/sort filter, and drills to a season or episode when the caller
    # passes the numbers. lang takes up to 16 comma separated codes; lang and format
    # are both ignored on a series or season bundle, so drill when a filter must hold.

    def by_tmdb(self, tmdb: int, season=None, episode=None, **params) -> dict:
        return self._get("/v1/by-tmdb/%d%s" % (int(tmdb), _drill(season, episode)), params)

    def by_imdb(self, imdb: str | int, season=None, episode=None, **params) -> dict:
        return self._get("/v1/by-imdb/%s%s" % (_imdb(imdb), _drill(season, episode)), params)

    def by_title(self, q: str, season=None, episode=None, **params) -> dict:
        # Free text goes in a query parameter, not the path: release and title text
        # carry dots and slashes that a path segment cannot.
        return self._get("/v1/by-title%s" % _drill(season, episode), {"q": q, **params})

    def download(self, url: str) -> bytes:
        """Fetch subtitle bytes from a ``download_url`` the API gave us.

        The URL is used as it was published rather than rebuilt: it redirects to
        wherever the file currently lives, and that address is not ours to store.
        Only our own hosts are asked, and a redirect is checked before it is
        followed, so a subtitle download cannot become a request to somewhere else.
        Every failure is a SubtitleDbError, the one exception callers catch.
        """
        if not _ours(url, self.api_base):
            raise SubtitleDbError("refusing to download from %s" % url)
        try:
            with self._open(url, "*/*") as res:
                return _read(res)
        except urllib.error.HTTPError as err:
            raise SubtitleDbError("HTTP %d from %s" % (err.code, url), err.code) from err
        except _BROKEN as err:
            raise SubtitleDbError("cannot download %s: %s" % (url, err)) from err


def _read(res) -> bytes:
    raw = res.read()
    if res.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    return raw


def _imdb(value: str | int) -> str:
    """The API takes either spelling. Send the digits and there is nothing to slip."""
    text = str(value).strip().lower()
    return text[2:] if text.startswith("tt") else text


def _drill(season, episode) -> str:
    """The ``/season/:s[/episode/:e]`` suffix a series lookup narrows with, or ''.

    A movie ignores it; a series bundle narrows to exactly that season or episode.
    """
    if season is None:
        return ""
    path = "/season/%d" % int(season)
    return path if episode is None else "%s/episode/%d" % (path, int(episode))


def _ours(url: str, api_base: str) -> bool:
    """True for the API host and the files host it redirects to, nothing else."""
    try:
        host = urllib.parse.urlsplit(url).hostname or ""
        base = urllib.parse.urlsplit(api_base).hostname or ""
    except ValueError:
        return False
    if not host:
        return False
    if host == base:
        return True
    # api.thesubtitledb.org redirects to files.thesubtitledb.org. Both are ours; the
    # split exists so a rate limit on the files host cannot be sidestepped.
    root = ".".join(base.split(".")[-2:])
    return bool(root) and (host == root or host.endswith("." + root))
