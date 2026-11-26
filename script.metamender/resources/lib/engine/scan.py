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
        - scan.season_no_show_id (DEBUG): A season skipped because its
          show has no TMDB id (yet), so it has no identity
        - scan.skip (DEBUG): Item skipped (not due, no candidates;
          reason="excluded": its library or subfolder is not included;
          reason="unmatched": its file is in no library; reason="unreachable":
          the media could not be found, so NFO state is unknown;
          reason="no_fields": its library has nothing switched on;
          reason="providers_down": every provider its library needs is
          disabled while another library's still work; scan.complete
          counts these)
        - scan.fields_disabled (DEBUG): An item's fields its library no
          longer manages lost their fingerprint, so they are checked again
          once switched back on
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
        - scan.tvdb_auth (ERROR), scan.fanart_auth (WARNING): TheTVDB or
          fanart.tv rejected the add-on's credentials; that provider is
          disabled for the cycle, the scan continues
        - scan.art_gated (DEBUG): An art field is left alone before any fetch
          (verdict: local, other, changed; see art.art_gate)
        - scan.local_art (DEBUG): A local art file was checked; state is
          exists, missing or unreachable (data/localart.py)
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
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

import xbmc
import xbmcgui

from resources.lib.constants import (
    BROWSE_IDLE_SECONDS,
    DEFAULT_REFETCH_SCHEDULE,
    FALLBACK_RECHECKS,
    KODI_HOME_WINDOW_ID,
    LOCAL_ART_RECHECK_DAYS,
    STOP_SCAN_PROPERTY,
    UPDATE_NOW_IDLE_SECONDS,
    VIDEO_NAV_WINDOW,
    parse_refetch_schedule,
)
from resources.lib.data import kodi
from resources.lib.data.identity import compute_identity
from resources.lib.data.kodi import get_item_by_id
from resources.lib.data.libraries import (
    TITLE_LANGUAGE,
    TITLE_ORIGINAL,
    Library,
    LibraryConfig,
    scan_settings,
)
from resources.lib.data.localart import EXISTS, MISSING, local_art_state
from resources.lib.data.media_types import SEASON, SET, MediaType
from resources.lib.data.nfo import NFO, UNREACHABLE, nfo_state
from resources.lib.data.presets import load_preset
from resources.lib.data.setfolder import folder_for
from resources.lib.data.sources import kodi_ui_language
from resources.lib.data.tracker import (
    REASON_CHANGED_OUTSIDE,
    REASON_FILL_ONLY,
    REASON_FROM_FILE,
    REASON_LOCAL_ART,
    REASON_LOCKED,
    REASON_NFO,
    REASON_NOTHING,
    REASON_OTHER_ART,
    REASON_SET_FOLDER,
    REASON_UNCHANGED,
    REASON_UNCHECKED,
    REASON_UPDATED,
    TrackerDB,
)
from resources.lib.engine.art import (
    ART_FIELDS,
    ENGLISH,
    ENGLISH_SOURCE_SUFFIX,
    FANART_ONLY_FIELDS,
    GATE_CHANGED,
    GATE_LOCAL,
    LOCAL,
    TEXT_ART_FIELDS,
    TMDB_ART_FIELDS,
    art_gate,
    classify,
    is_placeholder_art,
    name_gate,
    unwrap,
)
from resources.lib.engine.artsources import image_language, resolve_art
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
    _fetch_season,
    _fetch_set,
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
from resources.lib.engine.sets import prepare_sets, set_nfo_state
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
    shows and episodes (movies and movie sets ask TMDB only), plus the
    library's title mode for a show's or movie's title (a set's name has no
    title mode); an episode thumb depends on no setting;
    art both sites offer on the art source, the folder language and the
    fallback language, except key art, which has no text and so depends on
    the art source alone; fanart.tv-only art on the two languages; for every
    other field, one TMDB step, the folder language.
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
        if media_type not in ("movie", "set"):
            inputs["text_source_order"] = settings.get("text_source_order", TEXT_FOLLOW_SCRAPER)
            inputs["fallback_order"] = settings.get("fallback_order", FALLBACK_TVDB_FIRST)
        # Only another mode is recorded: titles kept in the library's
        # language keep the fingerprint they were sampled under.
        title_mode = settings.get("title_mode", TITLE_LANGUAGE)
        if (field == "title" and media_type not in ("episode", "set")
                and title_mode != TITLE_LANGUAGE):
            inputs["title_mode"] = title_mode
    elif field == "thumb":
        inputs = {}
    elif field == "keyart":
        inputs = {"art_source": settings.get("art_source", "tmdb")}
    elif field in TMDB_ART_FIELDS:
        inputs = {
            "art_source": settings.get("art_source", "tmdb"),
            "folder_language": folder_language,
            "fallback_language": fallback_language.strip(),
        }
    elif field in FANART_ONLY_FIELDS:
        inputs = {
            "folder_language": folder_language,
            "fallback_language": fallback_language.strip(),
        }
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
        # Items skipped because their library, or the subfolder they are in,
        # is not included; and items whose file is in no library.
        "excluded": 0,
        "unmatched": 0,
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
        # fanart.tv rejected the key this cycle / gave a real answer; the
        # art that needs it waits, so the caller tells the user.
        "fanart_auth_failed": False,
        "fanart_answered": False,
        # Movies the set pass moved out of a duplicate set (engine/sets.py).
        "moved": 0,
        # Movies in no set the set pass added to their collection's set, and
        # the sets it created for that.
        "joined": 0,
        "sets_created": 0,
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
    shows use the title directly; episodes use "ShowTitle S01E02" format and
    seasons "ShowTitle S01".
    """
    if media_type is SEASON:
        return "{showtitle} S{season:02d}".format(
            showtitle=item.get("showtitle", ""), season=item.get("season", 0),
        )
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
    art_fps: dict[str, str] | None = None,
    missing: frozenset[str] = frozenset(),
) -> tuple[dict[str, Any], set[str]]:
    """Split extracted values into (fields to write, fields Kodi already holds).

    Under the maturity model a non-final field is refreshed overwrite-on-diff:
    a differing value overwrites the current one, an identical value is never
    rewritten. On an NFO-managed item, and for a field in ``fill_only``,
    may_write decides with the field's stored provenance; a field it forbids
    is in neither result, so it gets no write and no source. ``art_fps``
    holds field_keep's written_fp of the art fields, which outlives Reset
    tracker: _gate_art and _drop_protected_art already let such a field
    through as MetaMender's own, so it must be writable here too. An art
    field in ``missing`` holds a local file that no longer exists, which
    may_write takes as blank.
    """
    to_write: dict[str, Any] = {}
    held: set[str] = set()
    for f, value in values.items():
        current = item.get(f)
        if current is not None and current == value:
            held.add(f)
            continue
        protected = nfo_managed or f in fill_only
        written = (art_fps or {}).get(f) or fs_map.get(f, {}).get("written_value")
        if not may_write(protected, "" if f in missing else current, written):
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
    english: set[str],
    missing: set[str],
) -> tuple[dict[str, FieldOutcome], dict[str, Any], dict[str, str | None]]:
    """Per-field verdicts for the non-rating fields.

    A field in ``reopened`` runs its chain as if empty, so a fallback step may
    replace its current value (see _reopened_fallbacks). An art field in
    ``english`` may take the English last resort (_english_allowed); one in
    ``missing`` (its local file no longer exists) is picked as if empty.

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
        if f == "title" and ctx.media_type is SET:
            # The collection's name, picked from its translations by
            # _fetch_set; the library's title mode does not apply.
            value = None if tmdb_transient else tmdb_data.get("title") or None
            outcome = FieldOutcome(
                transient=tmdb_transient, value=value,
                from_fallback=bool(value and tmdb_data.get("title_from_fallback")),
            )
            provider = None if value is None else "tmdb"
        elif (f == "title" and ctx.media_type.name != "episode"
                and ctx.title_mode == TITLE_ORIGINAL):
            # The original title is the same whatever language was asked for,
            # so it needs no language chain and no fallback.
            value = None if tmdb_transient else tmdb_data.get("original_title") or None
            outcome = FieldOutcome(transient=tmdb_transient, value=value, from_fallback=False)
            provider = None if value is None else "tmdb"
        elif f in _CHAIN_FIELDS:
            current = None if f in reopened else item.get(f)
            outcome, provider = _text_chain(ctx, text, f, folder_lang, fallback_lang, current)
        elif f in ART_FIELDS:
            current_art = "" if f in missing else str(item.get(f) or "")
            outcome, provider = resolve_art(
                ctx, text, primary, ids, identity, f, folder_lang, fallback_lang,
                current_art, f in english,
            )
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


