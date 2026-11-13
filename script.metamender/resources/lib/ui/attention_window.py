"""The attention window: a serious problem that needs the user, with the one
thing that fixes it, and a line for each other open problem. Same family
style as the setup and progress windows.

Logging:
    Logger: 'attention'
"""
from __future__ import annotations

from typing import Any

import xbmcgui

from resources.lib.service.attention import (
    FOLDER_OFFLINE,
    KEY_REJECTED,
    NO_KEY,
    SCANS_FAILING,
    SETUP,
    Problem,
)
from resources.lib.ui.theme import theme_colours
from resources.lib.utils import get_addon, lang

_XML = "script-metamender-attention.xml"
FIX = 31
LATER = 32
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

# The main problem's sentence, and its short form on an "Also:" line; a
# "{}" takes the problem's detail (the offline folders).
FULL_TEXT = {SETUP: 32491, NO_KEY: 32493, KEY_REJECTED: 32495,
             SCANS_FAILING: 32497, FOLDER_OFFLINE: 32499}
ALSO_TEXT = {SETUP: 32492, NO_KEY: 32494, KEY_REJECTED: 32496,
             SCANS_FAILING: 32498, FOLDER_OFFLINE: 32500}
# Only these problems can be fixed from Kodi: by running setup.
_FIXED_BY_SETUP = frozenset({SETUP, NO_KEY, KEY_REJECTED})


def attention_properties(main: Problem, others: list[Problem]) -> dict[str, str]:
    """Every window property the attention XML reads."""
    props = {
        "MM.Heading": lang(32490),
        "MM.Problem": lang(FULL_TEXT[main.kind]).format(main.detail),
        "MM.Also": "\n".join(
            lang(32501).format(lang(ALSO_TEXT[p.kind]).format(p.detail)) for p in others
        ),
        "MM.Action": lang(32502) if main.kind in _FIXED_BY_SETUP else "",
        "MM.Later": lang(32503),
    }
    props.update(theme_colours())
    return props


class AttentionWindow(xbmcgui.WindowXMLDialog):
    """``result`` is "setup" when the fix button was pressed, else "later".
    The properties are set before doModal()."""

    props: dict[str, str]
    result: str = "later"

    def onInit(self) -> None:
        # The fix button has focus when there is one, so an accidental OK
        # fixes rather than dismisses. Its visibility reads a property, so
        # the properties are set before the window opens (see
        # show_attention_window), not here.
        self.setFocusId(FIX if self.props["MM.Action"] else LATER)

    def onClick(self, controlId: int) -> None:
        if controlId == FIX:
            self.result = "setup"
        self.close()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()


def show_attention_window(main: Problem, others: list[Problem]) -> str:
    """Show the window until the user answers: "setup" or "later"."""
    window = AttentionWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.props = attention_properties(main, others)
    for key, value in window.props.items():
        window.setProperty(key, value)
    window.doModal()
    result = window.result
    del window
    return result
