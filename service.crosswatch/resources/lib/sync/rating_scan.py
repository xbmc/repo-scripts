# SPDX-License-Identifier: GPL-2.0-only
"""Ratings set in Kodi, found by comparing each row with the last value read for that row.

Kodi announces nothing for a rating (VideoDatabase.cpp:11851-11875: SetVideoUserRating sends
no OnUpdate), so a scan is the only way to see one. It runs every RATING_SCAN_SECONDS and reads
only file, userrating and dateadded per row, because the full read with ids is too slow to
repeat that often; tokens, copies and shows come from the last full library read.

What counts as a person's rating:
- only a row the add-on has a Seen for, compared with that same row's Seen. A row without
  one is noted (given a Seen) and nothing is sent; a row whose dateadded differs was added
  again by Kodi, and its Seen is dropped for the next full read;
- the changed row is read again in full, and only a value that is still there counts;
- a value equal to the add-on's own rating write still in flight is that write;
- an item whose copies aren't all known and in this read, or a row whose re-read fails, is
  left as it was and tried again on the next scan;
- on an item with several copies, a change on one copy counts while the other copies still
  show their Seen value (Kodi's info dialog and OSD rate one row, GUIDialogVideoInfo.cpp:123);
  the writer then gives the other copies the value. Copies changed to different values send
  nothing and keep their own values: separate ratings on a 4K and a 1080p copy are flattened
  only once a later rating is set on one of them.

More than MASS_RATING_CHANGE changes in one scan (a Kodi database restored from backup looks
like this) sends nothing and leaves their Seen as it was: the household is asked first. Those
rows are held, skipped by later scans until answered, unless a person rates one of them again,
which puts that row back in the normal path.

Log events: sync.rating_scan.done (debug), sync.rating_scan.held (info).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from resources.lib.log import get_logger
from resources.lib.media import strip_credentials
from resources.lib.sync.clock import kodi_to_utc
from resources.lib.sync.constants import MASS_RATING_CHANGE
from resources.lib.sync.items import ItemKind, JsonRpc, Library, LibraryRow, RowKey, Stopped, pages
from resources.lib.sync.record import Seen
from resources.lib.sync.rows import item_groups
from resources.lib.sync.writer import seen_of

_log = get_logger("sync")

_PAGE = 2000
_PROPERTIES = ["file", "userrating", "dateadded"]
_ID_FIELDS: dict[ItemKind, str] = {"movies": "movieid", "episodes": "episodeid"}


@dataclass(frozen=True)
class FoundRating:
    """A person's rating on one item: row is the copy it was set on, read again in full;
    copies are the item's other rows, which the writer gives the value."""

    row: LibraryRow
    value: int
    copies: tuple[RowKey, ...] = ()
    # Every copy the person's value was found on, row's own key included.
    rated: tuple[RowKey, ...] = ()


@dataclass
class ScanResult:
    found: list[FoundRating] = field(default_factory=list)
    # Seen to store; None drops it.
    seen: dict[RowKey, Seen | None] = field(default_factory=dict)
    # Set when this scan held its changes back for the household's answer.
    held: list[FoundRating] = field(default_factory=list)
    # Held rows a person rated again since: back in the normal path.
    released: set[RowKey] = field(default_factory=set)
    complete: bool = True


@dataclass(frozen=True)
class _Light:
    key: RowKey
    userrating: int
    dateadded: str


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _light_rows(kodi: JsonRpc, library_id: str, may_continue: Callable[[], bool]) -> tuple[dict[RowKey, _Light], bool]:
    out: dict[RowKey, _Light] = {}
    complete = True
    for kind, id_field in _ID_FIELDS.items():
        raws, held = pages(kodi, kind, _PROPERTIES, _PAGE, may_continue)
        complete = complete and held
        for raw in raws:
            kodi_id = raw.get(id_field)
            if not isinstance(kodi_id, int) or isinstance(kodi_id, bool):
                continue
            key = RowKey(library_id, kind, kodi_id, strip_credentials(str(raw.get("file") or "")))
            out[key] = _Light(key, _int(raw.get("userrating")), kodi_to_utc(str(raw.get("dateadded") or "")))
    return out, complete


