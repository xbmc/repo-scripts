"""Window colour themes, picked by the `theme` setting.

The windows read these as MM.* window properties; a property the XML reads
but nobody set tints a texture white, so every theme defines all three.
"""
from __future__ import annotations

from resources.lib.utils import get_int_setting

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
