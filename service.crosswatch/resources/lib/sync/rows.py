# SPDX-License-Identifier: GPL-2.0-only
"""Which rows one viewer's upload carries, with which state.

A library read gives Kodi's rows; the record gives the viewer's state. An upload row is the
library row's identity with the record's state, never Kodi's own play count (contract, "Viewer
state, not Kodi state"):
- copies of one item (rows sharing a token) are one item, sent once as its lowest Kodi id,
  as CrossWatch's _live_by_identity keeps the lowest (_addon_sync.py:1166);
- an item the viewer owns that the record doesn't know yet becomes a new entry: from Kodi's
  own state only for a seed viewer's first full and a single owner, otherwise empty (a new
  owner never inherits another viewer's watches);
- an item whose tokens hit several entries merges them (record.merge);
- a row first seen whose item Kodi showed watched or rated before, and no longer does, gets a
  catch-up intent: Refresh information, a clean and rescan or a file upgrade lost it. A
  person's unwatch the add-on saw was stored as Seen first, so it is never undone this way;
- an entry with no live row goes up as an in_library: false row from its meta, in a full only
  when it has something CrossWatch hasn't settled (rows left out remove nothing).

Log events: none; the engine logs counts.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from resources.lib.sync.items import Library, LibraryRow, identity
from resources.lib.sync.ownership import OwnersOf
from resources.lib.sync.record import Entry, History, ItemState, PendingWrite, Resume, Seen, fresh_state, merge
from resources.lib.sync.upload import UploadRow

Mode = Literal["full", "delta"]

_MOVIE_FIELDS = ("movieid", "uniqueid", "title", "year", "file", "dateadded")
_EPISODE_FIELDS = ("episodeid", "tvshowid", "uniqueid", "title", "showtitle", "season", "episode", "file", "dateadded")


@dataclass
class ViewerRows:
    rows: list[UploadRow] = field(default_factory=list)
    tvshows: dict[int, dict[str, Any]] = field(default_factory=dict)
    # surviving key -> every key merged into it, itself included
    merged: dict[str, list[str]] = field(default_factory=dict)
    # entries to write: new ones, merged ones, ones that gained tokens
    entries: list[Entry] = field(default_factory=list)
    catch_up: list[PendingWrite] = field(default_factory=list)
    # live episodes whose show row the read didn't have, sent as removed rows
    orphans: int = 0


def first_run_state(row: LibraryRow) -> ItemState:
    """Kodi's own history and resume for a seed viewer's single-owner item; never its rating,
    which a household sends on purpose with "Send existing ratings"."""
    raw = row.raw
    playcount = int(raw.get("playcount") or 0)
    history = History(watched=playcount > 0, playcount=playcount, lastplayed=str(raw.get("lastplayed") or ""))
    resume = raw.get("resume") or {}
    return ItemState(
        history=history,
        resume=Resume(position=float(resume.get("position") or 0), total=float(resume.get("total") or 0)),
    )


def _sorted_ids(uniqueid: Any) -> dict[str, Any]:
    # CrossWatch keeps the first value per namespace in key order, so send keys sorted.
    return {k: uniqueid[k] for k in sorted(uniqueid, key=str)} if isinstance(uniqueid, Mapping) else {}


def _show_row(show: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tvshowid": show.get("tvshowid"),
        "uniqueid": _sorted_ids(show.get("uniqueid")),
        "title": show.get("title") or "",
        "year": show.get("year") or 0,
    }


def entry_meta(row: LibraryRow, show: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = row.raw
    meta: dict[str, Any] = {
        "uniqueid": _sorted_ids(raw.get("uniqueid")),
        "file": row.key.file,
        "title": raw.get("title") or "",
    }
    if row.key.kind == "movies":
        meta["year"] = raw.get("year") or 0
    else:
        meta.update(showtitle=raw.get("showtitle") or "", season=raw.get("season"), episode=raw.get("episode"))
        if show is not None:
            meta["show"] = {k: v for k, v in _show_row(show).items() if k != "tvshowid"}
    return meta


def _state_fields(state: ItemState) -> dict[str, Any]:
    history = state.history
    fields: dict[str, Any] = {
        # CrossWatch reads playcount 0 as not watched, so a watch never goes up as 0.
        "playcount": max(history.playcount, 1) if history.watched else 0,
        "lastplayed": history.lastplayed if history.watched else "",
        "userrating": state.rating.value,
        "resume": {"position": state.resume.position, "total": state.resume.total},
    }
    if history.unwatched:
        fields["unwatched"] = True
    return fields


def _live_row(row: LibraryRow, state: ItemState) -> dict[str, Any]:
    fields = _MOVIE_FIELDS if row.key.kind == "movies" else _EPISODE_FIELDS
    out = {k: row.raw[k] for k in fields if k in row.raw}
    out["uniqueid"] = _sorted_ids(row.raw.get("uniqueid"))
    out["file"] = row.key.file
    out.update(_state_fields(state))
    return out


def _removed_row(entry: Entry, kind: str) -> dict[str, Any]:
    meta = entry.meta
    out: dict[str, Any] = {
        "in_library": False,
        "uniqueid": _sorted_ids(meta.get("uniqueid")),
        "title": meta.get("title") or "",
    }
    if meta.get("file"):
        out["file"] = meta["file"]
    if kind == "movies":
        out["year"] = meta.get("year") or 0
    else:
        out.update(showtitle=meta.get("showtitle") or "", season=meta.get("season"), episode=meta.get("episode"))
        if isinstance(meta.get("show"), Mapping):
            out["show"] = dict(meta["show"])
    out.update(_state_fields(entry.state))
    return out


def item_groups(rows: Sequence[LibraryRow]) -> list[list[LibraryRow]]:
    """Rows sharing a token are one item; each item's rows sorted by Kodi id."""
    parent: dict[int, int] = {}

    def find(i: int) -> int:
        while parent.get(i, i) != i:
            parent[i] = parent.get(parent[i], parent[i])
            i = parent[i]
        return i

    by_token: dict[str, int] = {}
    for i, row in enumerate(rows):
        for token in row.tokens:
            if token in by_token:
                a, b = find(i), find(by_token[token])
                if a != b:
                    parent[max(a, b)] = min(a, b)
            else:
                by_token[token] = i
    groups: dict[int, list[LibraryRow]] = {}
    for i, row in enumerate(rows):
        groups.setdefault(find(i), []).append(row)
    return [sorted(g, key=lambda r: r.key.kodi_id) for g in groups.values()]


