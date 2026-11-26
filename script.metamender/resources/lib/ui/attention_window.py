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
    LIBRARIES_CONVERTED,
    NEW_LIBRARY,
    NO_KEY,
    SCANS_FAILING,
    SETTINGS_UNREAD,
    SETUP,
    UNMATCHED,
    Problem,
)
from resources.lib.ui.theme import publish_theme
from resources.lib.utils import get_addon, lang

_XML = "script-metamender-attention.xml"
FIX = 31
LATER = 32
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

# The main problem's sentence, and its short form on an "Also:" line; a
# "{}" takes the problem's detail (the offline folders, the new libraries'
# labels, the number of items in no library).
FULL_TEXT = {SETUP: 32491, NO_KEY: 32493, KEY_REJECTED: 32495,
             SCANS_FAILING: 32497, FOLDER_OFFLINE: 32499,
             NEW_LIBRARY: 32652, UNMATCHED: 32654, LIBRARIES_CONVERTED: 32656}
ALSO_TEXT = {SETUP: 32492, NO_KEY: 32494, KEY_REJECTED: 32496,
             SCANS_FAILING: 32498, FOLDER_OFFLINE: 32500,
             NEW_LIBRARY: 32653, UNMATCHED: 32655, LIBRARIES_CONVERTED: 32657}
# The problems the fix button answers, the answer it gives and its label;
# the others cannot be fixed from Kodi.
_FIXES = {SETUP: "setup", NO_KEY: "setup", KEY_REJECTED: "setup",
          NEW_LIBRARY: "libraries", UNMATCHED: "libraries",
          LIBRARIES_CONVERTED: "libraries"}
_FIX_LABEL = {"setup": 32502, "libraries": 32651}
# (full, short) forms for a detail naming several libraries or counting
# other than one item; the tables above hold the other form.
_SEVERAL_TEXT = {NEW_LIBRARY: (32697, 32698)}
_ONE_TEXT = {UNMATCHED: (32699, 32700)}
# (full, short) forms of the conversion notice when the old settings could
# not be read.
_UNREAD_TEXT = (32705, 32706)


def problem_text(problem: Problem, short: bool) -> str:
    """The problem's sentence (or its short form) with its detail filled
    in, worded for one library or item or for several."""
    form = 1 if short else 0
    text = (ALSO_TEXT if short else FULL_TEXT)[problem.kind]
    if problem.kind in _SEVERAL_TEXT and ", " in problem.detail:
        text = _SEVERAL_TEXT[problem.kind][form]
    if problem.kind in _ONE_TEXT and problem.detail.strip() == "1":
        text = _ONE_TEXT[problem.kind][form]
    if problem.kind == LIBRARIES_CONVERTED and problem.detail == SETTINGS_UNREAD:
        text = _UNREAD_TEXT[form]
    return lang(text).format(problem.detail)


def fix_for(kind: str) -> str:
    """What the fix button does for a main problem of this kind: "setup",
    "libraries", or "" when there is no button."""
    return _FIXES.get(kind, "")


def attention_properties(main: Problem, others: list[Problem]) -> dict[str, str]:
    """Every window property the attention XML reads."""
    props = {
        "MM.Heading": lang(32490),
        "MM.Problem": problem_text(main, short=False),
        "MM.Also": "\n".join(lang(32501).format(problem_text(p, short=True)) for p in others),
        "MM.Action": lang(_FIX_LABEL[fix_for(main.kind)]) if fix_for(main.kind) else "",
        "MM.Later": lang(32503),
    }
    return props


class AttentionWindow(xbmcgui.WindowXMLDialog):
    """``result`` is ``fix`` (see fix_for) when the fix button was pressed,
    else "later". The properties and ``fix`` are set before doModal()."""

    props: dict[str, str]
    fix: str = ""
    result: str = "later"

    def onInit(self) -> None:
        # The fix button has focus when there is one, so an accidental OK
        # fixes rather than dismisses. Its visibility reads a property, so
        # the properties are set before the window opens (see
        # show_attention_window), not here.
        self.setFocusId(FIX if self.props["MM.Action"] else LATER)

    def onClick(self, controlId: int) -> None:
        if controlId == FIX and self.fix:
            self.result = self.fix
        self.close()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()


def show_attention_window(main: Problem, others: list[Problem]) -> str:
    """Show the window until the user answers: "setup", "libraries" or
    "later"."""
    window = AttentionWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.props = attention_properties(main, others)
    window.fix = fix_for(main.kind)
    for key, value in window.props.items():
        window.setProperty(key, value)
    publish_theme()
    window.doModal()
    result = window.result
    del window
    return result
