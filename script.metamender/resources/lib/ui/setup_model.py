"""The setup wizard as plain logic: which steps exist, what each needs
before Next, and what Finish writes. The window in setup_window is a thin
view over this module; nothing here talks to Kodi's GUI, so the whole flow
is unit tested.

The wizard asks for the TMDB key, then shows the library list, where each
library is included or left out and given its own settings on its page,
then a summary. Finish writes the key to Kodi's add-on settings and the
libraries to sources.json. The library list also opens on its own from
the add-on settings (LIBRARIES mode).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Optional

from resources.lib.data.libraries import (
    FIELD_TOGGLES,
    Library,
    LibraryConfig,
    add_new_libraries,
    resolve_country,
)
from resources.lib.data.sources import CONTENT_MOVIES, CONTENT_TVSHOWS, CONTENT_UNKNOWN
from resources.lib.providers.tmdb import KEY_OK, KEY_UNCHECKED

# The field toggles in the order the library page lists them.
TOGGLES: tuple[str, ...] = tuple(FIELD_TOGGLES)

# Toggles that mean something in one kind of library only: the page of a
# library that holds the other kind hides them, and their ticks stay as
# they are. A library Kodi has scanned nothing into, or one holding both
# kinds, shows every toggle.
MOVIE_TOGGLES: frozenset[str] = frozenset({"trailers", "taglines", "movie_sets"})
TV_TOGGLES: frozenset[str] = frozenset({"episode_titles", "episode_thumbs"})

# rating_source values in the order the rating picker lists them, the
# default first.
RATING_OPTIONS: tuple[int, ...] = (4, 0, 1, 2, 3)
# text_source_order values in the order the text picker lists them.
TEXT_OPTIONS: tuple[int, ...] = (2, 0, 1)
# fallback_order values: TheTVDB first, then TMDB first.
FALLBACK_ORDER_OPTIONS: tuple[int, ...] = (0, 1)
# The toggles text_source_order decides (engine/text.py _text_chain).
TEXT_TOGGLES: tuple[str, ...] = ("plots", "episode_titles", "main_titles")
# The toggles whose art comes from the Art source setting.
ART_TOGGLES: tuple[str, ...] = ("posters", "fanart", "other_art")
# art_source values: TMDB, then fanart.tv.
ART_OPTIONS: tuple[int, ...] = (0, 1)

WIZARD = "wizard"
LIBRARIES = "libraries"


@dataclass
class SetupState:
    api_key: str = ""
    # KEY_OK or KEY_UNCHECKED once the key step passed; "" before that. A
    # refused key never gets here: the key step keeps it out.
    key_status: str = ""
    libraries: LibraryConfig = field(default_factory=LibraryConfig)
    # The path of the library whose page is shown; None shows the step.
    open_library: Optional[str] = None


def initial_state(
    settings: dict[str, Any],
    libraries: Optional[LibraryConfig],
    discovered: list[dict[str, str]],
    ui_language: str,
) -> SetupState:
    """The state every step opens with: the stored libraries with Kodi's
    current labels, plus every discovered library they do not cover yet,
    not included. ``settings`` holds tmdb_api_key; a stored key was
    accepted when it was saved."""
    key = str(settings.get("tmdb_api_key") or "").strip()
    labels = {str(s.get("path") or ""): str(s.get("label") or "") for s in discovered}
    config = LibraryConfig([
        replace(lib, label=labels.get(lib.path) or lib.label)
        for lib in (libraries.libraries if libraries is not None else [])
    ])
    add_new_libraries(config, discovered, ui_language)
    return SetupState(api_key=key, key_status=KEY_OK if key else "", libraries=config)


def page_toggles(content: str) -> tuple[str, ...]:
    """The toggles a library page lists for a library holding ``content``
    (data/sources.library_content), in TOGGLES order."""
    hidden: frozenset[str] = frozenset()
    if content == CONTENT_MOVIES:
        hidden = TV_TOGGLES
    elif content == CONTENT_TVSHOWS:
        hidden = MOVIE_TOGGLES
    return tuple(t for t in TOGGLES if t not in hidden)


def shown_toggles(lib: Library, content: str) -> frozenset[str]:
    """The library's ticks that apply to what it holds."""
    return lib.toggles & frozenset(page_toggles(content))


def page_groups(lib: Library, content: str = CONTENT_UNKNOWN) -> list[str]:
    """The groups the library's page shows, in order: a group whose
    toggles are all off, or all hidden, is hidden."""
    on = shown_toggles(lib, content)
    groups = ["language", "fields"]
    if "ratings" in on:
        groups.append("rating")
    if any(t in on for t in TEXT_TOGGLES):
        groups.append("text")
    if "main_titles" in on:
        groups.append("titles")
    if any(t in on for t in ART_TOGGLES):
        groups.append("art")
    if "certifications" in on:
        groups.append("age_ratings")
    return groups


def country_missing(lib: Library, ui_language: str) -> bool:
    """True when the library writes age ratings but no country applies
    (Automatic found no preset for its language or Kodi's)."""
    return "certifications" in lib.toggles and resolve_country(lib, ui_language) is None


def changes_nothing(config: LibraryConfig) -> bool:
    """True when no included library has anything switched on."""
    return not any(lib.included and lib.toggles for lib in config.libraries)


class SetupFlow:
    """Step order and position. A library's page is not a step: while
    SetupState.open_library is set the window shows that page in place of
    the libraries step."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.current = LIBRARIES if mode == LIBRARIES else "key"

    def steps(self, state: SetupState) -> list[str]:
        if self.mode == LIBRARIES:
            return [LIBRARIES]
        return ["key", LIBRARIES, "summary"]

    def index(self, state: SetupState) -> int:
        """1-based position, for "Step N of M"."""
        return self._position(state) + 1

    def total(self, state: SetupState) -> int:
        return len(self.steps(state))

    def next(self, state: SetupState) -> bool:
        steps = self.steps(state)
        pos = self._position(state)
        if pos + 1 >= len(steps):
            return False
        self.current = steps[pos + 1]
        return True

    def back(self, state: SetupState) -> bool:
        pos = self._position(state)
        if pos == 0:
            return False
        self.current = self.steps(state)[pos - 1]
        return True

    def can_advance(self, state: SetupState) -> bool:
        if self.current == "key":
            return bool(state.api_key.strip()) and state.key_status in (KEY_OK, KEY_UNCHECKED)
        # A list with nothing included is allowed: the summary says that
        # nothing will change.
        return True

    def _position(self, state: SetupState) -> int:
        return self.steps(state).index(self.current)


def settings_to_write(state: SetupState) -> dict[str, Any]:
    """The add-on settings Finish writes, setup_complete last. Finish has
    saved the libraries, so the 1.1 settings are never converted again."""
    return {"tmdb_api_key": state.api_key.strip(), "libraries_converted": True,
            "setup_complete": True}


def libraries_to_write(state: SetupState) -> LibraryConfig:
    """The libraries Finish (or the Libraries dialog's Save) writes."""
    return LibraryConfig(list(state.libraries.libraries))


def mask_key(key: str) -> str:
    """Four stars and the key's last four characters, so the mask tells
    keys apart without showing how long the key is; a key that short is
    hidden entirely."""
    key = key.strip()
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]