def _kind_of_entry(entry: Entry) -> str:
    return "episodes" if entry.key.startswith("episodes") else "movies"


def viewer_rows(
    library: Library,
    *,
    viewer: str,
    owners: OwnersOf,
    match: Callable[[frozenset[str]], list[Entry]],
    seen_for: Callable[[tuple[str, ...], str], Seen | None],
    new_id: Callable[[], str],
    seed: bool,
    entries: Sequence[Entry],
    seen: Mapping[Any, Seen],
    mode: Mode,
    touched: set[str],
    now_utc: str,
) -> ViewerRows:
    """The rows one viewer's full or delta carries.

    A delta carries only entries in `touched` (changed since their last upload), plus the
    live rows sharing a file with a removed one, which must land in the same request.
    """
    out = ViewerRows()
    hit: set[str] = set()
    # Entries as this pass leaves them, so two items landing on one entry share one version.
    done: dict[str, Entry] = {}
    live_files: dict[str, list[UploadRow]] = {}
    for kind_rows in (library.movies, library.episodes):
        for item in item_groups(kind_rows):
            who = tuple(dict.fromkeys(v for row in item for v in owners(row)))
            if viewer not in who:
                continue
            rep = item[0]
            show = library.tvshows.get(rep.show_kodi_id) if rep.show_kodi_id is not None else None
            tokens = frozenset(t for r in item for t in r.tokens)
            found = [done.get(e.key, e) for e in match(tokens)]
            found = list({e.key: e for e in found}.values())
            changed = False
            if len(found) > 1:
                entry = merge(found)
                out.merged.setdefault(entry.key, [])
                out.merged[entry.key] = sorted({*out.merged[entry.key], *(e.key for e in found)})
                changed = True
            elif found:
                entry = found[0]
            elif mode == "delta":
                # New items reach CrossWatch with the next full, which also creates their entry.
                continue
            else:
                seeded = seed and len(who) == 1
                entry = Entry(
                    key=identity(rep.key.kind, rep.raw, show),
                    tokens=tokens,
                    meta=entry_meta(rep, show),
                    state=_seed_state(item) if seeded else fresh_state(),
                    origin="seed" if seeded else "empty",
                    seed_rating=max(int(r.raw.get("userrating") or 0) for r in item) if seeded else 0,
                )
                changed = True
            if found:
                meta = {**entry.meta, **entry_meta(rep, show)}
                if not tokens <= entry.tokens or meta != entry.meta:
                    # Its file or title moved on, or it gained ids: keep the entry current, so
                    # a removed row later carries the right file.
                    entry = replace(entry, tokens=entry.tokens | tokens, meta=meta, change_count=entry.change_count + 1)
                    changed = True
                out.catch_up.extend(_catch_up(item, entry, who, seen, seen_for, new_id, now_utc))
            if changed:
                done[entry.key] = entry
            sent_keys = {entry.key, *out.merged.get(entry.key, ())}
            hit |= sent_keys
            if mode == "delta" and not sent_keys & touched:
                # Not changed: sent only when a removed row on its file needs it alongside, and
                # never an orphan, whose show row this request couldn't carry.
                if not (rep.key.kind == "episodes" and show is None):
                    for row in item:
                        live_files.setdefault(row.key.file, []).append(
                            UploadRow(entry.key, row.key.kind, _live_row(row, entry.state), together=row.key.file)
                        )
                continue
            if rep.key.kind == "episodes" and show is None:
                # Its show row wasn't read: CrossWatch would refuse the episode, so it goes up
                # removed, keeping its history and ratings there.
                out.orphans += 1
                out.rows.append(UploadRow(entry.key, "episodes", _removed_row(entry, "episodes"), removed=True))
                continue
            if show is not None and rep.show_kodi_id is not None:
                out.tvshows[rep.show_kodi_id] = _show_row(show)
            # Every copy goes up with the item's state: CrossWatch keeps each row by Kodi id and
            # picks the lowest itself (_live_by_identity), and a copy carrying ids from two
            # entries is what makes it merge them, as the record just did.
            for row in item:
                out.rows.append(UploadRow(entry.key, row.key.kind, _live_row(row, entry.state), together=row.key.file))
    out.entries = list(done.values())
    for entry in entries:
        if entry.key in hit:
            continue
        wanted = entry.key in touched if mode == "delta" else bool(entry.unsent or entry.touched)
        if not wanted:
            continue
        kind = _kind_of_entry(entry)
        file = str(entry.meta.get("file") or "")
        out.rows.append(UploadRow(entry.key, kind, _removed_row(entry, kind), removed=True, together=file))  # type: ignore[arg-type]
        for live in live_files.pop(file, []) if file else []:
            out.rows.append(live)
            show_id = live.row.get("tvshowid")
            if live.kind == "episodes" and isinstance(show_id, int) and show_id in library.tvshows:
                out.tvshows[show_id] = _show_row(library.tvshows[show_id])
    return out


