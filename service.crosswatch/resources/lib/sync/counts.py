# SPDX-License-Identifier: GPL-2.0-only
"""Who owns what in the library, counted for the household's screens.

The setup screen counts from its own library read; the engine counts after each complete read
and keeps the result in the status file, so the status screen opens without reading the
library. Both count with the same owners function the engine syncs with.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from resources.lib.sync.items import Library, LibraryRow

# The status file holds at most this many titles for the screen to list; the counts stay whole.
UNOWNED_TITLES_LIMIT = 200


@dataclass
class Counts:
    """Shows and films per owner (sync id), shared between owners, and owned by nobody."""

    shows: dict[str, set[int]] = field(default_factory=dict)
    films: dict[str, int] = field(default_factory=dict)
    shared_shows: set[int] = field(default_factory=set)
    shared_films: int = 0
    unowned_shows: set[int] = field(default_factory=set)
    unowned_films: int = 0
    unowned_film_titles: list[str] = field(default_factory=list)


def count_owners(library: Library, owners: Callable[[LibraryRow], Sequence[str]]) -> Counts:
    """A film counts once however many copies Kodi holds (the same ids), a show once in
    each group its episodes fall into."""
    counts = Counts()
    seen_films: set[tuple[str, ...]] = set()
    for row in library.movies:
        # The same keys CrossWatch matches on, so copies count as the one film they are.
        key = row.tokens
        if key in seen_films:
            continue
        seen_films.add(key)
        who = list(dict.fromkeys(owners(row)))
        if not who:
            counts.unowned_films += 1
            counts.unowned_film_titles.append(_film_title(row))
        elif len(who) > 1:
            counts.shared_films += 1
        else:
            counts.films[who[0]] = counts.films.get(who[0], 0) + 1
    for row in library.episodes:
        show = row.show_kodi_id
        if show is None:
            continue
        who = list(dict.fromkeys(owners(row)))
        if not who:
            counts.unowned_shows.add(show)
        elif len(who) > 1:
            counts.shared_shows.add(show)
        else:
            counts.shows.setdefault(who[0], set()).add(show)
    return counts


def _film_title(row: LibraryRow) -> str:
    title = str(row.raw.get("title") or "").strip()
    year = row.raw.get("year")
    return f"{title} ({year})" if isinstance(year, int) and year > 0 else title


def unowned_titles(counts: Counts, library: Library) -> list[str]:
    """Sorted titles of the shows and films nobody owns, at most UNOWNED_TITLES_LIMIT."""
    shows = [str(library.tvshows.get(show, {}).get("title") or "").strip() for show in counts.unowned_shows]
    titles = sorted((t for t in [*shows, *counts.unowned_film_titles] if t), key=str.casefold)
    return titles[:UNOWNED_TITLES_LIMIT]


def to_status(counts: Counts) -> dict[str, Any]:
    """The status file's form: numbers only, [shows, films] per group."""
    owners = set(counts.shows) | set(counts.films)
    return {
        "viewers": {v: [len(counts.shows.get(v, ())), counts.films.get(v, 0)] for v in sorted(owners)},
        "shared": [len(counts.shared_shows), counts.shared_films],
        "unowned": [len(counts.unowned_shows), counts.unowned_films],
    }


def pair(raw: Any) -> tuple[int, int]:
    """[shows, films] from the status file, (0, 0) for anything else."""
    if isinstance(raw, list) and len(raw) == 2 and all(isinstance(n, int) and not isinstance(n, bool) for n in raw):
        return raw[0], raw[1]
    return 0, 0
