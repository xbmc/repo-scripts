"""Resolving and verifying an item's TMDB, TVDB and IMDb ids during a scan.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from resources.lib.constants import (
    FALLBACK_RECHECK_DAYS,
)
from resources.lib.data import kodi
from resources.lib.data.media_types import EPISODE
from resources.lib.engine.chain import TRANSIENT
from resources.lib.engine.idverify import show_mismatch
from resources.lib.engine.scanctx import (
    _call_provider,
    _ScanCtx,
    extract_ids,
)
from resources.lib.providers import tmdb, tvdb
from resources.lib.providers.languages import tvdb_language
from resources.lib.utils import (
    KodiQueryError,
    get_logger,
)

log = get_logger('scan')


def _enrich_imdb_id(
    ctx: _ScanCtx,
    item: dict[str, Any],
    kodi_id: Any,
    title: str,
    identity: str,
    new_imdb: str,
) -> None:
    """Write a discovered IMDB ID back to Kodi and the tracker. The item's
    own uniqueid is left as Kodi listed it: the scan computed its tracker
    identity from it, and the next scan adopts the new identity
    (_tracker_identity)."""
    uid = dict(item.get("uniqueid") or {})
    uid["imdb"] = new_imdb
    kodi.update_item(kodi_id, ctx.media_type, title, uniqueid=uid)
    ctx.tracker.upsert_item(ctx.media_type.name, identity, imdb_id=new_imdb)
    log.info(
        "Enriched IMDB ID from TMDB",
        event="scan.enrich_id", title=title, imdb_id=new_imdb,
    )


class _Ids:
    """An item's external ids for this scan: Kodi's, those the tracker kept
    from earlier scans, and those the lookups below add.

    A ``*_transient`` flag means the id is missing and a lookup that could
    have found it did not answer, so every field that depends on it is
    transient. A missing id without the flag is an answer: the provider has
    no such item.
    """

    def __init__(
        self,
        tmdb: str | None,
        imdb: str | None,
        tvdb: str | None,
        may_look_up: bool,
        tmdb_season: int | None = None,
    ) -> None:
        self.tmdb = tmdb
        self.imdb = imdb
        self.tvdb = tvdb
        # Episode only: the TMDB season /find placed the episode in, when its
        # TMDB id came from /find. None means Kodi's season number applies.
        self.tmdb_season = tmdb_season
        self.tmdb_transient = False
        self.tvdb_transient = False
        # Cross-reference lookups (and unknown-id verification) may run for
        # this item now; see _lookup_allowed.
        self.may_look_up = may_look_up
        # A lookup ran and answered / a lookup ran and did not answer.
        self.looked_up = False
        self.lookup_failed = False
        # The TMDB/TVDB ids came from matching the episode by its number
        # (engine/numbermatch.py), not from Kodi.
        self.number_matched = False

    def defer(self) -> None:
        """A lookup this item needs could not run yet (its show is not
        resolved): like a failed lookup, it must not close the gate."""
        self.lookup_failed = True

    def any(self) -> bool:
        return bool(self.tmdb or self.imdb or self.tvdb)


def _lookup_allowed(
    checked: str | None, today: str, due: bool, is_show: bool, reset: bool = False,
) -> bool:
    """Whether an item's id lookups may run this scan.

    Lookups serve due fields, so they run only when a field is due, and an
    answer that left an id missing is asked again only after
    FALLBACK_RECHECK_DAYS. A show that has never been looked up is resolved
    even when none of its own fields is due: its episodes depend on its ids,
    and they can only tell "the show is not on TMDB" from "not resolved yet"
    once the show's lookups have answered. Update now (``reset``) always
    asks: the user wants the item refreshed now, and a provider may have
    added the item since the last answer.
    """
    if reset:
        return True
    if not checked:
        return due or is_show
    if not due:
        return False
    try:
        age = (date.fromisoformat(today) - date.fromisoformat(checked)).days
    except ValueError:
        return True
    return age >= FALLBACK_RECHECK_DAYS


def _show_kodi_id(item: dict[str, Any]) -> int:
    """The episode's show Kodi id, the key of the per-show maps."""
    value = item.get("tvshowid")
    return value if isinstance(value, int) else -1


def _tmdb_season(item: dict[str, Any], ids: _Ids) -> int:
    """Season number to fetch the episode's TMDB record through."""
    if ids.tmdb_season is not None:
        return ids.tmdb_season
    return int(item.get("season", 0) or 0)


def _premiered_year(item: dict[str, Any]) -> int | None:
    raw = str(item.get("premiered") or "")[:4]
    return int(raw) if len(raw) == 4 and raw.isdigit() else None


