"""BBFC (United Kingdom) certification lookup through the bbfc.co.uk search.

The search page is a Next.js page: its results sit as JSON in the
`__NEXT_DATA__` script (props.pageProps.searchResults.results), each with a
type ("Film", "TV Show"), a title carrying the year ("Interstellar (2014)")
and a classification. A page without that script is a challenge or a
redesign, so it is transient rather than "no rating". The site answers
metamender's own User-Agent; no browser disguise is needed.

Logging:
    Logger: 'bbfc'
    Key events (from providers/http, label "bbfc.search"):
        - bbfc.search.transient (WARNING): The site failed or blocked the request
"""
from __future__ import annotations

import json
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
from resources.lib.providers.http import provider_get_text
from resources.lib.utils import TransientProviderError, get_logger

log = get_logger('bbfc')

SITE = "bbfc"
COUNTRY = "GB"
RATINGS = frozenset({"U", "PG", "12", "12A", "15", "18", "R18"})
MEDIA_TYPES = frozenset({"movie", "tvshow"})

_SEARCH_URL = "https://www.bbfc.co.uk/search"
_NEXT_DATA = '<script id="__NEXT_DATA__"'
_TITLE_YEAR = re.compile(r"^(.*?)\s*\((\d{4})\)\s*$")


def lookup(
    title: str,
    original_title: str,
    year: int | None,
    media_type: str,
    imdb_id: str | None = None,
    pace: Callable[[], bool] = no_pace,
) -> str | None:
    """The BBFC classification of the item, or None when the BBFC has no
    matching film or show. The original title is searched too when the item's
    title finds nothing. Raises TransientProviderError when the site is
    unavailable, the page lacks its result data, or ``pace`` refuses a
    request. ``imdb_id`` is part of the shared site interface; BBFC results
    carry no external ids."""
    rating = _search(title, title, original_title, year, media_type, pace)
    second = other_title(title, original_title)
    if rating is None and second:
        rating = _search(second, title, original_title, year, media_type, pace)
    return rating


def _search(
    query: str,
    title: str,
    original_title: str,
    year: int | None,
    media_type: str,
    pace: Callable[[], bool],
) -> str | None:
    tv = media_type == "tvshow"
    paced(pace)
    page = provider_get_text(
        _SEARCH_URL, logger=log, label="bbfc.search", provider=SITE,
        params={"q": query, "t[]": "TV Show" if tv else "Film"},
    )
    if page is None:
        return None
    candidates: list[Candidate] = []
    for result in _results(page):
        kind = str(result.get("type") or "").lower()
        if ("tv" in kind) != tv:
            continue
        rating = str(result.get("classification") or "")
        if rating not in RATINGS:
            continue
        name, site_year = _split_year(str(result.get("title") or ""))
        candidates.append(((name,), site_year, rating))
    return best_match((title, original_title), year, candidates)


def _results(page: str) -> list[dict[str, Any]]:
    start = page.find(_NEXT_DATA)
    body_start = page.find(">", start) + 1 if start >= 0 else -1
    end = page.find("</script>", body_start) if body_start > 0 else -1
    if end < 0:
        raise TransientProviderError("bbfc structure")
    try:
        data = json.loads(page[body_start:end])
        results = data["props"]["pageProps"]["searchResults"]["results"]
    except (ValueError, KeyError, TypeError) as exc:
        raise TransientProviderError("bbfc structure") from exc
    if not isinstance(results, list):
        raise TransientProviderError("bbfc structure")
    return [r for r in results if isinstance(r, dict)]


def _split_year(text: str) -> tuple[str, int | None]:
    match = _TITLE_YEAR.match(text)
    if match:
        return match.group(1), int(match.group(2))
    return text, None
