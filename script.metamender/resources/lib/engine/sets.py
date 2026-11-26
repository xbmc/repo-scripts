"""Movie set planning: which library a Kodi set follows, which TMDB
collection it stands for, which set MetaMender manages for that collection,
which movies move out of a duplicate set into the managed one, and which
movies in no set join their collection's set.

Kodi sets carry no TMDB id, so a set is read through its member movies: their
files place them in a library (by effective folder settings, the longest
prefix wins, as for movies) and their stored TMDB collection says what the
set is. A set is managed only when its counted members clearly agree on both;
anything less leaves the set alone with a reason Details can show.

The planning (plan_sets) is pure. prepare_sets runs it against Kodi and the
tracker before the set pass: it asks TMDB for the collections it still
lacks, merges duplicate sets by moving their movies, adds movies in no set to
their collection's set (creating it when the collection has none), and hands
the pass the managed sets to scan. describe_set plans one set the same way
from what is stored, for Details and Update now, without asking a site or
writing.

Logging:
    Logger: 'sets'
    Key events:
        - sets.moved (INFO): a movie moved out of a duplicate set into the
          managed set of its collection (movie, from_set, to_set)
        - sets.move_failed (WARNING): Kodi refused the move or the join, or
          the movie did not land in the intended set (AddSet matches names
          by LIKE); a misfiled join is taken back out of its set
        - sets.joined (INFO): a movie in no set added to its collection's
          set (movie, set, setid, created: whether the write made the set)
        - sets.join_skipped (DEBUG): a join not written this scan, with a
          reason (name_collision, has_set, no_name, member_unchecked)
        - sets.plot_restored (INFO): a move made Kodi overwrite the managed
          set's plot with the old set's, and it was put back
        - sets.left_alone (DEBUG): a set the pass does not scan, with the
          plan's reason
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Callable, Optional

from resources.lib.data import kodi
from resources.lib.data.identity import compute_identity
from resources.lib.data.libraries import Library, LibraryConfig
from resources.lib.data.media_types import MOVIE, SET
from resources.lib.data.nfo import NFO, NO_NFO, UNREACHABLE, nfo_state
from resources.lib.data.setfolder import folder_for
from resources.lib.engine.art import ENGLISH
from resources.lib.engine.chain import TRANSIENT
from resources.lib.engine.scanctx import _call_provider, _ScanCtx, extract_ids
from resources.lib.providers import tmdb
from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import get_logger

log = get_logger('sets')

# Why a set is left alone (SetPlan.reason); None means it is managed.
LEFT_TIE_LIBRARY = "tie_library"    # two libraries hold equally many members
LEFT_NO_MEMBERS = "no_members"      # no member is in an included library and folder
LEFT_OFF = "off"                    # the set's library does not have Movie sets ticked
LEFT_NO_COLLECTION = "no_collection"  # no counted member belongs to a TMDB collection
LEFT_NO_MAJORITY = "no_majority"    # no collection holds more than half the members
LEFT_DUPLICATE = "duplicate"        # a second set of a managed collection; merged
LEFT_SHARED = "shared"              # a set of the user's own that shares a collection

# A stored "in no collection" answer is asked again at this age: TMDB adds
# movies to collections over time. An answer naming a collection is final.
NONE_RECHECK_DAYS = 180

_SETS_TOGGLE = "movie_sets"


@dataclass(frozen=True)
class SetPlan:
    setid: int
    title: str
    reason: Optional[str]
    # The TMDB collection the members chose; None when they did not get
    # that far (or chose none).
    collection_id: Optional[str]
    # A member file of the winning library group, the first in sorted order:
    # the scan reads the set's library and folder settings from it. "" when
    # no library won.
    file: str
    # The newest counted member's premiered date: the set's age.
    premiered: str
    # Every counted member's file, sorted (the set's NFO state is theirs).
    member_files: tuple[str, ...]
    # For a duplicate, the managed set it merges into.
    managed_setid: Optional[int]


@dataclass(frozen=True)
class Move:
    movieid: int
    identity: str
    from_setid: int
    from_name: str
    to_setid: int


def _name_key(name: str) -> str:
    return name.strip().lower()


def _set_members(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The movies of a kodi.get_movies_for_sets listing that sit in a set."""
    return [m for m in movies if int(m.get("setid") or 0) > 0]


def user_moved(move: Optional[dict[str, Any]], movieid: int, current_setid: int) -> bool:
    """Whether the user moved this movie after MetaMender did: the recorded
    move is for the same Kodi movie, which now sits outside the set it was
    moved to. A recorded user move (locked) stays one for good. Another
    movieid means Kodi re-added the movie (a refresh deletes and re-adds), so
    the earlier move says nothing about it."""
    if move is None:
        return False
    if move.get("locked"):
        return True
    return int(move.get("kodi_id") or 0) == movieid and int(
        move.get("to_setid") or 0) != current_setid


def _counted_library(member: dict[str, Any], libraries: LibraryConfig) -> Optional[Library]:
    """The member's library when both it and the member's folder are
    included; None means the member does not count."""
    return libraries.included_for(str(member.get("file") or ""))


def _library_vote(
    counted: list[tuple[dict[str, Any], Library]], libraries: LibraryConfig,
) -> tuple[Optional[Library], str]:
    """(winning library, its representative file), or (None, "") on a tie.
    Members are grouped by library and effective language and fallback, so
    a subfolder with its own language votes on its own."""
    groups: dict[tuple[str, str, str], list[str]] = {}
    owner: dict[tuple[str, str, str], Library] = {}
    for member, lib in counted:
        path = str(member.get("file") or "")
        _, language, fallback = libraries.folder_settings(path, lib)
        key = (lib.path, language, fallback)
        groups.setdefault(key, []).append(path)
        owner[key] = lib
    ranked = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
    if len(ranked) > 1 and len(ranked[0][1]) == len(ranked[1][1]):
        return None, ""
    key, files = ranked[0]
    return owner[key], min(files)