def _image_languages(language: str, fallback_lang: str) -> tuple[str, ...]:
    """The languages to ask images in: the folder's, then its fallback when
    different, then English for the last resort (textless ones always come
    along)."""
    codes = [image_language(language)]
    if fallback_lang.strip():
        codes.append(image_language(fallback_lang))
    codes.append(ENGLISH)
    return tuple(dict.fromkeys(codes))


def _english_allowed(
    field: str,
    item: dict[str, Any],
    fs: dict[str, Any],
    keep_entry: dict[str, Any],
    missing: set[str],
) -> bool:
    """Whether the English last resort may fill this art slot: it holds no
    art worth keeping (empty, a placeholder, a local file that no longer
    exists), or Kodi still holds MetaMender's own English pick, which may
    then move to a better English image or give way to a higher step.
    English never replaces any other existing art. MetaMender's own is
    recognised by field_keep's written_fp first, which outlives Reset
    tracker, as _gate_art does."""
    if field in missing:
        return True
    current = kodi_form(item.get(field) or "")
    if is_placeholder_art(current):
        return True
    if not str(fs.get("source") or "").endswith(ENGLISH_SOURCE_SUFFIX):
        return False
    written_fp = keep_entry.get("written_fp") or fs.get("written_value")
    return written_fp is not None and fingerprint(current) == written_fp


def _art_reason(
    tracker: TrackerDB, media_type: str, identity: str, field: str,
    fs_map: dict[str, dict[str, Any]], reason: str,
) -> None:
    """Record why an art field is left alone, unless already recorded: a
    gated field is met again on every scan."""
    if (fs_map.get(field) or {}).get("last_reason") != reason:
        tracker.record_field_reason(media_type, identity, field, reason)


def _gate_art(
    tracker: TrackerDB,
    media_type: str,
    identity: str,
    item: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
    decisions: dict[str, str],
    missing: set[str],
    set_folder: str = "",
) -> None:
    """Take the art fields MetaMender may not touch out of ``decisions``
    (art.art_gate) before anything is fetched, and record why. A field in
    ``missing`` holds a local file that no longer exists, fair game.

    The URL Kodi holds at MetaMender's first look is stored as first seen,
    so a poster changed since, and not by MetaMender, is recognised as the
    user's choice and locked for good. A gated field is never sampled, so
    it does not settle into FINAL and is met here on every scan. A FINAL
    field is not looked at: nothing would be fetched for it anyway.

    A movie set's name follows the same first-seen / last-written rule
    (art.name_gate); its name at first look is also a known name of the
    collection, so a set Kodi makes under it later counts as a duplicate.
    """
    gated = [f for f in sorted(ART_FIELDS & decisions.keys()) if decisions[f] != FINAL]
    name = media_type == SET.name and decisions.get("title", FINAL) != FINAL
    if not gated and not name:
        return
    keep = tracker.get_keep(media_type, identity)
    if name:
        _gate_set_name(tracker, identity, item, fs_map, decisions, keep, set_folder)
    for f in gated:
        current = kodi_form(item.get(f) or "")
        current_fp = fingerprint(current)
        first_fp = tracker.get_first_fp(media_type, identity, f)
        if first_fp is None:
            tracker.set_first_fp(media_type, identity, f, current_fp)
        written_fp = ((keep.get(f) or {}).get("written_fp")
                      or (fs_map.get(f) or {}).get("written_value"))
        verdict = art_gate(f, current, current_fp, first_fp, written_fp, f in missing)
        if verdict is None:
            continue
        del decisions[f]
        if verdict == GATE_CHANGED:
            tracker.set_locked(media_type, identity, f, True)
            reason = REASON_CHANGED_OUTSIDE
        else:
            reason = REASON_LOCAL_ART if verdict == GATE_LOCAL else REASON_OTHER_ART
        _art_reason(tracker, media_type, identity, f, fs_map, reason)
        log.debug(
            "Art left as it is", event="scan.art_gated", identity=identity,
            field=f, verdict=verdict,
        )


