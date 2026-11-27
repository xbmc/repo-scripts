# SPDX-License-Identifier: GPL-2.0-only
"""Library items as CrossWatch identifies them, and the library read that produces them.

Library sync only works if the add-on and CrossWatch agree on which upload row, record entry
and queued change are the same item. CrossWatch decides that with its own normaliser and
token rules (providers/sync/kodi/_common.py and _addon_sync.py in CrossWatch), so those are
ported here exactly, quirks included, instead of reusing media.clean_ids: an item the two
sides key differently would be uploaded as one item and changed as another.

Two items are the same when they share any token. Kodi's database id is never part of an
identity: Refresh information gives a row a new id, and SQLite reuses the highest one.

Log events: none; callers log what a read produced.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from resources.lib.media import strip_credentials

ItemKind = Literal["movies", "episodes"]

# CrossWatch's namespaces, in its matching order (_common.py UNIQUEID_NAMESPACES).
_NAMESPACES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("anidb", ("anidb",)),
    ("anilist", ("anilist",)),
    ("kitsu", ("kitsu",)),
    ("mal", ("myanimelist", "mal")),
    ("imdb", ("imdb",)),
    ("tmdb", ("tmdb", "themoviedb")),
    ("tvdb", ("tvdb", "thetvdb")),
)
_PLACEHOLDERS = frozenset({"none", "null", "nan", "unknown", "0", "-1"})

PLUGIN_PREFIX = "plugin://"

MOVIE_PROPERTIES = ["uniqueid", "title", "year", "file", "playcount", "lastplayed", "userrating", "resume", "dateadded"]
# Kodi's episodes have no "year" (Video.Fields.Episode in types.json); asking for it is an error.
EPISODE_PROPERTIES = [
    "uniqueid", "title", "file", "playcount", "lastplayed", "userrating", "resume", "dateadded",
    "tvshowid", "showtitle", "season", "episode",
]  # fmt: skip
SHOW_PROPERTIES = ["uniqueid", "title", "year"]
_DATE_FIELDS = ("lastplayed", "dateadded")


class JsonRpc(Protocol):
    def jsonrpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...


def kind_of(kodi_type: Literal["movie", "episode"]) -> ItemKind:
    """Kodi's singular item type as CrossWatch's plural kind."""
    return "movies" if kodi_type == "movie" else "episodes"


def _namespace(name: str, text: str) -> str | None:
    if text.lower().startswith("tt"):
        return "imdb"
    for namespace, needles in _NAMESPACES:
        if any(needle in name for needle in needles):
            return namespace
    return None


def normalize_ids(uniqueid: Any) -> dict[str, str]:
    """CrossWatch's normalize_uniqueids, with the keys taken in sorted order.

    The first value per namespace wins. CrossWatch stores item meta with sorted keys and
    normalises from that, so sorting here makes both sides pick the same value when two
    keys map to one namespace ("tmdb" and "themoviedb").
    """
    raw = uniqueid if isinstance(uniqueid, Mapping) else {}
    out: dict[str, str] = {}
    for key in sorted(raw, key=str):
        text = str(raw[key] or "").strip()
        if not text or text.lower() in _PLACEHOLDERS:
            continue
        name = "".join(ch for ch in str(key or "").strip().lower() if ch.isalnum())
        namespace = _namespace(name, text)
        if namespace:
            out.setdefault(namespace, text)
    return out


def _text(value: Any) -> str:
    return str(value or "").strip()[:200]


def _show_of(row: Mapping[str, Any], show: Mapping[str, Any] | None) -> Mapping[str, Any]:
    embedded = row.get("show")
    if isinstance(embedded, Mapping):
        return embedded
    return show if isinstance(show, Mapping) else {}


def identity(kind: ItemKind, row: Mapping[str, Any], show: Mapping[str, Any] | None = None) -> str:
    """CrossWatch's _identity: the fallback key of an item with no usable id.

    `str()` of a missing season or episode gives "None", as in CrossWatch; keep it.
    """
    ids = normalize_ids(row.get("uniqueid"))
    if ids:
        return kind + "|" + "|".join(f"{k}:{v}" for k, v in sorted(ids.items()))
    if kind == "episodes":
        show_ids = normalize_ids(_show_of(row, show).get("uniqueid"))
        if show_ids:
            owner = "show:" + "|".join(f"{k}:{v}" for k, v in sorted(show_ids.items()))
        else:
            owner = _text(row.get("showtitle") or _show_of(row, show).get("title")).casefold()
        return "|".join([kind, owner, str(row.get("season")), str(row.get("episode"))])
    return "|".join([kind, _text(row.get("title")).casefold(), str(row.get("year"))])


def tokens(kind: ItemKind, row: Mapping[str, Any], show: Mapping[str, Any] | None = None) -> list[str]:
    """CrossWatch's _tokens: every key an item can be matched on.

    An episode also carries one token per show id with its season and episode, which is
    what lets an episode that later gains ids of its own still match its old entry.
    """
    ids = normalize_ids(row.get("uniqueid"))
    out = [f"{kind}|{k}:{v}" for k, v in sorted(ids.items())]
    if kind == "episodes":
        show_ids = normalize_ids(_show_of(row, show).get("uniqueid"))
        out += [f"{kind}|show:{k}:{v}|{row.get('season')}|{row.get('episode')}" for k, v in sorted(show_ids.items())]
    return out or [identity(kind, row, show)]


def keep_show_ids(new_shows: MutableMapping[int, dict[str, Any]], old_shows: Mapping[int, Mapping[str, Any]]) -> None:
    """CrossWatch's _keep_show_ids: a show that lost its ids but kept its title keeps the
    old ids, so its episodes' tokens don't change under a scraper hiccup."""
    for key, row in list(new_shows.items()):
        old = old_shows.get(key) or {}
        if normalize_ids(row.get("uniqueid")) or not normalize_ids(old.get("uniqueid")):
            continue
        if _text(row.get("title")).casefold() == _text(old.get("title")).casefold():
            new_shows[key] = {**row, "uniqueid": dict(old.get("uniqueid") or {})}


def is_server_backed(file: str) -> bool:
    """Rows a media server add-on owns and rewrites, which sync must leave alone.

    Covers plugin:// paths. Rows a server add-on manages through direct paths have ordinary
    file paths; read_library takes those from the add-on's own map (server_maps.py).
    """
    return file.startswith(PLUGIN_PREFIX)


@dataclass(frozen=True)
class RowKey:
    library_id: str
    kind: ItemKind
    kodi_id: int
    file: str


@dataclass(frozen=True)
class LibraryRow:
    key: RowKey
    tokens: tuple[str, ...]
    raw: dict[str, Any]
    show_kodi_id: int | None


@dataclass
class Library:
    library_id: str
    movies: list[LibraryRow]
    episodes: list[LibraryRow]
    tvshows: dict[int, dict[str, Any]]
    sources: list[dict[str, str]]
    complete: bool
    # Rows left out because a media server add-on owns them, so a play-count change Kodi
    # announces for one is never taken for a person's mark.
    server_backed: frozenset[tuple[ItemKind, int]] = frozenset()


_METHODS: dict[str, tuple[str, str, str]] = {
    "movies": ("VideoLibrary.GetMovies", "movies", "movieid"),
    "episodes": ("VideoLibrary.GetEpisodes", "episodes", "episodeid"),
    "tvshows": ("VideoLibrary.GetTVShows", "tvshows", "tvshowid"),
}


class Stopped(Exception):
    pass


def pages(
    kodi: JsonRpc, what: str, properties: list[str], page: int, may_continue: Callable[[], bool]
) -> tuple[list[dict[str, Any]], bool]:
    """All rows of one list, page by page, and whether the total held still while paging.

    A short or empty page is not the end. Kodi applies LIMIT before it drops rows in locked
    sources but counts the total without that filter (VideoDatabase.cpp GetMoviesByWhere),
    so on a box with a master lock a page can come back empty with more rows after it.
    """
    method, field, _ = _METHODS[what]
    rows: list[dict[str, Any]] = []
    first_total: int | None = None
    total = 0
    start = 0
    while True:
        if not may_continue():
            raise Stopped
        result = kodi.jsonrpc(method, {"properties": properties, "limits": {"start": start, "end": start + page}})
        batch = [r for r in result.get(field) or [] if isinstance(r, dict)]
        total = int((result.get("limits") or {}).get("total") or 0)
        if first_total is None:
            first_total = total
        rows.extend(batch)
        start += page
        if start >= total:
            return rows, total == first_total


def _ids(kodi: JsonRpc, what: str) -> set[int]:
    method, field, id_field = _METHODS[what]
    result = kodi.jsonrpc(method, {"properties": []})
    return {int(r[id_field]) for r in result.get(field) or [] if isinstance(r, dict) and id_field in r}


def _convert_dates(raw: dict[str, Any], to_utc: Callable[[str], str]) -> dict[str, Any]:
    out = dict(raw)
    for name in _DATE_FIELDS:
        out[name] = to_utc(str(raw.get(name) or ""))
    return out


def read_library(
    kodi: JsonRpc,
    library_id: str,
    *,
    may_continue: Callable[[], bool],
    previous_shows: Mapping[int, Mapping[str, Any]],
    to_utc: Callable[[str], str],
    page: int = 500,
    server_rows: frozenset[tuple[ItemKind, int]] = frozenset(),
) -> Library | None:
    """Read the whole video library, or None when `may_continue` turns False mid-read.

    `server_rows` are the rows a media server add-on maps through direct paths
    (server_maps.py): server-backed like plugin:// rows, whatever their path.

    `complete` is False when the library changed under the read. Kodi pages with LIMIT and
    no ORDER BY (VideoDatabase.cpp GetMoviesByWhere), so on a library another box writes to,
    a row added and one removed between pages can leave a row unseen with the total intact.
    A final id-only pass catches that; it compares against the ids before server-backed rows
    are filtered out, or a household with a media server add-on would never read complete.
    """
    try:
        show_rows, shows_ok = pages(kodi, "tvshows", SHOW_PROPERTIES, page, may_continue)
        tvshows = {int(s["tvshowid"]): dict(s) for s in show_rows if "tvshowid" in s}
        keep_show_ids(tvshows, previous_shows)
        complete = shows_ok
        lists: dict[str, list[LibraryRow]] = {}
        server_backed: set[tuple[ItemKind, int]] = set()
        reads: tuple[tuple[ItemKind, list[str]], ...] = (("movies", MOVIE_PROPERTIES), ("episodes", EPISODE_PROPERTIES))
        for kind, properties in reads:
            raws, held = pages(kodi, kind, properties, page, may_continue)
            if not may_continue():
                raise Stopped
            id_field = _METHODS[kind][2]
            seen_ids = {int(r[id_field]) for r in raws if id_field in r}
            complete = complete and held and seen_ids == _ids(kodi, kind)
            mapped = {int(r[id_field]) for r in raws if id_field in r and (kind, int(r[id_field])) in server_rows}
            lists[kind] = [
                row
                for raw in raws
                if (row := _row(kind, raw, library_id, tvshows, to_utc)) is not None and row.key.kodi_id not in mapped
            ]
            if kind == "episodes":
                # A show added under the read: its episodes would get title tokens instead of
                # the show's ids, and CrossWatch refuses an episode whose show row is missing.
                complete = complete and all(r.show_kodi_id in tvshows for r in lists[kind])
            server_backed |= {(kind, kodi_id) for kodi_id in mapped}
            server_backed |= {
                (kind, int(raw[id_field]))
                for raw in raws
                if id_field in raw and is_server_backed(strip_credentials(str(raw.get("file") or "")))
            }
        sources = _sources(kodi)
    except Stopped:
        return None
    return Library(
        library_id=library_id,
        movies=lists["movies"],
        episodes=lists["episodes"],
        tvshows=tvshows,
        sources=sources,
        complete=complete,
        server_backed=frozenset(server_backed),
    )


def _row(
    kind: ItemKind,
    raw: dict[str, Any],
    library_id: str,
    tvshows: Mapping[int, Mapping[str, Any]],
    to_utc: Callable[[str], str],
) -> LibraryRow | None:
    id_field = _METHODS[kind][2]
    if id_field not in raw:
        return None
    file = strip_credentials(str(raw.get("file") or ""))
    if is_server_backed(file):
        return None
    row = _convert_dates({**raw, "file": file}, to_utc)
    show_kodi_id: int | None = None
    show: Mapping[str, Any] | None = None
    if kind == "episodes":
        show_kodi_id = int(raw.get("tvshowid") or 0) or None
        show = tvshows.get(show_kodi_id) if show_kodi_id is not None else None
    return LibraryRow(
        key=RowKey(library_id=library_id, kind=kind, kodi_id=int(raw[id_field]), file=file),
        tokens=tuple(tokens(kind, row, show)),
        raw=row,
        show_kodi_id=show_kodi_id,
    )


def _sources(kodi: JsonRpc) -> list[dict[str, str]]:
    result = kodi.jsonrpc("Files.GetSources", {"media": "video"})
    return [
        {"file": strip_credentials(str(s.get("file") or "")), "label": str(s.get("label") or "")}
        for s in result.get("sources") or []
        if isinstance(s, dict)
    ]
