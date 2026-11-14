"""Matching an episode without a usable id of its own by its season and
episode number under its show, at TMDB and at TheTVDB.

An episode scraped from TVmaze carries only a TVmaze id, which no provider
metamender asks can look up, and TVmaze lists no other ids for episodes. Its
number under the show is the only route, and sites number some shows
differently, so each site's candidate is checked (engine/epmatch.py) before
it counts: a wrong episode's title and plot are worse than none.

The check always compares the title and date the episode had when first
seen unmatched (kept in the tracker): once metamender has filled the
episode, Kodi shows metamender's own values. Matched ids go to the tracker
only, never into Kodi.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from resources.lib.engine.chain import TRANSIENT
from resources.lib.engine.epmatch import MatchVerdict, SiteEpisode, check_number_match
from resources.lib.engine.ids import (
    _Ids,
    _lookup,
    _show_checked,
    _show_kodi_id,
    _tvdb_cached,
    _tvdb_lang,
    _verification_lang,
)
from resources.lib.engine.scanctx import _call_provider, _get_season_data, _ScanCtx
from resources.lib.providers import tmdb, tvdb
from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import get_logger

log = get_logger('scan')


@dataclass(frozen=True)
class _Kept:
    """The episode as the check sees it: the values it had when first seen
    unmatched."""

    title: str
    aired: str
    season: int
    number: int


def _primary(code: str) -> str:
    return code.split("-")[0].casefold()


def _merge(lists: list[list[SiteEpisode]]) -> list[SiteEpisode]:
    """One SiteEpisode per (season, number) carrying every language's title;
    the date and id come from the first list that has the episode."""
    merged: dict[tuple[int, int], SiteEpisode] = {}
    for episodes in lists:
        for ep in episodes:
            key = (ep.season, ep.number)
            have = merged.get(key)
            if have is None:
                merged[key] = ep
            else:
                merged[key] = SiteEpisode(
                    have.ep_id, have.season, have.number, have.aired,
                    have.titles + ep.titles,
                )
    return list(merged.values())


def _tmdb_original(ctx: _ScanCtx, show_tmdb_id: str, identity: str) -> Any:
    key = ("tmdb", show_tmdb_id)
    if key not in ctx.original_language:
        found = _lookup(
            "tmdb",
            lambda: tmdb.fetch_tvshow_original_language(show_tmdb_id, ctx.tmdb_api_key),
            ctx, identity,
        )
        if found is TRANSIENT:
            return TRANSIENT
        ctx.original_language[key] = found
    return ctx.original_language[key]


def _tmdb_site(
    ctx: _ScanCtx, show_tmdb_id: str, season: int, folder_lang: str, identity: str,
) -> Any:
    """TMDB's episodes of `season` with titles in the folder language and the
    show's original language; None when TMDB has no such season, TRANSIENT
    when a list could not be read."""
    original = _tmdb_original(ctx, show_tmdb_id, identity)
    if original is TRANSIENT:
        return TRANSIENT
    langs = [tmdb_language(folder_lang)]
    if original and _primary(original) != _primary(langs[0]):
        langs.append(tmdb_language(original))
    lists: list[list[SiteEpisode]] = []
    for lang in langs:
        cache_key = "{}:{}:{}".format(show_tmdb_id, season, lang)
        if cache_key in ctx.season_cache:
            data: Any = ctx.season_cache[cache_key]
        else:
            data = _lookup(
                "tmdb",
                lambda lang=lang: _get_season_data(
                    show_tmdb_id, season, ctx.tmdb_api_key, lang, ctx.season_cache,
                ),
                ctx, identity,
            )
        if data is TRANSIENT:
            return TRANSIENT
        if data is None:
            if not lists:
                return None
            continue
        lists.append([
            SiteEpisode(
                ep_id=str(ep.get("tmdb_id") or ""),
                season=int(ep.get("season_number", season) or 0),
                number=int(ep.get("episode_number") or 0),
                aired=str(ep.get("firstaired") or ""),
                titles=(str(ep.get("title") or ""),),
            )
            for ep in data if ep.get("tmdb_id")
        ])
    return _merge(lists)


def _tvdb_site(
    ctx: _ScanCtx, show_tvdb_id: str, folder_lang: str, identity: str,
) -> Any:
    """TheTVDB's episodes in aired order with titles in the folder language
    and the series' original language; None when TheTVDB has no such series,
    TRANSIENT when a list could not be read."""
    series = _tvdb_cached(
        ctx, "series", show_tvdb_id, _verification_lang(ctx, folder_lang),
        tvdb.fetch_series, identity,
    )
    if series is TRANSIENT:
        return TRANSIENT
    langs = [lang for lang in (_tvdb_lang(ctx, folder_lang),
                               (series or {}).get("original_language") or None) if lang]
    lists: list[list[SiteEpisode]] = []
    for lang in dict.fromkeys(langs):
        data = _tvdb_cached(
            ctx, "episode_numbers", show_tvdb_id, lang,
            tvdb.fetch_series_episode_numbers, identity,
        )
        if data is TRANSIENT:
            return TRANSIENT
        if data is None:
            if not lists:
                return None
            continue
        lists.append([
            SiteEpisode(
                ep_id=str(ep["tvdb_id"]), season=int(ep["season"]),
                number=int(ep["number"]), aired=str(ep.get("aired") or ""),
                titles=(str(ep.get("title") or ""),),
            )
            for ep in data
        ])
    return _merge(lists) if lists else None


def _verdict(site: Any, kept: _Kept) -> Any:
    """The check for one site's list; TRANSIENT passes through, and a site
    that has no list at all (no show id, no such series) is not_found."""
    if site is TRANSIENT:
        return TRANSIENT
    return check_number_match(kept.title, kept.aired, kept.season, kept.number, site or [])


_NOTE_KEYS = ("site", "site_title", "site_aired", "kodi_title", "kodi_aired")


def _note_entry(
    site_name: str, site: Any, verdict: MatchVerdict, kept: _Kept, identity: str,
) -> dict[str, Any]:
    """The log fields for a site that did not pass: both titles and dates,
    the candidate's empty when the site has no episode with that number."""
    candidate = next(
        (ep for ep in site or []
         if ep.season == kept.season and ep.number == kept.number), None,
    )
    return {
        "identity": identity, "site": site_name, "season": kept.season,
        "episode": kept.number, "kodi_title": kept.title, "kodi_aired": kept.aired,
        "site_title": " / ".join(t for t in candidate.titles if t) if candidate else "",
        "site_aired": candidate.aired if candidate else "", "reason": verdict.reason,
    }