def rating_scan(
    kodi: JsonRpc,
    library: Library,
    seen: Mapping[RowKey, Seen],
    in_flight: Mapping[RowKey, Mapping[str, Any]],
    read_row: Callable[[RowKey], LibraryRow | None],
    *,
    held: Mapping[RowKey, int],
    may_continue: Callable[[], bool],
) -> ScanResult:
    """One scan of this library. seen is every Seen of the library; in_flight the fields of
    the add-on's own writes not yet read back (writer.in_flight_rows); held the rows held for
    the household's answer, with the value each had when the question was raised. Pending
    inputs (rating writes, removals) must be drained before this runs, so seen is current."""
    out = ScanResult()
    try:
        light, complete = _light_rows(kodi, library.library_id, may_continue)
    except Stopped:
        out.complete = False
        return out
    out.complete = complete and library.complete
    for key, value in held.items():
        now = light.get(key)
        if now is not None and now.userrating != value:
            out.released.add(key)
    skip = {k for k in held if k not in out.released}

    by_key = {r.key: r for r in [*library.movies, *library.episodes]}
    changed: dict[RowKey, _Light] = {}
    for key, now in light.items():
        if key in skip:
            continue
        before = seen.get(key)
        if before is None:
            row = by_key.get(key)
            if row is not None and str(row.raw.get("dateadded") or "") == now.dateadded:
                # In the last full read as it is now, without a Seen yet: noted, so a later
                # rating counts. That read's catch-up already had its turn at this row.
                out.seen[key] = replace(seen_of(row.raw), userrating=now.userrating)
            continue
        if now.dateadded != before.dateadded:
            # Kodi added the file again under the same id and path (a clean and rescan, or
            # Refresh information): what Kodi holds is new, and the next full read's catch-up
            # restores what it lost, which needs the row to have no Seen.
            out.seen[key] = None
        elif now.userrating != before.userrating:
            changed[key] = now
    if out.complete:
        for key in seen:
            if key not in light:
                out.seen[key] = None

    found: list[FoundRating] = []
    seen_updates: dict[RowKey, Seen] = {}
    for item in item_groups(list(by_key.values())):
        keys = [r.key for r in item]
        moved = [k for k in keys if k in changed]
        if not moved:
            continue
        own = {k for k in moved if (in_flight.get(k) or {}).get("userrating") == changed[k].userrating}
        for k in own:
            seen_updates[k] = replace(seen[k], userrating=changed[k].userrating)
        moved = [k for k in moved if k not in own]
        if not moved:
            continue
        others = [k for k in keys if k not in moved]
        if any((k in changed and k not in own) or seen.get(k) is None or light.get(k) is None for k in others):
            # A copy isn't known yet or is missing from this read: tried again next scan,
            # with its Seen left as it was.
            continue
        fresh: dict[RowKey, LibraryRow | None] = {}
        for k in moved:
            if not may_continue():
                return ScanResult(complete=False)
            fresh[k] = read_row(k)
        if any(r is None for r in fresh.values()):
            # Gone, or no longer the same file, on the re-read: tried again next scan.
            continue
        values = {k: _int(r.raw.get("userrating")) for k, r in fresh.items() if r is not None}
        distinct = set(values.values())
        if len(distinct) != 1:
            # Copies rated differently: each keeps its value, nothing is sent.
            for k, v in values.items():
                seen_updates[k] = replace(seen[k], userrating=v)
            continue
        value = distinct.pop()
        rated = [k for k in moved if values[k] != seen[k].userrating]
        for k in moved:
            seen_updates[k] = replace(seen[k], userrating=values[k])
        if not rated:
            # Set back to the Seen value before the re-read.
            continue
        row = fresh[rated[0]]
        assert row is not None
        found.append(FoundRating(row, value, tuple(k for k in keys if k not in rated), tuple(rated)))

    if len(found) > MASS_RATING_CHANGE:
        out.held = found
        held_keys = {k for f in found for k in f.rated}
        out.seen.update({k: s for k, s in seen_updates.items() if k not in held_keys})
        _log.info("sync.rating_scan.held", count=len(found))
        return out
    out.found = found
    out.seen.update(seen_updates)
    _log.debug("sync.rating_scan.done", rows=len(light), found=len(found), complete=out.complete)
    return out
