"""Shared state and helpers for one scan pass: field names, the scan
context, provider pacing and calls, and item id extraction.

Logs under the 'scan' logger; the events are listed in engine/scan.py.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from resources.lib.constants import (
    PROVIDER_CIRCUIT_BREAKER_THRESHOLD,
)
from resources.lib.data.media_types import MediaType
from resources.lib.data.presets import Preset
from resources.lib.data.tracker import TrackerDB
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.certchain import (
    SiteGate,
)
from resources.lib.engine.chain import TRANSIENT
from resources.lib.engine.protect import fingerprint, is_blank
from resources.lib.providers import tmdb
from resources.lib.utils import (
    ApiKeyError,
    TransientProviderError,
    TvdbAuthError,
    get_logger,
)

log = get_logger('scan')

# Mapping from TMDB response keys to Kodi field names.
# "mpaa" is intentionally absent: Phase 8 handles certifications.
_TMDB_TO_KODI = {
    "rating": "rating",
    "votes": "votes",
    "plot": "plot",
    "tagline": "tagline",
    "directors": "director",
    "writers": "writer",
    "genres": "genre",
    "studios": "studio",
    "countries": "country",
    "trailer": "trailer",
    "runtime": "runtime",
    "firstaired": "firstaired",
    "title": "title",
}

_KODI_TO_TMDB = {v: k for k, v in _TMDB_TO_KODI.items()}

# Text fields TVDB also supplies. Only these get the full provider chain with
# fallback-language steps; every other field has a single TMDB step.
_CHAIN_FIELDS = frozenset({"title", "plot"})
RATING_FIELDS = frozenset({"rating", "votes"})

# Fields whose value is written in a language. In a folder with no configured
# language they only fill an empty value (see _plan_writes): the language is a
# guess, and replacing a library's text with another language's is what the
# guess must never do.
LANGUAGE_FIELDS = frozenset({"title", "plot", "tagline", "genre"})
# Key holding each chained field in a TVDB series record.
_TVDB_SERIES_KEYS = {"title": "name", "plot": "overview"}

_EPISODEGUIDE_TAG = re.compile(r"</?episodeguide>")

# text_source_order / fallback_order setting values (settings.xml).
TEXT_TMDB_FIRST = 0
TEXT_TVDB_FIRST = 1
# Per item, the provider whose scraper made it first (_scraper_provider);
# TMDB first when that cannot be told.
TEXT_FOLLOW_SCRAPER = 2
FALLBACK_TVDB_FIRST = 0
FALLBACK_TMDB_FIRST = 1


# ASCII only: \d and str.isdigit also accept other scripts' digits, which
# no provider uses in an id ("²" would even make int() raise).
_IMDB_ID = re.compile(r"tt[0-9]+")
# No provider id comes near 12 digits. The check avoids int(), which raises
# on very long digit strings from Python 3.11 on.
_NUMERIC_ID = re.compile(r"[0-9]{1,12}")


def _clean_id(raw: Any, imdb: bool = False) -> str | None:
    """A uniqueid value as an id, or None when it cannot be one.

    Scrapers leave values such as "", "None" and "0" behind. Ids are stored
    for good once found, so such a value would be sent to the providers and
    kept in the tracker forever: TMDB and TVDB ids must be positive integers,
    an IMDb id must be "tt" and digits.
    """
    if raw is None or isinstance(raw, bool):
        return None
    value = str(raw).strip()
    if imdb:
        return value if _IMDB_ID.fullmatch(value) else None
    return value if _NUMERIC_ID.fullmatch(value) and value.strip("0") else None


def extract_ids(
    item: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract (tmdb_id, imdb_id, tvdb_id, unknown_id) from a Kodi item's
    uniqueid dict, dropping values that cannot be an id (_clean_id).
    ``unknown_id`` is an id of type `unknown`, a TVDB id candidate that is
    only used once verified."""
    uid = item.get("uniqueid") or {}
    return (
        _clean_id(uid.get("tmdb")) or _clean_id(uid.get("themoviedb")),
        _clean_id(uid.get("imdb"), imdb=True),
        _clean_id(uid.get("tvdb")) or _clean_id(uid.get("thetvdb")),
        _clean_id(uid.get("unknown")),
    )


# Kodi's separator for list fields (advancedsettings itemseparator default).
# Lists are stored joined with it and split on it when read back.
_KODI_ITEM_SEPARATOR = " / "