def _collection_vote(
    counted: list[tuple[dict[str, Any], Library]], collections: dict[str, str],
) -> tuple[Optional[str], Optional[str]]:
    """(collection id, None) when one collection holds more than half of the
    counted members, else (None, reason). A member with no stored collection
    counts against every collection."""
    votes: Counter[str] = Counter()
    for member, _ in counted:
        cid = _member_collection(member, collections)
        if cid:
            votes[cid] += 1
    if not votes:
        return None, LEFT_NO_COLLECTION
    cid, count = votes.most_common(1)[0]
    if count * 2 > len(counted):
        return cid, None
    return None, LEFT_NO_MAJORITY


def _member_collection(member: dict[str, Any], collections: dict[str, str]) -> str:
    tmdb_id = extract_ids(member)[0]
    return collections.get(tmdb_id, "") if tmdb_id else ""


def _first_plan(
    kodi_set: dict[str, Any], members: list[dict[str, Any]],
    libraries: LibraryConfig, collections: dict[str, str],
) -> tuple[SetPlan, int]:
    """The set's plan before managed and duplicate sets are told apart, and
    its number of counted members."""
    counted = [(m, lib) for m in members
               for lib in [_counted_library(m, libraries)] if lib is not None]
    files = tuple(sorted(str(m.get("file") or "") for m, _ in counted))
    dates = [str(m.get("premiered") or "") for m, _ in counted]
    base = SetPlan(
        setid=int(kodi_set.get("setid") or 0),
        title=str(kodi_set.get("title") or ""),
        reason=None, collection_id=None, file="",
        premiered=max(dates, default=""), member_files=files, managed_setid=None,
    )
    if not counted:
        return replace(base, reason=LEFT_NO_MEMBERS), 0
    lib, file = _library_vote(counted, libraries)
    if lib is None:
        return replace(base, reason=LEFT_TIE_LIBRARY), len(counted)
    base = replace(base, file=file)
    if _SETS_TOGGLE not in lib.toggles:
        return replace(base, reason=LEFT_OFF), len(counted)
    cid, reason = _collection_vote(counted, collections)
    return replace(base, reason=reason, collection_id=cid), len(counted)


def _managed_setid(
    group: list[tuple[SetPlan, int]], holder: Optional[int], known: frozenset[str],
) -> Optional[int]:
    """The set managed for a collection, or None when none may be.

    The set the tracker row records wins. Without one (a collection's first
    scan, or a holder Kodi no longer has) only a set carrying a known name of
    the collection may be chosen, by most counted members, then lowest
    setid: a set the user named, such as "Favourites", must never become the
    target that the scraper's set is merged into. A collection with one set
    has nothing to merge, so that set is managed whatever its name."""
    setids = {plan.setid for plan, _ in group}
    if holder is not None and holder in setids:
        return holder
    if len(group) == 1:
        return group[0][0].setid
    named = [pc for pc in group if _name_key(pc[0].title) in known]
    if not named:
        return None
    return min(named, key=lambda pc: (-pc[1], pc[0].setid))[0].setid


def _moves_out_of(
    duplicate: SetPlan, managed_setid: int, members: list[dict[str, Any]],
    libraries: LibraryConfig, collections: dict[str, str],
    set_moves: dict[str, dict[str, Any]],
) -> list[Move]:
    """The duplicate's members that move into the managed set: each in an
    included library and folder with Movie sets ticked, of the managed
    collection, and not moved elsewhere by the user."""
    out: list[Move] = []
    for member in members:
        lib = _counted_library(member, libraries)
        if lib is None or _SETS_TOGGLE not in lib.toggles:
            continue
        if _member_collection(member, collections) != duplicate.collection_id:
            continue
        movieid = int(member.get("movieid") or 0)
        identity = compute_identity(member, MOVIE)
        if user_moved(set_moves.get(identity), movieid, duplicate.setid):
            continue
        out.append(Move(movieid=movieid, identity=identity, from_setid=duplicate.setid,
                        from_name=duplicate.title, to_setid=managed_setid))
    return out


def plan_sets(
    sets: list[dict[str, Any]],
    members: list[dict[str, Any]],
    libraries: LibraryConfig,
    collections: dict[str, str],
    holders: dict[str, int],
    names: dict[str, frozenset[str]],
    set_moves: dict[str, dict[str, Any]],
) -> tuple[list[SetPlan], list[Move]]:
    """A plan for every Kodi set (in the order given) and the moves that
    merge duplicate sets.

    ``members`` are the movies in a set (kodi.get_movies_for_sets, setid above 0);
    ``collections`` maps a movie's TMDB id to its stored collection ("" for
    none); ``holders`` maps a set identity to the setid its tracker row
    records; ``names`` maps a set identity to its known lowercased names;
    ``set_moves`` maps a movie identity to its recorded move.

    Among the sets whose members chose one collection, at most one is
    managed (see _managed_setid). Any other is a duplicate only when its name
    is a known name of the collection (the scraper's or an old TMDB name,
    which is how Kodi makes one); a set the user named is shared and left
    alone, and is never a merge target unless the tracker already records it
    as the collection's set. When no set may be managed, every set of the
    collection is shared and nothing moves.
    """
    by_set: dict[int, list[dict[str, Any]]] = {}
    for member in members:
        by_set.setdefault(int(member.get("setid") or 0), []).append(member)

    first = [_first_plan(s, by_set.get(int(s.get("setid") or 0), []), libraries, collections)
             for s in sets]
    by_collection: dict[str, list[tuple[SetPlan, int]]] = {}
    for plan, count in first:
        if plan.reason is None and plan.collection_id:
            by_collection.setdefault(plan.collection_id, []).append((plan, count))

    final: dict[int, SetPlan] = {}
    moves: list[Move] = []
    for cid, group in by_collection.items():
        identity = compute_identity({"collection_id": cid}, SET)
        known = names.get(identity, frozenset())
        managed = _managed_setid(group, holders.get(identity), known)
        for plan, _ in group:
            if plan.setid == managed:
                continue
            if managed is not None and _name_key(plan.title) in known:
                final[plan.setid] = replace(plan, reason=LEFT_DUPLICATE, managed_setid=managed)
                moves.extend(_moves_out_of(final[plan.setid], managed,
                                           by_set.get(plan.setid, []), libraries,
                                           collections, set_moves))
            else:
                final[plan.setid] = replace(plan, reason=LEFT_SHARED)
    plans = [final.get(plan.setid, plan) for plan, _ in first]
    return plans, moves


