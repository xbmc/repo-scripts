"""What the item details window says: one row per entry on the left (the Ids
entry, then each field under its heading) and, for each row, the story the
right pane tells.

Pure: built from the tracker's rows and the Kodi item, nothing is read or
written here. Strings come through ``lang`` so tests can patch it.

Logging: none (pure computation).
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from resources.lib.data.media_types import MediaType
from resources.lib.data.tracker import (
    REASON_FILL_ONLY,
    REASON_LOCKED,
    REASON_NFO,
    REASON_NOTHING,
    REASON_UNCHANGED,
    REASON_UNCHECKED,
    REASON_UPDATED,
)
from resources.lib.engine.maturity import (
    FINAL,
    SKIP_NOT_DUE,
    apply_fallback_recheck,
    decide_certification,
    decide_field,
)
from resources.lib.engine.protect import fingerprint, is_blank
from resources.lib.engine.scan import blanked, content_age_days
from resources.lib.engine.scanctx import (
    LANGUAGE_FIELDS,
    RATING_FIELDS,
    extract_ids,
    holds_written_value,
    kodi_form,
)
from resources.lib.service.details import can_restore
from resources.lib.utils import is_empty, lang

GROUP_UPDATED = "updated"
GROUP_LEFT = "left"
GROUP_WAITING = "waiting"
# Heading string per group, in the order the groups are listed.
GROUP_HEADINGS = {GROUP_UPDATED: 32524, GROUP_LEFT: 32525, GROUP_WAITING: 32526}

ACTION_RESTORE = "restore"
ACTION_UNLOCK = "unlock"
# Locks a field as it is now, for a value with no Restore (a hand edit).
ACTION_KEEP = "keep"

IDS_KEY = "ids"

# The scan's own default for stale_threshold_days (settings.xml, daemon).
DEFAULT_THRESHOLD_DAYS = 365

_FIELD_LABELS = {
    "plot": 32511, "title": 32512, "rating": 32513, "runtime": 32514,
    "director": 32515, "writer": 32516, "genre": 32517, "studio": 32518,
    "country": 32519, "tagline": 32520, "trailer": 32521, "firstaired": 32522,
    "mpaa": 32523,
}

# Brand names, not translated. A rating source is a Kodi rating slot name;
# a certification source may be a country's own site, or "tmdb-<country>"
# for one derived from another country's rating.
_SOURCE_NAMES = {
    "tmdb": "TMDB", "themoviedb": "TMDB", "tvdb": "TheTVDB", "thetvdb": "TheTVDB",
    "imdb": "IMDb", "bbfc": "BBFC", "fsk": "FSK", "medieraadet": "Medieraadet",
}
# "kodi" is a certification Kodi already held, which is the scraper's.
_SCRAPER_SOURCE = "kodi"

# Short month names, January first; then "12 Nov 2026", "12 Nov" and the
# separator between the header's two parts.
_MONTH_STRINGS = 32610
_LONG_DATE = 32622
_SHORT_DATE = 32623
_SEPARATED = 32624

_WHY = {
    REASON_UNCHANGED: 32540,
    REASON_NFO: 32541,
    REASON_FILL_ONLY: 32542,
    REASON_NOTHING: 32543,
    REASON_UNCHECKED: 32544,
    REASON_LOCKED: 32545,
}
_NEVER_CHECKED = 32546
_CHANGED_SINCE = 32576
_UNLOCKED = 32577
_SETTLED_NOTHING = 32600
_REFILL = 32601
_CONVERTED = 32629
# The source of MetaMender's own not-found certification (scan._resolve_cert).
_NOT_FOUND_SOURCE = "fallback"
_OFF_HINT = 32602
_OFF_NEXT = 32603
_UNLOCKED_OFF = 32604
# The same three for a certification left out because no usable age rating
# country is set up, though the field itself is switched on.
_NO_COUNTRY_HINT = 32609
_NO_COUNTRY_NEXT = 32608
_UNLOCKED_NO_COUNTRY = 32625
_TVMAZE_ONLY = 32599
# How a number match found an id (numbermatch's match note), "matched" key.
_MATCHED_HOW = {"date": 32597, "title": 32598, "tmdb_list": 32555}


@dataclass
class DetailRow:
    """One entry of the left list and the right pane's story for it.

    ``lines`` are (label, text) pairs; an empty label marks the field's
    current value, shown whole above the labelled lines.
    """

    key: str
    label: str
    group: str
    hint: str
    title: str
    lines: list[tuple[str, str]]
    action: str
    # The field is locked: the list shows a padlock beside its hint.
    locked: bool = False


def long_date(iso: str | None) -> str:
    """"12 Nov 2026" for "2026-11-12"; the text as given when it is not a date."""
    d = _parse(iso)
    if d is None:
        return str(iso or "")
    return lang(_LONG_DATE).format(day=d.day, month=_month(d), year=d.year)


def _short_date(iso: str | None) -> str:
    d = _parse(iso)
    return lang(_SHORT_DATE).format(day=d.day, month=_month(d)) if d else str(iso or "")


def _month(d: date) -> str:
    return lang(_MONTH_STRINGS + d.month - 1)


def _parse(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(str(iso)[:10])
    except ValueError:
        return None


def _source_name(source: str | None) -> str:
    if not source:
        return ""
    if source == _SCRAPER_SOURCE:
        return lang(32534)
    if source.startswith("tmdb-"):
        return "TMDB ({})".format(source[5:].upper())
    return _SOURCE_NAMES.get(source, source)


def _value_text(field: str, item: dict[str, Any]) -> str:
    value = item.get(field)
    if field == "rating":
        if is_empty(value):
            return lang(32574)
        votes = item.get("votes")
        return lang(32573).format(value, votes) if votes else str(value)
    if is_empty(value):
        return lang(32574)
    if field == "runtime":
        try:
            return lang(32572).format(int(value or 0) // 60)
        except (TypeError, ValueError):
            return str(value)
    if field == "firstaired":
        return long_date(value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _decision(field: str, fs: dict[str, Any], age: int | None, today: str,
              threshold: int) -> str:
    """The scan's maturity decision for the field, as engine/scan.py makes it."""
    count = int(fs.get("fetch_count") or 0)
    from_fallback = bool(fs.get("from_fallback"))
    checks = int(fs.get("fallback_checks") or 0)
    next_retry = fs.get("next_retry")
    if field == "mpaa":
        return decide_certification(count, from_fallback, checks, next_retry, today)
    base = decide_field(age, count, next_retry, today, threshold)
    return apply_fallback_recheck(base, from_fallback, checks, next_retry, today)


