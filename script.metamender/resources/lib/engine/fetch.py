"""Fetching an item's primary TMDB record (movie, show, season, episode or
movie set) during a scan, including the episode paths through TVDB ids.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from resources.lib.constants import (
    PROVIDER_CIRCUIT_BREAKER_THRESHOLD,
)
from resources.lib.data.setfolder import folder_for
from resources.lib.engine.art import drop_show_copies
from resources.lib.engine.chain import TRANSIENT
from resources.lib.engine.ids import (
    _enrich_imdb_id,
    _Ids,
    _show_checked,
    _show_kodi_id,
    _tmdb_season,
)
from resources.lib.engine.scanctx import (
    _call_provider,
    _get_season_data,
    _ScanCtx,
)
from resources.lib.engine.sets import collection_text, pick_set_name
from resources.lib.providers import tmdb
from resources.lib.utils import (
    TransientProviderError,
    get_logger,
)

log = get_logger('scan')


def _find_episode_by_tmdb_id(
    season_data: list[dict[str, Any]],
    tmdb_episode_id: str,
) -> dict[str, Any] | None:
    """Find an episode by TMDB episode ID in a season's episode list."""
    for ep in season_data:
        if ep.get("tmdb_id") == tmdb_episode_id:
            return ep
    return None


@dataclass(frozen=True)
class _Primary:
    """The item's folder-language TMDB answer and what it settled about IDs."""

    # TMDB record, None (TMDB answered "nothing", or no TMDB id), or TRANSIENT.
    tmdb: Any
    # Movie/show TMDB id or the episode's own TMDB id.
    tmdb_id: str | None
    # The episode's show TMDB id; None for movies and shows.
    show_tmdb_id: str | None
    imdb_id: str | None
    # The IMDb id is missing and the lookup that could have found it did not
    # answer, so an IMDb rating cannot be known this scan.
    imdb_id_transient: bool


def _fetch_movie_or_show(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    language: str,
) -> _Primary:
    """Fetch movie/TV show data from TMDB and write back an IMDb id TMDB
    reports.

    A TMDB call this item needs but cannot make or complete (breaker open, or
    the id lookup failed transiently) yields ``TRANSIENT``, never None: None
    means TMDB answered "nothing", which would advance the maturity clock.
    """
    tmdb_data: Any = None
    tmdb_id = ids.tmdb
    imdb_id = ids.imdb

    if ids.tmdb_transient or (tmdb_id and ctx.breaker.is_disabled("tmdb")):
        tmdb_data = TRANSIENT
    elif tmdb_id:
        fetch = tmdb.fetch_movie if ctx.media_type.name == "movie" else tmdb.fetch_tvshow
        # Poster candidates ride along on the same request, only when asked.
        images = {"image_languages": ctx.image_languages} if ctx.image_languages else {}
        tmdb_data = _call_provider(
            "tmdb",
            lambda: fetch(tmdb_id, ctx.tmdb_api_key, language, **images),
            ctx, identity,
        )

    if ctx.media_type.name == "tvshow" and tmdb_id and tmdb_data is not TRANSIENT:
        # The season pass reads its air dates from this record.
        ctx.show_cache[str(tmdb_id)] = tmdb_data

    if (ctx.media_type.name == "movie" and tmdb_id and isinstance(tmdb_data, dict)
            and "collection_id" in tmdb_data):
        # Every /movie answer says which collection the movie is in, so the
        # set pass need not ask TMDB for it again.
        ctx.tracker.set_movie_collection(
            str(tmdb_id), str(tmdb_data.get("collection_id") or ""), date.today().isoformat(),
        )

    if (not imdb_id and tmdb_data is not TRANSIENT and tmdb_data
            and tmdb_data.get("imdb_id")):
        imdb_id = tmdb_data["imdb_id"]
        _enrich_imdb_id(ctx, item, kodi_id, title, identity, imdb_id)

    return _Primary(
        tmdb=tmdb_data,
        tmdb_id=tmdb_id,
        show_tmdb_id=None,
        imdb_id=imdb_id,
        imdb_id_transient=not imdb_id and tmdb_data is TRANSIENT,
    )