@dataclass(frozen=True)
class Join:
    movieid: int
    identity: str
    title: str
    collection_id: str
    # The managed set it joins; None when the collection's set is created.
    to_setid: Optional[int]
    # The movie's file: the new set's library and folder settings read from it.
    file: str


def collections_with_sets(
    sets: list[dict[str, Any]], members: list[dict[str, Any]],
    collections: dict[str, str], names: dict[str, frozenset[str]],
) -> frozenset[str]:
    """Every collection some Kodi set stands for, whatever its plan reason:
    a set with a member (in any library, counted or not) of that stored
    collection, or titled with a known name of it. Such a collection never
    gets a second set made beside the one the user left out.

    ``collections`` must hold the stored collection of every set member in
    any library, not only the counted ones, and of every movie a join may
    be planned for: a collection missing from it cannot be found through a
    member, and a set titled with one of its names is only found when some
    movie in the map has it."""
    set_ids = {int(s.get("setid") or 0) for s in sets}
    found = {
        cid for member in members if int(member.get("setid") or 0) in set_ids
        for cid in [_member_collection(member, collections)] if cid
    }
    titles = {_name_key(str(s.get("title") or "")) for s in sets}
    for cid in {c for c in collections.values() if c} - found:
        if names.get(_set_identity(cid), frozenset()) & titles:
            found.add(cid)
    return frozenset(found)


def plan_joins(
    movies: list[dict[str, Any]], plans: list[SetPlan], libraries: LibraryConfig,
    collections: dict[str, str], set_moves: dict[str, dict[str, Any]],
    with_sets: frozenset[str],
) -> list[Join]:
    """The movies in no set that join their collection's set, by collection
    id then movieid. ``movies`` is the whole listing; only those with setid 0
    are candidates. A candidate is in an included library and folder with
    Movie sets ticked, has a stored non-empty collection and was not taken
    out of its set by the user. It joins the collection's managed plan; the
    set is created when the collection has no Kodi set at all (``with_sets``,
    see collections_with_sets); otherwise it waits, so a set the user made or
    left out is never a target or duplicated."""
    managed = {plan.collection_id: plan.setid for plan in reversed(plans)
               if plan.reason is None and plan.collection_id}
    joins: list[Join] = []
    for movie in movies:
        if int(movie.get("setid") or 0) != 0:
            continue
        lib = _counted_library(movie, libraries)
        if lib is None or _SETS_TOGGLE not in lib.toggles:
            continue
        cid = _member_collection(movie, collections)
        if not cid:
            continue
        movieid = int(movie.get("movieid") or 0)
        identity = compute_identity(movie, MOVIE)
        if user_moved(set_moves.get(identity), movieid, 0):
            continue
        if cid in managed:
            target: Optional[int] = managed[cid]
        elif cid in with_sets:
            continue
        else:
            target = None
        joins.append(Join(
            movieid=movieid, identity=identity, title=str(movie.get("title") or ""),
            collection_id=cid, to_setid=target, file=str(movie.get("file") or ""),
        ))
    return sorted(joins, key=lambda j: (j.collection_id, j.movieid))


def like_matches(pattern: str, name: str) -> bool:
    """Whether ``name`` matches the SQL LIKE ``pattern`` as Kodi's default
    database (SQLite) evaluates it: ``%`` any run, ``_`` one character, the
    whole string, case-insensitive. SQLite folds ASCII letters only; this
    folds all Unicode ones, which only over-reports a collision."""
    regex = "".join(".*" if c == "%" else "." if c == "_" else re.escape(c)
                    for c in pattern)
    return re.fullmatch("(?is)" + regex, name) is not None


def name_collides(name: str, sets: list[dict[str, Any]], target_setid: Optional[int]) -> bool:
    """Whether Kodi's name match for ``name`` (AddSet uses LIKE) would find a
    set other than ``target_setid``, so a write would misfile the movie."""
    return any(like_matches(name, str(s.get("title") or ""))
               for s in sets if int(s.get("setid") or 0) != target_setid)


# ---------------------------------------------------------------------------
# Names and NFO state
# ---------------------------------------------------------------------------


def collection_text(texts: dict[str, str], kodi_lang: str) -> Optional[str]:
    """A collection's name or plot in a Kodi language: the "xx-YY"
    translation, else the language's bare "xx" one; None when TMDB has
    neither."""
    full = tmdb_language(kodi_lang)
    if not full:
        return None
    return texts.get(full) or texts.get(full.split("-")[0]) or None


def pick_set_name(
    names: dict[str, str], lang: str, fallback: Optional[str],
) -> tuple[Optional[str], bool]:
    """(name, from_fallback): TMDB's name of the collection in the library
    language, then the fallback language, then English. Any step after the
    first counts as a fallback, so the name is rechecked monthly."""
    steps = [lang]
    if fallback and fallback.strip():
        steps.append(fallback.strip())
    steps.append(ENGLISH)
    for index, code in enumerate(steps):
        name = collection_text(names, code)
        if name and name.strip():
            return name, index > 0
    return None, False