def _log_rejected(fields: dict[str, Any]) -> None:
    """One line per site that did not pass: INFO for a rejected candidate, so
    the user can see why the episode stayed as it was; DEBUG when the site
    has no episode with that number (a whole year-numbered season would
    otherwise flood the log)."""
    if fields["reason"] == "rejected":
        log.info("Episode number match rejected", event="scan.number_match_rejected", **fields)
    else:
        log.debug("Episode number not found", event="scan.number_match_rejected", **fields)


def _cross_ids(ctx: _ScanCtx, show_tmdb_id: str, kept: _Kept, identity: str) -> Any:
    """TMDB's own TheTVDB and IMDb ids for the matched episode (best effort)."""
    found = _call_provider(
        "tmdb",
        lambda: tmdb.fetch_episode_external_ids(
            show_tmdb_id, kept.season, kept.number, ctx.tmdb_api_key,
        ),
        ctx, identity, best_effort=True,
    )
    return found if found is TRANSIENT else (found or {})


def _drop_match(ctx: _ScanCtx, identity: str, ids: _Ids, kodi_imdb: str | None) -> None:
    """Forget a stored number match: its ids leave the tracker and ``ids``;
    an IMDb id of the episode's own stays."""
    ctx.tracker.clear_number_match(ctx.media_type.name, identity)
    ids.tmdb = ids.tvdb = None
    ids.tmdb_season = None
    ids.imdb = kodi_imdb
    ids.number_matched = False
    if kodi_imdb:
        ctx.tracker.upsert_item(ctx.media_type.name, identity, imdb_id=kodi_imdb)


