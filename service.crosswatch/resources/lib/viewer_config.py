# SPDX-License-Identifier: GPL-2.0-only
"""Viewer configuration.

settings.xml is static and cannot express a variable number of viewers, so the list is
edited through CrossWatch windows and stored as JSON, saved after every change. The list
arithmetic and the rows are pure so they are testable without a GUI.

A viewer's name must match the name CrossWatch routes on, so when CrossWatch lists its
people, Add offers them and a picked viewer stays linked to that person (people.py); a typed
name is the fallback, linked when it matches a person. Kodi profiles are no source: these
names come from playlists and prompts.

This runs as a separate script with its own module state, so main() configures logging.
"""

from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import NamedTuple

from resources.lib import log as logmod
from resources.lib import paths
from resources.lib.config import read_settings
from resources.lib.constants import (
    NOTIFY_HEADING,
    VIEWER_FROM_CROSSWATCH,
    VIEWER_MORE,
    VIEWER_NONE,
    VIEWER_PLAYLISTS,
    VIEWER_PROFILES,
    VIEWER_ROUTE_MISSING,
    VIEWER_ROUTE_OK,
    VIEWER_UNUSABLE,
    VIEWERS_ADD_PEOPLE,
    VIEWERS_ALSO,
    VIEWERS_COUNT,
    VIEWERS_HEADING,
    VIEWERS_MISSING,
    VIEWERS_NAME_CLASH,
    VIEWERS_NAME_PROMPT,
    VIEWERS_NO_PLAYLISTS,
    VIEWERS_ONE_PERSON,
    VIEWERS_ONE_PLAYLIST,
    VIEWERS_ONE_PROFILE,
    VIEWERS_ONE_VIEWER,
    VIEWERS_PEOPLE,
    VIEWERS_PICK_CLASH,
    VIEWERS_PLAYLISTS,
    VIEWERS_PLAYLISTS_FOR,
    VIEWERS_PROFILES,
    VIEWERS_PROFILES_FAILED,
    VIEWERS_PROFILES_FOR,
    VIEWERS_REMOVE_CONFIRM,
    VIEWERS_REMOVE_MESSAGE,
    VIEWERS_TYPE_NAME,
)
from resources.lib.kodi import KodiApi, KodiRuntime
from resources.lib.log import get_logger
from resources.lib.models import Viewer
from resources.lib.outbox import config_fingerprint
from resources.lib.people import match_person, same_name
from resources.lib.playlist_index import INDEXABLE_TYPES, PLAYLIST_DIR, declared_type
from resources.lib.routes import Person, RouteFacts
from resources.lib.storage import JsonViewerStore, PromptMemory, RouteStore, ViewerStore
from resources.lib.ui.list_window import ListRequest, ListRow, ListState
from resources.lib.ui.panel import PanelLine
from resources.lib.ui.viewers_window import (
    ROUTE_ACCEPTED,
    ROUTE_REFUSED,
    ViewerRow,
    ViewersRequest,
    ViewersResult,
)

_log = get_logger("config")


def _text(kodi: KodiApi, string_id: int, value: object = None) -> str:
    """A translated label. replace rather than %, so a translation that drops the
    placeholder cannot raise."""
    text = kodi.localised(string_id)
    return text if value is None else text.replace("%s", str(value))


class PlaylistListing(NamedTuple):
    """Kodi's video smart playlists, split by whether the index can match them.

    Only show and film playlists are matched. A playlist whose file cannot be read counts
    as matchable: its type is unknown rather than wrong, and the index reports it.
    """

    matchable: list[str]
    unusable: list[str]


def available_playlists(kodi: KodiApi) -> PlaylistListing:
    try:
        result = kodi.jsonrpc("Files.GetDirectory", {"directory": PLAYLIST_DIR, "media": "video"})
    except Exception as exc:
        _log.warning("config.playlist_listing_failed", error=str(exc))
        return PlaylistListing([], [])
    files = result.get("files")
    if not isinstance(files, list):
        return PlaylistListing([], [])
    listing = PlaylistListing([], [])
    for entry in files:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("file") or "")
        if not path.endswith(".xsp"):
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        text = kodi.read_text(path)
        if text is None or declared_type(text) in INDEXABLE_TYPES:
            listing.matchable.append(label)
        else:
            listing.unusable.append(label)
    return listing