def set_nfo_state(member_files: tuple[str, ...]) -> str:
    """A set's NFO state from its counted members (it has no NFO of its
    own): NO_NFO as soon as a member answers without an NFO, UNREACHABLE
    when none did and a member's media cannot be reached, NFO when every
    member has one. A reachable member without an NFO already settles the
    set, whatever an unreachable one would say: the set's own fields live in
    Kodi's database, not on a share, so a member whose video is gone (a
    replaced release Kodi has not cleaned) must not hold the set back."""
    unreachable = False
    for path in member_files:
        state = nfo_state(MOVIE.name, path)
        if state == NO_NFO:
            return NO_NFO
        unreachable = unreachable or state == UNREACHABLE
    if unreachable:
        return UNREACHABLE
    return NFO if member_files else NO_NFO


# ---------------------------------------------------------------------------
# The set pass's preparation (Kodi, TMDB and the tracker)
# ---------------------------------------------------------------------------


def _set_identity(collection_id: str) -> str:
    return compute_identity({"collection_id": collection_id}, SET)


def _ask_tmdb(ctx: _ScanCtx, fetch: Callable[[], Any], identity: str) -> Any:
    """A TMDB answer, or TRANSIENT when TMDB is out for the cycle or did not
    answer."""
    if ctx.breaker.is_disabled("tmdb"):
        return TRANSIENT
    return _call_provider("tmdb", fetch, ctx, identity)


def collection_is_stale(row: Optional[dict[str, str]], today: str) -> bool:
    """Whether a movie's stored collection answer is to be asked again: it
    was never asked, or it is "none" and undated or at least
    NONE_RECHECK_DAYS old on ``today``."""
    if row is None:
        return True
    if row.get("collection_id"):
        return False
    checked_on = row.get("checked_on") or ""
    if not checked_on:
        return True
    try:
        age = date.fromisoformat(today) - date.fromisoformat(checked_on)
    except ValueError:
        return True
    return age.days >= NONE_RECHECK_DAYS


def _member_collections(
    ctx: _ScanCtx, movies: list[dict[str, Any]], wanted: Callable[[dict[str, Any]], bool],
    libraries: LibraryConfig, today: str, stats: dict[str, Any],
    stop: Callable[[], bool], counted_only: bool = True,
) -> tuple[dict[str, str], bool, bool]:
    """The TMDB collection of every movie ``wanted`` accepts, keyed on its
    TMDB id; whether ``stop`` ended the lookups; and whether TMDB left any
    of them unanswered. Only counted movies are looked at unless
    ``counted_only`` is False.

    A movie without a stored answer, or whose "none" is NONE_RECHECK_DAYS
    old, is asked (/movie/{id}, no append) and the answer kept; one TMDB did
    not answer is left out (a stale "none" stays as stored and counts as
    "none"), so it counts for no collection this scan and can only keep its
    set from being managed, never make it managed. It counts in
    stats["transient"], so Update now says it could not check rather than
    that the set is left alone. ``stop`` runs before each request: a first
    scan can ask about every movie in no set, so shutdown and Stop scan
    must be able to end it. The answers already received stay recorded."""
    collections: dict[str, str] = {}
    unanswered = False
    for member in movies:
        if not wanted(member):
            continue
        if counted_only and libraries.included_for(str(member.get("file") or "")) is None:
            continue
        tmdb_id = extract_ids(member)[0]
        if not tmdb_id or tmdb_id in collections:
            continue
        row = ctx.tracker.get_movie_collection_row(tmdb_id)
        stored = None if row is None else row["collection_id"]
        if collection_is_stale(row, today):
            if stop():
                return collections, True, unanswered
            answer = _ask_tmdb(
                ctx, _collection_lookup(tmdb_id, ctx.tmdb_api_key),
                compute_identity(member, MOVIE),
            )
            if answer is TRANSIENT:
                stats["transient"] = stats.get("transient", 0) + 1
                unanswered = True
            else:
                stored = str(answer or "")
                ctx.tracker.set_movie_collection(tmdb_id, stored, today)
        if stored is not None:
            collections[tmdb_id] = stored
    return collections, False, unanswered


def _collection_lookup(tmdb_id: str, api_key: str) -> Callable[[], Any]:
    return lambda: tmdb.fetch_movie_collection_id(tmdb_id, api_key)


def _learn_names(
    ctx: _ScanCtx, plans: list[SetPlan], names: dict[str, frozenset[str]],
) -> bool:
    """Record TMDB's names of every collection whose sets are all shared
    because none carries a known name (a collection's first scan with two
    or more Kodi sets). Without them the scraper's set could never be told
    from the user's and nothing would be merged. Returns whether any names
    were learned, so the caller plans again."""
    groups: dict[str, list[SetPlan]] = {}
    for plan in plans:
        if plan.collection_id and plan.reason in (None, LEFT_DUPLICATE, LEFT_SHARED):
            groups.setdefault(plan.collection_id, []).append(plan)
    learned = False
    for cid, group in sorted(groups.items()):
        if len(group) < 2 or any(p.reason != LEFT_SHARED for p in group):
            continue
        identity = _set_identity(cid)
        answer = _ask_tmdb(
            ctx, _collection_fetch(cid, ctx.tmdb_api_key), identity,
        )
        if not isinstance(answer, dict):
            continue
        ctx.tracker.add_set_names(identity, (answer.get("names") or {}).values())
        known = ctx.tracker.get_set_names(identity)
        if known != names.get(identity, frozenset()):
            names[identity] = known
            learned = True
    return learned


def _collection_fetch(collection_id: str, api_key: str) -> Callable[[], Any]:
    # Only the names are read here: no image language is needed.
    return lambda: tmdb.fetch_collection(collection_id, api_key, ())


