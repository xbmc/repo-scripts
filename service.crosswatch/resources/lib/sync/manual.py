# SPDX-License-Identifier: GPL-2.0-only
"""A person's watched mark or rating made in Kodi, taken into the record.

The mark reaches here only after local.classify found it to be a person's (not playback, a
scan, Refresh information or the add-on's own write) and the worker drained it from the
inbox against a fresh read of the row. What happens to it depends on who owns the item:
- one owner: it goes into that viewer's record as a person's change, sent with the next delta;
- several owners: it goes to the assignment list, and nothing is sent until the household
  says whose it was (contract, Setup: shared items);
- no owner: nothing, as the item is in no upload.

Ratings follow the same split; a rating cleared to 0 is a removal, sent only with the same
setting on. A rating set on one copy of an item is the item's: the engine has the writer give
the other copies the value. With it off the record keeps its rating and Kodi keeps the person's 0: the writer
rates Kodi only for a queued change or a row that lost its rating, never on its own.

An unwatch is sent only with "Send removals made in Kodi" on. Wherever it isn't sent (the
setting is off, or a shared item waits on the assignment list) each owner's record keeps the
watch and notes the unwatch (History.local_unwatch), so the writer doesn't raise Kodi again
until CrossWatch brings a watch made after it.

Log events: none; the engine logs counts.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Union

from resources.lib.sync.items import LibraryRow, identity
from resources.lib.sync.record import (
    Assignment,
    Batch,
    Entry,
    Group,
    History,
    ItemState,
    Rating,
    RecordStore,
    fresh_state,
    merge,
)
from resources.lib.sync.rows import entry_meta, item_groups
from resources.lib.sync.settings import SyncSettings


@dataclass(frozen=True)
class Recorded:
    """The viewer's entry as the mark leaves it. sent is False for a change kept in the
    record only (an unwatch noted here, which CrossWatch must not hear about)."""

    viewer: str
    entry: Entry
    sent: bool


@dataclass(frozen=True)
class ToAssign:
    assignment: Assignment


@dataclass(frozen=True)
class Ignored:
    reason: str


LocalOutcome = Union[Recorded, ToAssign, Ignored]


def _watched_history(old: History, playcount: int, lastplayed: str) -> History:
    # Kodi's count never lowers the record's: the record may hold plays from the services.
    return History(
        watched=True, playcount=max(old.playcount, playcount, 1), lastplayed=lastplayed, event=old.event, src=old.src
    )


def _unwatched_history(old: History) -> History:
    return History(watched=False, explicit=True, unwatched=True, event=old.event, src=old.src)


def _new_entry(key: str, tokens: frozenset[str], meta: dict[str, Any]) -> Entry:
    """An entry for an item the viewer's record doesn't have yet, by the normal ownership
    rules: the mark is the first thing it records."""
    return Entry(key=key, tokens=tokens, meta=meta, state=fresh_state(), origin="person")


def _person_change(entry: Entry, history: History, made_at: str) -> Entry:
    return _person_group(entry, replace(entry.state, history=history), "history", made_at)


def _person_group(entry: Entry, state: ItemState, group: Group, made_at: str) -> Entry:
    return replace(
        entry,
        state=state,
        unsent={**entry.unsent, group: made_at},
        # A new person change is carried by a new upload, not by one that carried an older one.
        unsent_upload={k: v for k, v in entry.unsent_upload.items() if k != group},
        touched=True,
        change_count=entry.change_count + 1,
    )


def _with_history(entry: Entry, history: History) -> Entry:
    """A change the record keeps without sending: change_count is raised all the same, so an
    upload built before it doesn't settle over it."""
    return replace(entry, state=replace(entry.state, history=history), change_count=entry.change_count + 1)


def _note_unwatch(viewer: str, entry: Entry, next_upload_seq: int) -> Recorded | Ignored:
    old = entry.state.history
    if not old.watched:
        return Ignored("not_watched")
    if old.local_unwatch:
        return Ignored("already_unwatched")
    history = replace(old, local_unwatch=True, local_unwatch_seq=next_upload_seq)
    return Recorded(viewer, _with_history(entry, history), sent=False)


def _decide(
    viewer: str,
    entry: Entry,
    playcount: int,
    lastplayed: str,
    send_removals: bool,
    made_at: str,
    next_upload_seq: int,
) -> Recorded | Ignored:
    old = entry.state.history
    if playcount > 0:
        if old.watched and not old.local_unwatch:
            return Ignored("already_watched")
        if old.watched:
            # Watched again after a noted unwatch: the record already holds the watch, so only
            # the note goes; nothing to send.
            lifted = replace(old, local_unwatch=False, local_unwatch_seq=0)
            return Recorded(viewer, _with_history(entry, lifted), sent=False)
        return Recorded(viewer, _person_change(entry, _watched_history(old, playcount, lastplayed), made_at), True)
    if not send_removals:
        return _note_unwatch(viewer, entry, next_upload_seq)
    if not old.watched:
        return Ignored("not_watched")
    return Recorded(viewer, _person_change(entry, _unwatched_history(old), made_at), True)


