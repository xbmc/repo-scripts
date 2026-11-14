"""
Scan orchestrator for MetaMender.

Coordinates a single scan cycle: queries Kodi, decides per field what is due,
calls providers, writes results, and updates the tracker.

Text fields come from TMDB and TheTVDB (TVDB): title and plot run through a
per-field provider chain (engine/chain.py) that ends in fallback-language
steps; every other text field has one TMDB step. Ratings come from TMDB and
the IMDb ratings store. Each field gets its own verdict: a field is transient
(no write, no clock advance) only when a provider in its own chain, or its
own ID prerequisite, was transient.

Logging:
    Logger: 'scan'
    Key events:
        - scan.start (INFO): Scan cycle starting for a media type
        - scan.complete (INFO): Scan cycle finished with stats, the
          providers disabled this cycle, and counts of the per-item DEBUG
          outcomes (unknown ids accepted, episodes found by TVDB id)
        - scan.skip (DEBUG): Item skipped (disabled source, not due, no
          candidates, or reason="unreachable": the media could not be found,
          so NFO state is unknown; scan.complete counts these)
        - scan.transient (DEBUG): An episode's TMDB path waits because its
          show's ids are not resolved yet (reason="show_unresolved")
        - scan.protected (DEBUG): An answered value was not written because
          the item is NFO-managed and the field holds a value metamender did
          not write
        - scan.abort (INFO): Scan interrupted by Kodi shutdown
        - scan.stopped (INFO): A progress callback stopped the pass (the
          user pressed Stop in the refresh window)
        - scan.processing (DEBUG): Starting to process a single item
        - scan.updated (INFO): Item metadata written to Kodi
        - scan.breaker (WARNING): A provider tripped, or every provider the
          enabled fields need is down so the pass stops (scope="all")
        - scan.tvdb_auth (ERROR): TVDB rejected the add-on's credentials;
          TVDB is disabled for the cycle, the scan continues
        - scan.imdb_lookup_failed (ERROR): The IMDb ratings store raised
          unexpectedly; the rating is transient for that item. Logged with
          the traceback once per scan, at DEBUG after that
        - scan.unknown_id_accepted (DEBUG): An `unknown`-type uniqueid was
          verified as the item's TVDB id; `reason` says how (name_match,
          accepted_by_episodes, in_series_list)
        - scan.unknown_id_rejected (INFO): An `unknown`-type uniqueid names a
          different TVDB series, or an episode outside the show's TVDB list;
          `reason` says which (name_mismatch, year_mismatch, ...)
        - scan.unknown_id_episodes (DEBUG): A show whose TVDB names match but
          whose year does not, checked against its own episode ids
        - scan.number_match (DEBUG): An episode without ids of its own was
          matched by season and episode number (engine/numbermatch.py)
        - scan.number_match_rejected (INFO; DEBUG when the site has no such
          number): a site's episode with that number failed the title/date
          check, with both titles and dates
        - scan.number_match_conflict (INFO): TMDB's own TVDB id for the
          matched episode differs from TheTVDB's number match; neither used
        - scan.language_unmapped (WARNING): A folder or fallback language code
          has no TheTVDB language, so TVDB is not asked for it; once per code
          per scan
        - scan.rekey_failed (WARNING): A show's title was written, but its
          episode rows could not be re-keyed to it
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import xbmc

from resources.lib.constants import (
    DEFAULT_REFETCH_SCHEDULE,
    FALLBACK_RECHECKS,
    parse_refetch_schedule,
)
from resources.lib.data import kodi
from resources.lib.data.identity import compute_identity
from resources.lib.data.kodi import get_item_by_id
from resources.lib.data.media_types import MediaType
from resources.lib.data.nfo import NFO, UNREACHABLE, nfo_state
from resources.lib.data.presets import load_preset
from resources.lib.data.sources import kodi_ui_language, match_source
from resources.lib.data.tracker import (
    REASON_FILL_ONLY,
    REASON_LOCKED,
    REASON_NFO,
    REASON_NOTHING,
    REASON_UNCHANGED,
    REASON_UNCHECKED,
    REASON_UPDATED,
    TrackerDB,
)
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.certchain import (
    DERIVED,
    NONE,
    NOT_ASKED,
    REAL,
    UNAVAILABLE,
    CertAnswer,
    CertQuery,
    SiteGate,
    resolve_certification,
)
from resources.lib.engine.certification import (
    BLANK,
    FOREIGN,
    OWN,
    PLACEHOLDER,
    classify_current,
    format_mpaa,
    parse_mpaa,
    sanitize_prefix,
)
from resources.lib.engine.chain import TRANSIENT, FieldOutcome
from resources.lib.engine.fetch import (
    _fetch_episode,
    _fetch_movie_or_show,
    _Primary,
)
from resources.lib.engine.ids import (
    _finish_lookups,
    _Ids,
    _lookup_allowed,
    _premiered_year,
    _resolve_ids,
)
from resources.lib.engine.maturity import (
    FETCH_NOW,
    FINAL,
    apply_fallback_recheck,
    compute_next_due,
    decide_certification,
    decide_field,
    fallback_recheck_due,
)
from resources.lib.engine.protect import fingerprint, is_blank, may_write
from resources.lib.engine.resolve import (
    FOLLOW_SCRAPER,
    slot_fingerprint,
)
from resources.lib.engine.scanctx import (
    _CHAIN_FIELDS,
    _KODI_TO_TMDB,
    _TMDB_TO_KODI,
    FALLBACK_TVDB_FIRST,
    LANGUAGE_FIELDS,
    RATING_FIELDS,
    TEXT_FOLLOW_SCRAPER,
    _CertConfig,
    _Pacer,
    _ScanCtx,
    extract_ids,
    kodi_form,
)
from resources.lib.engine.text import (
    _resolve_ratings,
    _text_chain,
    _TextSources,
)
from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import (
    get_logger,
    is_empty,
)

log = get_logger('scan')


def settings_fingerprint(
    field: str,
    settings: dict[str, Any],
    folder_language: str,
    media_type: str,
    fallback_language: str = "",
) -> str:
    """The settings a field's answer depends on, as a stable string.

    A field whose stored fingerprint differs is re-checked as if never
    sampled, so the inputs are exactly what changes the answer: rating_source
    for ratings; for title and plot the folder's language and fallback
    language ("" when it has none), plus the provider and fallback orders on
    shows and episodes (movies ask TMDB only); for every other field, one
    TMDB step, the folder language.
    """
    if field in RATING_FIELDS:
        inputs: dict[str, Any] = {
            "rating_source": settings.get("rating_source", FOLLOW_SCRAPER),
        }
    elif field == "mpaa":
        # The certification depends on the configured system and sources,
        # not on the folder language.
        inputs = {
            "country": settings.get("cert_country"),
            "prefix": settings.get("cert_prefix_override"),
            "sites": sorted(settings.get("cert_sites") or ()),
            "replace_foreign": bool(settings.get("cert_replace_foreign", True)),
            "not_found": settings.get("cert_not_found"),
        }
    elif field in _CHAIN_FIELDS:
        inputs = {
            "folder_language": folder_language,
            "fallback_language": fallback_language.strip(),
        }
        if media_type != "movie":
            inputs["text_source_order"] = settings.get("text_source_order", TEXT_FOLLOW_SCRAPER)
            inputs["fallback_order"] = settings.get("fallback_order", FALLBACK_TVDB_FIRST)
    else:
        inputs = {"folder_language": folder_language}
    return json.dumps(inputs, sort_keys=True)


def _make_stats() -> dict[str, Any]:
    """Return a fresh stats dict."""
    return {
        "processed": 0,
        "skipped": 0,
        "updated": 0,
        "errors": 0,
        # Items skipped because their media could not be reached, and answered
        # field values not written because an NFO supplied the field.
        "unreachable": 0,
        "protected": 0,
        # Fields left unchecked because a provider failed transiently, plus
        # items skipped while an id lookup had no answer: Update now tells
        # "could not check" from "nothing changed" by it.
        "transient": 0,
        "fields": {},
        # True when the pass stopped before reaching the end of the library
        # (shutdown, or every provider disabled). The caller must not treat
        # such a pass as a completed cycle.
        "aborted": False,
        # True when a progress callback stopped the pass (the user pressed
        # Stop); unlike "aborted" this is not a failure.
        "stopped": False,
        # True when TheTVDB has rejected the add-on's credentials this cycle
        # (in this pass or an earlier one sharing the breaker), so the caller
        # can tell the user TVDB text is paused.
        "tvdb_auth_failed": False,
        "tmdb_answered": False,
        "tvdb_answered": False,
    }


def content_age_days(
    item: dict[str, Any], media_type: MediaType, today: str
) -> int | None:
    """Age of the content in days from its release date, or None if unknown.

    Uses the release date (premiered/firstaired), never dateadded. Returns None
    when the date is missing or not a full ISO date.
    """
    raw = item.get(media_type.date_field, "")
    if not raw or len(raw) < 10:
        return None
    try:
        return (date.fromisoformat(today) - date.fromisoformat(raw[:10])).days
    except ValueError:
        return None


def _item_title(item: dict[str, Any], media_type: MediaType) -> str:
    """Build the display title for an item (logging/UI, not the tracker key).

    The tracker key is produced separately by compute_identity. Movies and TV
    shows use the title directly; episodes use "ShowTitle S01E02" format.
    """
    if media_type.name == "episode":
        return "{showtitle} S{season:02d}E{episode:02d}".format(
            showtitle=item.get("showtitle", ""),
            season=item.get("season", 0),
            episode=item.get("episode", 0),
        )
    return item.get("title", "")


def _extract_fields(
    provider_data: dict[str, Any],
    gap_fields: list[str],
) -> dict[str, Any]:
    """Provider values for the requested fields, in the form Kodi stores.

    Skips "mpaa" (Phase 8) and the named-slot rating/votes (handled by
    build_ratings). Values are put in Kodi's stored form (kodi_form), then
    empty ones are dropped, runtime is converted
    minutes -> seconds, and firstaired is kept only as a full ISO date (bare
    years are dropped). Title and plot arrive from the provider chain, which
    never yields a placeholder title, so no placeholder check is needed here.

    The result is what would be written, so it is also what the write's
    provenance fingerprint is taken of. Whether a value is written at all is
    _plan_writes' decision.
    """
    fields: dict[str, Any] = {}

    for tmdb_key, kodi_key in _TMDB_TO_KODI.items():
        if kodi_key not in gap_fields:
            continue

        # Rating and votes are written via the named-slot ratings map
        # (see build_ratings + the scan write path), never as flat fields.
        if kodi_key in ("rating", "votes"):
            continue

        value = kodi_form(provider_data.get(tmdb_key))

        # Skip empty provider values
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        if isinstance(value, (int, float)) and value == 0:
            continue

        # Runtime: providers return minutes; Kodi stores seconds
        if kodi_key == "runtime":
            if not isinstance(value, (int, float)):
                continue
            value = int(value) * 60

        # firstaired: only write a full ISO date; skip bare-year values
        if kodi_key == "firstaired" and not (
            isinstance(value, str) and len(value) == 10
            and value[4] == "-" and value[7] == "-"
        ):
            continue

        fields[kodi_key] = value

    return fields


def _plan_writes(
    values: dict[str, Any],
    item: dict[str, Any],
    nfo_managed: bool,
    fs_map: dict[str, dict[str, Any]],
    identity: str,
    fill_only: frozenset[str] = frozenset(),
) -> tuple[dict[str, Any], set[str]]:
    """Split extracted values into (fields to write, fields Kodi already holds).

    Under the maturity model a non-final field is refreshed overwrite-on-diff:
    a differing value overwrites the current one, an identical value is never
    rewritten. On an NFO-managed item, and for a field in ``fill_only``,
    may_write decides with the field's stored provenance; a field it forbids
    is in neither result, so it gets no write and no source.
    """
    to_write: dict[str, Any] = {}
    held: set[str] = set()
    for f, value in values.items():
        current = item.get(f)
        if current is not None and current == value:
            held.add(f)
            continue
        protected = nfo_managed or f in fill_only
        if not may_write(protected, current, fs_map.get(f, {}).get("written_value")):
            log.debug(
                "Field protected, value left as it is",
                event="scan.protected", identity=identity, field=f,
            )
            continue
        to_write[f] = value
    return to_write, held


def _parse_slots(raw: Any) -> dict[str, str]:
    """A rating row's JSON provenance; anything unreadable owns nothing."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    if isinstance(parsed, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
    ):
        return parsed
    return {}