def _gate_set_name(
    tracker: TrackerDB,
    identity: str,
    item: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
    decisions: dict[str, str],
    keep: dict[str, dict[str, Any]],
    set_folder: str = "",
) -> None:
    """_gate_art's rule for a movie set's name: a name changed outside
    MetaMender since its first look is the user's, locked for good. A name
    that has a subfolder in the movie set information folder is kept too,
    but not locked: the set follows TMDB again once the folder is gone."""
    current = kodi_form(item.get("title") or "")
    current_fp = fingerprint(current)
    first_fp = tracker.get_first_fp(SET.name, identity, "title")
    if first_fp is None:
        tracker.set_first_fp(SET.name, identity, "title", current_fp)
        tracker.add_set_names(identity, [current])
    written_fp = ((keep.get("title") or {}).get("written_fp")
                  or (fs_map.get("title") or {}).get("written_value"))
    if name_gate(current_fp, first_fp, written_fp) is None:
        if current and folder_for(set_folder, [current]) == current:
            del decisions["title"]
            _art_reason(tracker, SET.name, identity, "title", fs_map, REASON_SET_FOLDER)
            log.debug("Set name left as it is", event="scan.art_gated",
                      identity=identity, field="title", verdict=REASON_SET_FOLDER)
        return
    del decisions["title"]
    tracker.set_locked(SET.name, identity, "title", True)
    _art_reason(tracker, SET.name, identity, "title", fs_map, REASON_CHANGED_OUTSIDE)
    log.debug("Set name left as it is", event="scan.art_gated", identity=identity,
              field="title", verdict=GATE_CHANGED)


def _drop_protected_art(
    tracker: TrackerDB,
    media_type: str,
    identity: str,
    item: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
    decisions: dict[str, str],
    protected: frozenset[str],
    reason: str,
    missing: set[str],
) -> None:
    """Take out the ``protected`` art fields (all of them on an NFO item,
    the fill-only ones in a folder without a language) that _plan_writes
    would refuse to write (protect.may_write: neither empty nor a
    placeholder, nor MetaMender's own), so no request is made for them.
    MetaMender's own is recognised as _gate_art does, by field_keep's
    written_fp first, which outlives Reset tracker. A local file that no
    longer exists (``missing``) counts as empty."""
    fields = [f for f in sorted(ART_FIELDS & protected & decisions.keys())
              if decisions[f] != FINAL]
    keep = tracker.get_keep(media_type, identity) if fields else {}
    for f in fields:
        current = "" if f in missing else kodi_form(item.get(f) or "")
        written_fp = ((keep.get(f) or {}).get("written_fp")
                      or (fs_map.get(f) or {}).get("written_value"))
        if may_write(True, current, written_fp):
            continue
        del decisions[f]
        _art_reason(tracker, media_type, identity, f, fs_map, reason)


def _keep_originals(
    tracker: TrackerDB,
    media_type: str,
    identity: str,
    item: dict[str, Any],
    written: set[str],
    fields_to_write: dict[str, Any],
    fs_map: dict[str, dict[str, Any]],
    missing: set[str],
) -> None:
    """Keep the value each written field held before this scan replaced it,
    unless that value was metamender's own (its fingerprint is the one
    metamender last wrote: field_keep's written_fp, which survives Reset
    tracker, else field_status's written_value): then the kept original,
    from before metamender's first write, stays. A scraper's or user's
    value since then replaces it. A field filled from empty keeps "" or []
    by the written value's type, so Restore can clear it. Rating slots get
    no original: the scraper's slots stay beside metamender's. A local file
    that no longer exists (``missing``) is always kept: MetaMender never
    writes a local path, so a matching fingerprint is only the record of an
    earlier refill that found nothing."""
    fields = sorted(written - RATING_FIELDS)
    keep = tracker.get_keep(media_type, identity) if fields else {}
    for f in fields:
        current = kodi_form(item.get(f))
        ours = (keep.get(f) or {}).get("written_fp") or fs_map.get(f, {}).get("written_value")
        if f not in missing and fingerprint(current) == ours:
            continue
        if current is None:
            current = [] if isinstance(fields_to_write.get(f), list) else ""
        tracker.keep_original(media_type, identity, f, current)


def _checked_recently(check: tuple[str, str] | None, path_fp: str, today: str) -> bool:
    """The slot's file was found under this same path within
    LOCAL_ART_RECHECK_DAYS."""
    if check is None or check[0] != path_fp:
        return False
    try:
        age = date.fromisoformat(today) - date.fromisoformat(check[1])
    except (TypeError, ValueError):
        return False
    return age.days < LOCAL_ART_RECHECK_DAYS