def _lock_user_moves(
    tracker: Any, movies: list[dict[str, Any]], set_moves: dict[str, dict[str, Any]],
) -> None:
    """Lock, for good, the recorded move or join of every listed movie the
    user has since put in another set or taken out of its set. A movie in no
    set that the set pass last saw in a managed set under the same movieid
    was taken out by the user too, whoever put it there: its sighting is
    locked, and its entry in ``set_moves`` reads as locked, so it never
    joins a set again."""
    for movie in movies:
        identity = compute_identity(movie, MOVIE)
        movieid = int(movie.get("movieid") or 0)
        setid = int(movie.get("setid") or 0)
        move = set_moves.get(identity)
        if move is not None and not move.get("locked") and user_moved(move, movieid, setid):
            tracker.lock_set_move(identity)
            set_moves[identity] = move = dict(move, locked=1)
        if setid or (move is not None and move.get("locked")):
            continue
        seen = tracker.get_set_seen(identity)
        if seen is None:
            continue
        if not seen.get("locked"):
            if int(seen.get("kodi_id") or 0) != movieid or not int(seen.get("setid") or 0):
                continue
            tracker.lock_set_seen(identity)
        set_moves[identity] = dict(move or {}, locked=1)


def _target_setid(plans: list[SetPlan], only_setid: Optional[int]) -> Optional[int]:
    """For Update now on a set: the managed set of its collection, or None
    when the set is not one MetaMender manages or merges."""
    for plan in plans:
        if plan.setid != only_setid:
            continue
        if plan.reason is None and plan.collection_id:
            return plan.setid
        if plan.reason == LEFT_DUPLICATE:
            return plan.managed_setid
    return None


@dataclass
class _MoveResult:
    # The members that moved, by managed setid.
    moved: dict[int, list[dict[str, Any]]]
    # The plot each managed set holds after its moves (see _restore_plot).
    plots: dict[int, str]
    # The caller's before_write said to stop (shutdown or Stop scan).
    stopped: bool


def _move_movies(
    ctx: _ScanCtx, moves: list[Move], kodi_sets: dict[int, dict[str, Any]],
    members: dict[int, dict[str, Any]], today: str, stats: dict[str, Any],
    before_write: Callable[[], bool],
) -> _MoveResult:
    """Move each movie into its managed set by that set's current name, and
    keep the move once Kodi's own answer shows the movie in that set.

    ``before_write`` runs before each move: it holds while the user browses
    the video library and returns False to stop. A move and the plot
    restore it calls for are one unit, with no hold between them, so a stop
    never leaves a managed set with the old set's plot."""
    result = _MoveResult(moved={}, plots={}, stopped=False)
    for move in moves:
        if not before_write():
            result.stopped = True
            break
        target = kodi_sets[move.to_setid]
        name = str(target.get("title") or "")
        member = members.get(move.movieid) or {}
        title = str(member.get("title") or "")
        ok = kodi.update_item(move.movieid, MOVIE, title, set=name)
        landed = kodi.get_movie_setid(move.movieid) if ok else None
        # A refused or misfiled move may still have run AddSet on the set.
        result.plots[move.to_setid] = _restore_plot(target)
        if landed != move.to_setid:
            log.warning(
                "Movie not moved into the managed set", event="sets.move_failed",
                movie=title, movieid=move.movieid, from_set=move.from_name, to_set=name,
                written=ok, setid=landed,
            )
            continue
        ctx.tracker.record_set_move(move.identity, move.movieid, move.from_name,
                                    move.to_setid, today)
        stats["moved"] = stats.get("moved", 0) + 1
        result.moved.setdefault(move.to_setid, []).append(member)
        log.info("Movie moved into the managed set", event="sets.moved", movie=title,
                 from_set=move.from_name, to_set=name)
    return result


def _restore_plot(kodi_set: dict[str, Any]) -> str:
    """Put the managed set's plot back after a move into it, and return the
    plot it now has. Kodi's SetMovieDetails with ``set`` calls AddSet with
    the moved movie's old set overview, which overwrites the plot of the
    set it lands in."""
    setid = int(kodi_set.get("setid") or 0)
    before = str(kodi_set.get("plot") or "")
    detail = kodi.get_item_by_id(SET, setid, art=False)
    after = str((detail or {}).get("plot") or "")
    if detail is None or after == before:
        return before
    title = str(kodi_set.get("title") or "")
    if not kodi.update_item(setid, SET, title, plot=before):
        return after
    log.info("Managed set plot put back after a move", event="sets.plot_restored",
             set=title, setid=setid)
    return before


def _new_set_name(
    ctx: _ScanCtx, join: Join, listed: list[dict[str, Any]],
    names: dict[str, frozenset[str]], libraries: LibraryConfig, stats: dict[str, Any],
) -> Optional[str]:
    """The name to create the set of ``join``'s collection under, or None to
    leave the collection without a set this scan.

    TMDB's names are recorded either way (and ``names`` updated), so the
    next planning knows a Kodi set that carries one of them: such a set
    means the collection has a set after all, and none is created beside
    it. The name is picked for the joining movie's folder language, unless
    the movie set information folder has a subfolder for one of the
    collection's names: then the set is created under that name, so Kodi
    finds the folder for it."""
    cid = join.collection_id
    identity = _set_identity(cid)
    answer = _ask_tmdb(ctx, _collection_fetch(cid, ctx.tmdb_api_key), identity)
    if answer is TRANSIENT:
        stats["transient"] = stats.get("transient", 0) + 1
        return None
    raw = answer.get("names") if isinstance(answer, dict) else None
    tmdb_names = {code: text.strip() for code, text in (raw or {}).items()
                  if isinstance(text, str) and text.strip()}
    ctx.tracker.add_set_names(identity, tmdb_names.values())
    names[identity] = ctx.tracker.get_set_names(identity)
    keys = {_name_key(text) for text in tmdb_names.values()}
    if any(_name_key(str(s.get("title") or "")) in keys for s in listed):
        log.debug("Collection already has a set under one of its names",
                  event="sets.join_skipped", movie=join.title, collection_id=cid,
                  reason="has_set")
        return None
    lib = libraries.included_for(join.file)
    picked = None
    if lib is not None:
        _, language, fallback = libraries.folder_settings(join.file, lib)
        picked = pick_set_name(tmdb_names, language, fallback)[0]
    if not picked:
        log.debug("Collection has no name to create its set under",
                  event="sets.join_skipped", movie=join.title, collection_id=cid,
                  reason="no_name")
        return None
    if ctx.set_folder:
        others = [text for text in dict.fromkeys(tmdb_names.values()) if text != picked]
        return folder_for(ctx.set_folder, [picked] + others) or picked
    return picked


