"""The Home window properties shared with plugin.video.kofin and skins.

Kofin publishes ``[[start_seconds_or_null, text], ...]``.
"""

import json
from typing import List, Optional, Tuple

import xbmcgui

LyricLine = Tuple[Optional[float], str]

HOME_WINDOW = 10000

# Written by plugin.video.kofin.
PROP_HAS = "kofin.lyric.has"
PROP_JSON = "kofin.lyric.json"
PROP_PATH = "kofin.lyric.path"
# Written by a skin that draws the lyrics itself: the id of the list to drive.
PROP_CONTROL = "kofin.lyric.control"
# Written by such a skin to have the height setting applied to its overlay:
# the backdrop ids, space-separated. Skin XML cannot read a size from a
# property.
PROP_PANEL = "kofin.lyric.panel"
# Ours: raised while our window has taken over for scrolling, so the skin's
# overlay stands aside.
PROP_INTERACTIVE = "kofin.lyric.interactive"
# Ours: raised while lyrics belong on screen. Skins must gate on this, not on
# PROP_HAS: showAutomatically and showUntimed work by withholding it.
PROP_SHOW = "kofin.lyric.show"
# Ours: the song's width class -- "narrow", "mid", "medium" or "wide" -- for a
# skin to pick an authored overlay width by, as skin geometry cannot bind a
# property.
PROP_SIZE = "kofin.lyric.size"


def _window() -> xbmcgui.Window:
    return xbmcgui.Window(HOME_WINDOW)


def has_lyrics() -> bool:
    return _window().getProperty(PROP_HAS) == "true"


def directory_path() -> str:
    """The plugin path a skin's list is filled from; it carries the song id."""
    return _window().getProperty(PROP_PATH)


def skin_control_id() -> int:
    """The list control a skin has asked us to drive, or 0 if none has."""
    try:
        return int(_window().getProperty(PROP_CONTROL))
    except (TypeError, ValueError):
        return 0


def skin_panel_ids() -> List[int]:
    """The overlay backdrops a skin has opted into resizing; empty if none."""
    ids: List[int] = []
    for token in _window().getProperty(PROP_PANEL).split():
        try:
            ids.append(int(token))
        except ValueError:
            return []  # malformed: ignore it all
    return ids


def set_size(bucket: Optional[str]) -> None:
    if bucket:
        _window().setProperty(PROP_SIZE, bucket)
    else:
        _window().clearProperty(PROP_SIZE)


def set_interactive(active: bool) -> None:
    if active:
        _window().setProperty(PROP_INTERACTIVE, "true")
    else:
        _window().clearProperty(PROP_INTERACTIVE)


def set_show(active: bool) -> None:
    if active:
        _window().setProperty(PROP_SHOW, "true")
    else:
        _window().clearProperty(PROP_SHOW)


def published_lines() -> List[LyricLine]:
    """What kofin published for the playing song."""
    raw = _window().getProperty(PROP_JSON)
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(payload, list):
        return []

    lines: List[LyricLine] = []
    for entry in payload:
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        start, text = entry
        lines.append((float(start) if start is not None else None, str(text)))
    return lines


def is_timed(lines: List[LyricLine]) -> bool:
    """Whether the lyrics carry timings."""
    return bool(lines) and lines[0][0] is not None


def active_index(lines: List[LyricLine], position: float) -> Optional[int]:
    """Index of the line playing at ``position`` seconds, or None before the
    first timed line. Of lines sharing a time, the last."""
    for index in range(len(lines) - 1, -1, -1):
        start = lines[index][0]
        if start is not None and start <= position:
            return index
    return None
