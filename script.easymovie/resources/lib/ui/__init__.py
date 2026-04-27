"""
UI package initialization.

Provides theme application for all EasyMovie windows.
"""
from __future__ import annotations

from typing import Optional

import xbmcgui

from resources.lib.constants import THEME_COLORS


def apply_theme(window: xbmcgui.WindowXMLDialog, addon_id: Optional[str] = None) -> None:
    """Apply theme colors as window properties on the given dialog.

    Must be called in each dialog's onInit() so $INFO[Window.Property(...)]
    resolves correctly against the current window.

    Args:
        window: The dialog window to set color properties on.
        addon_id: Optional addon ID (for clone support).
    """
    import xbmcaddon
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    try:
        theme = int(addon.getSetting('theme') or '0')
    except (ValueError, TypeError):
        theme = 0
    colors = THEME_COLORS.get(theme, THEME_COLORS[0])
    for prop, value in colors.items():
        window.setProperty(prop, value)
