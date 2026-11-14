"""FSK (Germany) certification lookup through the FSK release search API.

The API searches its whole text, not just titles, and always answers with up
to 500 documents (there is no page size), so matching is strict (see
certification.best_match). TV series are rated per season: each season is
its own document ("Dark (S1)", "Dark Matter Staffel 2 Ep. 14"), so season
markers are stripped and the earliest season that matches wins.
`yearProduction` is the production year of the film or season.

Logging:
    Logger: 'fsk'
    Key events (from providers/http, label "fsk.search"):
        - fsk.search.transient (WARNING): The API failed or blocked the request
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from resources.lib.engine.certification import (
    Candidate,
    best_match,
    no_pace,
    other_title,
    paced,
)
from resources.lib.providers.http import provider_get
from resources.lib.utils import TransientProviderError, get_logger

log = get_logger('fsk')

SITE = "fsk"
COUNTRY = "DE"
RATINGS = frozenset({"0", "6", "12", "16", "18"})
MEDIA_TYPES = frozenset({"movie", "tvshow"})

_SEARCH_URL = "https://www.fsk.de/fskapi/ReleaseSearch"
_SEASON_MARKER = re.compile(
    r"\s*(\((s|staffel\s*)\d+\)|-?\s*\b(staffel|season|ep\.?|episode)\b.*)$",
    re.IGNORECASE,
)


def lookup(
    title: str,
    original_title: str,
    year: int | None,
    media_type: str,
    imdb_id: str | None = None,
    pace: Callable[[], bool] = no_pace,
) -> str | None:
    """The FSK rating ("0", "6", "12", "16", "18") of the item, or None when
    FSK has no matching release. The original title is searched too when the
    item's title finds nothing. Raises TransientProviderError when the API is
    unavailable, answers without its usual structure, or ``pace`` refuses a
    request."""
    rating = _search(title, title, original_title, year, media_type, imdb_id, pace)
    second = other_title(title, original_title)
    if rating is None and second:
        rating = _search(second, title, original_title, year, media_type, imdb_id, pace)
    return rating


def _search(
    query: str,
    title: str,
    original_title: str,
    year: int | None,
    media_type: str,
    imdb_id: str | None,
    pace: Callable[[], bool],
) -> str | None:
    tv = media_type == "tvshow"
    params: dict[str, Any] = {
        "searchLayout": "full",
        "searchTitle": query,
        "sort": "__ratingReleaseDateTc",
    }
    if tv:
        params.update({"superType": "serial", "serialOptions[]": "TVSR"})
        if year is not None:
            # Seasons are rated after they air: only a lower bound narrows
            # the answer without losing the first season.
            params["ratingReleaseDateFrom"] = "{}-01-01".format(year - 1)
    else:
        params.update({"superType": "single", "singleOptions[]": "SP"})
    paced(pace)
    data = provider_get(_SEARCH_URL, logger=log, label="fsk.search", params=params,
                        provider=SITE)
    if data is None:
        return None
    docs = (data.get("data") or {}).get("docs") if data.get("success") else None
    if not isinstance(docs, list):
        raise TransientProviderError("fsk structure")

    rated = [d for d in docs if isinstance(d, dict) and str(d.get("__rating")) in RATINGS]
    if imdb_id:
        for doc in rated:
            ids = {s.get("imdbId") for s in doc.get("subproducts") or [] if isinstance(s, dict)}
            if imdb_id in ids:
                return str(doc["__rating"])
    if tv:
        rated.sort(key=lambda d: d.get("seasonNumber") or 0)
    candidates: list[Candidate] = [
        (_titles(doc, tv), _year(doc), str(doc["__rating"])) for doc in rated
    ]
    return best_match((title, original_title), year, candidates)


def _titles(doc: dict[str, Any], tv: bool) -> tuple[str, ...]:
    titles = [str(doc.get("mainTitle") or ""), str(doc.get("mainOriginalTitle") or "")]
    if tv:
        titles = [_SEASON_MARKER.sub("", t) for t in titles]
    return tuple(t for t in titles if t)


def _year(doc: dict[str, Any]) -> int | None:
    value = doc.get("yearProduction")
    return value if isinstance(value, int) and value > 0 else None
