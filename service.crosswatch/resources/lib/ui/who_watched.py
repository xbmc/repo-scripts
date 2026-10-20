# SPDX-License-Identifier: GPL-2.0-only
"""What the who-watched window asks and what its answer means, free of Kodi windows.

Row 0 is Everyone, then each viewer in configuration order. The window holds the ticked
set; everything that decides what a tick means lives here, where it is unit testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from resources.lib.constants import WHO_WATCHED_EPISODE
from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger

_log = get_logger("ui")

EVERYONE_ROW = 0


@dataclass(frozen=True)
class WhoWatchedRequest:
    title: str
    subtitle: str
    poster: str
    names: tuple[str, ...]
    preselect: tuple[str, ...] = ()
    # 0 for none. The question at the end of playback must not park the service thread.
    autoclose_seconds: int = 0
    close_on_playback: bool = False


def initial(request: WhoWatchedRequest) -> frozenset[str]:
    return frozenset(name for name in request.preselect if name in request.names)


def toggle(names: tuple[str, ...], ticked: frozenset[str], row: int) -> frozenset[str]:
    if row == EVERYONE_ROW:
        # Expanded to names rather than kept as "everyone", so a viewer added later is not
        # credited with shows the household watched before they existed.
        return frozenset() if everyone(names, ticked) else frozenset(names)
    if not 1 <= row <= len(names):
        return ticked
    return ticked ^ {names[row - 1]}


def everyone(names: tuple[str, ...], ticked: frozenset[str]) -> bool:
    return bool(names) and all(name in ticked for name in names)


def answer(names: tuple[str, ...], ticked: frozenset[str]) -> tuple[str, ...]:
    return tuple(name for name in names if name in ticked)


def episode_subtitle(kodi: KodiApi, season: int | None, episode: int | None) -> str:
    if season is None or episode is None:
        return ""
    # replace rather than %: a translation that drops a placeholder must not raise.
    text = kodi.localised(WHO_WATCHED_EPISODE)
    return text.replace("%s", str(season), 1).replace("%s", str(episode), 1)


def year_subtitle(year: int | None) -> str:
    return str(year) if year else ""


def show_poster(kodi: KodiApi, show_library_id: int | None) -> str:
    return _poster(kodi, "VideoLibrary.GetTVShowDetails", "tvshowid", "tvshowdetails", show_library_id)


def movie_poster(kodi: KodiApi, library_id: int | None) -> str:
    return _poster(kodi, "VideoLibrary.GetMovieDetails", "movieid", "moviedetails", library_id)


def _poster(kodi: KodiApi, method: str, id_key: str, result_key: str, library_id: int | None) -> str:
    """The poster art, or "" for the window's placeholder. Never fails the question."""
    if library_id is None:
        return ""
    try:
        result = kodi.jsonrpc(method, {id_key: library_id, "properties": ["art"]})
    except Exception as exc:
        _log.debug("ui.poster_lookup_failed", method=method, error_type=type(exc).__name__)
        return ""
    details = result.get(result_key)
    art = details.get("art") if isinstance(details, dict) else None
    poster = art.get("poster") if isinstance(art, dict) else None
    return poster if isinstance(poster, str) else ""