def kodi_form(value: Any) -> Any:
    """A provider value as Kodi will store and return it.

    Kodi's CVideoInfoTag setters trim text and drop empty list entries, and a
    list comes back split on the item separator. Writing and fingerprinting
    this form keeps the same-value skip and the provenance check matching what
    Kodi reports on the next scan; the raw provider value would differ by
    whitespace and never match again.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[Any] = []
        for entry in value:
            if not isinstance(entry, str):
                parts.append(entry)
                continue
            for piece in entry.split(_KODI_ITEM_SEPARATOR):
                piece = piece.strip()
                if piece:
                    parts.append(piece)
        return parts
    return value


def holds_written_value(
    field: str, current: Any, fs: dict[str, Any], keep_entry: dict[str, Any],
) -> bool:
    """Kodi still holds the value metamender last wrote to the field.

    ``keep_entry`` is the field's get_keep() entry: its written_fp survives
    Reset tracker, so field_status's written_value is only the fallback. A
    rating row's written value is the JSON of the slots metamender owns,
    beside the scraper's own slots, so any recorded write counts. A blank
    value (empty or a placeholder, as scan.blanked sees it) never does: a
    refill that found nothing records the blank as written so the same
    blank does not trigger it again, but metamender never writes a blank.
    """
    if field in RATING_FIELDS:
        return bool(fs.get("written_value"))
    form = kodi_form(current)
    if is_blank(form):
        return False
    written = keep_entry.get("written_fp") or fs.get("written_value")
    return written is not None and fingerprint(form) == written


class _Pacer:
    """Rate-limit pacing for provider calls.

    Sleeps ``rate_limit`` seconds before a call, but only once "armed", so the
    first call in a scan is not delayed and subsequent ones are spaced out.
    """

    def __init__(self, rate_limit: float) -> None:
        self._rate = rate_limit
        self._armed = False

    def wait(self) -> None:
        """Sleep before this call if armed, then arm for the next one."""
        if self._armed and self._rate > 0:
            time.sleep(self._rate)
        self._armed = True

    def arm(self) -> None:
        """Arm without sleeping (a call happened without going through wait())."""
        self._armed = True


@dataclass(frozen=True)
class _CertConfig:
    """What the certification producer needs for one pass."""

    preset: Preset
    prefix: str
    replace_foreign: bool
    not_found: str | None
    gate: SiteGate


@dataclass(frozen=True)
class _ScanCtx:
    """Scan-level constants shared across one run_scan cycle.

    Holds everything that does not vary per item, so the per-item helpers take a
    single ``ctx`` plus the handful of per-item values. Mutable members
    (breaker, pacer, caches, tracker) are referenced, not copied.
    """

    media_type: MediaType
    tracker: TrackerDB
    breaker: CircuitBreaker
    pacer: _Pacer
    tmdb_api_key: str
    default_language: str
    # Whether sources.json set default_language; without it a folder no
    # source entry covers has no configured language.
    default_language_set: bool
    sources: list[dict[str, Any]]
    enabled_fields: frozenset[str]
    show_id_map: dict[int, str]
    show_tvdb_map: dict[int, str]
    # Kodi ids of the shows whose id lookups have answered (see
    # TrackerDB.get_checked_show_ids); episode passes only.
    checked_shows: frozenset[int]
    season_cache: dict[str, list[dict[str, Any]] | None]
    # (kind, tvdb_id, tvdb_lang) -> fetched record. Only real answers are
    # cached, so a transient failure is retried by the next item.
    tvdb_cache: dict[tuple[str, str, str], Any]
    # Events already logged in full this scan, so a persistent failure does
    # not repeat its traceback for every item.
    logged_once: set[str]
    # Per-item outcomes logged at DEBUG, summed for scan.complete.
    counts: dict[str, int]
    schedule: tuple[int, ...]
    rating_pref: int
    text_order: int
    fallback_order: int
    # sources.json's fallback_language, for folders whose entry sets none;
    # "" means no fallback.
    default_fallback: str
    imdb_ready: bool
    # Certification settings for this pass; None when certifications are off
    # or no usable country preset exists (episodes never have one).
    cert: _CertConfig | None = None
    # The Update now path (run_scan reset): lookups that answered empty and
    # stored number matches are asked again at once.
    reset: bool = False
    # (provider, show id) -> the show's original language, or None when the
    # provider names none; for matching episodes by number.
    original_language: dict[tuple[str, str], str | None] = field(default_factory=dict)
    # Kodi ids of the shows the tracker knows (episode passes only). A show
    # with no ids of its own is skipped before it is tracked, so it never
    # joins checked_shows: its episodes have no route rather than waiting.
    tracked_shows: frozenset[int] = frozenset()


def _get_season_data(
    show_tmdb_id: str,
    season_number: int,
    api_key: str,
    language: str,
    cache: dict[str, list[dict[str, Any]] | None],
) -> list[dict[str, Any]] | None:
    """Fetch season data from TMDB with caching.

    Caches by show_tmdb_id, season_number, and language to avoid
    repeated API calls for episodes of the same season.
    """
    key = "{}:{}:{}".format(show_tmdb_id, season_number, language)
    if key not in cache:
        cache[key] = tmdb.fetch_season(show_tmdb_id, season_number, api_key, language)
    return cache[key]


def _call_provider(
    provider: str,
    fn: Any,
    ctx: _ScanCtx,
    identity: str,
    best_effort: bool = False,
) -> Any:
    """Pace, run a provider fn, and apply circuit-breaker bookkeeping.

    Records breaker success on any non-raising return (including None, a real
    "nothing"). On ApiKeyError re-raises (terminal, TMDB only). On
    TvdbAuthError disables TVDB for the cycle, logs once, and returns
    ``TRANSIENT``. On TransientProviderError records a breaker failure, logs
    the trip once, and returns ``TRANSIENT``. When ``best_effort`` is True
    (episode ID enrichment) both TMDB exceptions are logged at scan.error and
    yield ``TRANSIENT`` without touching the breaker.
    """
    ctx.pacer.wait()
    try:
        result = fn()
    except TvdbAuthError:
        if ctx.breaker.disable("tvdb", auth=True):
            log.exception(
                "TheTVDB rejected the add-on's credentials, TVDB disabled for this cycle",
                event="scan.tvdb_auth", identity=identity,
            )
        return TRANSIENT
    except ApiKeyError:
        if best_effort:
            log.exception(
                "Provider call failed (best effort)",
                event="scan.error", provider=provider, identity=identity,
            )
            return TRANSIENT
        # Terminal: the caller that stops the scan logs it, once.
        raise
    except TransientProviderError:
        if best_effort:
            log.exception(
                "Provider call failed (best effort)",
                event="scan.error", provider=provider, identity=identity,
            )
            return TRANSIENT
        if ctx.breaker.record_failure(provider):
            log.warning(
                "Provider disabled for this cycle after repeated failures",
                event="scan.breaker", provider=provider,
                threshold=PROVIDER_CIRCUIT_BREAKER_THRESHOLD, identity=identity,
            )
        return TRANSIENT
    ctx.breaker.record_success(provider)
    return result