class NameClash(ValueError):
    """A name CrossWatch would route as an existing viewer's, who is named here."""

    def __init__(self, existing: str) -> None:
        super().__init__("crosswatch_same")
        self.existing = existing


def validate_name(name: str, existing: list[Viewer], own: str | None = None, picked: bool = False) -> str:
    """The cleaned name, or ValueError("empty") / ValueError("taken") / NameClash.

    Reason codes, not sentences: the reason is logged, and a sentence would carry the name.
    own is the viewer being renamed: their current name is not taken, so a change of case is
    allowed. picked means the name is a person CrossWatch listed: CrossWatch keeps two people
    apart by their own spelling, so it may sit next to a loose-equal viewer that is linked too.
    """
    cleaned = str(name or "").strip()
    if not cleaned:
        raise ValueError("empty")
    mine = own.casefold() if own else None
    if any(v.name.casefold() == cleaned.casefold() and v.name.casefold() != mine for v in existing):
        raise ValueError("taken")
    for viewer in existing:
        if picked and viewer.person_id:
            continue
        if same_name(cleaned, viewer.name) and viewer.name.casefold() != mine:
            raise NameClash(viewer.name)
    return cleaned


def rename_viewer(viewers: list[Viewer], old: str, new: str) -> list[Viewer]:
    return [replace(v, name=new) if v.name == old else v for v in viewers]


def apply_edit(
    viewers: list[Viewer], name: str, playlists: tuple[str, ...], profiles: tuple[str, ...]
) -> list[Viewer]:
    out = list(viewers)
    for index, viewer in enumerate(out):
        if viewer.name.casefold() == name.casefold():
            out[index] = replace(viewer, playlists=tuple(playlists), profiles=tuple(profiles))
            return out
    out.append(Viewer(name=name, playlists=tuple(playlists), profiles=tuple(profiles)))
    return out


def remove_viewer(viewers: list[Viewer], name: str) -> list[Viewer]:
    return [v for v in viewers if v.name.casefold() != name.casefold()]


def missing_playlists(viewer: Viewer, available: list[str], unusable: Sequence[str] = ()) -> tuple[str, ...]:
    """Playlists the viewer is configured with that Kodi no longer has.

    An empty listing means it failed rather than that nothing exists, and flagging every
    viewer during a Kodi hiccup would be a false alarm, so it reports none.
    """
    if not available and not unusable:
        return ()
    known = {*available, *unusable}
    return tuple(name for name in viewer.playlists if name not in known)


def unusable_playlists(viewer: Viewer, unusable: Sequence[str]) -> tuple[str, ...]:
    """Playlists the viewer is configured with that the index cannot match."""
    return tuple(name for name in viewer.playlists if name in unusable)


def _also(kodi: KodiApi, viewer: Viewer, viewers: Sequence[Viewer], has: Callable[[Viewer], bool]) -> str:
    # A shared playlist or profile credits everyone who has it, which is easy to miss.
    others = [v.name for v in viewers if v.name.casefold() != viewer.name.casefold() and has(v)]
    return _text(kodi, VIEWERS_ALSO, ", ".join(others)) if others else ""


def _count(kodi: KodiApi, n: int, one: int, many: int) -> str:
    return _text(kodi, one) if n == 1 else _text(kodi, many, n)


def current_routes(kodi: KodiApi) -> RouteFacts | None:
    """What CrossWatch last said about its routes, for the current pairing only."""
    settings = read_settings(kodi)
    if settings.webhook_url() is None:
        return None
    return RouteStore(paths.routes_path(kodi)).load(config_fingerprint(settings.webhook_token))


