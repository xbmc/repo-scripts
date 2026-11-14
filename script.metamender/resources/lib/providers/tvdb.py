"""
TheTVDB v4 provider for MetaMender metadata lookups.

Fetches series names, translations and aliases (for show text fields and for
verifying untyped TVDB ids) and the full episode list of a series in one
language (for episode titles and plots).

Auth:
    The add-on's project key is exchanged for a bearer token at login. The
    token is cached for the process; a 401 triggers one fresh login and one
    retry. A login rejection, or a 401 that survives the fresh login, raises
    TvdbAuthError so the caller can disable TVDB without touching other
    providers; the caller logs it once.

Logging:
    Logger: 'tvdb'
    Key events:
        - tvdb.login: bearer token obtained
        - tvdb.series: series names and translations fetched
        - tvdb.episodes: full episode list fetched
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from resources.lib.constants import TVDB_API_KEY, TVDB_BASE_URL
from resources.lib.providers.http import provider_get, provider_post
from resources.lib.utils import (
    ApiKeyError,
    TransientProviderError,
    TvdbAuthError,
    get_logger,
)

log = get_logger('tvdb')

_PROVIDER = "tvdb"
_FALLBACK_LANG = "eng"
# A series has far fewer than this many 500-episode pages; the cap only stops
# a server that never returns links.next=null from looping forever.
_MAX_EPISODE_PAGES = 100

_token: Optional[str] = None
_token_lock = threading.Lock()


def _reset_token() -> None:
    """Forget the cached bearer token (tests, and the forced re-login)."""
    global _token
    with _token_lock:
        _token = None


def _login() -> str:
    """Exchange the project key for a bearer token and cache it."""
    global _token
    try:
        body = provider_post(
            "{}/login".format(TVDB_BASE_URL),
            log,
            "tvdb.login",
            {"apikey": TVDB_API_KEY},
            provider=_PROVIDER,
            transient_400=True,
        )
    except ApiKeyError:
        raise TvdbAuthError("TVDB login rejected")
    token = ((body or {}).get("data") or {}).get("token")
    if not token:
        raise TransientProviderError("tvdb login returned no token")
    with _token_lock:
        _token = token
    log.debug("TVDB login ok", event="tvdb.login")
    return token


def _bearer() -> Dict[str, str]:
    token = _token or _login()
    return {"Authorization": "Bearer {}".format(token)}


def _get(path: str) -> Optional[Dict[str, Any]]:
    """GET a TVDB v4 path with the bearer token; None on 404."""
    url = "{}{}".format(TVDB_BASE_URL, path)
    for attempt in (0, 1):
        try:
            return provider_get(
                url,
                log,
                "tvdb.request",
                provider=_PROVIDER,
                headers=_bearer(),
                transient_400=True,
            )
        except ApiKeyError:
            if attempt:
                raise TvdbAuthError("TVDB refused a fresh token")
            _reset_token()
    raise AssertionError("unreachable")  # pragma: no cover


def _translation(tvdb_id: str, lang: str) -> Dict[str, str]:
    body = _get("/series/{}/translations/{}".format(tvdb_id, lang))
    data = (body or {}).get("data") or {}
    return {
        "name": data.get("name") or "",
        "overview": data.get("overview") or "",
    }


def _series_year(record: Dict[str, Any]) -> Optional[int]:
    for raw in (record.get("year"), (record.get("firstAired") or "")[:4]):
        text = str(raw or "")
        if len(text) == 4 and text.isdigit():
            return int(text)
    return None


def fetch_series(tvdb_id: str, lang: str) -> Optional[Dict[str, Any]]:
    """Fetch a series' text in `lang` (a TVDB code such as "nld") and its names.

    Returns {"name", "overview", "names", "year", "original_language"} or None when TVDB has no
    such series. ``year`` is the series' first-aired year as an int, or None
    when TVDB has neither a year nor a first-aired date. name/overview are the `lang` translation only ("" when TVDB has
    none), never the primary-language text, so a caller cannot mistake a
    foreign original for a native value. `names` holds the primary name, the
    `lang` and English translations and every alias, for id verification.
    """
    series = _get("/series/{}".format(tvdb_id))
    if series is None:
        return None
    record = series.get("data") or {}
    primary = record.get("name") or ""
    native = _translation(tvdb_id, lang)
    english = native if lang == _FALLBACK_LANG else _translation(tvdb_id, _FALLBACK_LANG)
    extended = _get("/series/{}/extended?short=true".format(tvdb_id))
    aliases = ((extended or {}).get("data") or {}).get("aliases") or []

    names: List[str] = []
    for candidate in [primary, native["name"], english["name"]] + [
        a.get("name") or "" for a in aliases
    ]:
        if candidate and candidate not in names:
            names.append(candidate)
    log.debug("TVDB series fetched", event="tvdb.series", tvdb_id=tvdb_id, lang=lang)
    return {
        "name": native["name"],
        "overview": native["overview"],
        "names": names,
        "year": _series_year(record),
        "original_language": record.get("originalLanguage") or "",
    }


def _episode_records(
    tvdb_id: str, order: str, lang: str
) -> Optional[List[Dict[str, Any]]]:
    """Every raw episode record of a series in `order` ("default", "official")
    and `lang`, across all pages; None when TVDB has no such series. Raises
    TransientProviderError when any later page fails or vanishes, so a partial
    list is never returned or cached."""
    records: List[Dict[str, Any]] = []
    for page in range(_MAX_EPISODE_PAGES):
        body = _get("/series/{}/episodes/{}/{}?page={}".format(tvdb_id, order, lang, page))
        if body is None:
            if page == 0:
                return None
            raise TransientProviderError("tvdb episode page {} missing".format(page))
        records.extend((body.get("data") or {}).get("episodes") or [])
        if not (body.get("links") or {}).get("next"):
            log.debug(
                "TVDB episodes fetched",
                event="tvdb.episodes",
                tvdb_id=tvdb_id,
                order=order,
                lang=lang,
                episodes=len(records),
            )
            return records
    raise TransientProviderError("tvdb episode paging did not end")


def fetch_series_episodes(
    tvdb_id: str, lang: str
) -> Optional[Dict[str, Dict[str, str]]]:
    """Fetch every episode of a series in `lang`, keyed by TVDB episode id.

    Returns {episode_id: {"title", "plot"}}, or None when TVDB has no such
    series. Title and plot are the `lang` translation only: TVDB returns null
    for an episode with no translation in `lang` (verified live, no fallback
    to the original or English text), which becomes "". Records without an id
    are skipped. Raises TransientProviderError when any page
    fails or vanishes, so a partial list is never returned or cached.
    """
    records = _episode_records(tvdb_id, "default", lang)
    if records is None:
        return None
    return {
        str(ep["id"]): {"title": ep.get("name") or "", "plot": ep.get("overview") or ""}
        for ep in records if ep.get("id") is not None
    }


def fetch_series_episode_numbers(
    tvdb_id: str, lang: str
) -> Optional[List[Dict[str, Any]]]:
    """Every episode of a series in the aired ("official") order, the order
    TVmaze numbers by, for matching an episode by its season and number.

    Returns [{"tvdb_id", "season", "number", "aired", "title"}] with "" for a
    missing date or `lang` translation, or None when TVDB has no such series.
    Raises TransientProviderError as fetch_series_episodes does.
    """
    records = _episode_records(tvdb_id, "official", lang)
    if records is None:
        return None
    return [
        {
            "tvdb_id": str(ep["id"]),
            "season": int(ep.get("seasonNumber") or 0),
            "number": int(ep.get("number") or 0),
            "aired": ep.get("aired") or "",
            "title": ep.get("name") or "",
        }
        for ep in records if ep.get("id") is not None
    ]