def _join_movies(
    ctx: _ScanCtx, joins: list[Join], kodi_sets: dict[int, dict[str, Any]],
    names: dict[str, frozenset[str]], libraries: LibraryConfig, today: str,
    stats: dict[str, Any], before_write: Callable[[], bool],
) -> tuple[dict[str, int], bool]:
    """Add each movie in no set to its collection's set by the set's name,
    creating the set with the first movie when the collection has none,
    and keep the join once Kodi's own answer shows the movie there.

    ``kodi_sets`` are Kodi's sets by setid, with the plots they hold now.
    A join into an existing set must land in it; a creation must land in a
    set that did not exist before (AddSet files the movie into any set its
    name LIKE-matches). A misfiled movie is taken out of the set again and
    nothing is recorded. ``before_write`` runs before each write, as in
    _move_movies. Returns the setid each collection's movies joined, and
    whether ``before_write`` said to stop."""
    listed = [dict(s) for s in kodi_sets.values()]
    done: dict[str, int] = {}
    new_names: dict[str, Optional[str]] = {}
    for join in joins:
        cid = join.collection_id
        target = join.to_setid if join.to_setid is not None else done.get(cid)
        if target is None:
            if cid not in new_names:
                new_names[cid] = _new_set_name(ctx, join, listed, names, libraries, stats)
            name = new_names[cid]
            if name is None:
                continue
        else:
            found = next((str(s.get("title") or "") for s in listed
                          if int(s.get("setid") or 0) == target), None)
            if found is None:
                continue
            name = found
        if name_collides(name, listed, target):
            log.debug("Movie not added to its collection's set", event="sets.join_skipped",
                      movie=join.title, set=name, reason="name_collision")
            continue
        if not before_write():
            return done, True
        ok = kodi.update_item(join.movieid, MOVIE, join.title, set=name)
        landed = kodi.get_movie_setid(join.movieid) if ok else None
        # A refused or misfiled join may still have run AddSet on the set it
        # was meant for and on the set it landed in.
        for touched in dict.fromkeys((target, landed)):
            if touched in kodi_sets:
                kodi_sets[touched]["plot"] = _restore_plot(kodi_sets[touched])
        if target is not None:
            good = landed == target
        else:
            good = bool(landed) and all(int(s.get("setid") or 0) != landed for s in listed)
        if landed is None or not good:
            # The movie sat in no set: taking it out again loses nothing.
            cleared = landed == 0 or kodi.update_item(join.movieid, MOVIE, join.title, set="")
            log.warning(
                "Movie not added to its collection's set", event="sets.move_failed",
                movie=join.title, movieid=join.movieid, from_set="", to_set=name,
                written=ok, setid=landed, cleared=bool(cleared),
            )
            if target is None:
                # The name files movies elsewhere: the collection's other
                # movies wait for the next scan.
                new_names[cid] = None
            continue
        created = target is None
        if created:
            listed.append({"setid": landed, "title": name})
        done[cid] = landed
        ctx.tracker.record_set_move(join.identity, join.movieid, "", landed, today)
        stats["joined"] = stats.get("joined", 0) + 1
        if created:
            stats["sets_created"] = stats.get("sets_created", 0) + 1
        log.info("Movie added to its collection's set", event="sets.joined",
                 movie=join.title, set=name, setid=landed, created=created)
    return done, False


def _seen_in_managed_sets(
    plans: list[SetPlan], members: list[dict[str, Any]], libraries: LibraryConfig,
) -> list[tuple[str, int, int]]:
    """(identity, movieid, setid) of every counted member of a managed set,
    for the tracker's record of who the set pass saw where."""
    managed = {plan.setid for plan in plans if plan.reason is None and plan.collection_id}
    return [
        (compute_identity(m, MOVIE), int(m.get("movieid") or 0), int(m.get("setid") or 0))
        for m in members
        if int(m.get("setid") or 0) in managed and _counted_library(m, libraries) is not None
    ]


def _stored_collections(tracker: Any, movies: list[dict[str, Any]]) -> dict[str, str]:
    """The stored collection of each listed movie TMDB was asked about,
    keyed on its TMDB id; asks no site."""
    collections: dict[str, str] = {}
    for movie in movies:
        tmdb_id = extract_ids(movie)[0]
        if tmdb_id and tmdb_id not in collections:
            stored = tracker.get_movie_collection(tmdb_id)
            if stored is not None:
                collections[tmdb_id] = stored
    return collections


