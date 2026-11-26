"""
fanart.tv provider for MetaMender art lookups.

Movies (and movie collections, which fanart.tv serves on the movies endpoint
under the collection's TMDB id) are looked up by TMDB id (IMDb id as the
fallback for a movie), shows by TVDB id. One request serves every art type of
the item. fanart.tv answers an id it does not know with HTTP 200 and an empty
object, which is a clean "no art", not an error.

Auth:
    The add-on's project key is always sent; the user's personal key
    (``client_key``) only when set, which lifts fanart.tv's delay on new
    uploads. A 401 raises FanartAuthError so the caller can stop using
    fanart.tv for the cycle; the caller logs it once.

Logging:
    Logger: 'fanart'
    Key events:
        - fanart.movie: movie art fetched (count per Kodi art key)
        - fanart.show: show and season art fetched (count per Kodi art key)
    Failures from providers/http.py log as `fanart.movie.transient` etc.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from resources.lib.constants import FANART_BASE_URL
from resources.lib.engine.art import Poster
from resources.lib.providers.http import provider_get
from resources.lib.utils import (
    ApiKeyError,
    FanartAuthError,
    TransientProviderError,
    get_logger,
    log_timing,
)

log = get_logger('fanart')

# fanart.tv marks a textless image with language "00".
_TEXTLESS = ("00", "")

# Kodi art key -> fanart.tv types, best first. The second type of clearlogo
# and clearart is the SD one: a candidate only when the HD type has nothing
# in the same language step (Poster.sd).
_MOVIE_TYPES: Dict[str, Tuple[str, ...]] = {
    "poster": ("movieposter",),
    "fanart": ("moviebackground",),
    "clearlogo": ("hdmovielogo", "movielogo"),
    "clearart": ("hdmovieclearart", "movieart"),
    "landscape": ("moviethumb",),
    "banner": ("moviebanner",),
    "discart": ("moviedisc",),
}
_SHOW_TYPES: Dict[str, Tuple[str, ...]] = {
    "poster": ("tvposter",),
    "fanart": ("showbackground",),
    "clearlogo": ("hdtvlogo", "clearlogo"),
    "clearart": ("hdclearart", "clearart"),
    "landscape": ("tvthumb",),
    "banner": ("tvbanner",),
    "characterart": ("characterart",),
}


def _get(
    path: str, label: str, project_key: str, client_key: str, **context: Any,
) -> Optional[Dict[str, Any]]:
    params = {"api_key": project_key}
    if client_key:
        params["client_key"] = client_key
    with log_timing(log, label, **context):
        try:
            data = provider_get(
                "{}/{}".format(FANART_BASE_URL, path), logger=log, label=label,
                params=params, provider="fanart",
            )
        except ApiKeyError:
            raise FanartAuthError("fanart.tv rejected the API key") from None
    if data is not None and not isinstance(data, dict):
        raise TransientProviderError("fanart.tv answered with a non-object body")
    return data


def _poster(item: Dict[str, Any], sd: bool = False) -> Optional[Poster]:
    """One image from a fanart.tv item; None when it has no url or its
    ``likes`` (a string) is not a number. Missing or empty likes count as 0."""
    url = item.get("url")
    if not url:
        return None
    try:
        likes = int(item.get("likes") or 0)
    except (TypeError, ValueError):
        return None
    lang = item.get("lang")
    return Poster(
        url=url, provider="fanart",
        lang=None if lang in _TEXTLESS or lang is None else lang,
        score=(likes,), sd=sd,
    )


def _posters(items: Any, sd: bool = False) -> List[Poster]:
    parsed = (_poster(item, sd) for item in items or [])
    return [p for p in parsed if p is not None]


def _art(data: Dict[str, Any], types: Dict[str, Tuple[str, ...]]) -> Dict[str, List[Poster]]:
    """Every Kodi art key of ``types`` (an empty list when fanart.tv has
    none), HD types before SD ones."""
    return {
        key: [
            poster
            for rank, name in enumerate(names)
            for poster in _posters(data.get(name), sd=rank > 0)
        ]
        for key, names in types.items()
    }


def _counts(art: Dict[str, List[Poster]]) -> Dict[str, int]:
    return {"n_" + key: len(posters) for key, posters in art.items()}


def fetch_movie_art(
    tmdb_id: Optional[Union[int, str]], imdb_id: Optional[str],
    project_key: str, client_key: str,
) -> Optional[Dict[str, List[Poster]]]:
    """Movie art by Kodi art key (poster, fanart, clearlogo, clearart,
    landscape, banner, discart; empty lists where fanart.tv has none), TMDB id
    preferred over IMDb id. A collection is asked the same way with its TMDB
    collection id. None when there is no id to ask with or the lookup
    answered 404. Raises FanartAuthError on HTTP 401 and
    TransientProviderError when fanart.tv could not be reached."""
    movie_id = str(tmdb_id) if tmdb_id else (imdb_id or "")
    if not movie_id:
        return None
    data = _get(
        "movies/{}".format(movie_id), "fanart.movie", project_key, client_key,
        movie_id=movie_id,
    )
    if data is None:
        return None
    art = _art(data, _MOVIE_TYPES)
    log.info("Movie art fetched", event="fanart.movie", movie_id=movie_id, **_counts(art))
    return art


def fetch_show_art(
    tvdb_id: Union[int, str], project_key: str, client_key: str,
) -> Optional[Dict[str, Any]]:
    """Show art as {"show": {art key: [Poster]}, "seasons": {season:
    [Poster]}} (poster, fanart, clearlogo, clearart, landscape, banner,
    characterart; season-agnostic "all" posters are dropped), or None on 404.
    Raises FanartAuthError on HTTP 401 and TransientProviderError when
    fanart.tv could not be reached."""
    data = _get(
        "tv/{}".format(tvdb_id), "fanart.show", project_key, client_key,
        tvdb_id=tvdb_id,
    )
    if data is None:
        return None
    seasons: Dict[int, List[Poster]] = {}
    for item in data.get("seasonposter") or []:
        try:
            season = int(item.get("season"))
        except (TypeError, ValueError):
            continue
        poster = _poster(item)
        if poster is not None:
            seasons.setdefault(season, []).append(poster)
    show = _art(data, _SHOW_TYPES)
    log.info(
        "Show art fetched", event="fanart.show", tvdb_id=tvdb_id,
        seasons=len(seasons), **_counts(show),
    )
    return {"show": show, "seasons": seasons}
