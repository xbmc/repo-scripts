# SPDX-License-Identifier: GPL-2.0-only
"""CrossWatch's queued changes, taken into the viewer's record.

A queued change is an intent for that viewer (contract, Queue). It always goes into the
record when the add-on can place it, also for an item not in the library now, which comes
without a Kodi id and is found by its item info; what Kodi gets is decided later, by the
rules and the writer. Only a change the add-on can't record at all is acked "failed": a
method or field outside what the contract allows, or a value of the wrong type or range.

seq and change_id together identify a change, also across a restore of CrossWatch's state,
and every ack carries both. A change acked before under the same pair is a redelivery: acked
again, not applied twice.

A change for a group with a person's change not yet settled with CrossWatch: which is newer
is decided by upload order alone, never by comparing Kodi's clock with CrossWatch's. A change
with `after` at or above the seq of the upload that carried the person's change was made after
CrossWatch saw it, and wins; any other change loses, also one for a person change no upload
has carried yet. The person's change then goes up again (CrossWatch skipped its row while its
own change was pending) and is settled only once a later upload carried it.

Log events: none; the engine logs counts.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from resources.lib.sync.items import ItemKind, Library, LibraryRow, identity, tokens
from resources.lib.sync.record import (
    Acked,
    Batch,
    Entry,
    Group,
    History,
    PendingWrite,
    Rating,
    RecordStore,
    Resume,
    fresh_state,
    merge,
)

ALLOWED_METHODS: dict[str, tuple[ItemKind, str]] = {
    "VideoLibrary.SetMovieDetails": ("movies", "movieid"),
    "VideoLibrary.SetEpisodeDetails": ("episodes", "episodeid"),
}
_FIELD_GROUP: dict[str, Group] = {
    "playcount": "history",
    "lastplayed": "history",
    "userrating": "ratings",
    "resume": "progress",
}
ALLOWED_FIELDS = frozenset(_FIELD_GROUP)


@dataclass
class Applied:
    batch: Batch = field(default_factory=Batch)
    acks: list[dict[str, Any]] = field(default_factory=list)
    # Entry keys whose state changed, merges included: the next delta carries them.
    touched: set[str] = field(default_factory=set)
    # (entry key, group) of every change in the batch, for settle_unsent after the last page.
    fetched: set[tuple[str, str]] = field(default_factory=set)


def _whole(value: Any, low: int, high: int | None = None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= low and (high is None or value <= high)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _valid(fields: Mapping[str, Any]) -> bool:
    """The types and ranges Kodi's JSON-RPC takes for these fields."""
    if "playcount" in fields and not _whole(fields["playcount"], 0):
        return False
    if "lastplayed" in fields and ("playcount" not in fields or not isinstance(fields["lastplayed"], str)):
        # A lastplayed alone would read as an unwatch.
        return False
    if "userrating" in fields and not _whole(fields["userrating"], 0, 10):
        return False
    if "resume" in fields:
        resume = fields["resume"]
        if not isinstance(resume, Mapping):
            return False
        if not _number(resume.get("position", 0)) or not _number(resume.get("total", 0)):
            return False
    return True