def _settled(field: str, fs: dict[str, Any], age: int | None, today: str,
             threshold: int) -> bool:
    """Not sampled again: FINAL, or answered with no date left to sample on
    (the refetch schedule ran out and the content has no release date)."""
    if int(fs.get("fetch_count") or 0) == 0:
        return False
    decision = _decision(field, fs, age, today, threshold)
    return decision == FINAL or (decision == SKIP_NOT_DUE and not fs.get("next_retry"))


def _field_row(
    media_type: MediaType,
    field: str,
    item: dict[str, Any],
    fs: dict[str, Any],
    keep: dict[str, dict[str, Any]],
    today: str,
    language: str,
    threshold: int,
    managed: bool,
    no_country: bool,
) -> DetailRow:
    """``managed``: the scan checks this field under the current settings;
    a field shown only for its lock is not, and gets no next-scan promise.
    ``no_country``: an unmanaged certification is left out for want of a
    usable age rating country, not because the field is switched off."""
    label = lang(_FIELD_LABELS.get(field, 0)) or field
    entry = keep.get(field) or {}
    rating = field in RATING_FIELDS
    locked = bool(entry.get("locked")) and not rating
    reason = fs.get("last_reason")
    count = int(fs.get("fetch_count") or 0)
    source = fs.get("source")
    age = content_age_days(item, media_type, today)
    current = item.get(field)
    mine = holds_written_value(field, current, fs, entry)
    written = entry.get("written_fp") or fs.get("written_value")
    blank = not rating and is_blank(kodi_form(current))
    # A refill that found nothing recorded the blank Kodi holds as written:
    # the field is blank (empty or a placeholder), not changed since a write.
    written_blank = blank and written == fingerprint(kodi_form(current))
    # MetaMender wrote this field once, but Kodi now holds something else.
    changed = not rating and not mine and bool(written) and not written_blank
    decision = _decision(field, fs, age, today, threshold)
    # Kodi lost a settled field's MetaMender value: the scan fills it again
    # (scan.blanked), so it is not settled.
    refill = (managed and not locked and count > 0 and decision == FINAL
              and blanked(item, field, fs))
    settled = not refill and _settled(field, fs, age, today, threshold)
    checked = count > 0 or reason in (REASON_NOTHING, REASON_UNCHECKED)
    # An unlock leaves the "locked" reason until the next scan records one,
    # and makes the field due at that scan (details.unlock_field). Kodi then
    # holds the restored original, so this wins over "changed".
    unlocked = reason == REASON_LOCKED and not locked

    if locked:
        group, hint, why = GROUP_LEFT, lang(32548), _WHY[REASON_LOCKED]
    elif not checked:
        group, hint, why = GROUP_WAITING, lang(32551), _NEVER_CHECKED
    elif unlocked:
        group, hint = GROUP_WAITING, lang(32552)
        why = _UNLOCKED if managed else (
            _UNLOCKED_NO_COUNTRY if no_country else _UNLOCKED_OFF)
    elif refill:
        group, hint, why = GROUP_WAITING, lang(32552), _REFILL
    elif changed:
        group, hint, why = GROUP_LEFT, lang(32575), _CHANGED_SINCE
    elif not blank and (reason == REASON_UPDATED or (
        source and source != _SCRAPER_SOURCE and mine
    )):
        group, hint, why = GROUP_UPDATED, _source_name(source), 0
    elif reason == REASON_UNCHECKED:
        group, hint, why = GROUP_WAITING, "", _WHY[REASON_UNCHECKED]
    elif settled or reason in (REASON_UNCHANGED, REASON_NFO, REASON_FILL_ONLY):
        group = GROUP_LEFT
        why = _WHY.get(reason or "", 0)
        if settled and reason == REASON_NOTHING:
            why = _SETTLED_NOTHING
        if reason == REASON_NFO:
            hint = lang(32549)
        elif settled:
            hint = lang(32547)
        else:
            hint = lang(32550)
    else:
        group, hint, why = GROUP_WAITING, "", _WHY[REASON_NOTHING]
    if group == GROUP_UPDATED and not hint:
        hint = "MetaMender"

    lines: list[tuple[str, str]] = [("", _value_text(field, item))]
    # The provider is named only while Kodi holds its value. A value changed
    # since MetaMender's write has no known origin; its Why line says so.
    if mine:
        lines.append((lang(32527), _from_text(field, source, fs, language)))
    elif checked and not changed and not is_empty(current):
        lines.append((lang(32527), lang(32534)))
    if group == GROUP_UPDATED and not rating:
        lines.append((lang(32528), _replaced_text(entry)))
    if fs.get("fetched_at"):
        lines.append((lang(32529), long_date(fs["fetched_at"])))
    if checked and not locked:
        if not managed:
            next_text = lang(_NO_COUNTRY_NEXT if no_country else _OFF_NEXT)
        elif unlocked or refill:
            next_text = lang(32539)
        elif settled:
            next_text = lang(32538)
        elif decision == SKIP_NOT_DUE:
            next_text = long_date(fs.get("next_retry"))
        else:
            next_text = lang(32539)
        lines.append((lang(32530), next_text))
        if group == GROUP_WAITING and not hint:
            hint = lang(32538) if settled else (
                _short_date(fs.get("next_retry")) if decision == SKIP_NOT_DUE
                else lang(32552)
            )
    if not managed and not locked:
        hint = lang(_NO_COUNTRY_HINT if no_country else _OFF_HINT)
    if why:
        lines.append((lang(32531), lang(why)))

    action = ""
    if not rating:
        if locked:
            action = ACTION_UNLOCK
        elif can_restore(field, current, fs, keep):
            action = ACTION_RESTORE
        elif managed:
            action = ACTION_KEEP
    return DetailRow(field, label, group, hint, label, lines, action, locked)