def _check_local_art(
    tracker: TrackerDB,
    media_type: str,
    identity: str,
    item: dict[str, Any],
    fields: list[str],
    check_now: bool,
    today: str,
) -> tuple[set[str], set[str]]:
    """Check the local art files of ``fields`` (the ticked, unlocked ones)
    and return (missing, unreachable).

    A file found to exist is checked again LOCAL_ART_RECHECK_DAYS later under
    the same path; ``check_now`` (Update now, a manual scan) ignores that.
    Missing and unreachable answers are not remembered, so they are asked
    again next scan. Web links are never checked. None of this touches a
    field's clock: a file on disk is not a provider answer.

    A set has no video of its own (its ``file`` only stands for its library),
    so its art is judged by the art's folder alone.
    """
    missing: set[str] = set()
    unreachable: set[str] = set()
    media_path = "" if media_type == SET.name else str(item.get("file") or "")
    for f in sorted(ART_FIELDS.intersection(fields)):
        current = kodi_form(item.get(f) or "")
        path = unwrap(current)
        if classify(path) != LOCAL:
            continue
        path_fp = fingerprint(current)
        if not check_now and _checked_recently(
                tracker.get_art_check(media_type, identity, f), path_fp, today):
            continue
        state = local_art_state(path, media_path)
        log.debug("Local art checked", event="scan.local_art", state=state, field=f,
                  identity=identity)
        if state == EXISTS:
            tracker.set_art_check(media_type, identity, f, path_fp, today)
        elif state == MISSING:
            missing.add(f)
        else:
            unreachable.add(f)
    return missing, unreachable


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


def _stop_requested() -> bool:
    """The user chose Stop scan (service/stopscan.py sets the property)."""
    return xbmcgui.Window(KODI_HOME_WINDOW_ID).getProperty(STOP_SCAN_PROPERTY) == "1"


def _browsing(idle_seconds: int) -> bool:
    # The idle time comes first: it is lock-free, while getCurrentWindowId
    # takes Kodi's graphics lock and so waits out a list reload.
    return (xbmc.getGlobalIdleTime() < idle_seconds
            and xbmcgui.getCurrentWindowId() == VIDEO_NAV_WINDOW)


