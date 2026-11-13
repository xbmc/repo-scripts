"""Text and rating resolution for one item: the per-field provider chains
for title and plot, and the named-slot ratings.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from resources.lib.data.media_types import MediaType
from resources.lib.engine.chain import TRANSIENT, FieldOutcome, Step, run_chain
from resources.lib.engine.fetch import (
    _find_episode_by_tmdb_id,
    _Primary,
)
from resources.lib.engine.ids import (
    _Ids,
    _show_checked,
    _show_kodi_id,
    _tmdb_season,
    _tvdb_cached,
    _tvdb_lang,
)
from resources.lib.engine.resolve import (
    FOLLOW_SCRAPER,
    build_ratings,
    effective_rating_pref,
    rating_sources,
)
from resources.lib.engine.scanctx import (
    _EPISODEGUIDE_TAG,
    _TVDB_SERIES_KEYS,
    FALLBACK_TMDB_FIRST,
    TEXT_FOLLOW_SCRAPER,
    TEXT_TVDB_FIRST,
    _call_provider,
    _get_season_data,
    _ScanCtx,
)
from resources.lib.providers import imdb_ratings, tmdb, tvdb
from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import (
    TransientProviderError,
    get_logger,
)

log = get_logger('scan')


_UNFETCHED = object()


class _TextSources:
    """Lazy per-item lookups behind the title/plot chain steps.

    Each method returns the field's value, None (the provider answered and has
    nothing, or the item has no id for it) or ``TRANSIENT``. TMDB in the folder
    language reuses the primary fetch; the fallback-language TMDB record is
    fetched at most once per item, and TVDB records go through the per-scan
    cache so a show's episode list is fetched once per language.
    """

    def __init__(
        self,
        ctx: _ScanCtx,
        item: dict[str, Any],
        identity: str,
        primary: _Primary,
        ids: _Ids,
        fallback_lang: str,
    ) -> None:
        self._ctx = ctx
        self._item = item
        self._identity = identity
        self._primary = primary
        self._ids = ids
        self._fallback_lang = fallback_lang
        self._tmdb_fallback: Any = _UNFETCHED

    @property
    def item(self) -> dict[str, Any]:
        return self._item

    def tmdb(self, field: str, fallback: bool) -> Any:
        if fallback:
            if self._tmdb_fallback is _UNFETCHED:
                self._tmdb_fallback = self._fetch_tmdb_fallback()
            data = self._tmdb_fallback
        else:
            data = self._primary.tmdb
        if data is TRANSIENT:
            return TRANSIENT
        return data.get(field) if data else None

    def _fetch_tmdb_fallback(self) -> Any:
        ctx = self._ctx
        p = self._primary
        lang = tmdb_language(self._fallback_lang)
        if p.tmdb is TRANSIENT:
            return TRANSIENT
        tmdb_id = p.tmdb_id
        if not tmdb_id:
            return None
        if ctx.media_type.name == "episode" and not p.show_tmdb_id:
            return None if _show_checked(ctx, self._item) else TRANSIENT
        if ctx.breaker.is_disabled("tmdb"):
            return TRANSIENT
        if ctx.media_type.name != "episode":
            fetch = tmdb.fetch_movie if ctx.media_type.name == "movie" else tmdb.fetch_tvshow
            return _call_provider(
                "tmdb",
                lambda: fetch(tmdb_id, ctx.tmdb_api_key, lang),
                ctx, self._identity,
            )
        season_number = _tmdb_season(self._item, self._ids)
        show_id = p.show_tmdb_id or ""
        cache_key = "{}:{}:{}".format(show_id, season_number, lang)
        if cache_key in ctx.season_cache:
            season: Any = ctx.season_cache[cache_key]
        else:
            season = _call_provider(
                "tmdb",
                lambda: _get_season_data(
                    show_id, season_number, ctx.tmdb_api_key, lang, ctx.season_cache,
                ),
                ctx, self._identity,
            )
        if season is TRANSIENT or season is None:
            return season
        return _find_episode_by_tmdb_id(season, tmdb_id)

    def tvdb(self, field: str, kodi_lang: str) -> Any:
        ctx = self._ctx
        lang = _tvdb_lang(ctx, kodi_lang)
        if lang is None:
            return None
        if self._ids.tvdb_transient:
            return TRANSIENT
        tvdb_id = self._ids.tvdb
        if not tvdb_id:
            return None
        if ctx.media_type.name == "tvshow":
            series = _tvdb_cached(
                ctx, "series", tvdb_id, lang, tvdb.fetch_series, self._identity,
            )
            if series is TRANSIENT or series is None:
                return series
            return series.get(_TVDB_SERIES_KEYS[field])
        if ctx.media_type.name == "episode":
            show_tvdb_id = ctx.show_tvdb_map.get(_show_kodi_id(self._item))
            if not show_tvdb_id:
                return None if _show_checked(ctx, self._item) else TRANSIENT
            episodes = _tvdb_cached(
                ctx, "episodes", show_tvdb_id, lang, tvdb.fetch_series_episodes,
                self._identity,
            )
            if episodes is TRANSIENT or episodes is None:
                return episodes
            episode = episodes.get(str(tvdb_id))
            return episode.get(field) if episode else None
        return None


def _scraper_provider(item: dict[str, Any], media_type: MediaType) -> str | None:
    """"tmdb" or "tvdb": the provider whose Kodi scraper made the item, or None
    when nothing tells.

    Kodi's JSON-RPC does not say which uniqueid is the default, so the
    scraper's traces decide. A show's episodeguide is a JSON object of the
    ids its scraper knows, the scraper's own first ({"tvdb": ..., "tmdb": ...}
    from TheTVDB's, {"tmdb": ..., "tvdb": ...} from TMDB's); failing that,
    the scraper marks its own rating slot default. An episode carries the ids its scraper set: the TMDB
    scraper always sets "tmdb", TheTVDB's never does.
    """
    if media_type.name == "episode":
        uid = item.get("uniqueid") or {}
        if uid.get("tmdb"):
            return "tmdb"
        return "tvdb" if uid.get("tvdb") else None
    guide = _EPISODEGUIDE_TAG.sub("", str(item.get("episodeguide") or "")).strip()
    try:
        guide_ids = json.loads(guide) if guide else {}
    except ValueError:
        guide_ids = {}
    if isinstance(guide_ids, dict):
        # Both scrapers list every id they know; their own comes first.
        for key, value in guide_ids.items():
            if key in ("tmdb", "tvdb") and value:
                return key
    for slot, entry in (item.get("ratings") or {}).items():
        if isinstance(entry, dict) and entry.get("default"):
            if slot in ("tmdb", "themoviedb"):
                return "tmdb"
            if slot == "tvdb":
                return "tvdb"
    return None


def _fallback_applies(fallback_lang: str, folder_lang: str) -> bool:
    """The fallback steps run only when the folder has a fallback language and
    it is not the folder's own language."""
    fallback = fallback_lang.strip()
    return bool(fallback) and tmdb_language(fallback) != tmdb_language(folder_lang)


