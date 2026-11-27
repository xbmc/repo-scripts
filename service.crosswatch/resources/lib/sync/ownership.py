# SPDX-License-Identifier: GPL-2.0-only
"""Which viewers own a library item, for library sync.

Ownership uses the same tiers as playback identity (identity.resolve), in the same order:
playlist membership, the active profile, a remembered answer, the only viewer. It is
decided here over the whole library rather than per play, so it reads an immutable
snapshot of the playlist index that the service thread publishes, never the controller's
live index.

Owners are returned as sync ids, in viewers.json order, because the record and the wire
know viewers by sync id; a name that is no longer a configured viewer, or a viewer without
a sync id yet, owns nothing.

The profile tier counts only when this profile has a database of its own: on a shared
library every profile sees the same watched state, so the profile says nothing about whose
item it is.

Log events: none; callers log counts.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Tuple

from resources.lib.media import clean_ids
from resources.lib.models import Viewer
from resources.lib.playlist_index import PlaylistIndex
from resources.lib.prompt import LIBRARY_KEY_PREFIX, key_for_show
from resources.lib.storage import RememberedAnswer
from resources.lib.sync.items import LibraryRow

OwnersOf = Callable[[LibraryRow], Tuple[str, ...]]


@dataclass(frozen=True)
class IndexSnapshot:
    """The playlist index as the service thread last published it, with the times the sync
    engine judges it by. All times come from the controller's monotonic clock."""

    index: PlaylistIndex | None
    built_at: float
    invalidated_at: float
    viewers: tuple[Viewer, ...]
    unreadable: tuple[str, ...] = ()

    def usable(self, *, last_scan_end: float, last_viewer_change: float, show_ids_changed_at: float) -> bool:
        """Complete, and built after everything that could have changed membership."""
        if self.index is None or self.index.degraded or self.unreadable:
            return False
        newest_change = max(self.invalidated_at, last_scan_end, last_viewer_change, show_ids_changed_at)
        return self.built_at >= newest_change


EMPTY_SNAPSHOT = IndexSnapshot(index=None, built_at=0.0, invalidated_at=0.0, viewers=())


def _same_year(stored: int | None, current: Any) -> bool:
    # Kodi reports an unknown show year as 0, while an answer stores None for it.
    return (stored or 0) == (current if isinstance(current, int) and not isinstance(current, bool) else 0)


def _remembered(
    row: LibraryRow, show: Mapping[str, Any] | None, answers: Mapping[str, RememberedAnswer]
) -> tuple[str, ...]:
    if row.key.kind != "episodes" or show is None:
        return ()
    key = key_for_show(clean_ids(show.get("uniqueid")), row.show_kodi_id)
    answer = answers.get(key) if key else None
    if answer is None:
        return ()
    if key is not None and key.startswith(LIBRARY_KEY_PREFIX):
        # The same guard as prompt.recall: a key on Kodi's database id counts only while the
        # show at that id still has the title and year the answer was given for.
        title = str(show.get("title") or "") or None
        if answer.title is None or answer.title != title or not _same_year(answer.year, show.get("year")):
            return ()
    return answer.viewers


def owners(
    row: LibraryRow,
    *,
    snapshot: IndexSnapshot,
    shows: Mapping[int, Mapping[str, Any]],
    answers: Mapping[str, RememberedAnswer],
    profile_label: str,
    private_profile_db: bool,
) -> tuple[str, ...]:
    index = snapshot.index
    if index is None or index.degraded or snapshot.unreadable:
        return ()
    viewers = snapshot.viewers
    known = {v.name for v in viewers}
    # Each tier keeps only configured viewers before deciding, as identity._by_playlist
    # does: an index built before a removal must not stop the later tiers from answering.
    if row.key.kind == "episodes":
        names = index.viewers_for("tvshow", row.show_kodi_id)
    else:
        names = index.viewers_for("movie", row.key.kodi_id)
    names = tuple(n for n in names if n in known)
    if not names and private_profile_db and profile_label:
        wanted = profile_label.casefold()
        names = tuple(v.name for v in viewers if any(p.casefold() == wanted for p in v.profiles))
    if not names:
        show = shows.get(row.show_kodi_id) if row.show_kodi_id is not None else None
        names = tuple(n for n in _remembered(row, show, answers) if n in known)
    if not names and len(viewers) == 1:
        names = (viewers[0].name,)
    wanted_names = set(names)
    return tuple(v.sync_id for v in viewers if v.name in wanted_names and v.sync_id)


def owners_of(
    snapshot: IndexSnapshot,
    shows: Mapping[int, Mapping[str, Any]],
    answers: Mapping[str, RememberedAnswer],
    profile_label: str,
    private_profile_db: bool,
) -> OwnersOf:
    def decide(row: LibraryRow) -> tuple[str, ...]:
        return owners(
            row,
            snapshot=snapshot,
            shows=shows,
            answers=answers,
            profile_label=profile_label,
            private_profile_db=private_profile_db,
        )

    return decide


def moved_viewers(rows: Iterable[LibraryRow], before: OwnersOf, after: OwnersOf) -> frozenset[str]:
    """The viewers who gained or lost an item between two ownership decisions over the same
    rows."""
    moved: set[str] = set()
    for row in rows:
        moved |= set(before(row)) ^ set(after(row))
    return frozenset(moved)


@dataclass(frozen=True)
class OwnershipCounts:
    per_viewer: dict[str, int] = field(default_factory=dict)
    shared: int = 0
    unowned: int = 0


def count(rows: Iterable[LibraryRow], owners_of_row: OwnersOf) -> OwnershipCounts:
    per_viewer: dict[str, int] = {}
    shared = unowned = 0
    for row in rows:
        found = owners_of_row(row)
        if len(found) == 1:
            per_viewer[found[0]] = per_viewer.get(found[0], 0) + 1
        elif found:
            shared += 1
        else:
            unowned += 1
    return OwnershipCounts(per_viewer=per_viewer, shared=shared, unowned=unowned)
