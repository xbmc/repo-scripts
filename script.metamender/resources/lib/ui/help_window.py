"""The "Manual and help" window opened from the add-on settings: a QR code
to scan with a phone, and the manual's address written out for a keyboard.

The QR image is drawn by docs/art/build_art.py from the same address, on
its own white square so phones read it in every window colour scheme.
"""
from __future__ import annotations

from typing import Any

import xbmcgui

from resources.lib.ui.message_window import kodi_lang
from resources.lib.ui.theme import publish_theme
from resources.lib.utils import get_addon, lang

_XML = "script-metamender-help.xml"
CLOSE = 21
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92
_KODI_CLOSE = 15067

MANUAL_ADDRESS = "rouzax.github.io/script.metamender/docs/"
MANUAL_URL = "https://" + MANUAL_ADDRESS
_QR_TEXTURE = "metamender/manual-qr.png"


def help_properties() -> dict[str, str]:
    """Every window property the XML reads."""
    props = {
        "MM.Heading": lang(32739),
        "MM.Message": lang(32740),
        "MM.Url": MANUAL_ADDRESS,
        "MM.Qr": _QR_TEXTURE,
        "MM.Primary": kodi_lang(_KODI_CLOSE),
    }
    return props


class HelpWindow(xbmcgui.WindowXMLDialog):
    def onInit(self) -> None:
        self.setFocusId(CLOSE)

    def onClick(self, controlId: int) -> None:
        self.close()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()


def show_help() -> None:
    """Show the window until the user closes it."""
    window = HelpWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    for key, value in help_properties().items():
        window.setProperty(key, value)
    publish_theme()
    window.doModal()
    del window