def watched_change(
    entries: Mapping[str, Entry],
    row: LibraryRow,
    show: Mapping[str, Any] | None,
    *,
    playcount: int,
    lastplayed: str,
    owners: Sequence[str],
    settings: SyncSettings,
    made_at: str,
    next_upload_seq: int,
    new_id: Callable[[], str],
) -> list[LocalOutcome]:
    """A mark on row: playcount above 0 is a watch, 0 an unwatch.

    entries holds each owner's entry for the item, already merged (an owner without one is
    left out). lastplayed is UTC, as the library read gives it. next_upload_seq must be above
    every upload_seq the viewer has sent and every seq CrossWatch reported: a CrossWatch watch
    with `after` at or above it was made after this unwatch, and lifts the note.
    """
    owners = list(dict.fromkeys(owners))
    if not owners:
        return [Ignored("no_owner")]
    key = identity(row.key.kind, row.raw, show)
    tokens = frozenset(row.tokens)
    meta = entry_meta(row, show)
    if len(owners) == 1:
        viewer = owners[0]
        entry = entries.get(viewer) or _new_entry(key, tokens, meta)
        return [_decide(viewer, entry, playcount, lastplayed, settings.send_removals, made_at, next_upload_seq)]
    out: list[LocalOutcome] = []
    if playcount <= 0:
        # Until someone says whose it was (or for good, with removals off), Kodi keeps the
        # person's unwatch: every owner's record notes it, and the shared rule then holds.
        for viewer in owners:
            entry = entries.get(viewer)
            if entry is not None:
                noted = _note_unwatch(viewer, entry, next_upload_seq)
                if isinstance(noted, Recorded):
                    out.append(noted)
        if not settings.send_removals:
            return out or [Ignored("removals_off")]
    history = _watched_history(History(), playcount, lastplayed) if playcount > 0 else _unwatched_history(History())
    assignment = Assignment(
        id=new_id(),
        entry_key=key,
        tokens=tokens,
        group="history",
        value=ItemState(history=history),
        title=_title(row),
        at=made_at,
        meta=meta,
    )
    return [*out, ToAssign(assignment)]


def _decide_rating(viewer: str, entry: Entry, value: int, send_removals: bool, made_at: str) -> Recorded | Ignored:
    old = entry.state.rating
    if value == old.value:
        return Ignored("same_rating")
    if value == 0 and not send_removals:
        return Ignored("removals_off")
    rating = Rating(value=value, removed=value == 0, src=old.src)
    return Recorded(viewer, _person_group(entry, replace(entry.state, rating=rating), "ratings", made_at), True)


def rating_change(
    entries: Mapping[str, Entry],
    row: LibraryRow,
    show: Mapping[str, Any] | None,
    *,
    value: int,
    owners: Sequence[str],
    settings: SyncSettings,
    made_at: str,
    new_id: Callable[[], str],
) -> list[LocalOutcome]:
    """A person's rating found by the rating scan: value 0 is a cleared rating. entries as
    for watched_change."""
    owners = list(dict.fromkeys(owners))
    if not owners:
        return [Ignored("no_owner")]
    if value == 0 and not settings.send_removals:
        return [Ignored("removals_off")]
    key = identity(row.key.kind, row.raw, show)
    tokens = frozenset(row.tokens)
    meta = entry_meta(row, show)
    if len(owners) == 1:
        viewer = owners[0]
        entry = entries.get(viewer) or _new_entry(key, tokens, meta)
        return [_decide_rating(viewer, entry, value, settings.send_removals, made_at)]
    if all((e := entries.get(v)) is not None and e.state.rating.value == value for v in owners):
        return [Ignored("same_rating")]
    assignment = Assignment(
        id=new_id(),
        entry_key=key,
        tokens=tokens,
        group="ratings",
        value=ItemState(rating=Rating(value=value, removed=value == 0)),
        title=_title(row),
        at=made_at,
        meta=meta,
    )
    return [ToAssign(assignment)]