def _plan_set_joins(
    ctx: _ScanCtx, movies: list[dict[str, Any]], kodi_sets: list[dict[str, Any]],
    plans: list[SetPlan], libraries: LibraryConfig, collections: dict[str, str],
    names: dict[str, frozenset[str]], set_moves: dict[str, dict[str, Any]],
    only_collection: Optional[str], today: str, stats: dict[str, Any],
    stop: Callable[[], bool], members_unanswered: bool,
) -> tuple[list[Join], dict[str, str], bool]:
    """The joins to write, the collection map they were planned with, and
    whether ``stop`` ended the lookups (then no join is planned).

    Candidates (movies in no set, counted, in a library with Movie sets
    ticked, not taken out by the user) are looked up as set members are
    (_member_collections). For Update now on a set (``only_collection``)
    only stored answers are read and only that collection joins, so Update
    now asks TMDB nothing about other movies. Whether a collection already
    has a set is judged from the stored answers of every set member, in
    any library, so a set the user keeps outside the ticked libraries is
    never duplicated.

    A set made beside one of the user's cannot be taken back, so no set is
    created while any set member's collection is unknown: when a creation
    is planned, every set member with no stored answer (in any library) is
    asked once and the joins planned again; when TMDB left a member
    unanswered, here or before (``members_unanswered``), only joins into
    existing sets are kept and creations wait for a later scan."""
    def candidate(movie: dict[str, Any]) -> bool:
        if int(movie.get("setid") or 0) != 0:
            return False
        lib = _counted_library(movie, libraries)
        if lib is None or _SETS_TOGGLE not in lib.toggles:
            return False
        return not user_moved(set_moves.get(compute_identity(movie, MOVIE)),
                              int(movie.get("movieid") or 0), 0)

    if only_collection is not None:
        found = _stored_collections(ctx.tracker, [m for m in movies if candidate(m)])
    else:
        found, stopped, _ = _member_collections(ctx, movies, candidate, libraries, today,
                                                stats, stop)
        if stopped:
            return [], {}, True
    members = _set_members(movies)
    join_cols = {**_stored_collections(ctx.tracker, members), **collections, **found}
    joins = _joins_for(ctx, movies, kodi_sets, members, plans, libraries, join_cols,
                       names, set_moves)
    if only_collection is not None:
        return [j for j in joins if j.collection_id == only_collection], join_cols, False
    if not members_unanswered and any(j.to_setid is None for j in joins):
        def unasked(member: dict[str, Any]) -> bool:
            tmdb_id = extract_ids(member)[0]
            return bool(tmdb_id) and ctx.tracker.get_movie_collection_row(tmdb_id) is None

        asked, stopped, members_unanswered = _member_collections(
            ctx, members, unasked, libraries, today, stats, stop, counted_only=False)
        if stopped:
            return [], {}, True
        if asked:
            join_cols = {**asked, **join_cols}
            joins = _joins_for(ctx, movies, kodi_sets, members, plans, libraries,
                               join_cols, names, set_moves)
    if members_unanswered:
        for join in joins:
            if join.to_setid is None:
                log.debug("Set not created while a set member is unchecked",
                          event="sets.join_skipped", movie=join.title,
                          collection_id=join.collection_id, reason="member_unchecked")
        joins = [j for j in joins if j.to_setid is not None]
    return joins, join_cols, False


def _joins_for(
    ctx: _ScanCtx, movies: list[dict[str, Any]], kodi_sets: list[dict[str, Any]],
    members: list[dict[str, Any]], plans: list[SetPlan], libraries: LibraryConfig,
    join_cols: dict[str, str], names: dict[str, frozenset[str]],
    set_moves: dict[str, dict[str, Any]],
) -> list[Join]:
    """plan_joins with ``names`` filled for every collection in ``join_cols``
    and the collections that already have a set worked out from them."""
    for cid in {c for c in join_cols.values() if c}:
        identity = _set_identity(cid)
        if identity not in names:
            names[identity] = ctx.tracker.get_set_names(identity)
    with_sets = collections_with_sets(kodi_sets, members, join_cols, names)
    return plan_joins(movies, plans, libraries, join_cols, set_moves, with_sets)


def _tracker_facts(
    tracker: Any, members: list[dict[str, Any]], collections: dict[str, str],
) -> tuple[dict[str, int], dict[str, frozenset[str]], dict[str, dict[str, Any]]]:
    """plan_sets' holders, names and set_moves, read from the tracker."""
    holders: dict[str, int] = {}
    names: dict[str, frozenset[str]] = {}
    for identity in {_set_identity(cid) for cid in collections.values() if cid}:
        row = tracker.get_item(SET.name, identity)
        if row and row.get("kodi_id") is not None:
            holders[identity] = int(row["kodi_id"])
        names[identity] = tracker.get_set_names(identity)
    set_moves: dict[str, dict[str, Any]] = {}
    for member in members:
        movie = compute_identity(member, MOVIE)
        recorded = tracker.get_set_move(movie)
        if recorded is not None:
            set_moves[movie] = recorded
    return holders, names, set_moves


def describe_set(setid: int, libraries: LibraryConfig, tracker: Any) -> Optional[SetPlan]:
    """The plan of one Kodi set as the next scan would make it, for Details
    and Update now; None when Kodi has no such set.

    Reads only: it uses the collections already stored (a movie TMDB was
    never asked about counts for none, as one TMDB did not answer does in a
    scan), asks no site and records nothing. For a shared set,
    ``managed_setid`` is the set that follows the collection, or, when no
    set of it is managed, another set of the collection, so Details can
    name the set it shares with.
    """
    kodi_sets = kodi.get_all_items(SET, art=False)
    if not any(int(s.get("setid") or 0) == setid for s in kodi_sets):
        return None
    members = _set_members(kodi.get_movies_for_sets())
    collections = _stored_collections(tracker, members)
    holders, names, set_moves = _tracker_facts(tracker, members, collections)
    plans, _ = plan_sets(kodi_sets, members, libraries, collections, holders, names,
                         set_moves)
    plan = next(p for p in plans if p.setid == setid)
    if plan.reason != LEFT_SHARED:
        return plan
    same = [p for p in plans if p.collection_id == plan.collection_id and p.setid != setid]
    managed = [p for p in same if p.reason is None] or sorted(same, key=lambda p: p.setid)
    return replace(plan, managed_setid=managed[0].setid if managed else None)


