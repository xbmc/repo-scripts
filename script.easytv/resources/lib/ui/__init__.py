#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV User Interface Components.

This package provides UI functionality:
- main.py: UI entry point logic (called from default.py)
- browse_window.py: BrowseWindow class (main episode list window)
- context_menu.py: ContextMenuWindow class (right-click menu)
- dialogs.py: Dialog helper functions (error dialogs, playlist selection)
"""
from __future__ import annotations

from typing import Optional

import xbmcgui


def apply_theme(window: xbmcgui.WindowXMLDialog, addon_id: Optional[str] = None) -> None:
    """Set theme color properties on a window for skin XML $INFO references.

    Args:
        window: The dialog window to set properties on.
        addon_id: Optional addon ID to read theme from (for clone support).
            If None, reads from the calling addon's settings.
    """
    import xbmcaddon
    from resources.lib.constants import THEME_COLORS, SETTING_THEME
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    theme = addon.getSetting(SETTING_THEME) or '0'
    for prop, value in THEME_COLORS.get(theme, THEME_COLORS['0']).items():
        window.setProperty(prop, value)