def panel_lines(
    kodi: KodiApi, viewer: Viewer, listing: PlaylistListing, profiles: Sequence[str] | None
) -> tuple[PanelLine, ...]:
    """The viewer's playlists and profiles in full, each tagged when it needs fixing.

    profiles is None when Kodi's profiles could not be read: then nothing is called missing.
    """
    gone = set(missing_playlists(viewer, listing.matchable, listing.unusable))
    wrong = set(unusable_playlists(viewer, listing.unusable))
    missing, none = _text(kodi, VIEWERS_MISSING), _text(kodi, VIEWER_NONE)
    lines = [PanelLine(_text(kodi, VIEWER_FROM_CROSSWATCH))] if viewer.person_id else []
    lines.append(PanelLine(_text(kodi, VIEWER_PLAYLISTS), heading=True))
    for name in viewer.playlists:
        if name in wrong:
            lines.append(PanelLine(name, tag=_text(kodi, VIEWER_UNUSABLE), warn=True))
        elif name in gone:
            lines.append(PanelLine(name, tag=missing, warn=True))
        else:
            lines.append(PanelLine(name))
    if not viewer.playlists:
        lines.append(PanelLine(none))
    lines.append(PanelLine(_text(kodi, VIEWER_PROFILES), heading=True))
    known = None if profiles is None else {p.casefold() for p in profiles}
    for profile in viewer.profiles:
        if known is not None and profile.casefold() not in known:
            lines.append(PanelLine(profile, tag=missing, warn=True))
        else:
            lines.append(PanelLine(profile))
    if not viewer.profiles:
        lines.append(PanelLine(none))
    return tuple(lines)


def route_state(viewer: Viewer, routes: RouteFacts | None) -> str:
    # Only what CrossWatch said about this pairing: without a reply there is no claim.
    if routes is None or viewer.name not in routes.asked:
        return ""
    return ROUTE_ACCEPTED if viewer.name in routes.accepted else ROUTE_REFUSED


def viewers_request(
    kodi: KodiApi,
    viewers: Sequence[Viewer],
    listing: PlaylistListing,
    profiles: Sequence[str] | None,
    routes: RouteFacts | None,
) -> ViewersRequest:
    rows = tuple(
        ViewerRow(
            key=v.name,
            lines=panel_lines(kodi, v, listing, profiles),
            route=route_state(v, routes),
            linked=v.person_id is not None,
        )
        for v in viewers
    )
    return ViewersRequest(
        heading=_text(kodi, VIEWERS_HEADING),
        count=_count(kodi, len(rows), VIEWERS_ONE_VIEWER, VIEWERS_COUNT) if rows else "",
        rows=rows,
        more=_text(kodi, VIEWER_MORE),
        route_ok=_text(kodi, VIEWER_ROUTE_OK),
        route_missing=_text(kodi, VIEWER_ROUTE_MISSING),
    )


def available_profiles(kodi: KodiApi) -> list[str] | None:
    """Kodi's profile labels; None when they could not be read, which is not "none"."""
    try:
        result = kodi.jsonrpc("Profiles.GetProfiles")
    except Exception as exc:
        _log.warning("config.profile_listing_failed", error=type(exc).__name__)
        return None
    profiles = result.get("profiles")
    if not isinstance(profiles, list):
        return None
    labels = (str(p.get("label") or "").strip() for p in profiles if isinstance(p, dict))
    return [label for label in labels if label]


def profile_rows(
    kodi: KodiApi, viewer: Viewer, profiles: Sequence[str], viewers: Sequence[Viewer]
) -> tuple[tuple[ListRow, ...], tuple[str, ...]]:
    """Kodi's profiles, then the viewer's ones Kodi no longer has; and what starts ticked.

    Matched without case, as playback matches the active profile, and ticked under Kodi's
    own label so the stored name follows Kodi once picked.
    """
    kodi_labels = {p.casefold(): p for p in profiles}

    def also(label: str) -> str:
        return _also(kodi, viewer, viewers, lambda v: any(p.casefold() == label.casefold() for p in v.profiles))

    missing = [p for p in viewer.profiles if p.casefold() not in kodi_labels]
    rows = (
        *(ListRow(key=p, title=p, detail=also(p)) for p in profiles),
        *(ListRow(key=p, title=p, detail=also(p), tag=_text(kodi, VIEWERS_MISSING)) for p in missing),
    )
    ticked = tuple(kodi_labels.get(p.casefold(), p) for p in viewer.profiles)
    return rows, ticked


