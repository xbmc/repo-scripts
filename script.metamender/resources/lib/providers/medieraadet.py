"""Medieraadet (Denmark) certification lookup through the Danish film
database's public API.

The search lists films by title prefix (`FilmList`, with each film's
`ReleaseYear`); the rating (`AssesmentCode`, the API's own spelling) and
the Danish and original titles only come with a film's detail record. So
the search results are ranked by year and at most MAX_DETAILS details are
fetched per item. A search that misses with a leading article ("The Hunt")
is tried once more without it. Medieraadet rates films only, so a TV show
is answered "no rating" without a request.

Logging:
    Logger: 'medieraadet'
    Key events (from providers/http, labels "medieraadet.search" and
    "medieraadet.film"):
        - <label>.transient (WARNING): The API failed or blocked the request
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
    years_match,
)
from resources.lib.providers.http import provider_get
from resources.lib.utils import TransientProviderError, get_logger

log = get_logger('medieraadet')

SITE = "medieraadet"
COUNTRY = "DK"
RATINGS = frozenset({"A", "7", "11", "15"})
MEDIA_TYPES = frozenset({"movie"})
CODE_MAP = {"tfa": "A", "fr.u7": "7", "to7": "7", "to11": "11", "to15": "15"}
MAX_DETAILS = 3

_BASE = ("https://appfilmvurderinger.silver.extension.gopublic.dk/api/"
         "93c1d303-ae9e-44b1-b939-fb91ba32200a")
_ARTICLE = re.compile(
    r"^(the|a|an|der|die|das|den|det|de|le|la|les|el|los|las)\s+", re.IGNORECASE,
)


def lookup(
    title: str,
    original_title: str,
    year: int | None,
    media_type: str,
    imdb_id: str | None = None,
    pace: Callable[[], bool] = no_pace,
) -> str | None:
    """The Medieraadet rating ("A", "7", "11", "15") of a film, or None when
    it has none (always for a TV show). The original title is searched too
    when the item's title finds nothing. Raises TransientProviderError when
    the API is unavailable, answers without its usual structure, or ``pace``
    refuses a request (every search and detail fetch asks it first).
    ``imdb_id`` is part of the shared site interface; the API has no ids."""
    if media_type != "movie":
        return None
    rating = _find(title, title, original_title, year, pace)
    second = other_title(title, original_title)
    if rating is None and second:
        rating = _find(second, title, original_title, year, pace)
    return rating


def _find(
    query: str, title: str, original_title: str, year: int | None,
    pace: Callable[[], bool],
) -> str | None:
    films = _search(query, pace)
    if not films and _ARTICLE.match(query):
        films = _search(_ARTICLE.sub("", query), pace)
    # A known year first, in the API's order; a film without a year after
    # them rather than dropped.
    ranked = sorted(
        (f for f in films if years_match(_year(f), year)),
        key=lambda f: _year(f) is None,
    )
    candidates: list[Candidate] = []
    for film in ranked[:MAX_DETAILS]:
        detail = _detail(film, pace)
        if detail is None:
            continue
        rating = CODE_MAP.get(str(detail.get("AssesmentCode") or ""))
        if rating is None:
            continue
        titles = tuple(
            variant
            for key in ("Title", "OriginalTitle", "DanishTitle")
            for variant in _with_and_without_article(str(detail.get(key) or ""))
        )
        candidates.append((titles, _year(detail), rating))
    wanted = tuple(
        variant for t in (title, original_title) for variant in _with_and_without_article(t)
    )
    return best_match(wanted, year, candidates)


def _search(query: str, pace: Callable[[], bool]) -> list[dict[str, Any]]:
    paced(pace)
    data = provider_get(
        _BASE + "/film", logger=log, label="medieraadet.search", provider=SITE,
        params={"Title": query, "Sortby": "assessmentreleasedate", "Take": 10, "Skip": 0},
        headers={"Accept": "application/json"},
    )
    if data is None:
        return []
    films = data.get("FilmList")
    if not isinstance(films, list):
        raise TransientProviderError("medieraadet structure")
    return [f for f in films if isinstance(f, dict)]


def _detail(film: dict[str, Any], pace: Callable[[], bool]) -> dict[str, Any] | None:
    try:
        film_id = int(str(film.get("Id")))
    except (TypeError, ValueError):
        return None
    paced(pace)
    return provider_get(
        "{}/film/{}".format(_BASE, film_id), logger=log, label="medieraadet.film",
        provider=SITE, headers={"Accept": "application/json"},
    )


def _year(record: dict[str, Any]) -> int | None:
    value = record.get("ReleaseYear")
    return value if isinstance(value, int) and value > 0 else None


def _with_and_without_article(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    bare = _ARTICLE.sub("", text)
    return (text, bare) if bare != text else (text,)