def match_episode_by_number(
    ctx: _ScanCtx,
    item: dict[str, Any],
    identity: str,
    ids: _Ids,
    stored: dict[str, Any],
    folder_lang: str,
    kodi_ids: tuple[str | None, str | None, str | None, str | None],
) -> None:
    """Match an episode with no TMDB and no TheTVDB id by its number, each
    site separately, and record what passed (tracker only).

    A stored number match is used as is, except on Update now (ctx.reset),
    which checks it again and drops it when it no longer passes. A transient
    failure anywhere records nothing and leaves `ids` as they were, so the
    next scan asks again; a show whose own lookups have not answered yet
    defers the episode the same way. Until the match is settled again,
    ``ids.number_matched`` keeps saying where the loaded ids came from, so
    nothing they lead to reaches Kodi.

    ``kodi_ids`` are the episode's own typed ids (extract_ids): an episode
    that has a TMDB or TheTVDB id of its own (a rescrape) drops any stored
    number match, and an IMDb id of its own is never replaced.
    """
    if ctx.media_type.name != "episode":
        return
    kodi_tmdb, kodi_imdb, kodi_tvdb, _unknown = kodi_ids
    recheck = bool(stored.get("number_matched"))
    if kodi_tmdb or kodi_tvdb:
        if stored.get("match_note"):
            # Never matched by number again: the last check's note is stale.
            ctx.tracker.upsert_item(ctx.media_type.name, identity, match_note="")
        if recheck:
            ctx.tracker.clear_number_match(ctx.media_type.name, identity)
            ctx.tracker.upsert_item(
                ctx.media_type.name, identity,
                tmdb_id=kodi_tmdb, tvdb_id=kodi_tvdb, imdb_id=kodi_imdb,
            )
            ids.tmdb, ids.tvdb, ids.imdb = kodi_tmdb, kodi_tvdb, kodi_imdb
            ids.tmdb_season = None
        return
    ids.number_matched = recheck
    if recheck and not ctx.reset:
        return
    if not recheck and (ids.tmdb or ids.tvdb):
        return
    if not ids.may_look_up:
        return

    if not _show_checked(ctx, item):
        if _show_kodi_id(item) not in ctx.tracked_shows:
            # The show has no ids of its own: nothing to ask, now or later,
            # and nothing a stored match can still rest on.
            if recheck:
                _drop_match(ctx, identity, ids, kodi_imdb)
            return
        ids.tmdb_transient = ids.tvdb_transient = True
        ids.defer()
        return

    # Once captured, the originals are used as they were, empty ones too:
    # falling back to Kodi's current value would compare a site with what
    # metamender wrote from that site.
    captured = stored.get("orig_title") is not None or stored.get("orig_aired") is not None
    source = stored if captured else {
        "orig_title": item.get("title"), "orig_aired": item.get(ctx.media_type.date_field),
    }
    kept = _Kept(
        title=str(source.get("orig_title") or ""),
        aired=str(source.get("orig_aired") or ""),
        season=int(item.get("season", 0) or 0),
        number=int(item.get("episode", 0) or 0),
    )
    if not captured:
        ctx.tracker.upsert_item(
            ctx.media_type.name, identity, orig_title=kept.title, orig_aired=kept.aired,
        )

    show_tmdb_id = ctx.show_id_map.get(_show_kodi_id(item))
    show_tvdb_id = ctx.show_tvdb_map.get(_show_kodi_id(item))
    if not show_tmdb_id and not show_tvdb_id:
        # The show answered that neither site has it: nothing to ask, and
        # derived without a call, so not recorded as a lookup.
        if recheck:
            _drop_match(ctx, identity, ids, kodi_imdb)
        return

    tmdb_list = (
        _tmdb_site(ctx, show_tmdb_id, kept.season, folder_lang, identity)
        if show_tmdb_id else None
    )
    tvdb_list = _tvdb_site(ctx, show_tvdb_id, folder_lang, identity) if show_tvdb_id else None
    tmdb_verdict = _verdict(tmdb_list, kept)
    tvdb_verdict = _verdict(tvdb_list, kept)
    cross: Any = {}
    if isinstance(tmdb_verdict, MatchVerdict) and tmdb_verdict.episode and show_tmdb_id:
        cross = _cross_ids(ctx, show_tmdb_id, kept, identity)
    if TRANSIENT in (tmdb_verdict, tvdb_verdict, cross):
        # Both sites, even one that answered: its match is not used this
        # scan, so a field it would serve must not read as "no such episode".
        ids.tmdb_transient = ids.tvdb_transient = True
        ids.lookup_failed = True
        return

    ids.looked_up = True
    notes: list[dict[str, Any]] = []
    for name, site, verdict in (("tmdb", tmdb_list, tmdb_verdict),
                                ("tvdb", tvdb_list, tvdb_verdict)):
        if verdict.episode is None:
            fields = _note_entry(name, site, verdict, kept, identity)
            _log_rejected(fields)
            # A rejected candidate goes in the note with both titles and
            # dates; a site without such an episode has nothing to show.
            if verdict.reason == "rejected":
                notes.append({k: fields[k] for k in _NOTE_KEYS})

    tmdb_ep = tmdb_verdict.episode
    tvdb_ep = tvdb_verdict.episode
    cross_tvdb = cross.get("tvdb_id")
    conflict: dict[str, Any] | None = None
    if tmdb_ep and tvdb_ep and cross_tvdb and str(cross_tvdb) != tvdb_ep.ep_id:
        conflict = {
            "site": "conflict", "tmdb_id": tmdb_ep.ep_id,
            "tmdb_tvdb_id": str(cross_tvdb), "tvdb_id": tvdb_ep.ep_id,
        }
        notes.append(conflict)
    elif tmdb_ep or tvdb_ep:
        # How each recorded id was found: "title" or "date" when its own
        # site's candidate passed, "tmdb_list" for a TheTVDB id taken from
        # TMDB's cross-id list.
        if tmdb_ep:
            notes.append({"site": "tmdb", "matched": tmdb_verdict.reason})
        if tvdb_ep:
            notes.append({"site": "tvdb", "matched": tvdb_verdict.reason})
        elif cross_tvdb:
            notes.append({"site": "tvdb", "matched": "tmdb_list"})
    # The note describes the latest completed check: the sites that rejected
    # their candidate, a conflict between two passed sites, how the used ids
    # were found, or nothing.
    ctx.tracker.upsert_item(
        ctx.media_type.name, identity, match_note=json.dumps(notes) if notes else "",
    )
    if recheck:
        _drop_match(ctx, identity, ids, kodi_imdb)
    if conflict is not None:
        log.info(
            "TMDB and TheTVDB number matches name different episodes, neither used",
            event="scan.number_match_conflict", identity=identity,
            season=kept.season, episode=kept.number, tmdb_id=conflict["tmdb_id"],
            tmdb_tvdb_id=conflict["tmdb_tvdb_id"], tvdb_id=conflict["tvdb_id"],
        )
        return
    if not tmdb_ep and not tvdb_ep:
        return

    ids.tmdb = tmdb_ep.ep_id if tmdb_ep else None
    ids.tmdb_season = kept.season if tmdb_ep else None
    ids.tvdb = tvdb_ep.ep_id if tvdb_ep else (str(cross_tvdb) if cross_tvdb else None)
    ids.imdb = kodi_imdb or cross.get("imdb_id") or None
    ids.number_matched = True
    ctx.tracker.upsert_item(
        ctx.media_type.name, identity, tmdb_id=ids.tmdb, tmdb_season=ids.tmdb_season,
        tvdb_id=ids.tvdb, imdb_id=ids.imdb, number_matched=1,
    )
    log.debug(
        "Episode matched by number",
        event="scan.number_match", identity=identity,
        tmdb_id=ids.tmdb, tmdb_reason=tmdb_verdict.reason,
        tvdb_id=ids.tvdb, tvdb_reason=tvdb_verdict.reason,
    )