def playlist_rows(
    kodi: KodiApi, viewer: Viewer, playlists: Sequence[str], unusable: Sequence[str], viewers: Sequence[Viewer]
) -> tuple[ListRow, ...]:
    """Every matchable playlist, then the viewer's own vanished ones.

    A vanished playlist may come back (a share offline, a rename), so it is listed under its
    real name: without it Done would drop it silently, and a removal the household never saw
    would look like their own edit. An unusable one is not listed and Done drops it: it can
    never credit anyone, so there is nothing to choose, and the viewer list already marks it.
    """

    def also(name: str) -> str:
        return _also(kodi, viewer, viewers, lambda v: name in v.playlists)

    missing = _text(kodi, VIEWERS_MISSING)
    return (
        *(ListRow(key=name, title=name, detail=also(name)) for name in playlists),
        *(
            ListRow(key=name, title=name, detail=also(name), tag=missing)
            for name in missing_playlists(viewer, list(playlists), unusable)
        ),
    )


def _edit_playlists(
    kodi: KodiApi,
    viewer: Viewer,
    playlists: list[str],
    unusable: Sequence[str] = (),
    viewers: Sequence[Viewer] = (),
) -> tuple[str, ...] | None:
    """None means cancelled, so the existing mapping is kept."""
    heading = _text(kodi, VIEWERS_PLAYLISTS_FOR, viewer.name)
    rows = playlist_rows(kodi, viewer, playlists, unusable, viewers)
    if not rows:
        # Also what a failed listing looks like, and an empty window would then drop every
        # playlist the viewer has on Done.
        _log.info("config.no_playlists_to_pick", unusable=len(unusable))
        kodi.ok(heading, _text(kodi, VIEWERS_NO_PLAYLISTS))
        return None
    request = ListRequest(
        heading=heading,
        rows=rows,
        count_one=_text(kodi, VIEWERS_ONE_PLAYLIST),
        count_all=_text(kodi, VIEWERS_PLAYLISTS),
        ticked=viewer.playlists,
    )
    result = kodi.list_window(request, ListState())
    return result.keys if result.action == "done" else None


def _save(store: ViewerStore, viewers: list[Viewer]) -> None:
    # At once, not when the screen closes: the service reads the file per playback, and a
    # screen Kodi closes under us loses nothing.
    store.save(viewers)
    _log.info("config.saved", viewers=len(viewers))


def _edit_profiles(
    kodi: KodiApi, viewer: Viewer, profiles: list[str] | None, viewers: Sequence[Viewer]
) -> tuple[str, ...] | None:
    """None means cancelled or unavailable, so the existing profiles are kept."""
    heading = _text(kodi, VIEWERS_PROFILES_FOR, viewer.name)
    rows, ticked = profile_rows(kodi, viewer, profiles or [], viewers)
    if profiles is None or not rows:
        _log.info("config.profiles_unchanged", reason="listing_failed")
        kodi.ok(heading, _text(kodi, VIEWERS_PROFILES_FAILED))
        return None
    request = ListRequest(
        heading=heading,
        rows=rows,
        count_one=_text(kodi, VIEWERS_ONE_PROFILE),
        count_all=_text(kodi, VIEWERS_PROFILES),
        ticked=ticked,
    )
    result = kodi.list_window(request, ListState())
    if result.action != "done":
        _log.info("config.profiles_unchanged", reason="cancelled")
        return None
    return result.keys