def prepare_sets(
    ctx: _ScanCtx,
    libraries: LibraryConfig,
    new_only: bool,
    only_setid: Optional[int],
    stats: dict[str, Any],
    before_write: Optional[Callable[[], bool]] = None,
    stop: Optional[Callable[[], bool]] = None,
) -> list[dict[str, Any]]:
    """The managed sets for the set pass, after merging duplicate sets.

    Lists Kodi's sets and their movies; asks TMDB for the collection of a
    counted member that has no stored answer; makes sure a collection with
    two or more Kodi sets has its names on record before the merge decision
    (_learn_names); plans; locks moves and joins the user undid; moves the
    movies of duplicate sets, verifies each by re-reading the movie's setid,
    and puts the managed set's plot back where a move changed it. Then adds
    the movies in no set to their collection's set (_plan_set_joins,
    _join_movies) and, when any joined, lists and plans again so a created
    or grown set is returned as it now is. ``before_write`` runs before each
    move and join (run_scan's browse hold, shutdown and Stop scan checks);
    when it returns False no further movie is written and no set is
    returned. ``stop`` runs before each TMDB lookup of a movie's collection
    (run_scan's shutdown and Stop scan checks, without the browse hold); when
    it returns True nothing further is asked or written and no set is
    returned.

    A set left alone that the tracker holds a row for (its Movie sets tick
    went off, its library was left out, a tie) is marked present, so orphan
    pruning keeps its history (originals, names) for when it is managed
    again, as the movie pass does for excluded movies.

    ``new_only`` (a library-event cycle) still merges and joins every
    collection but returns only the sets the tracker does not know yet.
    ``only_setid`` (Update now on a set) merges, joins and returns only that
    set's collection.
    Each item is the Kodi set with its art flattened, plus ``file`` (the
    member file whose folder settings the set follows), ``premiered`` (its
    newest counted member's), ``collection_id`` and ``member_files``.
    Raises KodiQueryError when a listing fails.
    """
    tracker = ctx.tracker
    today = date.today().isoformat()
    write_ok = before_write or (lambda: True)
    stop_now = stop or (lambda: False)
    kodi_sets = kodi.get_all_items(SET)
    movies = kodi.get_movies_for_sets()
    members = _set_members(movies)
    by_setid = {int(s.get("setid") or 0): s for s in kodi_sets}
    by_movieid = {int(m.get("movieid") or 0): m for m in members}

    # Planned without collections first: a set its library leaves alone (a
    # tie, no counted member, Movie sets not ticked) costs no TMDB request.
    probe, _ = plan_sets(kodi_sets, members, libraries, {}, {}, {}, {})
    asking = {p.setid for p in probe if p.reason == LEFT_NO_COLLECTION}
    collections, stopped, members_unanswered = _member_collections(
        ctx, members, lambda m: int(m.get("setid") or 0) in asking, libraries, today, stats,
        stop_now,
    )
    if stopped:
        tracker.commit()
        return []

    # Every listed movie's recorded move, so a joined movie the user took
    # back out of its set is locked too.
    holders, names, set_moves = _tracker_facts(tracker, movies, collections)
    _lock_user_moves(tracker, movies, set_moves)

    plans, moves = plan_sets(kodi_sets, members, libraries, collections, holders, names,
                             set_moves)
    if _learn_names(ctx, plans, names):
        plans, moves = plan_sets(kodi_sets, members, libraries, collections, holders,
                                 names, set_moves)

    target = _target_setid(plans, only_setid) if only_setid is not None else None
    if only_setid is not None:
        moves = [m for m in moves if target is not None and m.to_setid == target]
    result = _move_movies(ctx, moves, by_setid, by_movieid, today, stats, write_ok)
    moved, plots = result.moved, result.plots
    stopped = result.stopped

    only_collection = next((p.collection_id for p in plans if p.setid == target), None)
    if not stopped and (only_setid is None or only_collection is not None):
        joins, join_cols, stopped = _plan_set_joins(
            ctx, movies, kodi_sets, plans, libraries, collections, names, set_moves,
            only_collection, today, stats, stop_now, members_unanswered,
        )
        join_setids: dict[str, int] = {}
        if not stopped:
            current = {sid: dict(s, plot=plots.get(sid, s.get("plot") or ""))
                       for sid, s in by_setid.items()}
            join_setids, stopped = _join_movies(ctx, joins, current, names, libraries, today,
                                               stats, write_ok)
        tracker.commit()
        if join_setids:
            # A created or grown set is planned again from Kodi's own
            # listing, so the pass scans it with its new members and plot.
            kodi_sets = kodi.get_all_items(SET)
            members = _set_members(kodi.get_movies_for_sets())
            by_setid = {int(s.get("setid") or 0): s for s in kodi_sets}
            holders, names, set_moves = _tracker_facts(tracker, members, join_cols)
            plans, _ = plan_sets(kodi_sets, members, libraries, join_cols, holders, names,
                                 set_moves)
            moved, plots = {}, {}

    tracked = tracker.identities_by_kodi_id(SET.name)
    for plan in plans:
        if plan.reason is not None and plan.setid in tracked:
            tracker.update_last_seen(SET.name, tracked[plan.setid], today)
    tracker.record_set_seen(_seen_in_managed_sets(plans, members, libraries), today)
    tracker.commit()
    if stopped:
        return []

    known = tracker.known_kodi_ids(SET.name) if new_only else set()
    items: list[dict[str, Any]] = []
    for plan in plans:
        if plan.reason is not None or not plan.collection_id:
            log.debug("Set left alone", event="sets.left_alone", set=plan.title,
                      setid=plan.setid, reason=plan.reason)
            continue
        if only_setid is not None and plan.setid != target:
            continue
        if plan.setid in known:
            continue
        item = dict(by_setid[plan.setid])
        joined = moved.get(plan.setid, [])
        if plan.setid in plots:
            item["plot"] = plots[plan.setid]
        item.update(
            file=plan.file,
            premiered=max([plan.premiered] + [str(m.get("premiered") or "") for m in joined]),
            collection_id=plan.collection_id,
            member_files=tuple(sorted(set(plan.member_files) | {
                str(m.get("file") or "") for m in joined})),
        )
        items.append(item)
    return items