def _owned_slots(
    fs_map: dict[str, dict[str, Any]],
    current_ratings: dict[str, Any],
) -> dict[str, str]:
    """Rating slots metamender wrote, from the JSON provenance on the rating
    and votes rows.

    The rows can disagree: only the due rating fields are recorded, so a row
    whose field is final or disabled keeps older JSON. Per slot, the
    fingerprint that matches the slot Kodi holds now wins, since that is the
    write that put it there; otherwise the rating row's. Unreadable JSON owns
    nothing, which protects every slot it would have named.
    """
    rows = [_parse_slots(fs_map.get(f, {}).get("written_value")) for f in ("rating", "votes")]
    owned: dict[str, str] = {}
    for slot in set(rows[0]) | set(rows[1]):
        claims = [r[slot] for r in rows if slot in r]
        entry = current_ratings.get(slot)
        held = slot_fingerprint(entry) if isinstance(entry, dict) else None
        owned[slot] = held if held in claims else claims[0]
    return owned


def blanked(item: dict[str, Any], field: str, fs: dict[str, Any]) -> bool:
    """Kodi holds an empty or placeholder value where metamender last wrote
    something else: a Kodi refresh or rescrape wiped the fill.

    A FINAL field is otherwise never looked at again, so the gap would stay.
    A field metamender never wrote (no provenance) is not "wiped", and one
    whose recorded value is the blank itself (metamender cleared it, or a
    refill found nothing) does not trigger again. Ratings are a slot map, not
    one value, and Kodi's refresh rewrites them rather than blanking them.
    """
    if field in RATING_FIELDS:
        return False
    written = fs.get("written_value")
    current = kodi_form(item.get(field))
    return written is not None and is_blank(current) and fingerprint(current) != written