def _from_text(field: str, source: str | None, fs: dict[str, Any], language: str) -> str:
    name = _source_name(source) or "MetaMender"
    if field == "mpaa" and fs.get("from_fallback") and source != _NOT_FOUND_SOURCE:
        # Another country's rating converted to this system: it is not
        # this country's own decision and is re-checked monthly.
        return lang(_CONVERTED).format(name)
    if field not in LANGUAGE_FIELDS or source == _SCRAPER_SOURCE:
        return name
    if fs.get("from_fallback"):
        return lang(32533).format(name)
    return lang(32532).format(name, language) if language else name


def _replaced_text(entry: dict[str, Any]) -> str:
    if not entry.get("has_original"):
        return lang(32537)
    if is_empty(entry.get("original")):
        return lang(32536)
    return lang(32535)


def _match_notes(item_row: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        notes = json.loads(item_row.get("match_note") or "[]")
    except ValueError:
        return []
    return [n for n in notes if isinstance(n, dict)] if isinstance(notes, list) else []


def _tvmaze_only(item: dict[str, Any]) -> bool:
    """Kodi's uniqueid holds a TVmaze id and nothing else, which no site
    MetaMender asks can look up."""
    held = {k for k, v in (item.get("uniqueid") or {}).items() if v}
    return held == {"tvmaze"}


def _ids_row(media_type: MediaType, item: dict[str, Any],
             item_row: dict[str, Any] | None) -> DetailRow:
    kodi_tmdb, kodi_imdb, kodi_tvdb, kodi_unknown = extract_ids(item)
    row = item_row or {}
    number_matched = bool(row.get("number_matched"))
    notes = _match_notes(row)
    # How the number match found each id, by the name shown.
    how = {_SOURCE_NAMES[n["site"]]: str(n["matched"]) for n in notes
           if n.get("matched") and n.get("site") in ("tmdb", "tvdb")}
    lines: list[tuple[str, str]] = []
    from_kodi = found = False
    for name, kodi_id, stored, matchable in (
        ("TMDB", kodi_tmdb, row.get("tmdb_id"), True),
        # An `unknown` uniqueid is a TheTVDB id once the scan verified it.
        ("TheTVDB", kodi_tvdb or (
            kodi_unknown if kodi_unknown and str(kodi_unknown) == str(row.get("tvdb_id"))
            else None
        ), row.get("tvdb_id"), True),
        ("IMDb", kodi_imdb, row.get("imdb_id"), False),
    ):
        if kodi_id:
            lines.append((name, lang(32553).format(kodi_id)))
            from_kodi = True
        elif stored:
            if matchable and number_matched:
                text = lang(_MATCHED_HOW.get(how.get(name, ""), 32554))
            elif not matchable:
                text = lang(32555)
            else:
                text = lang(32556)
            lines.append((name, text.format(stored)))
            found = True
    if _tvmaze_only(item):
        lines.append(("", lang(_TVMAZE_ONLY)))
    if found:
        lines.append(("", lang(32557)))

    # A note is stale once the episode has an id of its own (a rescrape):
    # the scan then never matches it by number again.
    rejected = False
    if media_type.name == "episode" and not (kodi_tmdb or kodi_tvdb):
        for note in notes:
            site = note.get("site")
            if note.get("matched"):
                continue
            if site == "conflict":
                lines.append((lang(32566), lang(32567)))
                rejected = True
            elif site in ("tmdb", "tvdb"):
                lines.append((_SOURCE_NAMES[site], lang(32563).format(
                    note.get("site_title") or "", long_date(note.get("site_aired")))))
                lines.append((lang(32564), lang(32563).format(
                    note.get("kodi_title") or "", long_date(note.get("kodi_aired")))))
                # Only this site's candidate was rejected: on a partial match
                # the other site's values were used.
                lines.append((lang(32531), lang(32565).format(_SOURCE_NAMES[site])))
                rejected = True
    if not lines:
        lines.append(("", lang(32558)))

    if number_matched:
        hint = lang(32559)
    elif rejected and not found:
        hint = lang(32561)
    elif from_kodi:
        hint = lang(32560)
    elif found:
        hint = lang(32562)
    else:
        hint = ""
    label = lang(32510)
    return DetailRow(IDS_KEY, label, "", hint, label, lines, "")


def build_rows(
    media_type: MediaType,
    item: dict[str, Any],
    item_row: dict[str, Any] | None,
    fs_map: dict[str, dict[str, Any]],
    keep: dict[str, dict[str, Any]],
    today: str,
    *,
    language: str = "",
    fields: Iterable[str] | None = None,
    managed: Iterable[str] | None = None,
    cert_country_missing: bool = False,
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
) -> list[DetailRow]:
    """The Ids entry, then the fields grouped updated, left as it is and
    waiting, each group in the scan's field order (sorted by name).

    ``language`` is the folder language's display name ("Dutch"), for the
    "From" line of a field written in a language. ``fields`` are the fields
    to show (default: every field of the media type); ``managed`` those the
    scan checks under the current settings (default: ``fields``).
    ``cert_country_missing``: certifications are switched on but no usable
    age rating country is set up.
    ``threshold_days`` is the stale_threshold_days setting, which decides
    when a field is settled. Rating and votes are one "Rating" row.
    """
    names = sorted(set(fields if fields is not None else media_type.backfill_fields))
    managed_set = set(managed) if managed is not None else set(names)
    if "votes" in managed_set:
        managed_set.add("rating")
    if "votes" in names:
        names.remove("votes")
        if "rating" not in names:
            names.append("rating")
            names.sort()
    rows = [
        _field_row(media_type, f, item, fs_map.get(f) or {}, keep, today, language,
                   threshold_days, f in managed_set,
                   f == "mpaa" and cert_country_missing)
        for f in names
    ]
    ordered = [_ids_row(media_type, item, item_row)]
    for group in GROUP_HEADINGS:
        ordered.extend(r for r in rows if r.group == group)
    return ordered


def header_line(
    item_row: dict[str, Any] | None,
    fs_map: dict[str, dict[str, Any]],
    folder_language: str,
) -> str:
    """"Dutch folder · last looked at 12 Nov 2026": the folder language's
    display name and when MetaMender last looked at the item (its last scan
    pass, else its latest field check)."""
    folder = lang(32568).format(folder_language) if folder_language else lang(32569)
    seen = (item_row or {}).get("last_seen") or max(
        (str(fs["fetched_at"]) for fs in fs_map.values() if fs.get("fetched_at")),
        default="",
    )
    looked = lang(32570).format(long_date(seen)) if seen else lang(32571)
    return lang(_SEPARATED).format(folder, looked)
