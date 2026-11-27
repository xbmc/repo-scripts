# SPDX-License-Identifier: GPL-2.0-only
"""What library sync writes to Kodi for one group of one item.

The record holds each owner's state; Kodi holds one play count, one rating and one bookmark
per row, shared by everyone who owns the item. These rules turn the owners' states into the
fields to write, worked out against Kodi's values read just before the write, so a change
that arrived weeks ago never overwrites what happened in Kodi since:
- play counts and last-played dates only go up; Kodi is lowered only for an explicit unwatch
  with "Send removals" on;
- a rating someone gave in Kodi that the rating scan hasn't seen yet is never overwritten;
- a resume point is written only for an item one person owns.

Everything is UTC; the writer converts dates to Kodi's local time.

Log events: none.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from resources.lib.sync.clock import parse_utc
from resources.lib.sync.constants import RESUME_GUARD_SECONDS
from resources.lib.sync.record import Group, History, ItemState, Seen
from resources.lib.sync.settings import SyncSettings


def _later(a: str, b: str) -> str:
    """The later of two UTC timestamps, as given; "" only when both are empty."""
    ta, tb = parse_utc(a), parse_utc(b)
    if ta is None:
        return b if tb is not None else ""
    if tb is None:
        return a
    return a if ta >= tb else b


def _newer(a: str, b: str) -> bool:
    """Whether a is strictly later than b; an empty b counts as the distant past."""
    ta, tb = parse_utc(a), parse_utc(b)
    return ta is not None and (tb is None or ta > tb)


def rule_met(histories: Sequence[History], settings: SyncSettings) -> bool:
    """Whether the owners' histories count as watched in Kodi, by the household's shared rule."""
    if not histories:
        return False
    if len(histories) == 1 or settings.shared_rule == "everyone":
        return all(h.watched for h in histories)
    return any(h.watched for h in histories)


def _history(
    owners: Sequence[ItemState], kodi: Seen, siblings_watched: bool, settings: SyncSettings, now_utc: str
) -> dict[str, Any]:
    histories = [o.history for o in owners]
    if rule_met(histories, settings):
        if any(h.local_unwatch for h in histories):
            # A person unwatched it here with removals off; only a newer watch raises it again.
            return {}
        watched = [h for h in histories if h.watched]
        count = max(kodi.playcount, min(h.playcount for h in watched), 1)
        newest = ""
        for h in watched:
            newest = _later(newest, h.lastplayed)
        lastplayed = _later(kodi.lastplayed, newest)
        if count == kodi.playcount and lastplayed == kodi.lastplayed:
            return {}
        if not lastplayed:
            if kodi.playcount > 0:
                # Already watched here without a date; stamping now would change nothing else.
                return {}
            # Never an empty date on a new watch: Kodi lists a watched item without one oddly.
            lastplayed = now_utc
        return {"playcount": count, "lastplayed": lastplayed}
    explicit_unwatch = any(h.explicit and not h.watched for h in histories)
    if kodi.playcount > 0 and explicit_unwatch and settings.send_removals and not siblings_watched:
        # Only the count, as JSON-RPC's SetMovieDetails takes it; the last-played date and the
        # bookmark stay, unlike Kodi's own "mark as unwatched", which nulls both.
        return {"playcount": 0}
    return {}


def _rating(owners: Sequence[ItemState], kodi: Seen, seen: Seen | None, settings: SyncSettings) -> dict[str, Any]:
    if seen is not None and kodi.userrating != seen.userrating:
        # Someone rated it in Kodi since the last scan; the scan sends that first.
        return {}
    ratings = [o.rating for o in owners]
    values = {r.value for r in ratings}
    if len(values) != 1:
        return {}
    value = values.pop()
    if value == 0:
        # A removal only when it was deliberate for every owner, by CrossWatch or a person,
        # and the household asked for removals; an owner who never rated it is no reason to
        # clear Kodi's rating.
        if not (settings.send_removals and all(r.removed for r in ratings) and kodi.userrating != 0):
            return {}
    if seen is None and kodi.userrating != 0:
        # A row first seen: only fill an empty rating, never replace one.
        return {}
    return {} if value == kodi.userrating else {"userrating": value}


def _resume(owners: Sequence[ItemState], kodi: Seen, seen: Seen | None, fetched_at: str) -> dict[str, Any]:
    if len(owners) != 1:
        # One bookmark per file can't hold several owners' positions.
        return {}
    owner = owners[0]
    position = owner.resume.position
    kodi_position = float((kodi.resume or {}).get("position") or 0)
    # "The last play here" as the add-on last saw it, not Kodi's date now: the writer's own
    # history write for the same item moves that, and must not change this decision.
    played_here = seen.lastplayed if seen is not None else kodi.lastplayed
    if position <= 0:
        finished_elsewhere = owner.history.watched and _newer(owner.history.lastplayed, played_here)
        if kodi_position > 0 and finished_elsewhere:
            return {"resume": {"position": 0, "total": 0}}
        return {}
    total = owner.resume.total
    if total > 0 and position >= total:
        # At or past the end: nothing to resume.
        return {}
    if fetched_at:
        # A queued resume carries no time. A play here after the fetch, or within the guard
        # before it, may be one CrossWatch hasn't seen, so Kodi's own bookmark stays. The
        # intent is dropped, not kept: fetched_at is fixed and plays only move forward, so it
        # could never become writable later.
        # Kodi's own date counts too: a play stopped below the watched threshold announces no
        # play count, so what the add-on last saw can predate it. Not when that date is the
        # owner's watch: the writer's own history write put it there, and it is no play here.
        own_write = parse_utc(kodi.lastplayed) == parse_utc(owner.history.lastplayed)
        local_play = _newer(kodi.lastplayed, played_here) and not own_write
        guard_from = kodi.lastplayed if local_play else played_here
        if _newer(guard_from, fetched_at):
            return {}
        fetched = parse_utc(fetched_at)
        played = parse_utc(guard_from)
        if fetched is not None and played is not None and fetched - played < timedelta(seconds=RESUME_GUARD_SECONDS):
            return {}
    if abs(position - kodi_position) < 1:
        return {}
    return {"resume": {"position": position, "total": total}}


def kodi_fields(
    group: Group,
    *,
    owners: Sequence[ItemState],
    kodi: Seen,
    seen: Seen | None,
    siblings_watched: bool,
    settings: SyncSettings,
    now_utc: str,
    fetched_at: str = "",
) -> dict[str, Any]:
    """The fields to write for one group, or {} when Kodi should stay as it is.

    owners are the item's owners' record states; kodi is the row read just before the write;
    seen is what the add-on last stored for that row (None for a row first seen); fetched_at
    is when the queued change behind a resume intent was fetched.
    """
    if not owners:
        return {}
    if group == "history":
        return _history(owners, kodi, siblings_watched, settings, now_utc)
    if group == "ratings":
        return _rating(owners, kodi, seen, settings)
    if group == "progress":
        return _resume(owners, kodi, seen, fetched_at)
    raise ValueError(f"unknown group {group!r}")