def _reopened_fallbacks(
    item: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
    rebaseline: set[str],
) -> set[str]:
    """Chain fields whose current value metamender filled from the fallback
    language and that are re-checked under changed settings.

    The chain is fill-only, so without this a value filled from an old
    fallback language would never give way to the new one. Only a value
    Kodi still holds exactly as written is reopened; one the user edited
    stays fill-only.
    """
    reopened: set[str] = set()
    for f in rebaseline & _CHAIN_FIELDS:
        fs = fs_map.get(f) or {}
        written = fs.get("written_value")
        if (
            fs.get("from_fallback") and written is not None
            and fingerprint(kodi_form(item.get(f))) == written
        ):
            reopened.add(f)
    return reopened


def _resolve_fields(
    ctx: _ScanCtx,
    item: dict[str, Any],
    identity: str,
    primary: _Primary,
    ids: _Ids,
    folder_lang: str,
    fallback_lang: str,
    fields: list[str],
    reopened: set[str],
) -> tuple[dict[str, FieldOutcome], dict[str, Any], dict[str, str | None]]:
    """Per-field verdicts for the non-rating fields.

    A field in ``reopened`` runs its chain as if empty, so a fallback step may
    replace its current value (see _reopened_fallbacks).

    Returns (outcomes keyed by Kodi field, provider values keyed by TMDB key
    for _extract_fields, winning provider per Kodi field).
    """
    outcomes: dict[str, FieldOutcome] = {}
    values: dict[str, Any] = {}
    providers: dict[str, str | None] = {}
    text = _TextSources(ctx, item, identity, primary, ids, fallback_lang)
    tmdb_transient = primary.tmdb is TRANSIENT
    tmdb_data = {} if tmdb_transient or not primary.tmdb else primary.tmdb

    for f in fields:
        if f in RATING_FIELDS or f == "mpaa":
            # Ratings and certifications have their own producers.
            continue
        key = _KODI_TO_TMDB.get(f, f)
        if f in _CHAIN_FIELDS:
            current = None if f in reopened else item.get(f)
            outcome, provider = _text_chain(ctx, text, f, folder_lang, fallback_lang, current)
        else:
            value = None if tmdb_transient else tmdb_data.get(key)
            outcome = FieldOutcome(transient=tmdb_transient, value=value, from_fallback=False)
            provider = None if is_empty(value) else "tmdb"
        outcomes[f] = outcome
        providers[f] = provider
        if outcome.value is not None:
            values[key] = outcome.value
    return outcomes, values, providers


def _write_fields(
    ctx: _ScanCtx,
    kodi_id: Any,
    title: str,
    identity: str,
    fields_to_write: dict[str, Any],
    stats: dict[str, Any],
) -> set:
    """Write fields to Kodi and count stats. Returns the set of fields written
    this pass (empty if the write failed or there was nothing to write).

    Field facts (fetch_count, next_retry, source, vote_count) are recorded by the
    caller via tracker.record_field_fetch, not here.
    """
    ratings_written = "ratings" in fields_to_write
    write_succeeded = False

    if fields_to_write:
        write_succeeded = kodi.update_item(kodi_id, ctx.media_type, title, **fields_to_write)
        if write_succeeded:
            stats["updated"] += 1
            for field_name in fields_to_write:
                stats["fields"][field_name] = stats["fields"].get(field_name, 0) + 1
            log.info(
                "Item updated",
                event="scan.updated", title=title, identity=identity,
                media_type=ctx.media_type.name,
                fields_written=list(fields_to_write.keys()),
            )
        else:
            stats["errors"] += 1

    written: set[str] = set()
    if write_succeeded:
        written = set(fields_to_write.keys())
        if ratings_written:
            written.update({"rating", "votes"})
            written.discard("ratings")
    return written


def _field_reason(
    f: str,
    written: set[str],
    held: set[str],
    extracted: dict[str, Any],
    nfo_managed: bool,
    item: dict[str, Any],
    cert_kept: bool,
) -> str:
    """Why an answered field is as it is after this scan, as the scan acted.

    A value _plan_writes dropped was protected by the NFO or by the folder's
    fill-only rule. A certification the chain left in Kodi (an NFO's, or a
    foreign one while replacing is off) reaches no plan: it is the NFO's on
    an NFO item, otherwise Kodi's value kept as it is. Ratings are a slot
    map that never reaches the plan either: nothing written means Kodi's
    slots stand, or there were none to write.
    """
    if f in written:
        return REASON_UPDATED
    if f in held:
        return REASON_UNCHANGED
    if f in extracted:
        return REASON_NFO if nfo_managed else REASON_FILL_ONLY
    if f == "mpaa" and cert_kept:
        return REASON_NFO if nfo_managed else REASON_UNCHANGED
    # build_ratings returns no map both when Kodi's slots already hold the
    # answer and when there was nothing to write, so slots in Kodi are read
    # as "unchanged" and none as "nothing".
    if f in RATING_FIELDS and item.get("ratings"):
        return REASON_UNCHANGED
    return REASON_NOTHING