def _refused(kodi: KodiApi, exc: ValueError, picked: str | None = None) -> None:
    _log.info("config.name_rejected", reason=str(exc))
    # A clash is told, unlike a plain duplicate: the two names look different, so a silent
    # refusal would read as the input having been lost.
    if isinstance(exc, NameClash):
        if picked is None:
            body = _text(kodi, VIEWERS_NAME_CLASH, exc.existing)
        else:
            # Told apart from a typed name: "choose another name" means nothing for a person
            # picked from the list, whose name only CrossWatch can change.
            body = kodi.localised(VIEWERS_PICK_CLASH).replace("%s", picked, 1).replace("%s", exc.existing, 1)
        kodi.ok(_text(kodi, NOTIFY_HEADING), body)


def _ask_name(kodi: KodiApi, viewers: list[Viewer], current: str = "") -> str | None:
    try:
        return validate_name(kodi.text_input(_text(kodi, VIEWERS_NAME_PROMPT), current), viewers, own=current or None)
    except ValueError as exc:
        _refused(kodi, exc)
        return None


def _find(viewers: Sequence[Viewer], viewer: Viewer) -> Viewer | None:
    """The viewer as the list holds it now: by person id when linked, since CrossWatch may
    have renamed it, else by the name it had."""
    if viewer.person_id:
        return next((v for v in viewers if v.person_id == viewer.person_id), None)
    return next((v for v in viewers if v.name == viewer.name), None)


class _Updated(NamedTuple):
    viewers: list[Viewer]
    # The edited viewer as found before the edit, and where it stood.
    viewer: Viewer
    position: int


def _update(
    store: ViewerStore, viewer: Viewer, edit: Callable[[list[Viewer], Viewer], list[Viewer] | None]
) -> _Updated | None:
    """Apply edit to viewers.json as it is now, and save.

    Read at save time because the service saves this file too, renaming and linking viewers
    when CrossWatch's people change, and a sub-dialog can be open for as long as the household
    likes: an edit made on the list read before it would save the stale copy over that.
    None when the viewer is gone or edit returns None, and nothing is saved. edit runs
    under the store's lock, so it must not open a dialog.
    """
    with store.locked():
        viewers = store.viewers()
        current = _find(viewers, viewer)
        if current is None:
            _log.info("config.edit_dropped", count=1, reason="gone")
            return None
        edited = edit(viewers, current)
        if edited is None:
            return None
        _save(store, edited)
    return _Updated(edited, current, viewers.index(current))


def _add_typed(kodi: KodiApi, store: ViewerStore, playlists: list[str], people: Sequence[Person]) -> str | None:
    viewers = store.viewers()
    name = _ask_name(kodi, viewers)
    if name is None:
        return None
    person = match_person(name, people, {v.person_id for v in viewers if v.person_id})
    # A linked viewer carries CrossWatch's spelling, as the service would rename it to anyway.
    name = person.name if person else name
    selected = _edit_playlists(kodi, Viewer(name=name), playlists, viewers=viewers) or ()
    try:
        with store.locked():
            viewers = store.viewers()
            # Again: the keyboard and the playlist step may have been open across a save by
            # the service, which can have taken the name or linked the person since.
            validate_name(name, viewers)
            if person and any(v.person_id == person.id for v in viewers):
                raise ValueError("taken")
            row = Viewer(name=name, playlists=tuple(selected), person_id=person.id if person else None)
            _save(store, [*viewers, row])
    except ValueError as exc:
        _refused(kodi, exc)
        return None
    _log.info("config.viewer_added", playlists=len(selected), linked=person is not None)
    return name


def _add_viewer(
    kodi: KodiApi,
    store: ViewerStore,
    memory: PromptMemory,
    playlists: list[str],
    people: tuple[Person, ...] | None,
) -> str | None:
    """The first viewer added, to reopen on; None when nothing was."""
    taken = {v.person_id for v in store.viewers() if v.person_id}
    offer = [p for p in people or () if p.id not in taken]
    if not offer:
        return _add_typed(kodi, store, playlists, people or ())
    result = kodi.list_window(
        ListRequest(
            heading=_text(kodi, VIEWERS_ADD_PEOPLE),
            rows=tuple(ListRow(key=p.id, title=p.name) for p in offer),
            count_one=_text(kodi, VIEWERS_ONE_PERSON),
            count_all=_text(kodi, VIEWERS_PEOPLE),
            extra=_text(kodi, VIEWERS_TYPE_NAME),
        ),
        ListState(),
    )
    chosen = [p for p in offer if p.id in result.keys]
    if result.action == "extra":
        # Ticking people and then choosing to type one more keeps the ticks.
        first = _add_people(kodi, store, memory, playlists, chosen, people or ())
        typed = _add_typed(kodi, store, playlists, people or ())
        return first or typed
    if result.action != "done" or not chosen:
        return None
    return _add_people(kodi, store, memory, playlists, chosen, people or ())


