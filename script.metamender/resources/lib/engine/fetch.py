"""Fetching an item's primary TMDB record (movie, show or episode) during a
scan, including the episode paths through TVDB ids.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resources.lib.constants import (
    PROVIDER_CIRCUIT_BREAKER_THRESHOLD,
)
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
        tmdb_data = _call_provider(
            "tmdb",
            lambda: fetch(tmdb_id, ctx.tmdb_api_key, language),
            ctx, identity,
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