def rating_window_write(
    entries: Mapping[str, Entry],
    row: LibraryRow,
    show: Mapping[str, Any] | None,
    *,
    value: int,
    rated: Sequence[str],
    owners: Sequence[str],
    made_at: str,
) -> list[LocalOutcome]:
    """The add-on's own rating window wrote value to Kodi for the viewers in rated (sync ids).
    The caller passes row as read back after the write, and only when it holds value: a write
    whose answer was lost may not have landed.

    Their scores already went to CrossWatch as rate events, so the record takes them as a
    person's change only when the viewers who rated are exactly the item's owners: Kodi's
    one rating then stands for each of them, and an equal value at CrossWatch is a no-op.
    Otherwise the owners' records are left alone; the caller still stores the row's Seen,
    so the next rating scan doesn't take the window's write for a person's change.
    """
    owners = list(dict.fromkeys(owners))
    if not owners or set(rated) != set(owners) or value <= 0:
        return [Ignored("not_the_owners")]
    key = identity(row.key.kind, row.raw, show)
    tokens = frozenset(row.tokens)
    meta = entry_meta(row, show)
    return [
        _decide_rating(viewer, entries.get(viewer) or _new_entry(key, tokens, meta), value, False, made_at)
        for viewer in owners
    ]


def _title(row: LibraryRow) -> str:
    raw = row.raw
    if row.key.kind == "episodes":
        season, episode = raw.get("season"), raw.get("episode")
        show = str(raw.get("showtitle") or "")
        if isinstance(season, int) and isinstance(episode, int):
            return f"{show} S{season:02d}E{episode:02d}"
        return show or str(raw.get("title") or "")
    year = raw.get("year")
    title = str(raw.get("title") or "")
    return f"{title} ({year})" if isinstance(year, int) and year > 0 else title


def apply_assignment(
    assignment: Assignment, viewer_ids: Sequence[str], store: RecordStore, settings: SyncSettings, next_upload_seq: int
) -> Batch:
    """The household said whose a shared change was: each chosen viewer's record takes it as
    a person's change made at the time of the mark, by the same rules as a single owner's and
    the removals setting as it is now. A viewer whose record holds a newer person change for
    the item keeps it. No viewer chosen drops it; the unwatch notes stay."""
    batch = Batch(assignments_done=[assignment.id])
    for viewer in dict.fromkeys(viewer_ids):
        found = store.match(viewer, assignment.tokens)
        changed = len(found) > 1
        if changed:
            entry = merge(found)
            batch.merged.setdefault(viewer, {})[entry.key] = [e.key for e in found]
        elif found:
            entry = found[0]
        else:
            entry = _new_entry(assignment.entry_key, assignment.tokens, dict(assignment.meta))
        if not assignment.tokens <= entry.tokens:
            entry = replace(entry, tokens=entry.tokens | assignment.tokens, change_count=entry.change_count + 1)
            changed = True
        newer = entry.unsent.get(assignment.group, "")
        outcome: Recorded | Ignored
        if newer and newer > assignment.at:
            outcome = Ignored("newer_change")
        elif assignment.group == "ratings":
            value = assignment.value.rating.value
            outcome = _decide_rating(viewer, entry, value, settings.send_removals, assignment.at)
        else:
            history = assignment.value.history
            playcount = max(history.playcount, 1) if history.watched else 0
            outcome = _decide(
                viewer, entry, playcount, history.lastplayed, settings.send_removals, assignment.at, next_upload_seq
            )
        if isinstance(outcome, Recorded):
            batch.entries.setdefault(viewer, []).append(outcome.entry)
        elif changed and found:
            # Nothing to record, but the merge or the new tokens the match found are kept.
            batch.entries.setdefault(viewer, []).append(entry)
    return batch


def existing_ratings(
    entries: Sequence[Entry],
    rows: Sequence[LibraryRow],
    owners_of: Callable[[LibraryRow], Sequence[str]],
    viewer: str,
    made_at: str,
) -> list[Entry]:
    """Send existing ratings: the viewer's single-owner items the first run seeded, that
    CrossWatch queued no rating for (none, and none removed), whose Kodi rating still equals
    the one the first full stored (on every rated copy; an unrated copy doesn't count). A
    rating given later, perhaps by another owner, is never sent as this viewer's. An item
    whose rows hit two entries not yet merged waits for the next full to merge them. Each
    goes up as a person change made now."""
    by_token: dict[str, list[Entry]] = {}
    for entry in entries:
        for token in entry.tokens:
            by_token.setdefault(token, []).append(entry)
    out: dict[str, Entry] = {}
    for item in item_groups(list(rows)):
        if any(tuple(dict.fromkeys(owners_of(r))) != (viewer,) for r in item):
            continue
        hits = {e.key: e for r in item for t in r.tokens for e in by_token.get(t, ())}
        if len(hits) != 1:
            continue
        entry = next(iter(hits.values()))
        if entry.key in out or entry.origin != "seed" or entry.seed_rating <= 0:
            continue
        rating = entry.state.rating
        if rating.value or rating.from_cw or rating.removed:
            continue
        rated = [value for r in item if (value := int(r.raw.get("userrating") or 0))]
        if not rated or any(value != entry.seed_rating for value in rated):
            continue
        state = replace(entry.state, rating=Rating(value=entry.seed_rating, src=rating.src))
        out[entry.key] = _person_group(entry, state, "ratings", made_at)
    return list(out.values())