def _episode_cross_ids(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    ep_show_tmdb_id: str,
    season_number: int,
    episode_number: int,
) -> bool:
    """Fill the episode's missing IMDb and TVDB ids from TMDB's episode
    external ids. Returns True when the IMDb id stays unknown because the
    lookup did not answer.

    Best effort: a failure does not count against the TMDB breaker. A found
    IMDb id is written back to Kodi (_enrich_imdb_id), except for a
    number-matched episode; a TVDB id goes to the tracker only.
    """
    found = _call_provider(
        "tmdb",
        lambda: tmdb.fetch_episode_external_ids(
            ep_show_tmdb_id, season_number, episode_number, ctx.tmdb_api_key,
        ),
        ctx, identity, best_effort=True,
    )
    if found is TRANSIENT:
        ids.lookup_failed = True
        if not ids.tvdb:
            ids.tvdb_transient = True
        return not ids.imdb
    ids.looked_up = True
    found = found or {}
    if not ids.imdb and found.get("imdb_id"):
        ids.imdb = found["imdb_id"]
        if ids.number_matched:
            # A number match is metamender's own inference, so the id it
            # leads to stays in the tracker and never reaches Kodi.
            ctx.tracker.upsert_item(ctx.media_type.name, identity, imdb_id=ids.imdb)
        else:
            _enrich_imdb_id(ctx, item, kodi_id, title, identity, ids.imdb)
    if not ids.tvdb and found.get("tvdb_id"):
        ids.tvdb = found["tvdb_id"]
        ctx.tracker.upsert_item(ctx.media_type.name, identity, tvdb_id=ids.tvdb)
    return False


def _fetch_episode_tmdb(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    ep_show_tmdb_id: str,
    season_number: int,
    language: str,
) -> tuple[Any, bool]:
    """TMDB episode path: look up the season (cached), match by episode ID,
    and fill missing IMDb/TVDB ids. Returns (tmdb_episode_data,
    imdb_id_transient).

    The (cached) season fetch is not preceded by a pacing sleep and only arms
    the pacer on a cache miss; breaker success is recorded once at the end;
    ApiKeyError propagates and a transient failure trips the breaker.
    """
    tmdb_data: Any = None
    imdb_id_transient = False
    try:
        cache_key = "{}:{}:{}".format(ep_show_tmdb_id, season_number, language)
        is_cache_miss = cache_key not in ctx.season_cache
        season_data = _get_season_data(
            ep_show_tmdb_id, season_number, ctx.tmdb_api_key, language, ctx.season_cache
        )
        if season_data is not None:
            tmdb_data = _find_episode_by_tmdb_id(season_data, ids.tmdb or "")
            if (tmdb_data is not None and ids.may_look_up
                    and not (ids.imdb and ids.tvdb)):
                imdb_id_transient = _episode_cross_ids(
                    ctx, item, kodi_id, title, identity, ids,
                    ep_show_tmdb_id, season_number,
                    tmdb_data.get("episode_number", 0),
                )
        if is_cache_miss:
            ctx.pacer.arm()
        ctx.breaker.record_success("tmdb")
    except TransientProviderError:
        tmdb_data = TRANSIENT
        if ctx.breaker.record_failure("tmdb"):
            log.warning(
                "Provider disabled for this cycle after repeated failures",
                event="scan.breaker", provider="tmdb",
                threshold=PROVIDER_CIRCUIT_BREAKER_THRESHOLD, identity=identity,
            )
    return tmdb_data, imdb_id_transient


def _fetch_episode(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    language: str,
) -> _Primary:
    """Fetch the episode's TMDB record by its TMDB id via the show's season.

    As in _fetch_movie_or_show, a needed TMDB call that cannot be made (breaker
    open, show not resolved yet) yields ``TRANSIENT`` rather than None. A show
    whose lookups answered that TMDB does not have it yields None.
    """
    tmdb_data: Any = None
    imdb_id_transient = False
    tmdb_id = ids.tmdb
    ep_show_tmdb_id = ctx.show_id_map.get(_show_kodi_id(item))

    if ids.tmdb_transient or (tmdb_id and ctx.breaker.is_disabled("tmdb")):
        tmdb_data = TRANSIENT
    elif tmdb_id and not ep_show_tmdb_id:
        if not _show_checked(ctx, item):
            # Not knowing the show is not an answer from TMDB: hold the clock.
            log.debug(
                "No show TMDB ID for episode, TMDB path transient",
                event="scan.transient", reason="show_unresolved",
                title=title, tvshowid=item.get("tvshowid"),
            )
            tmdb_data = TRANSIENT
    elif tmdb_id and ep_show_tmdb_id:
        tmdb_data, imdb_id_transient = _fetch_episode_tmdb(
            ctx, item, kodi_id, title, identity, ids,
            ep_show_tmdb_id, _tmdb_season(item, ids), language,
        )

    if (tmdb_data is TRANSIENT and ids.may_look_up and tmdb_id
            and not (ids.imdb and ids.tvdb)):
        # The episode external ids lookup needs the TMDB record, so it did
        # not run. A missing TVDB id can only come from there.
        ids.defer()
        if not ids.tvdb:
            ids.tvdb_transient = True

    return _Primary(
        tmdb=tmdb_data,
        tmdb_id=tmdb_id,
        show_tmdb_id=ep_show_tmdb_id,
        imdb_id=ids.imdb,
        imdb_id_transient=imdb_id_transient or (not ids.imdb and tmdb_data is TRANSIENT),
    )


