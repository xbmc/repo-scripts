# SPDX-License-Identifier: GPL-2.0-only
"""Upload requests: rows packed into full parts or deltas within CrossWatch's limits.

The rows themselves, which items go up with which state, are decided elsewhere; this module
only packs them the way CrossWatch accepts them (contract, Upload; _addon_sync.py):
- every full part carries all three lists, empty when there are none, and sources go in the
  first part; an empty full is one part with empty lists;
- each episode travels with its show row, repeated in every part or delta that holds one of
  the show's episodes, because CrossWatch refuses an episode whose show row is missing;
- removed rows (in_library: false) come before live rows, and rows that must land together
  (a removed row and the live rows on its file) stay in one request;
- at most MAX_ROWS_PER_LIST rows per list and MAX_REQUEST_BYTES per request after gzip; a
  full counts every staged row, repeated show rows included, against MAX_FULL_ROWS, and has
  at most MAX_PARTS parts (_addon_sync.py MAX_ROWS, MAX_PARTS, _staged_rows).

Each request lists the entries whose rows it sent. That is not what CrossWatch stamped: it
skips a group a queued change still holds, a delta sent between full parts keeps its newer
stamp, and full parts stamp nothing until the last one completes. The engine's commit applies
those rules; this list only says which rows went up.

Log events: none.
"""
from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Dict, List

from resources.lib.sync.constants import MAX_FULL_ROWS, MAX_PARTS, MAX_REQUEST_BYTES, MAX_ROWS_PER_LIST
from resources.lib.sync.items import ItemKind
from resources.lib.sync.record import GROUPS

ALL_GROUPS = frozenset(GROUPS)


class UploadTooLarge(Exception):
    """More than CrossWatch accepts, and splitting can't help: a full over its row total or
    part count, or one item (with the rows that must travel with it) over a request's limits."""


# Room for the request's own fields beside the lists, so a part whose lists fit is a request
# that fits.
ENVELOPE_BYTES = 1024


@dataclass(frozen=True)
class UploadRow:
    entry_key: str
    kind: ItemKind
    row: dict[str, Any]
    removed: bool = False
    # Rows with the same non-empty key go in the same request.
    together: str = ""


@dataclass(frozen=True)
class UploadBody:
    body: bytes
    seq: int
    part: int = 1
    parts: int = 1
    # entry key -> groups this request carried
    carried: dict[str, frozenset[str]] = field(default_factory=dict)
    rows: int = 0


def _show_of(row: UploadRow) -> int | None:
    if row.kind != "episodes" or row.removed:
        # A removed episode carries its show block itself and needs no show row.
        return None
    value = row.row.get("tvshowid")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _units(rows: Sequence[UploadRow]) -> list[list[UploadRow]]:
    """Rows in sending order, grouped where they must stay together: removed rows first, and
    within each section episodes of one show together, so a show row repeats in as few
    requests as possible (CrossWatch counts every repeat against its row total)."""
    ordered = sorted(rows, key=lambda r: (not r.removed, _show_of(r) is not None, _show_of(r) or 0))
    units: list[list[UploadRow]] = []
    index: dict[str, list[UploadRow]] = {}
    for row in ordered:
        if row.together:
            if row.together in index:
                index[row.together].append(row)
                continue
            index[row.together] = unit = [row]
            units.append(unit)
        else:
            units.append([row])
    return units


def _counts(unit: Sequence[UploadRow]) -> tuple[int, int, set[int]]:
    movies = sum(1 for r in unit if r.kind == "movies")
    episodes = len(unit) - movies
    shows = {s for r in unit if (s := _show_of(r)) is not None}
    return movies, episodes, shows


def _pack(units: list[list[UploadRow]], max_rows: int) -> list[list[UploadRow]]:
    """Greedy packing by the per-list row limit; a unit is never split."""
    batches: list[list[UploadRow]] = []
    current: list[UploadRow] = []
    movies = episodes = 0
    shows: set[int] = set()
    for unit in units:
        m, e, s = _counts(unit)
        if m > max_rows or e > max_rows:
            raise UploadTooLarge("rows that must travel together exceed a request's row limit")
        if current and (movies + m > max_rows or episodes + e > max_rows or len(shows | s) > max_rows):
            batches.append(current)
            current, movies, episodes, shows = [], 0, 0, set()
        current.extend(unit)
        movies, episodes, shows = movies + m, episodes + e, shows | s
    if current or not batches:
        batches.append(current)
    return batches


