"""Candidates for one art field during a scan: the episode thumb from TMDB
or TheTVDB, and every other art type (movie, show, season or movie set
poster, fanart, clear logo, key art and the fanart.tv-only types) picked
from TMDB's and fanart.tv's images.

Whether the slot may be touched at all is decided before any fetch
(art.art_gate in run_scan); this module only answers what the image should be.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

from typing import Any, Callable

from resources.lib.constants import FANART_API_KEY
from resources.lib.engine.art import (
    ENGLISH_SOURCE_SUFFIX,
    TEXTLESS_SOURCE_SUFFIX,
    Poster,
    is_placeholder_art,
    pick_art,
    season_tie_break,
)
from resources.lib.engine.chain import TRANSIENT, FieldOutcome
from resources.lib.engine.fetch import _Primary
from resources.lib.engine.ids import _Ids
from resources.lib.engine.scanctx import _call_provider, _ScanCtx
from resources.lib.engine.text import _TextSources
from resources.lib.providers import fanart
from resources.lib.providers.languages import tmdb_language

_TRANSIENT_OUTCOME = FieldOutcome(transient=True, value=None, from_fallback=False)
_ANSWERED_EMPTY = FieldOutcome(transient=False, value=None, from_fallback=False)

# The TMDB images list each art type both sites offer is picked from.
_TMDB_IMAGES = {
    "poster": "posters", "keyart": "posters", "fanart": "backdrops", "clearlogo": "logos",
}
# fanart.tv has no key art type: key art is a poster without text, as in
# Kodi's own fanart.tv mapping.
_FANART_KEYS = {"keyart": "poster"}


def image_language(kodi_lang: str) -> str:
    """The bare ISO 639-1 code TMDB and fanart.tv tag images with."""
    return tmdb_language(kodi_lang).split("-")[0]


def _fanart_answer(
    ctx: _ScanCtx, key: tuple[str, str], fetch: Callable[[], Any], identity: str,
) -> Any:
    """fanart.tv's answer through the per-scan cache, or TRANSIENT.

    A disabled fanart.tv, tripped or with its keys rejected, is not an
    answer: a poster whose pick needs it waits with its clock untouched,
    as text fields do while TheTVDB is out. A pick TMDB settles on its own
    never asks (art.pick_art is lazy).
    """
    if key in ctx.fanart_cache:
        return ctx.fanart_cache[key]
    if ctx.breaker.is_disabled("fanart"):
        return TRANSIENT
    answer = _call_provider("fanart", fetch, ctx, identity)
    if answer is not TRANSIENT:
        ctx.fanart_cache[key] = answer
    return answer


def _fanart_images(
    ctx: _ScanCtx, item: dict[str, Any], primary: _Primary, ids: _Ids, identity: str,
    field: str,
) -> Any:
    """The item's fanart.tv images for an art field ([] when it has none or
    no id to ask with), or TRANSIENT. One answer per item serves all its art
    types; a season's posters come from its show's answer, so one call
    covers the show and all its seasons."""
    key = _FANART_KEYS.get(field, field)
    if ctx.media_type.name == "set":
        # fanart.tv serves a collection's art on the movies endpoint, under
        # the collection's TMDB id.
        collection_id = primary.tmdb_id
        if not collection_id:
            return []
        answer = _fanart_answer(
            ctx, ("collection", str(collection_id)),
            lambda: fanart.fetch_movie_art(
                collection_id, None, FANART_API_KEY, ctx.fanart_client_key,
            ),
            identity,
        )
        return answer if answer is TRANSIENT else (answer or {}).get(key) or []
    if ctx.media_type.name == "movie":
        tmdb_id, imdb_id = primary.tmdb_id, primary.imdb_id
        if not (tmdb_id or imdb_id):
            return []
        answer = _fanart_answer(
            ctx, ("movie", str(tmdb_id or imdb_id)),
            lambda: fanart.fetch_movie_art(
                tmdb_id, imdb_id, FANART_API_KEY, ctx.fanart_client_key,
            ),
            identity,
        )
        return answer if answer is TRANSIENT else (answer or {}).get(key) or []
    if ids.tvdb_transient:
        return TRANSIENT
    tvdb_id = ids.tvdb
    if not tvdb_id:
        return []
    # The whole answer is cached: it carries the show's other art and its
    # season posters too.
    answer = _fanart_answer(
        ctx, ("tv", str(tvdb_id)),
        lambda: fanart.fetch_show_art(tvdb_id, FANART_API_KEY, ctx.fanart_client_key),
        identity,
    )
    if answer is TRANSIENT:
        return TRANSIENT
    answer = answer or {}
    if ctx.media_type.name == "season":
        season = int(item.get("season", 0) or 0)
        return (answer.get("seasons") or {}).get(season) or []
    return (answer.get("show") or {}).get(key) or []


def _resolve_thumb(
    primary: _Primary, sources: _TextSources, folder_lang: str,
) -> tuple[FieldOutcome, str | None]:
    """The TMDB still, else TheTVDB's episode image. Neither is a fallback:
    language does not apply to a still. A link that is itself a placeholder
    (TheTVDB's empty banner path) counts as no image, so it never replaces
    a frame grab."""
    if primary.tmdb is TRANSIENT:
        return _TRANSIENT_OUTCOME, None
    still = (primary.tmdb or {}).get("thumb") or ""
    if not is_placeholder_art(still):
        return FieldOutcome(transient=False, value=still, from_fallback=False), "tmdb"
    image = sources.tvdb("image", folder_lang)
    if image is TRANSIENT:
        return _TRANSIENT_OUTCOME, None
    if image and not is_placeholder_art(image):
        return FieldOutcome(transient=False, value=image, from_fallback=False), "tvdb"
    return _ANSWERED_EMPTY, None


def _season_tie_break(
    ctx: _ScanCtx, item: dict[str, Any], ids: _Ids,
) -> Callable[[Poster], int] | None:
    """The tie-break for a season's fanart.tv posters, or None for any other
    type. Its reference is every fanart.tv poster of the show's other library
    seasons. It is first used after the cached show answer was fetched, which
    is when the reference can be read."""
    if ctx.media_type.name != "season":
        return None
    season = int(item.get("season", 0) or 0)
    others = [n for n in item.get("show_seasons") or [] if n != season]
    cached: list[Callable[[Poster], int]] = []

    def tie_break(poster: Poster) -> int:
        if not cached:
            answer = ctx.fanart_cache.get(("tv", str(ids.tvdb))) or {}
            seasons = answer.get("seasons") or {}
            cached.append(season_tie_break([seasons.get(n, []) for n in others]))
        return cached[0](poster)
    return tie_break


def resolve_art(
    ctx: _ScanCtx,
    sources: _TextSources,
    primary: _Primary,
    ids: _Ids,
    identity: str,
    field: str,
    folder_lang: str,
    fallback_lang: str,
    current: str,
    english: bool,
) -> tuple[FieldOutcome, str | None]:
    """The field's outcome and the provider of its value (a textless
    pick's with art.TEXTLESS_SOURCE_SUFFIX, an English last-resort pick's
    with art.ENGLISH_SOURCE_SUFFIX).

    ``current`` is the art the pick compares with ("" when its local file
    no longer exists); ``english`` allows the English last resort.

    Every art type needs TMDB's answer, whatever the art source: TMDB's
    images are a candidate tier of the types both sites offer, so without
    them the pick could be wrong, and a movie's fanart.tv lookup may rest on
    the id TMDB settles. No candidate is an answer with no value, which keeps
    the current art.
    """
    if field == "thumb":
        return _resolve_thumb(primary, sources, folder_lang)
    if primary.tmdb is TRANSIENT:
        return _TRANSIENT_OUTCOME, None
    lang = image_language(folder_lang)
    fallback = image_language(fallback_lang) if fallback_lang.strip() else None
    images = _TMDB_IMAGES.get(field)
    pick = pick_art(
        field,
        ((primary.tmdb or {}).get(images) or []) if images else [],
        lambda: _fanart_images(ctx, sources.item, primary, ids, identity, field),
        ctx.art_source, lang, fallback, current, english,
        tie_break=_season_tie_break(ctx, sources.item, ids),
    )
    if pick is TRANSIENT:
        return _TRANSIENT_OUTCOME, None
    if pick is None:
        return _ANSWERED_EMPTY, None
    outcome = FieldOutcome(transient=False, value=pick.url, from_fallback=pick.from_fallback)
    if pick.textless:
        return outcome, pick.provider + TEXTLESS_SOURCE_SUFFIX
    if pick.english:
        return outcome, pick.provider + ENGLISH_SOURCE_SUFFIX
    return outcome, pick.provider