def _hold_while_browsing(media_type: MediaType, monitor: Any,
                         idle_seconds: int = BROWSE_IDLE_SECONDS) -> None:
    """Hold the next Kodi write while the user is browsing the video library.

    Kodi reloads the active window's list after every JSON-RPC library write,
    so writing while the Videos window is in use keeps the list the user is
    looking at reloading. The hold ends when the user has been idle for
    ``idle_seconds``, leaves the Videos window, or Kodi quits. A background
    scan waits BROWSE_IDLE_SECONDS; Update now only UPDATE_NOW_IDLE_SECONDS,
    long enough for the next key press to reach its progress window.
    """
    if monitor is None or not _browsing(idle_seconds):
        return
    started = time.monotonic()
    while (_browsing(idle_seconds) and not monitor.abortRequested()
           and not _stop_requested()):
        if monitor.waitForAbort(2):
            break
    log.debug(
        "Write held while browsing",
        event="scan.browse_hold", media_type=media_type.name,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def _set_pass_stop(
    monitor: Any, reset: bool, stats: dict[str, Any],
) -> Callable[[], bool]:
    """The check sets.prepare_sets runs between TMDB lookups: True on
    shutdown or Stop scan (recorded in ``stats`` as the scan loop does).
    Update now (``reset``) ignores Stop scan. A lookup writes nothing to the
    library, so it does not hold while the user browses."""
    def stop() -> bool:
        if monitor is not None and monitor.abortRequested():
            log.info("Scan interrupted by shutdown", event="scan.abort",
                     media_type=SET.name, processed=0)
            stats["aborted"] = True
            return True
        if not reset and _stop_requested():
            log.info("Scan stopped by the user", event="scan.stopped",
                     media_type=SET.name, processed=0)
            stats["stopped"] = True
            stats["aborted"] = True
            return True
        return False
    return stop


def _before_set_move(
    monitor: Any, reset: bool, stats: dict[str, Any],
) -> Callable[[], bool]:
    """The check sets.prepare_sets runs before moving a movie between sets
    or into one: False on shutdown or Stop scan (_set_pass_stop), otherwise
    it holds while the user browses the video library. A move rewrites the
    library like any scan write. Update now (``reset``) holds only while
    keys are pressed."""
    stop = _set_pass_stop(monitor, reset, stats)

    def check() -> bool:
        # The hold ends on shutdown and on Stop scan too, so both are
        # checked after it.
        _hold_while_browsing(
            SET, monitor, UPDATE_NOW_IDLE_SECONDS if reset else BROWSE_IDLE_SECONDS)
        return not stop()
    return check


def _cert_config(
    media_type: MediaType,
    enabled_fields: frozenset[str],
    settings: dict[str, Any],
    breaker: CircuitBreaker,
    monitor: Any,
    gate: SiteGate | None,
) -> _CertConfig | None:
    """A library's certification settings, or None when certifications are
    off for it. A configured country without a usable preset turns them off
    for the library's items with one ERROR, rather than writing ratings from
    a wrong system."""
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
    or movie's as "main_title", since they have separate toggles. A set's
    name and plot come with the Movie sets tick alone, its art with that tick
    and the art's own."""
    if media_type is SET:
        if "movie_set" not in enabled_fields:
            return []
        return sorted({"plot", "title"} | (enabled_fields & SET.backfill_fields & ART_FIELDS))
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
    new title would make it a new tracker item. A set's identity is its
    collection, which a new name does not change."""
    if media_type.name in ("episode", "set") or identity.startswith(("tmdb:", "imdb:")):
        return candidates
    return [f for f in candidates if f != "title"]


def _needed_providers(media_type: MediaType, candidates: list[str]) -> list[str]:
    """Providers the pass can still make progress with. TMDB always; TVDB
    when a show or episode text field it supplies is managed. The IMDb store
    has no breaker, so it never stops a pass. A movie set's text comes from
    TMDB alone."""
    needed = ["tmdb"]
    if media_type.name not in ("movie", "set") and _CHAIN_FIELDS & set(candidates):
        needed.append("tvdb")
    return needed


def _tracker_identity(
    tracker: TrackerDB, media_type: MediaType, item: dict[str, Any], kodi_id: Any,
    show_id_map: dict[int, str] | None = None,
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
    names another item, and this item takes the row over. Kodi gives a
    season no ids, so the holder season gets its show's TMDB id from
    ``show_id_map``, as the listing did for this one.
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
    if other and media_type is SEASON:
        other["show_tmdb_id"] = (show_id_map or {}).get(int(other.get("tvshowid", -1)))
    if other and compute_identity(other, media_type) == identity:
        log.debug(
            "Duplicate identity, item tracked under its file",
            event="scan.duplicate_identity", identity=identity,
            kodi_id=kodi_id, holder=holder,
        )
        return own
    return identity


def scans_seasons(libraries: LibraryConfig) -> bool:
    """Whether an included library manages a season field (the poster). The
    callers skip the season pass otherwise, and with it the season listing."""
    return any(
        lib.included and candidate_fields(SEASON, lib.fields())
        for lib in libraries.libraries
    )


def scans_sets(libraries: LibraryConfig) -> bool:
    """Whether an included library has Movie sets ticked. The callers skip
    the set pass otherwise, and with it the set and member listings."""
    return any(
        lib.included and candidate_fields(SET, lib.fields())
        for lib in libraries.libraries
    )


def manages_art(media_type: MediaType, libraries: LibraryConfig) -> bool:
    """Whether an included library manages an art field of the media type.
    Only then does the pass's listing ask Kodi for the art map, which is
    the bulk of a large episode listing."""
    return any(
        lib.included and ART_FIELDS & set(candidate_fields(media_type, lib.fields()))
        for lib in libraries.libraries
    )


def _season_items(
    tracker: TrackerDB, show_id_map: dict[int, str], new_only: bool,
) -> list[dict[str, Any]]:
    """The library's seasons with their show's folder and ids
    (kodi.get_seasons_for_scan); with ``new_only`` those whose Kodi id the
    tracker does not know yet."""
    items = kodi.get_seasons_for_scan(show_id_map, show_tvdb_map=tracker.get_show_tvdb_map())
    if new_only:
        known = tracker.known_kodi_ids(SEASON.name)
        items = [i for i in items if i.get(SEASON.kodi_id_field) not in known]
    return items


def _new_items(
    tracker: TrackerDB, media_type: MediaType, art: bool,
) -> list[dict[str, Any]]:
    """The library's items whose Kodi id the tracker does not know yet, with
    full details (the art map only with ``art``). An id listed but gone by
    the details call is skipped."""
    known = tracker.known_kodi_ids(media_type.name)
    listed = kodi.get_all_items(media_type, ids_only=True)
    fresh = [
        i[media_type.kodi_id_field] for i in listed
        if i.get(media_type.kodi_id_field) not in known
    ]
    items = [d for d in (get_item_by_id(media_type, i, art=art) for i in fresh) if d]
    log.info(
        "New library items selected", event="scan.new_items",
        media_type=media_type.name, listed=len(listed), new=len(items),
    )
    return items


@dataclass(frozen=True)
class _LibraryPass:
    """One library's share of a pass: its ctx, its settings as the engine
    reads them, the fields it manages and the providers those need."""

    ctx: _ScanCtx
    settings: dict[str, Any]
    candidates: list[str]
    needed: list[str]


def _library_pass(
    base: _ScanCtx,
    lib: Library,
    settings: dict[str, Any],
    ui_language: str,
    monitor: Any,
    gate: SiteGate,
) -> _LibraryPass:
    """The ctx and fields for the items of ``lib``, derived from the pass's
    base ctx so caches, pacing and the breaker stay shared."""
    lib_settings = scan_settings(lib, settings, ui_language)
    fields = lib.fields()
    ctx = replace(
        base,
        enabled_fields=fields,
        rating_pref=lib_settings["rating_source"],
        text_order=lib_settings["text_source_order"],
        fallback_order=lib_settings["fallback_order"],
        cert=_cert_config(base.media_type, fields, lib_settings, base.breaker, monitor, gate),
        title_mode=lib.title_mode,
        art_source=lib_settings["art_source"],
    )
    candidates = candidate_fields(base.media_type, fields)
    if ctx.cert is not None:
        candidates = sorted(set(candidates) | {"mpaa"})
    return _LibraryPass(ctx, lib_settings, candidates,
                        _needed_providers(base.media_type, candidates))


def _pass_providers(
    media_type: MediaType,
    libraries: LibraryConfig,
    items: list[dict[str, Any]],
    reset: bool,
) -> list[str]:
    """Providers the pass as a whole can still make progress with: those of
    every library with items to scan (included, or any on Update now) and
    fields switched on. The pass stops only when all of them are down."""
    seen: dict[str, Library] = {}
    for item in items:
        lib = libraries.for_file(item.get("file", ""))
        if lib is not None and (lib.included or reset):
            seen[lib.path] = lib
    needed: set[str] = set()
    for lib in seen.values():
        candidates = candidate_fields(media_type, lib.fields())
        if candidates or "mpaa" in lib.fields():
            needed.update(_needed_providers(media_type, candidates))
    return sorted(needed)


def run_scan(
    media_type: MediaType,
    tracker: TrackerDB,
    libraries: LibraryConfig,
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
    fanart_cache: dict[tuple[str, str], Any] | None = None,
    show_cache: dict[str, Any] | None = None,
    only_set: int | None = None,
) -> dict[str, int]:
    """Run a single scan cycle for one media type.

    Queries Kodi for all items (or uses a pre-built list), computes a per-field
    maturity decision for each, fetches metadata when any field is due,
    refreshes non-final fields overwrite-on-diff, and records the per-field
    sampling facts in the tracker.

    Args:
        media_type: MOVIE, TVSHOW, SEASON or EPISODE. A season is scanned
            in its show's library, with its show's ids (identity
            ``tmdb:<show>/Snn``) and its show's tvshow.nfo; its content age
            is its TMDB air date, kept in the tracker once fetched. A movie
            set is scanned in the library most of its movies are in, keyed
            on its TMDB collection (``collection:<id>``); its NFO state is
            its movies', its content age its newest movie's
            (engine/sets.py).
        tracker: Open TrackerDB instance.
        libraries: The libraries. Each item is scanned with the fields and
            options of the library its file is in (an episode by its own
            file); an item in no library is skipped (stats["unmatched"]).
        tmdb_api_key: TMDB API key.
        settings: The general settings: stale_threshold_days, rate_limit,
            cert_sites, optionally refetch_schedule, plus imdb_ready
            (whether the IMDb ratings store is loaded this cycle; an IMDb
            rating is transient while it is False), ui_language (Kodi's
            interface language; read from Kodi when absent) and optionally
            check_local_art_now (the manual scan: check every local art
            file now instead of weekly; Update now always does).
        monitor: xbmc.Monitor instance (has abortRequested()), or
            None for tests.
        show_id_map: Dict mapping a show's Kodi id to its show-level TMDB ID.
            Required for season and episode scans so their TMDB calls use the
            show ID. The show TVDB ids come from the tracker.
        items: Pre-built list of Kodi items to process. When provided,
            skips the Kodi library query. Useful for targeted scans
            (single item, folder, season) and testing.
        breaker: Shared CircuitBreaker for this scan cycle. The daemon
            creates one per cycle and passes the same instance into each
            media-type pass so a provider that fails repeatedly stays
            disabled across passes. When None, a fresh per-call breaker
            is created (single-pass / test convenience).
        reset: The "Update now" path. When True every candidate field is
            treated as due regardless of recorded maturity, the inclusion
            gate (library and subfolder) and the playback yield are skipped
            (so the action always runs; the caller decides whether it may),
            and a field with history keeps its clock: only what was written
            is recorded (record_manual_check). A field without history gets
            a normal first sample.
        new_only: Library-event scan: process only the items whose Kodi id
            the tracker does not hold for this type. Kodi's dateadded is the
            file's date, not when the item entered the library, so it cannot
            pick out new items. A re-scraped item gets a new Kodi id and is
            included.
        progress: Called before each item with its index, the item and the
            live stats dict. Returning False stops the pass before that item
            (stats["stopped"]); an item is never stopped half-way.
        fanart_cache, show_cache: fanart.tv answers and TMDB show records
            already fetched. A caller running several passes in one cycle
            passes the same dicts to each, like ``breaker``, so the show
            pass and the season pass ask once per show (fanart.tv's terms
            allow one call per show). A fresh dict each when None.
        only_set: Update now on a movie set: the set pass merges and scans
            only the collection of this Kodi setid (sets.prepare_sets).

    Returns:
        Stats dict with processed, skipped, updated, errors, excluded,
        unmatched and per-field counts.
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
    ui_language = str(settings.get("ui_language") or kodi_ui_language())
    # One gate for every library: its request cap and memo are per cycle.
    gate = cert_gate or SiteGate(frozenset(settings.get("cert_sites") or ()), breaker, monitor)
    shared = _ScanCtx(
        media_type=media_type,
        tracker=tracker,
        breaker=breaker,
        pacer=_Pacer(settings.get("rate_limit", 0.25)),
        tmdb_api_key=tmdb_api_key,
        enabled_fields=frozenset(),
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
        rating_pref=FOLLOW_SCRAPER,
        text_order=TEXT_FOLLOW_SCRAPER,
        fallback_order=FALLBACK_TVDB_FIRST,
        imdb_ready=bool(settings.get("imdb_ready", False)),
        reset=reset,
        tracked_shows=(
            tracker.get_tracked_show_ids()
            if media_type.name == "episode" else frozenset()
        ),
        fanart_client_key=str(settings.get("fanart_client_key") or ""),
        fanart_cache={} if fanart_cache is None else fanart_cache,
        show_cache={} if show_cache is None else show_cache,
        set_folder=kodi.movie_set_folder() if media_type is SET else "",
    )
    # Built on a library's first item, so a library the pass never meets
    # costs nothing (and logs no certification error).
    passes: dict[str, _LibraryPass] = {}

    log.info(
        "Scan starting",
        event="scan.start",
        media_type=media_type.name,
        reset=reset,
    )

    # A stop requested before this pass (the previous pass ended on it, or it
    # arrived between passes) ends it before Kodi is asked for its item list,
    # which on a large library takes seconds. Update now ignores the stop.
    if not reset and _stop_requested():
        log.info(
            "Scan stopped by the user",
            event="scan.stopped",
            media_type=media_type.name,
            processed=0,
        )
        stats["stopped"] = True
        stats["aborted"] = True
        return stats

    if items is None and media_type is SEASON:
        items = _season_items(tracker, shared.show_id_map, new_only)
    elif items is None and media_type is SET:
        items = prepare_sets(shared, libraries, new_only, only_set, stats,
                             _before_set_move(monitor, reset, stats),
                             _set_pass_stop(monitor, reset, stats))
    elif items is None:
        art = manages_art(media_type, libraries)
        items = (
            _new_items(tracker, media_type, art) if new_only
            else kodi.get_all_items(media_type, art=art)
        )
    needed = _pass_providers(media_type, libraries, items, reset)

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

        # Stop scan from the context menu: the pass ends before this item and,
        # like a shutdown, leaves the cycle open so the next scan resumes here.
        # Update now (reset) is the user's own action and ignores it.
        if not reset and _stop_requested():
            log.info(
                "Scan stopped by the user",
                event="scan.stopped",
                media_type=media_type.name,
                processed=stats["processed"],
            )
            stats["stopped"] = True
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
            _yield_to_playback(shared, monitor, stats["processed"])

        title = _item_title(item, media_type)
        file_path = item.get("file", "")
        # An item in no library has no settings to scan it with, on Update
        # now too; it is not tracked, so it leaves no trace.
        lib = libraries.for_file(file_path)
        if lib is None:
            log.debug(
                "Skipping item in no library",
                event="scan.skip", reason="unmatched", title=title,
                media_type=media_type.name, file_path=file_path,
            )
            stats["skipped"] += 1
            stats["unmatched"] += 1
            continue
        included_here, folder_language, fallback_lang = libraries.folder_settings(
            file_path, lib)
        fallback_lang = fallback_lang.strip()

        # A season is keyed on its show's TMDB id, so without one it has no
        # identity; it is picked up once its show is resolved.
        if media_type is SEASON and not compute_identity(item, media_type):
            log.debug(
                "Skipping season of a show without a TMDB id",
                event="scan.season_no_show_id", title=title,
                tvshowid=item.get("tvshowid"),
            )
            stats["skipped"] += 1
            continue

        kodi_id = item.get(media_type.kodi_id_field, 0)
        # One managed set per collection: its row follows whichever Kodi
        # set prepare_sets chose.
        identity = (
            compute_identity(item, media_type) if media_type is SET
            else _tracker_identity(tracker, media_type, item, kodi_id, shared.show_id_map)
        )
        if media_type is SEASON and not item.get(media_type.date_field):
            # Kodi has no date on a season: its TMDB air date, once a fetch
            # found it, is kept as the row's premiered.
            known = tracker.get_item(media_type.name, identity) or {}
            item[media_type.date_field] = known.get("premiered") or ""

        # A library or subfolder that is not included is skipped, but its
        # items count as present, so orphan pruning keeps their history for
        # when it is included again. Update now bypasses the gate: whether
        # it may run there is the caller's call.
        if not reset and not (lib.included and included_here):
            log.debug(
                "Skipping item outside the included libraries",
                event="scan.skip", reason="excluded", title=title,
                media_type=media_type.name, library=lib.path,
            )
            tracker.update_last_seen(media_type.name, identity, date.today().isoformat())
            stats["skipped"] += 1
            stats["excluded"] += 1
            continue

        # Resume: skip items already processed in this cycle. The reset path
        # (Update now) bypasses this so a just-scanned item can still be
        # corrected on demand.
        if not reset:
            pre_tracker = tracker.get_item(media_type.name, identity)
            if pre_tracker and pre_tracker.get("cycle_processed"):
                stats["skipped"] += 1
                continue

        lib_pass = passes.get(lib.path)
        if lib_pass is None:
            lib_pass = _library_pass(shared, lib, settings, ui_language, monitor, gate)
            passes[lib.path] = lib_pass
        ctx = lib_pass.ctx
        candidates = lib_pass.candidates

        # A library with nothing switched on has nothing to fetch: no id
        # lookups, no new tracker row. A row it already has stays present
        # for orphan pruning and drops the fingerprints of its old fields.
        if not candidates:
            log.debug(
                "Skipping item in a library with no fields",
                event="scan.skip", reason="no_fields", title=title,
                media_type=media_type.name, library=lib.path,
            )
            tracker.forget_item_fields(media_type.name, identity, candidates)
            tracker.update_last_seen(media_type.name, identity, date.today().isoformat())
            stats["skipped"] += 1
            continue

        # A folder without a configured language is fetched in Kodi's
        # interface language, a guess, so its text and its art with text
        # only fill empty fields. Key art has no text, so it is not held back.
        language = folder_language or ui_language
        fill_only = frozenset() if folder_language else LANGUAGE_FIELDS.union(TEXT_ART_FIELDS)
        if fill_only and "language_unconfigured" not in ctx.logged_once:
            ctx.logged_once.add("language_unconfigured")
            log.info(
                "Folder without a configured language: text fills empty fields only",
                event="scan.language_unconfigured", language=language,
                media_type=media_type.name, source_path=file_path,
            )

        # Extract external IDs; a season has its show's, a set its
        # collection's TMDB id.
        if media_type is SEASON:
            kodi_ids = (item.get("show_tmdb_id"), None, item.get("show_tvdb_id"), None)
        elif media_type is SET:
            kodi_ids = (item.get("collection_id"), None, None, None)
        else:
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
        forgotten = tracker.forget_item_fields(media_type.name, identity, candidates)
        if forgotten:
            log.debug("Disabled fields will be checked again when enabled",
                      event="scan.fields_disabled", media_type=media_type.name,
                      identity=identity, rows=forgotten)
        stored = tracker.get_item(media_type.name, identity) or {}

        # --- Per-field maturity decisions (see maturity.decide_field) ---
        today = date.today().isoformat()
        age = content_age_days(item, media_type, today)
        fs_map = tracker.get_field_status_map(media_type.name, identity)
        threshold = settings.get("stale_threshold_days", 365)

        fields = item_fields(candidates, media_type, identity)
        # A locked field is the user's: never fetched, written or sampled,
        # on Update now and after a settings change too. Its reason is
        # recorded each scan it would have been considered, except art the
        # scan itself locked: "changed outside MetaMender" says more.
        locked = (tracker.locked_fields(media_type.name, identity) - RATING_FIELDS) & set(fields)
        if locked:
            fields = [f for f in fields if f not in locked]
            for f in sorted(locked):
                if (fs_map.get(f) or {}).get("last_reason") != REASON_CHANGED_OUTSIDE:
                    tracker.record_field_reason(media_type.name, identity, f, REASON_LOCKED)
        # A field sampled under other settings (or before fingerprints were
        # stored) is re-checked as if never sampled, and re-baselined once it
        # answers. A transient keeps the old fingerprint, so it stays due.
        fps = {
            f: settings_fingerprint(f, lib_pass.settings, language, media_type.name,
                                    fallback_lang)
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

        # A local art file that no longer exists is fair game like a broken
        # link; one whose share does not answer waits, untouched and
        # unsampled. A FINAL field gets one refill for a missing file, like
        # a blanked one; a refill that found nothing recorded the dead path
        # as written, so that field is not checked (or fetched) again.
        art_check = [
            f for f in fields if f in ART_FIELDS and not (
                decisions[f] == FINAL
                and (fs_map.get(f) or {}).get("written_value")
                == fingerprint(kodi_form(item.get(f) or ""))
            )
        ]
        missing, unreachable = _check_local_art(
            tracker, media_type.name, identity, item, art_check,
            reset or bool(settings.get("check_local_art_now")), today,
        )
        for f in sorted(missing):
            if decisions[f] == FINAL:
                decisions[f] = FETCH_NOW
                refills.add(f)
        for f in sorted(unreachable):
            if decisions[f] != FINAL:
                del decisions[f]
                stats["transient"] += 1
                _art_reason(tracker, media_type.name, identity, f, fs_map, REASON_UNCHECKED)

        _gate_art(tracker, media_type.name, identity, item, fs_map, decisions, missing,
                  ctx.set_folder)
        _drop_protected_art(tracker, media_type.name, identity, item, fs_map, decisions,
                            fill_only, REASON_FILL_ONLY, missing)
        due = any(d == FETCH_NOW for d in decisions.values())

        # NFO detection touches the share, so it runs once, and only for an
        # item with a field to process. Unreachable media (a sleeping or
        # offline share) says nothing about the NFO: the item is left exactly
        # as it is, ids_checked and cycle flag included, and retried later.
        nfo_managed = False
        if due:
            # A season has no NFO of its own: its show's tvshow.nfo governs
            # it. Nor has a set: it is NFO-managed when all its movies are.
            if media_type is SET:
                state = set_nfo_state(tuple(item.get("member_files") or ()))
            else:
                nfo_kind = "tvshow" if media_type is SEASON else media_type.name
                state = nfo_state(nfo_kind, item.get("file", ""))
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
            if nfo_managed:
                _drop_protected_art(tracker, media_type.name, identity, item, fs_map,
                                    decisions, ART_FIELDS, REASON_NFO, missing)
                due = any(d == FETCH_NOW for d in decisions.values())

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
        # Another library of the pass can still make progress: this item
        # waits for its providers, with nothing recorded.
        if breaker.all_disabled(lib_pass.needed):
            log.debug(
                "Providers of this library are disabled, skipping item",
                event="scan.skip", reason="providers_down", title=title,
                media_type=media_type.name, providers=lib_pass.needed,
            )
            stats["skipped"] += 1
            stats["transient"] += 1
            continue

        # Non-final fields are refreshed (overwrite-on-diff); final ones are not.
        nonfinal = [f for f, d in decisions.items() if d != FINAL]
        if TMDB_ART_FIELDS.intersection(nonfinal):
            # The primary fetch brings TMDB's posters, backdrops and logos
            # along; fanart.tv-only art does not need them.
            ctx = replace(ctx, image_languages=_image_languages(language, fallback_lang))
        tmdb_lang = tmdb_language(language)
        fetch_primary = {
            "episode": _fetch_episode, "season": _fetch_season,
        }.get(media_type.name, _fetch_movie_or_show)
        if media_type is SET:
            primary = _fetch_set(ctx, item, kodi_id, title, identity, ids, tmdb_lang,
                                 fallback_lang)
        else:
            primary = fetch_primary(ctx, item, kodi_id, title, identity, ids, tmdb_lang)
        if media_type is SEASON:
            # The fetch may have found the season's first air date.
            age = content_age_days(item, media_type, today)

        reopened = _reopened_fallbacks(item, fs_map, rebaseline)
        art_due = sorted(ART_FIELDS.intersection(nonfinal))
        due_keep = tracker.get_keep(media_type.name, identity) if art_due else {}
        english = {
            f for f in art_due
            if _english_allowed(f, item, fs_map.get(f) or {}, due_keep.get(f) or {}, missing)
        }
        outcomes, values, providers = _resolve_fields(
            ctx, item, identity, primary, ids, language, fallback_lang, nonfinal,
            reopened, english, missing,
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
        art_keep = (
            tracker.get_keep(media_type.name, identity)
            if ART_FIELDS & extracted.keys() else {}
        )
        fields_to_write, held = _plan_writes(
            extracted, item, nfo_managed, fs_map, identity, fill_only,
            {f: k["written_fp"] for f, k in art_keep.items()
             if f in ART_FIELDS and k.get("written_fp")},
            frozenset(missing),
        )
        stats["protected"] += len(extracted) - len(fields_to_write) - len(held)
        # Kodi shows a video file's own length over the library's runtime, so
        # a runtime written there would never be seen. The listing carries
        # the library's value only, so the file is looked up before a write.
        from_file: set[str] = set()
        if "runtime" in fields_to_write and kodi.file_runtime(media_type, kodi_id):
            del fields_to_write["runtime"]
            from_file.add("runtime")
            log.debug("Runtime left to the video file's length",
                      event="scan.runtime_from_file", identity=identity)

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

        # Update now is the user's own request, so it only holds while keys
        # are being pressed.
        if fields_to_write:
            _hold_while_browsing(
                media_type, monitor,
                UPDATE_NOW_IDLE_SECONDS if reset else BROWSE_IDLE_SECONDS)
        written = _write_fields(
            ctx, kodi_id, title, identity, fields_to_write, stats,
        )
        if media_type is SET and "title" in written:
            # Kodi's scraper may still file a movie under this name later.
            tracker.add_set_names(identity, [str(fields_to_write["title"])])
        _keep_originals(
            tracker, media_type.name, identity, item, written, fields_to_write, fs_map,
            missing,
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
            reason = REASON_FROM_FILE if f in from_file else _field_reason(
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

    # The last items' last_seen stamps, when they were skipped as excluded.
    tracker.commit()
    stats["tvdb_auth_failed"] = "tvdb" in breaker.auth_rejected()
    stats["tmdb_answered"] = breaker.answered("tmdb")
    stats["tvdb_answered"] = breaker.answered("tvdb")
    stats["fanart_auth_failed"] = "fanart" in breaker.auth_rejected()
    stats["fanart_answered"] = breaker.answered("fanart")
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
        excluded=stats["excluded"],
        unmatched=stats["unmatched"],
        unknown_ids_accepted=shared.counts["unknown_ids_accepted"],
        episodes_found_by_tvdb=shared.counts["episodes_found_by_tvdb"],
        disabled=breaker.disabled(),
        duration_ms=int((time.perf_counter() - scan_start) * 1000),
    )

    return stats