def _lists(batch: Sequence[UploadRow], tvshows: Mapping[int, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    shows = sorted({s for r in batch if (s := _show_of(r)) is not None})
    missing = [s for s in shows if s not in tvshows]
    if missing:
        # CrossWatch would refuse the whole full at its last part, and again on every retry.
        raise ValueError(f"episodes without their show row: tvshowid {missing[:5]}")
    return {
        "movies": [r.row for r in batch if r.kind == "movies"],
        "episodes": [r.row for r in batch if r.kind == "episodes"],
        "tvshows": [dict(tvshows[s]) for s in shows],
    }


def _encode(body: Mapping[str, Any]) -> bytes:
    # UTF-8 as is: an escaped non-Latin character costs six bytes against the request limit.
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _fits(raw: bytes, max_bytes: int) -> bool:
    return len(gzip.compress(raw)) <= max_bytes


Lists = Dict[str, List[Dict[str, Any]]]


def _split_to_fit(
    batches: list[list[UploadRow]], build: Callable[[list[UploadRow]], Lists], max_bytes: int
) -> list[tuple[list[UploadRow], Lists]]:
    """Halve any batch whose request is too big after gzip, keeping units whole."""
    out: list[tuple[list[UploadRow], Lists]] = []
    pending = list(batches)
    while pending:
        batch = pending.pop(0)
        lists = build(batch)
        if _fits(_encode(lists), max_bytes):
            out.append((batch, lists))
            continue
        units = _units(batch)
        if len(units) < 2:
            raise UploadTooLarge("one item is larger than a request may be")
        half = len(units) // 2
        pending[0:0] = [[r for u in units[:half] for r in u], [r for u in units[half:] for r in u]]
    return out


def _carried(batch: Sequence[UploadRow]) -> dict[str, frozenset[str]]:
    return {r.entry_key: ALL_GROUPS for r in batch}


def full_parts(
    rows: Sequence[UploadRow],
    tvshows: Mapping[int, Mapping[str, Any]],
    *,
    viewer_id: str,
    upload_id: str,
    upload_seq: int,
    applied_seq: int,
    sources: list[dict[str, str]],
    max_rows: int = MAX_ROWS_PER_LIST,
    max_bytes: int = MAX_REQUEST_BYTES,
    fresh: bool = False,
) -> list[UploadBody]:
    units = _units(rows)
    batches = _pack(units, max_rows)
    # Every part leaves room for the envelope and part 1's sources, so the number of parts
    # doesn't depend on which part a batch becomes.
    budget = max_bytes - ENVELOPE_BYTES - len(gzip.compress(_encode({"sources": sources})))
    fitted = _split_to_fit(batches, lambda b: _lists(b, tvshows), budget)
    total = sum(sum(len(v) for v in lists.values()) for _, lists in fitted)
    if total > MAX_FULL_ROWS:
        raise UploadTooLarge(f"{total} rows")
    if len(fitted) > MAX_PARTS:
        raise UploadTooLarge(f"{len(fitted)} parts")
    out: list[UploadBody] = []
    parts = len(fitted)
    for number, (batch, lists) in enumerate(fitted, start=1):
        body: dict[str, Any] = {
            "version": 1,
            "viewer_id": viewer_id,
            "mode": "full",
            "upload_id": upload_id,
            "upload_seq": upload_seq,
            "part": number,
            "parts": parts,
            "applied_seq": applied_seq,
        }
        if number == 1:
            body["sources"] = sources
            if fresh:
                # On any part it starts the viewer over at CrossWatch (contract, Upload); the
                # first is enough.
                body["fresh"] = True
        body.update(lists)
        out.append(
            UploadBody(
                body=_encode(body),
                seq=upload_seq,
                part=number,
                parts=parts,
                carried=_carried(batch),
                rows=sum(len(v) for v in lists.values()),
            )
        )
    return out


def deltas(
    rows: Sequence[UploadRow],
    tvshows: Mapping[int, Mapping[str, Any]],
    *,
    viewer_id: str,
    first_seq: int,
    applied_seq: int,
    max_rows: int = MAX_ROWS_PER_LIST,
    max_bytes: int = MAX_REQUEST_BYTES,
) -> list[UploadBody]:
    """Consecutive seqs from first_seq; nothing to send gives no deltas.

    How many requests the rows need doesn't depend on the seqs, so the engine can pack once
    to learn the count, reserve that many seqs, and pack again with the first one.
    """
    if not rows:
        return []
    fitted = _split_to_fit(_pack(_units(rows), max_rows), lambda b: _lists(b, tvshows), max_bytes - ENVELOPE_BYTES)
    out: list[UploadBody] = []
    for offset, (batch, lists) in enumerate(fitted):
        seq = first_seq + offset
        body: dict[str, Any] = {"version": 1, "viewer_id": viewer_id, "mode": "delta", "upload_seq": seq,
                                "applied_seq": applied_seq}  # fmt: skip
        body.update({k: v for k, v in lists.items() if v})
        out.append(
            UploadBody(body=_encode(body), seq=seq, carried=_carried(batch), rows=sum(len(v) for v in lists.values()))
        )
    return out
