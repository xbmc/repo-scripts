"""
MetaMender's own questions and messages (yes/no, OK), in the setup
windows' style, instead of Kodi's dialogs: those look different in every
skin, and while one is open the setup window behind it loses its heading
and accent colours, which it reads from window properties.

Kodi cannot size a panel to its text, so the line count is estimated by
wrapping the text at a width that errs on the long side; the message is
centred in its box, so a line to spare shows as margin, not as a gap.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any

import xbmc
import xbmcgui

from resources.lib.ui.theme import publish_theme
from resources.lib.utils import get_addon

_XML = "script-metamender-message.xml"
PANEL = 10
PANEL_IMAGE = 11
FRAME_IMAGE = 12
MESSAGE = 20
PRIMARY = 21
SECONDARY = 22
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92
_KODI_YES, _KODI_NO, _KODI_OK = 107, 106, 186

# Geometry, in the 1080i coordinates of the XML.
MAX_LINES = 7
LINE_HEIGHT = 46
# Characters per line at font13 in the message's 880 pixels, on the low
# side so a wide line is not undercounted.
_LINE_CHARS = 58
PANEL_WIDTH = 1000
_SCREEN = (1920, 1080)
_ABOVE_TEXT = 130
_BUTTONS_GAP = 36
_BUTTON = (260, 72)
_BUTTON_GAP = 28
_BELOW_BUTTONS = 40


@dataclass(frozen=True)
class MessageLayout:
    text_height: int
    buttons_top: int
    panel_height: int
    top: int


def kodi_lang(string_id: int) -> str:
    return xbmc.getLocalizedString(string_id)


def message_lines(message: str) -> int:
    """The estimated number of lines ``message`` wraps to, 1 to MAX_LINES."""
    lines = sum(max(1, len(textwrap.wrap(part, _LINE_CHARS))) for part in message.split("\n"))
    return min(max(lines, 1), MAX_LINES)


def message_layout(lines: int) -> MessageLayout:
    text_height = lines * LINE_HEIGHT
    buttons_top = _ABOVE_TEXT + text_height + _BUTTONS_GAP
    panel_height = buttons_top + _BUTTON[1] + _BELOW_BUTTONS
    return MessageLayout(text_height, buttons_top, panel_height,
                         (_SCREEN[1] - panel_height) // 2)


def message_properties(heading: str, message: str, question: bool) -> dict[str, str]:
    """Every window property the XML reads. A question has Yes (primary)
    and No; a message has only OK."""
    props = {
        "MM.Heading": heading,
        "MM.Message": message,
        "MM.Primary": kodi_lang(_KODI_YES if question else _KODI_OK),
        "MM.Secondary": kodi_lang(_KODI_NO) if question else "",
    }
    return props


class MessageWindow(xbmcgui.WindowXMLDialog):
    """``answer`` is True once the primary button (Yes, OK) was pressed.
    The properties and ``lines`` are set before doModal()."""

    lines: int = 1
    question: bool = False
    answer: bool = False

    def onInit(self) -> None:
        layout = message_layout(self.lines)
        self.getControl(PANEL).setPosition((_SCREEN[0] - PANEL_WIDTH) // 2, layout.top)
        self.getControl(PANEL_IMAGE).setHeight(layout.panel_height)
        self.getControl(FRAME_IMAGE).setHeight(layout.panel_height)
        self.getControl(MESSAGE).setHeight(layout.text_height)
        width, gap = _BUTTON[0], _BUTTON_GAP
        if self.question:
            # No left, Yes right: the confirming button sits where Next
            # and Finish sit in the setup window.
            left = (PANEL_WIDTH - 2 * width - gap) // 2
            self.getControl(SECONDARY).setPosition(left, layout.buttons_top)
            self.getControl(PRIMARY).setPosition(left + width + gap, layout.buttons_top)
            # Kodi's own question has No focused; an accidental OK changes nothing.
            self.setFocusId(SECONDARY)
        else:
            self.getControl(PRIMARY).setPosition((PANEL_WIDTH - width) // 2, layout.buttons_top)
            self.setFocusId(PRIMARY)

    def onClick(self, controlId: int) -> None:
        self.answer = controlId == PRIMARY
        self.close()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()


def show_message(heading: str, message: str, question: bool = False) -> bool:
    """Show a message (OK) or a question (Yes/No) until the user answers.
    True for Yes or OK; False for No, Back, or a message closed with Back."""
    window = MessageWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.lines = message_lines(message)
    window.question = question
    for key, value in message_properties(heading, message, question).items():
        window.setProperty(key, value)
    publish_theme()
    window.doModal()
    answer = window.answer
    del window
    return answer


def show_question(heading: str, message: str) -> bool:
    """True when the user answered Yes."""
    return show_message(heading, message, question=True)