def _item_row(kind: ItemKind, item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """The queued item as a row and show, for CrossWatch's token and identity rules."""
    row: dict[str, Any] = {"uniqueid": item.get("uniqueid") or {}, "title": item.get("title") or ""}
    if kind == "movies":
        row["year"] = item.get("year")
        return row, None
    row.update(showtitle=item.get("showtitle") or "", season=item.get("season"), episode=item.get("episode"))
    show = {"uniqueid": item.get("show_uniqueid") or {}, "title": item.get("showtitle") or ""}
    return row, show


def _meta(kind: ItemKind, item: Mapping[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {"uniqueid": dict(item.get("uniqueid") or {}), "title": item.get("title") or ""}
    if item.get("file"):
        meta["file"] = item["file"]
    if kind == "movies":
        meta["year"] = item.get("year") or 0
    else:
        meta.update(showtitle=item.get("showtitle") or "", season=item.get("season"), episode=item.get("episode"))
        meta["show"] = {"uniqueid": dict(item.get("show_uniqueid") or {}), "title": item.get("showtitle") or ""}
    return meta


@dataclass(frozen=True)
class _Change:
    seq: int
    after: int


def _apply_group(entry: Entry, group: Group, fields: Mapping[str, Any], change: _Change, fetched_at: str) -> Entry:
    state = entry.state
    if group == "history":
        playcount = int(fields.get("playcount") or 0)
        old = state.history
        if playcount > 0:
            # A local unwatch made here with removals off holds until a watch made after it.
            keep = old.local_unwatch and change.after < old.local_unwatch_seq
            history = History(watched=True, playcount=playcount, lastplayed=str(fields.get("lastplayed") or ""),
                              local_unwatch=keep, local_unwatch_seq=old.local_unwatch_seq if keep else 0,
                              event=old.event, src=old.src)  # fmt: skip
        else:
            history = History(watched=False, explicit=True, event=old.event, src=old.src)
        state = replace(state, history=history)
    elif group == "ratings":
        value = int(fields.get("userrating") or 0)
        state = replace(state, rating=Rating(value=value, from_cw=True, removed=value == 0, src=state.rating.src))
    else:
        resume = fields.get("resume") or {}
        state = replace(
            state,
            resume=Resume(
                position=float(resume.get("position") or 0),
                total=float(resume.get("total") or 0),
                # Kodi's clock, as the play times the rules compare it with.
                at=fetched_at,
                src=state.resume.src,
            ),  # fmt: skip
        )
    return replace(
        entry,
        state=state,
        touched=True,
        change_count=entry.change_count + 1,
        applied_change={**entry.applied_change, group: change.seq},
        applied_after={**entry.applied_after, group: change.after},
    )


def _person_wins(entry: Entry, group: Group, change: _Change) -> bool:
    if group not in entry.unsent:
        return False
    carried = entry.unsent_upload.get(group)
    return carried is None or change.after < carried


class _Entries:
    """The batch's view of the record: entries changed so far win over the stored ones, and
    keys merged away resolve to their survivor."""

    def __init__(self, store: RecordStore, viewer: str) -> None:
        self._store, self._viewer = store, viewer
        self.changed: dict[str, Entry] = {}
        self._gone: dict[str, str] = {}

    def match(self, item_tokens: frozenset[str]) -> list[Entry]:
        found: dict[str, Entry] = {}
        for entry in self._store.match(self._viewer, item_tokens):
            key = entry.key
            while key in self._gone:
                key = self._gone[key]
            found[key] = self.changed.get(key, entry)
        for key, entry in self.changed.items():
            if entry.tokens & item_tokens:
                found[key] = entry
        return sorted(found.values(), key=lambda e: e.key)

    def put(self, entry: Entry) -> None:
        self.changed[entry.key] = entry

    def merged(self, survivor: str, keys: list[str]) -> None:
        for key in keys:
            if key != survivor:
                self._gone[key] = survivor
                self.changed.pop(key, None)

    def resolve(self, key: str) -> str:
        while key in self._gone:
            key = self._gone[key]
        return key


def apply_changes(
    viewer: str,
    changes: Sequence[Mapping[str, Any]],
    *,
    store: RecordStore,
    library: Library,
    fetched_at: str,
    new_id: Callable[[], str],
) -> Applied:
    out = Applied()
    entries = _Entries(store, viewer)
    applied_seqs: list[int] = []
    fetched: set[tuple[str, str]] = set()
    rows_by_token: dict[str, list[LibraryRow]] = {}
    for row in (*library.movies, *library.episodes):
        for token in row.tokens:
            rows_by_token.setdefault(token, []).append(row)
    for raw in changes:
        seq, change_id = raw.get("seq"), raw.get("change_id")
        if not isinstance(seq, int) or not _whole(seq, 1) or not isinstance(change_id, str) or not change_id:
            # Without both the change can't be acked at all (contract, Confirming).
            continue
        ack = {"seq": seq, "change_id": change_id}
        method, params, item = raw.get("method"), raw.get("params"), raw.get("item")
        kind_field = ALLOWED_METHODS.get(method) if isinstance(method, str) else None
        if kind_field is None or not isinstance(params, Mapping) or not isinstance(item, Mapping):
            out.acks.append({**ack, "status": "failed", "error": "not_allowed"})
            continue
        kind, id_field = kind_field
        # The Kodi id is CrossWatch's view of the row, and missing for an item it has no live
        # row for; the item info is what places the change.
        fields = {k: v for k, v in params.items() if k != id_field}
        if not fields or not set(fields) <= ALLOWED_FIELDS or not _valid(fields):
            out.acks.append({**ack, "status": "failed", "error": "not_allowed"})
            continue
        change = _Change(seq=seq, after=raw["after"] if _whole(raw.get("after"), 0) else 0)
        groups: list[Group] = sorted({_FIELD_GROUP[k] for k in fields})
        row, show = _item_row(kind, item)
        item_tokens = frozenset(tokens(kind, row, show))
        found = entries.match(item_tokens)
        if len(found) > 1:
            entry = merge(found)
            keys = [e.key for e in found]
            group_of = out.batch.merged.setdefault(viewer, {})
            gathered = {k2 for k in keys if k != entry.key for k2 in (k, *group_of.pop(k, []))}
            group_of[entry.key] = sorted({*group_of.get(entry.key, []), *gathered, entry.key})
            entries.merged(entry.key, keys)
            out.touched.add(entry.key)
        elif found:
            entry = found[0]
        else:
            entry = Entry(key=identity(kind, row, show), tokens=item_tokens, meta=_meta(kind, item), state=fresh_state(),
                          origin="cw")  # fmt: skip
        if not item_tokens <= entry.tokens:
            entry = replace(entry, tokens=entry.tokens | item_tokens)
            out.touched.add(entry.key)
        for group in groups:
            fetched.add((entry.key, group))
        if store.acked(viewer, seq, change_id):
            # A redelivery: the ack didn't reach CrossWatch. Acked again, not applied twice;
            # a merge it caused is still kept, an item the record no longer holds isn't made.
            if found:
                entries.put(entry)
            out.acks.append({**ack, "status": "applied"})
            continue
        for group in groups:
            if _person_wins(entry, group, change):
                # CrossWatch skipped the carrying upload's row while this change was pending
                # (contract, applied_seq), so the person's change didn't land: it goes up
                # again, in a later upload whose applied_seq covers this change, and is only
                # settled once that one is carried.
                entry = replace(
                    entry,
                    unsent_upload={g: s for g, s in entry.unsent_upload.items() if g != group},
                    touched=True,
                    change_count=entry.change_count + 1,
                )
                out.touched.add(entry.key)
                continue
            entry = _apply_group(entry, group, fields, change, fetched_at)
            if group in entry.unsent:
                entry = replace(
                    entry,
                    unsent={g: t for g, t in entry.unsent.items() if g != group},
                    unsent_upload={g: s for g, s in entry.unsent_upload.items() if g != group},
                )
            out.touched.add(entry.key)
            for library_row in _rows_for(entry, rows_by_token):
                out.batch.pending_add.append(
                    PendingWrite(
                        id=new_id(),
                        row=library_row.key,
                        tokens=entry.tokens,
                        group=group,
                        created=fetched_at,
                        fetched_at=fetched_at,
                    )  # fmt: skip
                )
        entries.put(entry)
        out.batch.acked_add.setdefault(viewer, []).extend(Acked(seq, change_id, entry.key, g) for g in groups)
        out.acks.append({**ack, "status": "applied"})
        applied_seqs.append(seq)
    # Keys as they stand after the whole batch: a later merge moves an earlier key.
    out.fetched = {(entries.resolve(k), g) for k, g in fetched}
    out.touched = {entries.resolve(k) for k in out.touched}
    if entries.changed:
        out.batch.entries[viewer] = list(entries.changed.values())
    if applied_seqs:
        out.batch.applied_seq[viewer] = max(applied_seqs)
    if out.acks:
        out.batch.acks_add[viewer] = list(out.acks)
    return out


def _rows_for(entry: Entry, rows_by_token: Mapping[str, list[LibraryRow]]) -> list[LibraryRow]:
    """One live row of the item, the lowest id: the writer reaches every copy from there."""
    found = {r.key: r for t in entry.tokens for r in rows_by_token.get(t, [])}
    if not found:
        return []
    return [min(found.values(), key=lambda r: r.key.kodi_id)]


def settle_unsent(viewer: str, fetched: set[tuple[str, str]], store: RecordStore) -> Batch:
    """After a complete fetch: a carried person change with no queued change for its group
    in the whole fetch landed, so it leaves unsent. fetched holds the pages' keys, resolved
    here through merges a later page made."""
    current = {(store.resolve(viewer, k), g) for k, g in fetched}
    cleared: dict[str, list[str]] = {}
    for entry in store.entries(viewer):
        groups = [g for g in entry.unsent_upload if (entry.key, g) not in current]
        if groups:
            cleared[entry.key] = groups
    return Batch(unsent_cleared={viewer: cleared}) if cleared else Batch()