def _keep_originals(
    tracker: TrackerDB,
    media_type: str,
    identity: str,
    item: dict[str, Any],
    written: set[str],
    fields_to_write: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
) -> None:
    """Keep the value each written field held before this scan replaced it,
    unless that value was metamender's own (its fingerprint is the one
    metamender last wrote: field_keep's written_fp, which survives Reset
    tracker, else field_status's written_value): then the kept original,
    from before metamender's first write, stays. A scraper's or user's
    value since then replaces it. A field filled from empty keeps "" or []
    by the written value's type, so Restore can clear it. Rating slots get
    no original: the scraper's slots stay beside metamender's."""
    fields = sorted(written - RATING_FIELDS)
    keep = tracker.get_keep(media_type, identity) if fields else {}
    for f in fields:
        current = kodi_form(item.get(f))
        ours = (keep.get(f) or {}).get("written_fp") or fs_map.get(f, {}).get("written_value")
        if fingerprint(current) == ours:
            continue
        if current is None:
            current = [] if isinstance(fields_to_write.get(f), list) else ""
        tracker.keep_original(media_type, identity, f, current)


def _yield_to_playback(ctx: _ScanCtx, monitor: Any, processed: int) -> None:
    """Pause the scan while a video is playing, resume when it stops."""
    if monitor is None or not xbmc.getCondVisibility("Player.HasVideo"):
        return
    log.info(
        "Scan paused, video playing",
        event="scan.pause", media_type=ctx.media_type.name, processed=processed,
    )
    while (xbmc.getCondVisibility("Player.HasVideo")
           and not monitor.abortRequested()):
        if monitor.waitForAbort(10):
            break
    if not monitor.abortRequested():
        log.info(
            "Scan resumed, playback stopped",
            event="scan.resume", media_type=ctx.media_type.name,
        )


def _cert_config(
    media_type: MediaType,
    enabled_fields: frozenset[str],
    settings: dict[str, Any],
    breaker: CircuitBreaker,
    monitor: Any,
    gate: SiteGate | None,
) -> _CertConfig | None:
    """The pass's certification settings, or None when certifications are off
    for it. A configured country without a usable preset turns them off for
    the pass with one ERROR, rather than writing ratings from a wrong system."""
    if "mpaa" not in enabled_fields or media_type.name not in ("movie", "tvshow"):
        return None
    country = settings.get("cert_country")
    preset = load_preset(country) if country else None
    if preset is None:
        log.error(
            "Certifications skipped: no country preset applies",
            event="scan.cert_unavailable", country=country, media_type=media_type.name,
        )
        return None
    override = settings.get("cert_prefix_override")
    prefix = preset.prefix if override is None else sanitize_prefix(override, preset.prefix)
    return _CertConfig(
        preset=preset,
        prefix=prefix,
        replace_foreign=bool(settings.get("cert_replace_foreign", True)),
        not_found=settings.get("cert_not_found") or None,
        gate=gate or SiteGate(frozenset(settings.get("cert_sites") or ()), breaker, monitor),
    )


def _resolve_cert(
    cfg: _CertConfig,
    item: dict[str, Any],
    identity: str,
    primary: _Primary,
    ids: _Ids,
    fs: dict[str, Any],
    media_type: str,
    due: bool,
    recheck: bool,
    nfo_managed: bool,
) -> tuple[CertAnswer, str | None]:
    """The certification answer for the item and the value to plan, if any.

    An NFO's certification, which may not be replaced, costs no lookups. A
    rating already in the configured system is kept (only its prefix is
    normalized); a foreign one is kept when replacing is off; otherwise the
    chain runs, with the sites only when the field itself is due. The
    not-found value fills an empty field on the last of the monthly rechecks,
    never a rating, and metamender's own placeholder follows the not-found
    setting when that changes.
    """
    preset = cfg.preset
    current = str(item.get("mpaa") or "")
    written = fs.get("written_value")
    ours = written is not None and fingerprint(kodi_form(current)) == written
    placeholder = ours and fs.get("source") == "fallback"
    # A derived rating metamender wrote is in the configured system too, but
    # it is not the item's own: it stays on its monthly rechecks.
    ours_derived = ours and bool(fs.get("from_fallback"))
    state = classify_current(current, preset.valid, cfg.prefix, preset.country, placeholder,
                             canonical=preset.canonical)
    if nfo_managed and not may_write(True, current, written):
        answer, value = CertAnswer(REAL, None, "kodi"), None
    elif state == OWN and not ours_derived:
        bare = preset.canonical(_own_bare(current, cfg.prefix))
        answer, value = CertAnswer(REAL, bare, "kodi"), format_mpaa(bare, cfg.prefix)
    elif state == FOREIGN and not cfg.replace_foreign:
        answer, value = CertAnswer(REAL, None, "kodi"), None
    else:
        tmdb = primary.tmdb
        certs = TRANSIENT if tmdb is TRANSIENT else ((tmdb or {}).get("certifications") or {})
        query = CertQuery(
            title=str(item.get("title") or ""),
            original_title=str(item.get("originaltitle") or ""),
            year=_premiered_year(item),
            media_type=media_type,
            imdb_id=ids.imdb,
            tmdb_certs=certs,
        )
        answer = resolve_certification(query, preset, cfg.gate if due else None)
        value = format_mpaa(answer.rating, cfg.prefix) if answer.rating else None
        if answer.kind == NONE and state == PLACEHOLDER:
            # Reached through a settings change: the placeholder becomes the
            # current not-found value, or goes when that is switched off.
            if cfg.not_found:
                answer, value = CertAnswer(REAL, cfg.not_found, "fallback"), cfg.not_found
            else:
                value = ""
        elif (answer.kind == NONE and state == BLANK and cfg.not_found and recheck
                and int(fs.get("fallback_checks") or 0) >= FALLBACK_RECHECKS - 1):
            answer, value = CertAnswer(REAL, cfg.not_found, "fallback"), cfg.not_found
    log.debug(
        "Certification resolved", event="scan.cert", identity=identity,
        kind=answer.kind, source=answer.source, rating=answer.rating,
    )
    return answer, value


def _own_bare(current: str, prefix: str) -> str:
    """The bare rating of a value already in the configured system."""
    custom = prefix.strip()
    stripped = current.strip()
    if custom and stripped.lower().startswith(custom.lower()):
        return stripped[len(custom):].strip()
    return parse_mpaa(current)[1]


def candidate_fields(media_type: MediaType, enabled_fields: frozenset[str]) -> list[str]:
    """Fields this pass manages: enabled, backfilled for the media type, and
    known to the providers. An episode's title is enabled as "title", a show's
    or movie's as "main_title", since they have separate toggles."""
    fields = (
        {_TMDB_TO_KODI.get(k, k) for k in _TMDB_TO_KODI}
        & enabled_fields & media_type.backfill_fields
    )
    if media_type.name != "episode":
        fields.discard("title")
        if "main_title" in enabled_fields and "title" in media_type.backfill_fields:
            fields.add("title")
    return sorted(fields)