def _link_existing(
    viewers: list[Viewer], person: Person, people: Sequence[Person]
) -> tuple[list[Viewer], str] | None:
    """The viewers with the unlinked viewer already named like the person linked to them, and
    that viewer's old name; or None.

    That viewer was typed before CrossWatch listed the person. It keeps its playlists and takes
    CrossWatch's spelling; the caller moves its remembered answers to the new spelling.
    """
    taken = {v.person_id for v in viewers if v.person_id}
    holder = next((v for v in viewers if v.name.casefold() == person.name.casefold()), None)
    if holder is None or holder.person_id or match_person(holder.name, people, taken) != person:
        return None
    return [replace(v, name=person.name, person_id=person.id) if v is holder else v for v in viewers], holder.name


def _add_people(
    kodi: KodiApi,
    store: ViewerStore,
    memory: PromptMemory,
    playlists: list[str],
    chosen: list[Person],
    people: Sequence[Person],
) -> str | None:
    """Add the chosen people; the first one added."""
    if not chosen:
        return None
    first: str | None = None
    added = linked = 0
    for person in chosen:
        refused: ValueError | None = None
        old: str | None = None
        with store.locked():
            # Per person: the playlist step for the one before may have been open across a
            # save by the service.
            viewers = store.viewers()
            try:
                name = validate_name(person.name, viewers, picked=True)
            except ValueError as exc:
                name = person.name
                relinked = None if isinstance(exc, NameClash) else _link_existing(viewers, person, people)
                if relinked is None:
                    refused = exc
                else:
                    viewers, old = relinked
                    # The list first, as a rename saves it: answers under a name no viewer
                    # has yet credit nobody.
                    _save(store, viewers)
            else:
                # Saved before the playlist step, so Back there keeps the person added.
                viewers = [*viewers, Viewer(name=name, person_id=person.id)]
                _save(store, viewers)
        if refused is not None:
            _refused(kodi, refused, picked=person.name)
            continue
        if old is not None:
            if old != person.name:
                memory.rename_viewer(old, person.name)
            first = first or person.name
            linked += 1
            continue
        first = first or name
        added += 1
        selected = _edit_playlists(kodi, Viewer(name=name), playlists, viewers=viewers) or ()
        if selected:
            _update(
                store,
                Viewer(name=name, person_id=person.id),
                lambda vs, cur, picked=selected: apply_edit(vs, cur.name, picked, cur.profiles),
            )
    _log.info("config.people_added", count=added, linked=linked, rejected=len(chosen) - added - linked)
    return first


def _renamed(viewers: list[Viewer], current: Viewer, new: str) -> list[Viewer] | None:
    """The rename applied, or None when the service linked the viewer meanwhile: its name is
    CrossWatch's now, and the service would rename it back. Raises validate_name's
    ValueError: checked against the list as it is now, as the service may have taken the
    name meanwhile."""
    if current.person_id:
        _log.info("config.edit_dropped", count=1, reason="linked")
        return None
    validate_name(new, viewers, own=current.name)
    return rename_viewer(viewers, current.name, new)


