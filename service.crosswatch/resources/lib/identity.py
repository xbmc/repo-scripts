# SPDX-License-Identifier: GPL-2.0-only
"""Who watched this: a pure decision, playlist then profile, and the one viewer when there is
only one.

No I/O. The caller supplies the index and the active profile label, so this module is a
decision table its tests can exercise without any Kodi double at all. The prompt is the
third mechanism and lives in prompt.py, because it can only run after the stop event.

The log line carries the mechanism and the ids, never the names: identity is DEBUG, and
reaches only the addon's own file.
"""

from __future__ import annotations

from dataclasses import dataclass

from resources.lib.log import get_logger
from resources.lib.models import MediaItem, Viewer, ViewersSource
from resources.lib.playlist_index import PlaylistIndex

_log = get_logger("identity")


@dataclass(frozen=True)
class Identity:
    viewers: tuple[str, ...]
    source: ViewersSource | None


UNRESOLVED = Identity((), None)


def _by_playlist(index: PlaylistIndex | None, media: MediaItem, viewers: list[Viewer]) -> tuple[str, ...]:
    if index is None:
        return ()
    if media.media_type == "episode":
        names = index.viewers_for("tvshow", media.show_library_id)
    else:
        names = index.viewers_for("movie", media.library_id)
    # The index holds the names it was built with; a viewer renamed or removed since must
    # not be sent under the old name.
    known = {v.name for v in viewers}
    return tuple(name for name in names if name in known)


def _by_profile(label: str, viewers: list[Viewer]) -> tuple[str, ...]:
    if not label:
        return ()
    wanted = label.casefold()
    return tuple(v.name for v in viewers if any(p.casefold() == wanted for p in v.profiles))


def resolve(
    index: PlaylistIndex | None,
    viewers: list[Viewer],
    media: MediaItem,
    profile_label: str,
    remembered: tuple[str, ...] = (),
) -> Identity:
    """Playlist, then profile, then a remembered answer, then the only viewer.

    The memory is passed in rather than read here, so this stays a pure decision. It is
    consulted at start as well as at stop: a show answered once resolves its next episode
    before playback begins, so start and progress carry the viewer too.
    """
    lookup_id = media.show_library_id if media.media_type == "episode" else media.library_id

    names = _by_playlist(index, media, viewers)
    if names:
        _log.info(
            "identity.resolved",
            source="playlist",
            media_type=media.media_type,
            library_id=media.library_id,
            lookup_id=lookup_id,
            viewers_count=len(names),
        )
        _log.debug("identity.viewers", source="playlist", viewers=",".join(names))
        return Identity(names, "playlist")

    names = _by_profile(profile_label, viewers)
    if names:
        _log.info(
            "identity.resolved",
            source="profile",
            media_type=media.media_type,
            library_id=media.library_id,
            viewers_count=len(names),
        )
        _log.debug("identity.viewers", source="profile", profile=profile_label, viewers=",".join(names))
        return Identity(names, "profile")

    if remembered:
        _log.info(
            "identity.resolved",
            source="prompt",
            media_type=media.media_type,
            library_id=media.library_id,
            viewers_count=len(remembered),
            recalled=True,
        )
        _log.debug("identity.viewers", source="remembered", viewers=",".join(remembered))
        return Identity(remembered, "prompt")

    if len(viewers) == 1:
        # One person in the household: whatever plays is theirs, and the question is never
        # asked for one viewer. No mechanism decided it, so no viewers_source is claimed.
        _log.info(
            "identity.resolved",
            source="single",
            media_type=media.media_type,
            library_id=media.library_id,
            viewers_count=1,
        )
        return Identity((viewers[0].name,), None)

    _log.info(
        "identity.unresolved",
        media_type=media.media_type,
        library_id=media.library_id,
        lookup_id=lookup_id,
        index_ready=index is not None,
    )
    return UNRESOLVED