def _show_record(ctx: _ScanCtx, show_tmdb_id: str, language: str, identity: str) -> Any:
    """The show's TMDB record (None when TMDB has no such show), fetched once
    per show in the cycle (the show pass may already have it), or
    TRANSIENT. The record carries the show's posters (the season pass drops
    season posters that are the same file); a cached one without them, from a
    show pass that did not ask for images, is fetched again and replaced."""
    cached = ctx.show_cache.get(show_tmdb_id)
    if show_tmdb_id in ctx.show_cache and (
        cached is None or "posters" in cached or not ctx.image_languages
    ):
        return cached
    images = {"image_languages": ctx.image_languages} if ctx.image_languages else {}
    record = _call_provider(
        "tmdb",
        lambda: tmdb.fetch_tvshow(show_tmdb_id, ctx.tmdb_api_key, language, **images),
        ctx, identity,
    )
    if record is not TRANSIENT:
        ctx.show_cache[show_tmdb_id] = record
    return record


def _fetch_season(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    language: str,
) -> _Primary:
    """Fetch a season's poster candidates and its TMDB air date.

    The record is {"posters": [...]}: no posters when TMDB has no such season.
    Posters that are the same file as one of the show's own are left out.
    The season's air date, from its show's record, becomes the item's
    ``firstaired`` and the tracker row's ``premiered``, so the content age of
    this and later scans has it; a season TMDB gives no date keeps an unknown
    age. Either call failing makes the record TRANSIENT.
    """
    show_tmdb_id = ids.tmdb or ""
    season = int(item.get("season", 0) or 0)
    tmdb_data: Any = None
    if ctx.breaker.is_disabled("tmdb"):
        tmdb_data = TRANSIENT
    else:
        show = _show_record(ctx, show_tmdb_id, language, identity)
        if show is TRANSIENT:
            tmdb_data = TRANSIENT
        elif show is not None:
            posters = _call_provider(
                "tmdb",
                lambda: tmdb.fetch_season_posters(
                    show_tmdb_id, season, ctx.tmdb_api_key, ctx.image_languages,
                ),
                ctx, identity,
            )
            tmdb_data = TRANSIENT if posters is TRANSIENT else {
                "posters": drop_show_copies(posters or [], show.get("posters") or []),
            }
            air_date = (show.get("season_air_dates") or {}).get(season)
            if air_date:
                item[ctx.media_type.date_field] = air_date
                ctx.tracker.upsert_item(ctx.media_type.name, identity, premiered=air_date)
    return _Primary(
        tmdb=tmdb_data,
        tmdb_id=show_tmdb_id,
        show_tmdb_id=show_tmdb_id,
        imdb_id=None,
        imdb_id_transient=False,
    )


def _fetch_set(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    ids: _Ids,
    language: str,
    fallback_lang: str = "",
) -> _Primary:
    """Fetch a movie set's TMDB collection: its name and plot in every
    language and its images, from one request.

    The record's "title" is the name pick_set_name chooses (library
    language, fallback, English; "title_from_fallback" when not the first)
    and "plot" the library language's; the set pass's fallback plot step
    reads "plots" rather than asking again. Every name TMDB knows is kept
    as a known name of the collection, so a set Kodi makes under one of
    them later is recognised as a duplicate. A disabled or failing TMDB
    makes the record TRANSIENT."""
    collection_id = ids.tmdb or ""
    data: Any = None
    if ctx.breaker.is_disabled("tmdb"):
        data = TRANSIENT
    elif collection_id:
        answer = _call_provider(
            "tmdb",
            lambda: tmdb.fetch_collection(
                collection_id, ctx.tmdb_api_key, ctx.image_languages,
            ),
            ctx, identity,
        )
        if answer is TRANSIENT or answer is None:
            data = answer
        else:
            names = answer.get("names") or {}
            plots = answer.get("plots") or {}
            name, from_fallback = pick_set_name(names, language, fallback_lang or None)
            if name and ctx.set_folder:
                # Kodi's set art picker and Export library look for the
                # set's folder by its name, so a name that has one wins.
                others = [n for n in dict.fromkeys(names.values()) if n and n != name]
                name = folder_for(ctx.set_folder, [name] + others) or name
            data = {
                "title": name,
                "title_from_fallback": from_fallback,
                "plot": collection_text(plots, language),
                "names": names,
                "plots": plots,
                "posters": answer.get("posters") or [],
                "backdrops": answer.get("backdrops") or [],
            }
            ctx.tracker.add_set_names(identity, names.values())
    return _Primary(
        tmdb=data,
        tmdb_id=collection_id or None,
        show_tmdb_id=None,
        imdb_id=None,
        imdb_id_transient=False,
    )