def _show_checked(ctx: _ScanCtx, item: dict[str, Any]) -> bool:
    """True when the episode's show has answered its id lookups, so a show id
    it lacks is an answer rather than not known yet."""
    return _show_kodi_id(item) in ctx.checked_shows


def _lookup(provider: str, fn: Any, ctx: _ScanCtx, identity: str) -> Any:
    """_call_provider, or ``TRANSIENT`` without a call while the provider's
    breaker is open."""
    if ctx.breaker.is_disabled(provider):
        return TRANSIENT
    return _call_provider(provider, fn, ctx, identity)


def _tvdb_cached(
    ctx: _ScanCtx,
    kind: str,
    tvdb_id: str,
    lang: str,
    fetch: Callable[[str, str], Any],
    identity: str,
) -> Any:
    """A TVDB record through the per-scan cache. Only real answers are cached,
    so a transient failure is retried by the next item."""
    key = (kind, tvdb_id, lang)
    if key in ctx.tvdb_cache:
        return ctx.tvdb_cache[key]
    result = _lookup("tvdb", lambda: fetch(tvdb_id, lang), ctx, identity)
    if result is not TRANSIENT:
        ctx.tvdb_cache[key] = result
    return result


def _tvdb_lang(ctx: _ScanCtx, kodi_lang: str) -> str | None:
    """TVDB language id for a Kodi language code, or None when TVDB has none.

    TVDB then has nothing for that language, which is an answer, so a code
    that maps to nothing (a typo such as "dutch" in sources.json) would
    silently turn TVDB off for the folder. It is logged once per code per
    scan.
    """
    lang = tvdb_language(kodi_lang)
    key = "scan.language_unmapped:" + kodi_lang
    if lang is None and kodi_lang.strip() and key not in ctx.logged_once:
        ctx.logged_once.add(key)
        log.warning(
            "Language code has no TheTVDB language, TVDB is not asked for it",
            event="scan.language_unmapped", language=kodi_lang,
            media_type=ctx.media_type.name,
        )
    return lang


def _verification_lang(ctx: _ScanCtx, folder_lang: str) -> str:
    """TVDB language for the verification fetch: the folder language, so the
    record is the one the text chain asks for anyway, else English."""
    return _tvdb_lang(ctx, folder_lang) or "eng"


def _unknown_verdict(
    ctx: _ScanCtx, ids: _Ids, identity: str, unknown_id: str,
    accepted: Any, reason: str,
) -> None:
    """Apply a verification result (True, False or TRANSIENT) to ``ids``;
    ``reason`` says why it was accepted or rejected."""
    if accepted is TRANSIENT:
        ids.tvdb_transient = True
        ids.lookup_failed = True
        return
    ids.looked_up = True
    if accepted:
        ids.tvdb = unknown_id
        ctx.tracker.upsert_item(ctx.media_type.name, identity, tvdb_id=unknown_id)
        ctx.counts["unknown_ids_accepted"] += 1
        log.debug(
            "Unknown-type id verified as TVDB id",
            event="scan.unknown_id_accepted", identity=identity,
            media_type=ctx.media_type.name, tvdb_id=unknown_id, reason=reason,
        )
    else:
        log.info(
            "Unknown-type id rejected, not used as TVDB id",
            event="scan.unknown_id_rejected", identity=identity,
            media_type=ctx.media_type.name, unknown_id=unknown_id, reason=reason,
        )


# A show id whose names or year do not match the Kodi show is accepted when at
# least this many of the show's untyped episode ids, and a majority of them,
# are in that TVDB series' episode list. TVDB episode ids are unique across
# series, so a remake or namesake cannot confirm itself this way, and one
# stray or mistyped episode id cannot carry a show.
_MIN_CONFIRMING_EPISODES = 2


def _verify_unknown_show(
    ctx: _ScanCtx, item: dict[str, Any], identity: str, ids: _Ids,
    unknown_id: str, folder_lang: str,
) -> None:
    """Accept the show's unknown id when the TVDB series it names carries the
    Kodi title among its names, translations or aliases and the years agree,
    or else when the show's own episode ids confirm it (_confirmed_by_episodes):
    a title can differ from every name TVDB knows ("Alfred Jodocus Kwak" for
    "Alfred J. Kwak"), while the episode ids are TVDB's own."""
    series = _tvdb_cached(
        ctx, "series", unknown_id, _verification_lang(ctx, folder_lang),
        tvdb.fetch_series, identity,
    )
    if series is TRANSIENT:
        _unknown_verdict(ctx, ids, identity, unknown_id, TRANSIENT, "")
        return
    if series is None:
        _unknown_verdict(ctx, ids, identity, unknown_id, False, "no_such_series")
        return
    reason = show_mismatch(
        item.get("title", ""), series.get("names") or [],
        kodi_year=_premiered_year(item), candidate_year=series.get("year"),
    )
    if reason is None:
        _unknown_verdict(ctx, ids, identity, unknown_id, True, "name_match")
        return
    confirmed = _confirmed_by_episodes(ctx, item, identity, unknown_id, folder_lang)
    if confirmed is TRANSIENT:
        _unknown_verdict(ctx, ids, identity, unknown_id, TRANSIENT, "")
        return
    if confirmed:
        _unknown_verdict(ctx, ids, identity, unknown_id, True, "accepted_by_episodes")
        return
    _unknown_verdict(ctx, ids, identity, unknown_id, False, reason)