def _text_chain(
    ctx: _ScanCtx,
    sources: _TextSources,
    field: str,
    folder_lang: str,
    fallback_lang: str,
    current: Any,
) -> tuple[FieldOutcome, str | None]:
    """Run the title/plot chain. Returns the outcome and the provider whose
    step produced the value (None when there is no value).

    Shows and episodes ask TMDB and TVDB in the folder language in the
    text_source_order, then (when the folder has a fallback language that
    differs) both in the fallback language in the fallback_order. Movies ask TMDB only.
    """
    def tmdb_step(fallback: bool) -> tuple[str, Callable[[], Any], bool]:
        return ("tmdb", lambda: sources.tmdb(field, fallback), fallback)

    def tvdb_step(lang: str, fallback: bool) -> tuple[str, Callable[[], Any], bool]:
        return ("tvdb", lambda: sources.tvdb(field, lang), fallback)

    movie = ctx.media_type.name == "movie"
    if movie:
        specs = [tmdb_step(False)]
    elif ctx.text_order == TEXT_TVDB_FIRST or (
            ctx.text_order == TEXT_FOLLOW_SCRAPER
            and _scraper_provider(sources.item, ctx.media_type) == "tvdb"):
        specs = [tvdb_step(folder_lang, False), tmdb_step(False)]
    else:
        specs = [tmdb_step(False), tvdb_step(folder_lang, False)]

    # A show or movie title in another language would be worse than the one
    # the scraper gave it, so main titles have no fallback steps.
    main_title = field == "title" and ctx.media_type.name != "episode"
    if not main_title and _fallback_applies(fallback_lang, folder_lang):
        if movie:
            specs.append(tmdb_step(True))
        elif ctx.fallback_order == FALLBACK_TMDB_FIRST:
            specs += [tmdb_step(True), tvdb_step(fallback_lang, True)]
        else:
            specs += [tvdb_step(fallback_lang, True), tmdb_step(True)]

    heard: list[str] = []

    def step(provider: str, fetch: Callable[[], Any], fallback: bool) -> Step:
        def run() -> Any:
            heard.append(provider)
            return fetch()
        return Step(fetch=run, fallback=fallback)

    outcome = run_chain([step(*spec) for spec in specs], current)
    return outcome, (heard[-1] if outcome.value is not None else None)


def _imdb_rating(ctx: _ScanCtx, primary: _Primary, identity: str) -> Any:
    """The item's IMDb (rating, votes), None when IMDb has none, or TRANSIENT
    when the store is not ready, the IMDb id could not be settled, or the
    lookup failed."""
    if not ctx.imdb_ready or primary.imdb_id_transient:
        return TRANSIENT
    if not primary.imdb_id:
        return None
    try:
        return imdb_ratings.lookup(primary.imdb_id)
    except TransientProviderError:
        return TRANSIENT
    except Exception:
        event = "scan.imdb_lookup_failed"
        if event in ctx.logged_once:
            log.debug("IMDb rating lookup failed again", event=event, identity=identity)
        else:
            ctx.logged_once.add(event)
            log.exception("IMDb rating lookup failed", event=event, identity=identity)
        return TRANSIENT


def _resolve_ratings(
    ctx: _ScanCtx,
    item: dict[str, Any],
    primary: _Primary,
    identity: str,
    nfo_managed: bool,
    owned_slots: dict[str, str],
) -> tuple[bool, dict[str, Any] | None, str | None, int | None, dict[str, str]]:
    """Ratings verdict and map. Returns (transient, new_ratings_map,
    default_source, default_votes, slot_fingerprints of the slots written).

    Transient when a source rating_source consults did not answer for this
    item; a source it does not consult cannot hold the rating back.
    """
    current = item.get("ratings") or {}
    pref = effective_rating_pref(ctx.rating_pref, current)
    use_tmdb, use_imdb = rating_sources(pref)
    imdb = _imdb_rating(ctx, primary, identity) if use_imdb else None
    if (use_tmdb and primary.tmdb is TRANSIENT) or imdb is TRANSIENT:
        return True, None, None, None, {}
    tmdb_data = primary.tmdb if primary.tmdb is not TRANSIENT else None
    new_ratings, source, votes, slot_fps = build_ratings(
        tmdb_data or {}, imdb, current, pref, nfo_managed=nfo_managed,
        owned_slots=owned_slots, keep_default_mark=ctx.rating_pref == FOLLOW_SCRAPER,
    )
    return False, new_ratings, source, votes, slot_fps
