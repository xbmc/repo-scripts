# SPDX-License-Identifier: GPL-2.0-only
"""Ask who watched, but only when it is worth asking, and only at the end of playback.

The gate is separate from the dialog so every suppression is unit testable and logged with
a reason code. A silent branch here is indistinguishable from a bug.

A dismissed dialog returns no viewers, nothing is remembered, and the same show is asked
about next time. Never lose a watch, never guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from resources.lib.advanced_settings import Thresholds
from resources.lib.identity import Identity
from resources.lib.kodi import WINDOW_INVALID, KodiApi
from resources.lib.log import get_logger
from resources.lib.models import MediaItem, Viewer
from resources.lib.storage import PromptMemory
from resources.lib.ui.who_watched import WhoWatchedRequest, episode_subtitle, movie_poster, show_poster, year_subtitle

_log = get_logger("prompt")

# Ordered by preference: the first present wins, so the key is stable across id ordering.
_ID_PREFERENCE = ("tvdb", "tmdb", "imdb")


def show_key(media: MediaItem) -> str | None:
    """The key a remembered answer hangs on.

    Prefers the show's unique id: tvshowid is a database row id that a library clean
    reassigns, so a key built on it can start attributing a different show to whoever
    answered for the old one. A movie returns None; there is no second showing to benefit.
    """
    if media.media_type != "episode":
        return None
    return key_for_show(media.show_ids, media.show_library_id)


def key_for_show(show_ids: dict[str, str], show_library_id: int | None) -> str | None:
    """The one rule for a show's key, shared by the prompt and the settings screen."""
    for namespace in _ID_PREFERENCE:
        value = show_ids.get(namespace)
        if value:
            return f"show:{namespace}:{value}"
    if show_library_id is not None:
        return f"{LIBRARY_KEY_PREFIX}{show_library_id}"
    return None


# A key on Kodi's own database id. Used only for a show the scraper could not identify, and
# never trusted on its own: a library clean can hand the id to a different show.
LIBRARY_KEY_PREFIX = "tvshow:"


def recall(memory: PromptMemory, media: MediaItem) -> tuple[str, ...]:
    """The remembered answer for this show, or nothing.

    An answer keyed on Kodi's database id counts only while the show at that id still has
    the title and year it had when the answer was given.
    """
    key = show_key(media)
    answer = memory.recall(key) if key else None
    if answer is None:
        return ()
    if key and key.startswith(LIBRARY_KEY_PREFIX):
        if answer.title is None or (answer.title, answer.year) != (media.title, media.show_year):
            _log.info("prompt.memory_unverified", media_type=media.media_type, library_id=media.show_library_id)
            return ()
    return answer.viewers


@dataclass(frozen=True)
class GateDecision:
    ask: bool
    reason: str = ""


def gate(
    identity: Identity,
    viewers: list[Viewer],
    media: MediaItem,
    position_ms: int | None,
    thresholds: Thresholds,
    movie_prompts_enabled: bool,
    dialog_id: int,
    shutting_down: bool,
) -> GateDecision:
    def refuse(reason: str) -> GateDecision:
        _log.info(
            "prompt.suppressed", reason=reason, media_type=media.media_type, library_id=media.library_id
        )
        return GateDecision(ask=False, reason=reason)

    # A remembered answer is not looked up here: start resolution used it, so a watch that
    # has one arrives resolved.
    if identity.viewers:
        return refuse("resolved")
    if not viewers:
        return refuse("no_viewers_configured")
    if len(viewers) < 2:
        return refuse("single_viewer")
    if media.media_type == "movie" and not movie_prompts_enabled:
        return refuse("movie_prompt_disabled")
    if (position_ms or 0) < thresholds.ignore_seconds_at_start * 1000:
        return refuse("below_ignore_seconds_at_start")

    if shutting_down:
        # Must be checked before the dialog: during shutdown Kodi refuses to draw one and
        # returns None without saying so, which would otherwise be recorded as a dismissal.
        return refuse("shutting_down")
    if dialog_id != WINDOW_INVALID:
        return refuse("dialog_busy")

    _log.info("prompt.asking", media_type=media.media_type, library_id=media.library_id)
    return GateDecision(ask=True)


def choose_viewers(
    kodi: KodiApi,
    viewers: list[Viewer],
    title: str,
    subtitle: str,
    poster: str,
    preselect: tuple[str, ...] = (),
    autoclose: int = 0,
    close_on_playback: bool = False,
) -> tuple[str, ...] | None:
    """None when cancelled, () when Done with nobody ticked, else the names.

    The two differ for the settings screen: cancel leaves an answer alone, while confirming
    with nobody ticked is a deliberate request to forget it.
    """
    request = WhoWatchedRequest(
        title=title,
        subtitle=subtitle,
        poster=poster,
        names=tuple(v.name for v in viewers),
        preselect=preselect,
        autoclose_seconds=autoclose,
        close_on_playback=close_on_playback,
    )
    return kodi.who_watched(request)


def header(kodi: KodiApi, media: MediaItem) -> tuple[str, str]:
    """The subtitle and poster an end-of-playback window shows, the same for every question."""
    if media.media_type == "episode":
        return episode_subtitle(kodi, media.season, media.episode), show_poster(kodi, media.show_library_id)
    return year_subtitle(media.year), movie_poster(kodi, media.library_id)


def ask(kodi: KodiApi, viewers: list[Viewer], media: MediaItem, autoclose: int) -> tuple[str, ...]:
    subtitle, poster = header(kodi, media)
    # Closes when playback starts: the household has moved on, and an open window would
    # otherwise sit over the next item.
    answer = choose_viewers(
        kodi, viewers, media.title or "", subtitle, poster, autoclose=autoclose, close_on_playback=True
    )
    if not answer:
        _log.info("prompt.dismissed", media_type=media.media_type, library_id=media.library_id)
        return ()
    _log.info(
        "prompt.answered", media_type=media.media_type, viewers_count=len(answer), everyone=len(answer) == len(viewers)
    )
    _log.debug("prompt.answer", viewers=",".join(answer))
    return answer


def remember(memory: PromptMemory, media: MediaItem, names: tuple[str, ...]) -> None:
    key = show_key(media)
    if key and names:
        memory.remember(key, names, title=media.title, year=media.show_year)