def _confirmed_by_episodes(
    ctx: _ScanCtx, item: dict[str, Any], identity: str, unknown_id: str,
    folder_lang: str,
) -> Any:
    """Whether the show's untyped episode ids confirm ``unknown_id`` as its
    TVDB series (see _MIN_CONFIRMING_EPISODES): True, False, or TRANSIENT
    when Kodi's episode list or TVDB's could not be read.

    The show pass runs before the episode pass, so the episodes come from
    Kodi here, for this show only.
    """
    try:
        episodes = kodi.get_all_items(EPISODE, tvshowid=item.get("tvshowid"))
    except KodiQueryError:
        # kodi.get_all_items logged it; the next scan asks again.
        return TRANSIENT
    candidates = {extract_ids(ep)[3] for ep in episodes}
    candidates.discard(None)
    if not candidates:
        return False
    listed = _tvdb_cached(
        ctx, "episodes", unknown_id, _verification_lang(ctx, folder_lang),
        tvdb.fetch_series_episodes, identity,
    )
    if listed is TRANSIENT:
        return TRANSIENT
    confirming = len(candidates & set(listed or {}))
    log.debug(
        "Show episode ids checked against the TVDB series",
        event="scan.unknown_id_episodes", identity=identity, tvdb_id=unknown_id,
        checked=len(candidates), confirming=confirming,
    )
    return confirming >= _MIN_CONFIRMING_EPISODES and confirming * 2 > len(candidates)


def _verify_unknown_episode(
    ctx: _ScanCtx, item: dict[str, Any], identity: str, ids: _Ids,
    unknown_id: str, folder_lang: str,
) -> None:
    """Accept the episode's unknown id when it is in the show's TVDB episode
    list (one cached fetch per show, no per-episode call)."""
    show_tvdb_id = ctx.show_tvdb_map.get(_show_kodi_id(item))
    if not show_tvdb_id:
        if not _show_checked(ctx, item):
            ids.tvdb_transient = True
            ids.defer()
        # The show has no TVDB id, so no episode list can confirm this one.
        # Derived without a call, so it is not recorded as a lookup.
        return
    episodes = _tvdb_cached(
        ctx, "episodes", show_tvdb_id, _verification_lang(ctx, folder_lang),
        tvdb.fetch_series_episodes, identity,
    )
    if episodes is TRANSIENT:
        _unknown_verdict(ctx, ids, identity, unknown_id, TRANSIENT, "")
        return
    listed = bool(episodes) and str(unknown_id) in episodes
    _unknown_verdict(
        ctx, ids, identity, unknown_id, listed,
        "in_series_list" if listed else "not_in_series_list",
    )


def _resolve_tmdb_by_external(ctx: _ScanCtx, identity: str, ids: _Ids) -> None:
    """Movie/show TMDB id from its TVDB or IMDb id via TMDB /find."""
    resolved = _lookup(
        "tmdb",
        lambda: tmdb.resolve_id(
            ctx.tmdb_api_key, ctx.media_type.name, tvdb_id=ids.tvdb, imdb_id=ids.imdb,
        ),
        ctx, identity,
    )
    if resolved is TRANSIENT:
        ids.tmdb_transient = True
        ids.lookup_failed = True
        return
    ids.looked_up = True
    if resolved:
        ids.tmdb = resolved
        ctx.tracker.upsert_item(ctx.media_type.name, identity, tmdb_id=resolved)