def _act(
    kodi: KodiApi,
    store: ViewerStore,
    memory: PromptMemory,
    viewers: list[Viewer],
    result: ViewersResult,
    listing: PlaylistListing,
    profiles: list[str] | None,
) -> str:
    """One action on the highlighted viewer; the row to reopen on.

    Each edit is applied by _update, to the list as it is when saved.
    """
    viewer = next((v for v in viewers if v.name == result.key), None)
    if viewer is None:
        return ""
    if result.action == "playlists":
        picked = _edit_playlists(kodi, viewer, listing.matchable, listing.unusable, viewers)
        if picked is None:
            _log.info("config.playlists_unchanged", reason="cancelled")
            return viewer.name
        done = _update(store, viewer, lambda vs, cur: apply_edit(vs, cur.name, picked, cur.profiles))
        if done is None:
            return ""
        _log.info("config.viewer_updated", playlists=len(picked))
        return done.viewer.name
    if result.action == "profiles":
        chosen = _edit_profiles(kodi, viewer, profiles, viewers)
        if chosen is None:
            return viewer.name
        done = _update(store, viewer, lambda vs, cur: apply_edit(vs, cur.name, cur.playlists, chosen))
        if done is None:
            return ""
        _log.info("config.viewer_updated", profiles=len(chosen))
        return done.viewer.name
    if result.action == "rename":
        # A linked viewer's name is CrossWatch's, and the service would rename it back.
        if viewer.person_id:
            return viewer.name
        new = _ask_name(kodi, viewers, viewer.name)
        if new is None or new == viewer.name:
            return viewer.name
        try:
            done = _update(store, viewer, lambda vs, cur: _renamed(vs, cur, new))
        except ValueError as exc:
            _refused(kodi, exc)
            return viewer.name
        if done is None:
            return ""
        _log.info("config.viewer_renamed", answers=memory.rename_viewer(done.viewer.name, new))
        return new
    if result.action == "remove":
        question = _text(kodi, VIEWERS_REMOVE_CONFIRM, viewer.name)
        if not kodi.confirm_window(question, _text(kodi, VIEWERS_REMOVE_MESSAGE)):
            return viewer.name
        done = _update(store, viewer, lambda vs, cur: remove_viewer(vs, cur.name))
        if done is None:
            return ""
        changed, forgotten = memory.drop_viewer(done.viewer.name)
        _log.info("config.viewer_removed", answers=changed, forgotten=forgotten)
        # The row that takes its place: the next one, or the one before at the end.
        left = done.viewers
        return left[min(done.position, len(left) - 1)].name if left else ""
    return viewer.name


def run_dialog(
    kodi: KodiApi,
    store: ViewerStore,
    memory: PromptMemory,
    routes: Callable[[], RouteFacts | None] = lambda: None,
) -> None:
    """routes and viewers.json are read on every pass, and every edit is applied to
    viewers.json as it is when saved: the service pings within a tick of a change and renames
    linked viewers when CrossWatch does, and the open screen should catch up rather than save
    its stale copy over that."""
    # Once per screen: each is a directory or profile listing over JSON-RPC.
    listing = available_playlists(kodi)
    if not listing.matchable:
        _log.info("config.no_playlists_found", unusable=len(listing.unusable))
    profiles = available_profiles(kodi)

    key = ""
    if not store.viewers():
        # An empty list has nothing to choose from: start where the household must.
        facts = routes()
        added = _add_viewer(kodi, store, memory, listing.matchable, facts.people if facts else None)
        if added is None:
            return
        key = added

    while True:
        facts = routes()
        result = kodi.viewers_window(viewers_request(kodi, store.viewers(), listing, profiles, facts), key)
        if result.action == "close":
            return
        if result.action == "add":
            key = _add_viewer(kodi, store, memory, listing.matchable, facts.people if facts else None) or result.key
        else:
            # Read again: the window may have been open across a save by the service.
            key = _act(kodi, store, memory, store.viewers(), result, listing, profiles)


def main() -> None:
    kodi = KodiRuntime()
    settings = read_settings(kodi)
    # A separate interpreter with its own module state: without this every line below is
    # written to a no-op sink and a failure here is invisible everywhere.
    logmod.configure(log_dir=paths.log_dir(kodi), debug=settings.debug_logging, sink=kodi.log)
    run_dialog(
        kodi,
        JsonViewerStore(paths.viewers_path(kodi)),
        PromptMemory(paths.prompts_path(kodi)),
        lambda: current_routes(kodi),
    )