def item_fields(candidates: list[str], media_type: MediaType, identity: str) -> list[str]:
    """The pass's fields for one item. A show or movie keyed on its title
    ("title (year)", no tmdb or imdb id) does not get its title managed: a
    new title would make it a new tracker item."""
    if media_type.name == "episode" or identity.startswith(("tmdb:", "imdb:")):
        return candidates
    return [f for f in candidates if f != "title"]


def _needed_providers(media_type: MediaType, candidates: list[str]) -> list[str]:
    """Providers the pass can still make progress with. TMDB always; TVDB
    when a show or episode text field it supplies is managed. The IMDb store
    has no breaker, so it never stops a pass."""
    needed = ["tmdb"]
    if media_type.name != "movie" and _CHAIN_FIELDS & set(candidates):
        needed.append("tvdb")
    return needed


def _tracker_identity(
    tracker: TrackerDB, media_type: MediaType, item: dict[str, Any], kodi_id: Any,
) -> str:
    """The tracker key for this Kodi item: compute_identity's, unless another
    Kodi item in the library holds that row.

    Two items can compute one identity, such as two files of a movie that
    both carry its tmdb id. Sharing a row would let the first mark it
    processed for the cycle and the second never be scanned, so the item
    that does not hold the row gets ``<identity>|<file>``, and keeps it.
    The holder is the item whose Kodi id the row records. Whether that item
    still exists is asked from Kodi, and only when the ids differ: after a
    file is replaced or the library rebuilt, the recorded id is gone or
    names another item, and this item takes the row over.
    """
    identity = compute_identity(item, media_type)
    own = "{}|{}".format(identity, item.get("file", ""))
    if tracker.get_item(media_type.name, own) is not None:
        return own
    # An id written back to Kodi (_enrich_imdb_id) changes the identity the
    # item computes; keep its tracker row under the new one.
    tracker.adopt_identity(media_type.name, identity, kodi_id)
    row = tracker.get_item(media_type.name, identity)
    holder = row.get("kodi_id") if row else None
    if holder is None or holder == kodi_id:
        return identity
    other = get_item_by_id(media_type, holder)
    if other and compute_identity(other, media_type) == identity:
        log.debug(
            "Duplicate identity, item tracked under its file",
            event="scan.duplicate_identity", identity=identity,
            kodi_id=kodi_id, holder=holder,
        )
        return own
    return identity


def _new_items(tracker: TrackerDB, media_type: MediaType) -> list[dict[str, Any]]:
    """The library's items whose Kodi id the tracker does not know yet, with
    full details. An id listed but gone by the details call is skipped."""
    known = tracker.known_kodi_ids(media_type.name)
    listed = kodi.get_all_items(media_type, ids_only=True)
    fresh = [
        i[media_type.kodi_id_field] for i in listed
        if i.get(media_type.kodi_id_field) not in known
    ]
    items = [d for d in (get_item_by_id(media_type, i) for i in fresh) if d]
    log.info(
        "New library items selected", event="scan.new_items",
        media_type=media_type.name, listed=len(listed), new=len(items),
    )
    return items