def _show_tvdb_from_tmdb(ctx: _ScanCtx, identity: str, ids: _Ids) -> None:
    """Show TVDB id from TMDB's curated external ids."""
    tmdb_id = ids.tmdb or ""
    found = _lookup(
        "tmdb", lambda: tmdb.fetch_tvshow_external_ids(ctx.tmdb_api_key, tmdb_id),
        ctx, identity,
    )
    if found is TRANSIENT:
        ids.tvdb_transient = True
        ids.lookup_failed = True
        return
    ids.looked_up = True
    ids.tvdb_transient = False
    if found and found.get("tvdb_id"):
        ids.tvdb = found["tvdb_id"]
        ctx.tracker.upsert_item(ctx.media_type.name, identity, tvdb_id=ids.tvdb)


def _episode_tmdb_from_tvdb(
    ctx: _ScanCtx, item: dict[str, Any], identity: str, ids: _Ids,
) -> None:
    """Episode TMDB id from its TVDB id via TMDB /find.

    Without the show's TMDB id there is nothing to fetch the episode through,
    so no /find is made: when the show's lookups answered that TMDB does not
    have the show, TMDB has no answer for its episodes either; when they have
    not answered yet, the episode's TMDB fields wait for them.
    """
    if not ctx.show_id_map.get(_show_kodi_id(item)):
        if not _show_checked(ctx, item):
            ids.tmdb_transient = True
            ids.defer()
        return
    if not ids.may_look_up:
        return
    tvdb_id = ids.tvdb or ""
    found = _lookup(
        "tmdb", lambda: tmdb.find_episode_by_tvdb(ctx.tmdb_api_key, tvdb_id),
        ctx, identity,
    )
    if found is TRANSIENT:
        ids.tmdb_transient = True
        ids.lookup_failed = True
        return
    ids.looked_up = True
    if found:
        ctx.counts["episodes_found_by_tvdb"] += 1
        ids.tmdb = found["tmdb_id"]
        ids.tmdb_season = found["season"]
        ctx.tracker.upsert_item(
            ctx.media_type.name, identity,
            tmdb_id=ids.tmdb, tmdb_season=ids.tmdb_season,
        )


def _resolve_ids(
    ctx: _ScanCtx,
    item: dict[str, Any],
    identity: str,
    kodi_ids: tuple[str | None, str | None, str | None, str | None],
    stored: dict[str, Any],
    folder_lang: str,
    may_look_up: bool,
) -> _Ids:
    """Settle the item's ids before any field is fetched.

    Kodi's typed ids win; ids found by earlier scans come from the tracker.
    Then, while lookups are allowed: an `unknown` id is verified as a TVDB id
    (shows and episodes), a missing TMDB id is found from the TVDB or IMDb id,
    and a show's missing TVDB id comes from TMDB's external ids. An episode's
    missing TVDB and IMDb ids come from TMDB's episode external ids in
    _fetch_episode_tmdb, which has the TMDB episode numbers. Found ids go to
    the tracker only, never to Kodi.
    """
    kodi_tmdb, kodi_imdb, kodi_tvdb, unknown_id = kodi_ids
    kind = ctx.media_type.name
    ids = _Ids(
        tmdb=kodi_tmdb or stored.get("tmdb_id"),
        imdb=kodi_imdb or stored.get("imdb_id"),
        tvdb=kodi_tvdb or stored.get("tvdb_id"),
        may_look_up=may_look_up,
        # A Kodi-typed TMDB id goes with Kodi's own season number.
        tmdb_season=None if kodi_tmdb else stored.get("tmdb_season"),
    )

    if kind != "movie" and not ids.tvdb and unknown_id and may_look_up:
        verify = _verify_unknown_show if kind == "tvshow" else _verify_unknown_episode
        verify(ctx, item, identity, ids, unknown_id, folder_lang)

    if kind == "episode":
        # numbermatch imports this module's helpers, so it is imported here
        # rather than at module level.
        from resources.lib.engine.numbermatch import match_episode_by_number
        match_episode_by_number(ctx, item, identity, ids, stored, folder_lang, kodi_ids)
        if not ids.tmdb and ids.tvdb:
            _episode_tmdb_from_tvdb(ctx, item, identity, ids)
        return ids

    if not ids.tmdb and (ids.tvdb or ids.imdb) and may_look_up:
        _resolve_tmdb_by_external(ctx, identity, ids)
    if kind == "tvshow" and ids.tmdb and not ids.tvdb and may_look_up:
        _show_tvdb_from_tmdb(ctx, identity, ids)
    return ids


def _finish_lookups(ctx: _ScanCtx, identity: str, ids: _Ids, today: str) -> None:
    """Record that the item's lookups answered, so an id they left missing is
    not asked for again before FALLBACK_RECHECK_DAYS. Nothing is recorded
    when any lookup failed, so the next scan retries."""
    if ids.looked_up and not ids.lookup_failed:
        ctx.tracker.upsert_item(ctx.media_type.name, identity, ids_checked=today)
