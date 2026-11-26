"""Window colour themes, picked by the `theme` setting.

The skin XML reads these colours from the Home window as MetaMender.*
properties, never from its own window: Kodi expands a colour's $INFO without
a window context, so an unqualified Window.Property() is read from whichever
dialog is on top, and every library write briefly puts another one there
while the Videos window redraws. A property the XML reads but nobody set
tints a texture white, so every theme defines all three.
"""
from __future__ import annotations

import xbmcgui

from resources.lib.constants import KODI_HOME_WINDOW_ID
from resources.lib.utils import get_int_setting

HOME_PREFIX = "MetaMender."

THEMES: dict[int, dict[str, str]] = {
    0: {"MM.Accent": "FFF5A623", "MM.ButtonFocus": "FFD4912A",
        "MM.ButtonTextFocused": "FF0D1117"},  # Golden Hour
    1: {"MM.Accent": "FFA78BFA", "MM.ButtonFocus": "FF7C3AED",
        "MM.ButtonTextFocused": "FFFFFFFF"},  # Ultraviolet
    2: {"MM.Accent": "FFF87171", "MM.ButtonFocus": "FFEF4444",
        "MM.ButtonTextFocused": "FFFFFFFF"},  # Ember
    3: {"MM.Accent": "FF60A5FA", "MM.ButtonFocus": "FF3B82F6",
        "MM.ButtonTextFocused": "FFFFFFFF"},  # Nightfall
}


def theme_colours() -> dict[str, str]:
    """The colours of the chosen theme; an unknown value means Golden Hour."""
    return dict(THEMES.get(get_int_setting("theme", 0), THEMES[0]))


def publish_theme() -> None:
    """Put the chosen theme's colours on the Home window, before a window
    opens, so a theme picked since the last window shows in the next one."""
    home = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    for key, value in theme_colours().items():
        home.setProperty(HOME_PREFIX + key[len("MM."):], value)