def run_scan(
    media_type: MediaType,
    tracker: TrackerDB,
    source_config: dict[str, Any],
    enabled_fields: frozenset[str],
    tmdb_api_key: str,
    settings: dict[str, Any],
    monitor: Any = None,
    show_id_map: dict[int, str] | None = None,
    items: list[dict[str, Any]] | None = None,
    breaker: CircuitBreaker | None = None,
    reset: bool = False,
    new_only: bool = False,
    cert_gate: SiteGate | None = None,
    progress: Callable[[int, dict[str, Any], dict[str, Any]], bool] | None = None,
) -> dict[str, int]:
    """Run a single scan cycle for one media type.

    Queries Kodi for all items (or uses a pre-built list), computes a per-field
    maturity decision for each, fetches metadata when any field is due,
    refreshes non-final fields overwrite-on-diff, and records the per-field
    sampling facts in the tracker.

    Args:
        media_type: MOVIE, TVSHOW, or EPISODE.
        tracker: Open TrackerDB instance.
        source_config: Loaded source config dict with a "sources" list and
            optionally "default_language" and "fallback_language"; a source
            entry may set its own "language" and "fallback_language".
        enabled_fields: Set of field names the user wants backfilled.
        tmdb_api_key: TMDB API key.
        settings: Dict with stale_threshold_days, rate_limit, rating_source,
            text_source_order, fallback_order, imdb_ready
            (whether the IMDb ratings store is loaded this cycle; an IMDb
            rating is transient while it is False) and optionally
            refetch_schedule.
        monitor: xbmc.Monitor instance (has abortRequested()), or
            None for tests.
        show_id_map: Dict mapping a show's Kodi id to its show-level TMDB ID.
            Required for episode scans so fetch_season uses the show
            ID, not the episode ID. The show TVDB ids come from the tracker.
        items: Pre-built list of Kodi items to process. When provided,
            skips the Kodi library query. Useful for targeted scans
            (single item, folder, season) and testing.
        breaker: Shared CircuitBreaker for this scan cycle. The daemon
            creates one per cycle and passes the same instance into each
            media-type pass so a provider that fails repeatedly stays
            disabled across passes. When None, a fresh per-call breaker
            is created (single-pass / test convenience).
        reset: The "Update now" path. When True every candidate field is
            treated as due regardless of recorded maturity, the
            disabled-source gate and the playback yield are skipped (so the
            action always runs), and a field with history keeps its clock:
            only what was written is recorded (record_manual_check). A field
            without history gets a normal first sample.
        new_only: Library-event scan: process only the items whose Kodi id
            the tracker does not hold for this type. Kodi's dateadded is the
            file's date, not when the item entered the library, so it cannot
            pick out new items. A re-scraped item gets a new Kodi id and is
            included.
        progress: Called before each item with its index, the item and the
            live stats dict. Returning False stops the pass before that item
            (stats["stopped"]); an item is never stopped half-way.

    Returns:
        Stats dict with processed, skipped, updated, errors, and
        per-field counts.
    """
    scan_start = time.perf_counter()
    stats = _make_stats()
    if breaker is None:
        breaker = CircuitBreaker()
    raw_schedule = settings.get("refetch_schedule")
    if isinstance(raw_schedule, str):
        schedule = parse_refetch_schedule(raw_schedule)
    elif raw_schedule:
        schedule = tuple(raw_schedule)
    else:
        schedule = DEFAULT_REFETCH_SCHEDULE
    ctx = _ScanCtx(
        media_type=media_type,
        tracker=tracker,
        breaker=breaker,
        pacer=_Pacer(settings.get("rate_limit", 0.25)),
        tmdb_api_key=tmdb_api_key,
        default_language=source_config.get("default_language") or kodi_ui_language(),
        default_language_set=bool(source_config.get("default_language")),
        sources=source_config.get("sources", []),
        enabled_fields=enabled_fields,
        show_id_map=show_id_map or {},
        show_tvdb_map=(
            tracker.get_show_tvdb_map() if media_type.name == "episode" else {}
        ),
        checked_shows=(
            tracker.get_checked_show_ids()
            if media_type.name == "episode" else frozenset()
        ),
        season_cache={},
        tvdb_cache={},
        logged_once=set(),
        counts={"unknown_ids_accepted": 0, "episodes_found_by_tvdb": 0},
        schedule=schedule,
        rating_pref=settings.get("rating_source", FOLLOW_SCRAPER),
        text_order=settings.get("text_source_order", TEXT_FOLLOW_SCRAPER),
        fallback_order=settings.get("fallback_order", FALLBACK_TVDB_FIRST),
        default_fallback=str(source_config.get("fallback_language") or ""),
        imdb_ready=bool(settings.get("imdb_ready", False)),
        cert=_cert_config(media_type, enabled_fields, settings, breaker, monitor, cert_gate),
        reset=reset,
        tracked_shows=(
            tracker.get_tracked_show_ids()
            if media_type.name == "episode" else frozenset()
        ),
    )
    candidates = candidate_fields(media_type, enabled_fields)
    if ctx.cert is not None:
        candidates = sorted(set(candidates) | {"mpaa"})
    forgotten = tracker.forget_disabled_fields(media_type.name, candidates)
    if forgotten:
        log.debug("Disabled fields will be checked again when enabled",
                  event="scan.fields_disabled", media_type=media_type.name, rows=forgotten)
    needed = _needed_providers(media_type, candidates)

    log.info(
        "Scan starting",
        event="scan.start",
        media_type=media_type.name,
        reset=reset,
    )

    if items is None:
        items = _new_items(tracker, media_type) if new_only else kodi.get_all_items(media_type)

    for index, item in enumerate(items):
        # Check for Kodi shutdown
        if monitor is not None and monitor.abortRequested():
            log.info(
                "Scan interrupted by shutdown",
                event="scan.abort",
                media_type=media_type.name,
                processed=stats["processed"],
            )
            stats["aborted"] = True
            break

        if progress is not None and not progress(index, item, stats):
            log.info(
                "Scan stopped by the user",
                event="scan.stopped",
                media_type=media_type.name,
                processed=stats["processed"],
            )
            stats["stopped"] = True
            break

        # Yield: pause while video is playing. The reset path (Update now)
        # skips this so a manual single-item action does not silently block.
        if not reset:
            _yield_to_playback(ctx, monitor, stats["processed"])

        title = _item_title(item, media_type)
        kodi_id = item.get(media_type.kodi_id_field, 0)
        identity = _tracker_identity(tracker, media_type, item, kodi_id)

        # Resume: skip items already processed in this cycle. The reset path
        # (Update now) bypasses this so a just-scanned item can still be
        # corrected on demand.
        if not reset:
            pre_tracker = tracker.get_item(media_type.name, identity)
            if pre_tracker and pre_tracker.get("cycle_processed"):
                stats["skipped"] += 1
                continue

        # Match source. The reset path (Update now) bypasses the disabled-source
        # gate: the user explicitly requested a refresh, so the source setting
        # must not silently block it.
        source = match_source(item.get("file", ""), ctx.sources)
        if not reset and not source.get("enabled", True):
            log.debug(
                "Skipping disabled source",
                event="scan.skip",
                title=title,
                source_path=source.get("path", ""),
            )
            stats["skipped"] += 1
            continue

        language = source.get("language") or ctx.default_language
        # A source's own fallback_language wins, "" included (no fallback for
        # that folder even when sources.json sets a default).
        fallback_lang = str(
            source.get("fallback_language", ctx.default_fallback) or ""
        ).strip()
        fill_only = (
            frozenset() if source.get("language") or ctx.default_language_set
            else LANGUAGE_FIELDS
        )
        if fill_only and "language_unconfigured" not in ctx.logged_once:
            ctx.logged_once.add("language_unconfigured")
            log.info(
                "Folder without a configured language: text fills empty fields only",
                event="scan.language_unconfigured", language=language,
                media_type=media_type.name, source_path=item.get("file", ""),
            )

        # Extract external IDs
        kodi_ids = extract_ids(item)
        # An episode without ids of its own can still be matched by its
        # number under the show (engine/numbermatch.py).
        if not any(kodi_ids) and media_type.name != "episode":
            log.debug(
                "Skipping item without external IDs",
                event="scan.skip",
                title=title,
            )
            stats["skipped"] += 1
            continue
        tmdb_id, imdb_id, tvdb_id, _unknown = kodi_ids

        # Sync to tracker. None ids are not written, so ids found by earlier
        # scans survive and are read back below.
        tracker.upsert_item(
            media_type.name,
            identity,
            title=title,
            kodi_id=kodi_id,
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            tvdb_id=tvdb_id,
            source_path=item.get("file", ""),
            premiered=item.get(media_type.date_field, ""),
            date_added=item.get("dateadded", ""),
        )
        tracker.update_last_seen(media_type.name, identity, date.today().isoformat())
        stored = tracker.get_item(media_type.name, identity) or {}

        # --- Per-field maturity decisions (see maturity.decide_field) ---
        today = date.today().isoformat()
        age = content_age_days(item, media_type, today)
        fs_map = tracker.get_field_status_map(media_type.name, identity)
        threshold = settings.get("stale_threshold_days", 365)

        fields = item_fields(candidates, media_type, identity)
        # A locked field is the user's: never fetched, written or sampled,
        # on Update now and after a settings change too. Its reason is
        # recorded each scan it would have been considered.
        locked = (tracker.locked_fields(media_type.name, identity) - RATING_FIELDS) & set(fields)
        if locked:
            fields = [f for f in fields if f not in locked]
            for f in sorted(locked):
                tracker.record_field_reason(media_type.name, identity, f, REASON_LOCKED)
        # A field sampled under other settings (or before fingerprints were
        # stored) is re-checked as if never sampled, and re-baselined once it
        # answers. A transient keeps the old fingerprint, so it stays due.
        fps = {
            f: settings_fingerprint(f, settings, language, media_type.name, fallback_lang)
            for f in fields
        }
        rebaseline = {
            f for f in fields
            if reset or (f in fs_map and fs_map[f].get("settings_fp") != fps[f])
        }

        decisions: dict[str, str] = {}
        # Fields due only because a fallback value holds back FINAL: their
        # sample is a monthly recheck and spends one of FALLBACK_RECHECKS.
        rechecks: set[str] = set()
        # FINAL fields fetched once more because Kodi lost metamender's value.
        refills: set[str] = set()
        for f in fields:
            if f in rebaseline:
                # Update now, or changed settings: due regardless of the
                # recorded maturity, so the clock re-baselines.
                decisions[f] = FETCH_NOW
                continue
            fs = fs_map.get(f, {})
            if f == "mpaa":
                # Certifications do not age: see decide_certification.
                count = int(fs.get("fetch_count") or 0)
                decisions[f] = decide_certification(
                    count, bool(fs.get("from_fallback")),
                    int(fs.get("fallback_checks") or 0), fs.get("next_retry"), today,
                )
                if decisions[f] == FETCH_NOW and count and fs.get("from_fallback"):
                    rechecks.add(f)
                elif decisions[f] == FINAL and blanked(item, f, fs):
                    decisions[f] = FETCH_NOW
                    refills.add(f)
                continue
            base = decide_field(
                age,
                int(fs.get("fetch_count") or 0),
                fs.get("next_retry"),
                today,
                threshold,
            )
            decisions[f] = apply_fallback_recheck(
                base,
                bool(fs.get("from_fallback")),
                int(fs.get("fallback_checks") or 0),
                fs.get("next_retry"),
                today,
            )
            if base == FINAL and decisions[f] == FETCH_NOW:
                rechecks.add(f)
            elif decisions[f] == FINAL and blanked(item, f, fs):
                decisions[f] = FETCH_NOW
                refills.add(f)

        due = any(d == FETCH_NOW for d in decisions.values())

        # NFO detection touches the share, so it runs once, and only for an
        # item with a field to process. Unreachable media (a sleeping or
        # offline share) says nothing about the NFO: the item is left exactly
        # as it is, ids_checked and cycle flag included, and retried later.
        nfo_managed = False
        if due:
            state = nfo_state(media_type.name, item.get("file", ""))
            if state == UNREACHABLE:
                log.debug(
                    "Media unreachable, skipping item",
                    event="scan.skip", reason="unreachable", title=title,
                    identity=identity, media_type=media_type.name,
                )
                stats["skipped"] += 1
                stats["unreachable"] += 1
                continue
            nfo_managed = state == NFO

        ids = _resolve_ids(
            ctx, item, identity, kodi_ids, stored, language,
            _lookup_allowed(
                stored.get("ids_checked"), today, due, media_type.name == "tvshow",
                reset,
            ),
        )

        # Nothing is due this scan: mark processed and move on without a fetch.
        if not due:
            _finish_lookups(ctx, identity, ids, today)
            tracker.mark_cycle_processed(media_type.name, identity)
            stats["skipped"] += 1
            continue

        # Only an unverified (rejected, or not yet answered) unknown id: no
        # provider can be asked, and no field is sampled.
        if not ids.any():
            log.debug(
                "Item has no usable ID, skipping",
                event="scan.skip", title=title, media_type=media_type.name,
                tvdb_transient=ids.tvdb_transient,
            )
            _finish_lookups(ctx, identity, ids, today)
            tracker.mark_cycle_processed(media_type.name, identity)
            stats["skipped"] += 1
            if ids.tvdb_transient or ids.tmdb_transient:
                stats["transient"] += 1
            continue

        log.debug(
            "Processing item",
            event="scan.processing",
            title=title,
            identity=identity,
            media_type=media_type.name,
            tmdb_id=ids.tmdb,
            tvdb_id=ids.tvdb,
            decisions=decisions,
            rebaseline=sorted(rebaseline),
            refills=sorted(refills),
        )

        if breaker.all_disabled(needed):
            log.warning(
                "Every provider the enabled fields need is disabled, stopping scan",
                event="scan.breaker", scope="all", providers=needed,
                media_type=media_type.name, processed=stats["processed"],
            )
            stats["aborted"] = True
            break

        tmdb_lang = tmdb_language(language)
        fetch_primary = (
            _fetch_episode if media_type.name == "episode" else _fetch_movie_or_show
        )
        primary = fetch_primary(ctx, item, kodi_id, title, identity, ids, tmdb_lang)

        # Non-final fields are refreshed (overwrite-on-diff); final ones are not.
        nonfinal = [f for f, d in decisions.items() if d != FINAL]
        reopened = _reopened_fallbacks(item, fs_map, rebaseline)
        outcomes, values, providers = _resolve_fields(
            ctx, item, identity, primary, ids, language, fallback_lang, nonfinal,
            reopened,
        )
        cert_value: str | None = None
        cert_kept = False
        if "mpaa" in nonfinal and ctx.cert is not None:
            cert_answer, cert_value = _resolve_cert(
                ctx.cert, item, identity, primary, ids, fs_map.get("mpaa", {}),
                media_type.name, decisions["mpaa"] == FETCH_NOW, "mpaa" in rechecks,
                nfo_managed,
            )
            # Not asked (sites not due, TMDB without an answer) and
            # unavailable both leave the field's clock alone.
            outcomes["mpaa"] = FieldOutcome(
                transient=cert_answer.kind in (UNAVAILABLE, NOT_ASKED),
                value=cert_value,
                from_fallback=cert_answer.kind in (DERIVED, NONE),
            )
            providers["mpaa"] = cert_answer.source
            cert_kept = cert_answer.kind == REAL and cert_answer.source == "kodi"
        answered = [f for f in nonfinal if f in outcomes and not outcomes[f].transient]
        extracted = _extract_fields(values, answered)
        if cert_value is not None and "mpaa" in answered:
            extracted["mpaa"] = cert_value
        # A reopened fallback value whose chain now has nothing (the folder's
        # fallback was removed, or the new one has no text either) is cleared:
        # it was only ever there because of the old setting. Only a value Kodi
        # still holds exactly as metamender wrote it is reopened, so a user's
        # edit is never cleared.
        for f in reopened:
            if f in answered and outcomes[f].value is None:
                extracted[f] = ""
        fields_to_write, held = _plan_writes(
            extracted, item, nfo_managed, fs_map, identity, fill_only,
        )
        stats["protected"] += len(extracted) - len(fields_to_write) - len(held)

        ratings_source: str | None = None
        ratings_votes: int | None = None
        owned_slots = _owned_slots(fs_map, item.get("ratings") or {})
        slot_fps: dict[str, str] = {}
        rating_due = [f for f in nonfinal if f in RATING_FIELDS]
        if rating_due:
            (transient, new_ratings, ratings_source, ratings_votes,
             slot_fps) = _resolve_ratings(
                ctx, item, primary, identity, nfo_managed, owned_slots,
            )
            rating_outcome = FieldOutcome(
                transient=transient, value=None, from_fallback=False,
            )
            for f in rating_due:
                outcomes[f] = rating_outcome
            if new_ratings is not None:
                fields_to_write["ratings"] = new_ratings

        written = _write_fields(
            ctx, kodi_id, title, identity, fields_to_write, stats,
        )
        _keep_originals(
            tracker, media_type.name, identity, item, written, fields_to_write, fs_map,
        )
        # Episodes are keyed on their show's title; keep their rows. A failed
        # re-key is undone in the tracker, so the episodes keep the old key
        # and start over under the new title.
        if (media_type.name == "tvshow" and "title" in written and item.get("title")
                and tracker.rename_show_episodes(
                    item["title"], fields_to_write["title"]) is None):
            log.warning(
                "Show title written, but its episode rows kept the old title",
                event="scan.rekey_failed", identity=identity,
                old_title=item["title"], new_title=fields_to_write["title"],
            )

        # A field whose write was attempted and rejected by Kodi was NOT filled,
        # so its clock must not advance: otherwise aged content reaches FINAL on
        # the next scan and is never written again. Fields with nothing to write
        # (provider answered, value empty or unchanged) are a clean sample and
        # do advance.
        attempted = set(fields_to_write)
        if "ratings" in attempted:
            attempted.discard("ratings")
            attempted.update(RATING_FIELDS)
        write_failed = attempted - written

        # Provenance: the fingerprint of each value as written to Kodi. Rating
        # rows hold the per-slot fingerprints as JSON, merged over the slots
        # owned before so a slot not rewritten this scan stays owned.
        provenance: dict[str, str] = {
            f: fingerprint(fields_to_write[f])
            for f in written if f in fields_to_write
        }
        # A refill the provider could not fill records the blank as the
        # field's value, so the same blank does not trigger it again.
        for f in refills - written:
            provenance[f] = fingerprint(kodi_form(item.get(f)))
        # The same fingerprints in field_keep, which Reset tracker keeps, so
        # _keep_originals still knows metamender's own value after a reset.
        for f, fp in provenance.items():
            if f not in RATING_FIELDS:
                tracker.set_written_fp(media_type.name, identity, f, fp)
        if slot_fps and RATING_FIELDS & written:
            merged = dict(owned_slots)
            merged.update(slot_fps)
            for f in RATING_FIELDS & written:
                provenance[f] = json.dumps(merged, sort_keys=True)

        # Advance a field's clock ONLY when its own providers answered; a
        # transient field is retried next scan instead of being wrongly
        # sampled/finalized. A protected field is answered and advances.
        # Changed settings re-baseline it. Update now leaves the clock of a
        # field with history alone and records only what it wrote: a manual
        # refresh is not a sample of the item's ageing.
        premiered = item.get(media_type.date_field, "")
        for f in nonfinal:
            outcome = outcomes[f]
            if outcome.transient:
                stats["transient"] += 1
                tracker.record_field_reason(media_type.name, identity, f, REASON_UNCHECKED)
                continue
            if f in write_failed:
                continue
            fs = fs_map.get(f, {})
            new_count = 1 if f in rebaseline else int(fs.get("fetch_count") or 0) + 1
            next_due = compute_next_due(
                new_count, ctx.schedule, premiered, threshold, today,
            )
            if f in RATING_FIELDS:
                # Rating/votes are sourced from the named-slot ratings map;
                # record the chosen slot and its votes for staleness.
                source = ratings_source
                vote_count = ratings_votes
                from_fallback: bool | None = None
            else:
                # Source describes the value Kodi now holds, so it is recorded
                # only when the answer is in Kodi (written now, or already
                # equal); a dropped or protected answer keeps the old one. The
                # fallback flag follows a write, and a folder-language answer
                # equal to Kodi's value clears it: the value no longer depends
                # on the fallback language.
                source = providers.get(f) if f in written or f in held else None
                vote_count = None
                if f in written or f == "mpaa":
                    # A certification's flag is its answer's kind (derived or
                    # none is rechecked), whether or not anything was written.
                    from_fallback = outcome.from_fallback
                elif f in held and not outcome.from_fallback:
                    from_fallback = False
                else:
                    from_fallback = None
            stays_fallback = (
                from_fallback if from_fallback is not None
                else bool(fs.get("from_fallback"))
            )
            if stays_fallback:
                # Past the stability age the schedule no longer applies, so
                # the recheck is a month out; younger content keeps an
                # earlier schedule date.
                # A certification is rechecked monthly at any age.
                mature = f == "mpaa" or (age is not None and age >= threshold)
                next_due = fallback_recheck_due(None if mature else next_due, today)
            reason = _field_reason(
                f, written, held, extracted, nfo_managed, item, cert_kept,
            )
            if reset and int(fs.get("fetch_count") or 0) > 0:
                tracker.record_manual_check(
                    media_type.name, identity, f, settings_fp=fps[f],
                    written_value=provenance.get(f), source=source,
                    vote_count=vote_count, from_fallback=from_fallback,
                    reason=reason,
                )
            elif f in rebaseline:
                tracker.reset_field_clock(
                    media_type.name, identity, f,
                    next_retry=next_due, settings_fp=fps[f],
                    written_value=provenance.get(f), source=source,
                    vote_count=vote_count, from_fallback=from_fallback,
                    reason=reason,
                )
            else:
                tracker.record_field_fetch(
                    media_type.name, identity, f,
                    next_retry=next_due, settings_fp=fps[f],
                    written_value=provenance.get(f), source=source,
                    vote_count=vote_count, from_fallback=from_fallback,
                    fallback_recheck=f in rechecks, reason=reason,
                )
        _finish_lookups(ctx, identity, ids, today)
        tracker.commit()

        tracker.mark_cycle_processed(media_type.name, identity)
        stats["processed"] += 1

    stats["tvdb_auth_failed"] = "tvdb" in breaker.auth_rejected()
    stats["tmdb_answered"] = breaker.answered("tmdb")
    stats["tvdb_answered"] = breaker.answered("tvdb")
    log.info(
        "Scan complete",
        event="scan.complete",
        media_type=media_type.name,
        reset=reset,
        processed=stats["processed"],
        skipped=stats["skipped"],
        updated=stats["updated"],
        errors=stats["errors"],
        unreachable=stats["unreachable"],
        protected=stats["protected"],
        unknown_ids_accepted=ctx.counts["unknown_ids_accepted"],
        episodes_found_by_tvdb=ctx.counts["episodes_found_by_tvdb"],
        disabled=breaker.disabled(),
        duration_ms=int((time.perf_counter() - scan_start) * 1000),
    )

    return stats