def _seed_state(item: Sequence[LibraryRow]) -> ItemState:
    """A seed's state from the copy Kodi shows most watched: a watch on any copy is real."""
    best = max(item, key=lambda r: (int(r.raw.get("playcount") or 0), str(r.raw.get("lastplayed") or "")))
    return first_run_state(best)


def _catch_up(
    item: Sequence[LibraryRow],
    entry: Entry,
    who: Sequence[str],
    seen: Mapping[Any, Seen],
    seen_for: Callable[[tuple[str, ...], str], Seen | None],
    new_id: Callable[[], str],
    now_utc: str,
) -> list[PendingWrite]:
    """Intents for rows Kodi lost state on: first seen, while the item was watched or rated."""
    out: list[PendingWrite] = []
    for row in item:
        if seen.get(row.key) is not None:
            continue
        before = seen_for(row.tokens, row.key.file)
        if before is None:
            continue
        if before.playcount > 0 and int(row.raw.get("playcount") or 0) == 0:
            out.append(PendingWrite(id=new_id(), row=row.key, tokens=entry.tokens, group="history", created=now_utc))
        if len(who) == 1 and before.userrating > 0 and int(row.raw.get("userrating") or 0) == 0:
            out.append(PendingWrite(id=new_id(), row=row.key, tokens=entry.tokens, group="ratings", created=now_utc))
    return out
