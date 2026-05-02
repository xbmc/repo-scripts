"""
login_dialog.py — Custom Kodi window showing a QR code alongside the
device-code login details.

Users with a phone can scan the QR; users on a computer can read the URL
and code.  The dialog auto-closes when the login is approved, or the
user can dismiss it with OK/Back.
"""

from __future__ import annotations

import threading

import xbmcgui


# Kodi action IDs that should dismiss the dialog.
_ACTION_CLOSE_IDS = {
    7,    # ACTION_SELECT_ITEM (OK / Enter)
    9,    # ACTION_PARENT_DIR
    10,   # ACTION_PREVIOUS_MENU
    13,   # ACTION_PARENT_DIR2
    92,   # ACTION_NAV_BACK
    107,  # ACTION_MOUSE_LEFT_CLICK
}


class LoginDialog(xbmcgui.WindowDialog):
    """Full-screen dialog: QR on the left, code/URL on the right."""

    def __init__(
        self,
        *,
        bg_path: str,
        qr_path: str,
        title: str,
        scan_label: str,
        or_visit_label: str,
        uri: str,
        code_label: str,
        code: str,
        expires_label: str,
        dismiss_hint: str,
    ):
        # Kodi's WindowDialog.__init__ is implicit — no super() call needed.
        # Layout is authored at 1280x720; Kodi scales automatically.

        self._approved = threading.Event()

        # Backdrop (stretches the 32x32 dark PNG across the full screen).
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, bg_path))

        # Title bar
        self.addControl(
            xbmcgui.ControlLabel(
                0, 50, 1280, 40,
                "[B]" + title + "[/B]",
                font="font30",
                alignment=2,  # XBFONT_CENTER_X
            )
        )

        # --- Left column: QR code ---
        self.addControl(
            xbmcgui.ControlImage(
                240, 140, 340, 340, qr_path,
                aspectRatio=2,  # keep aspect, scale to fit
            )
        )
        self.addControl(
            xbmcgui.ControlLabel(
                240, 490, 340, 30,
                scan_label,
                font="font12",
                alignment=2,
                textColor="0xFFAAAAAA",
            )
        )

        # --- Right column: URL + code ---
        self.addControl(
            xbmcgui.ControlLabel(
                640, 180, 440, 30,
                or_visit_label,
                font="font13",
                textColor="0xFFAAAAAA",
            )
        )
        self.addControl(
            xbmcgui.ControlLabel(
                640, 210, 440, 40,
                "[B]" + uri + "[/B]",
                font="font20",
                textColor="0xFF00D9FF",
            )
        )

        self.addControl(
            xbmcgui.ControlLabel(
                640, 290, 440, 30,
                code_label,
                font="font13",
                textColor="0xFFAAAAAA",
            )
        )
        self.addControl(
            xbmcgui.ControlLabel(
                640, 320, 440, 80,
                "[B]" + code + "[/B]",
                font="font45",
            )
        )

        self.addControl(
            xbmcgui.ControlLabel(
                640, 430, 440, 30,
                expires_label,
                font="font12",
                textColor="0xFF777777",
            )
        )

        # Footer hint
        self.addControl(
            xbmcgui.ControlLabel(
                0, 650, 1280, 30,
                dismiss_hint,
                font="font12",
                alignment=2,
                textColor="0xFF777777",
            )
        )

    @property
    def was_approved(self) -> bool:
        """True if the dialog was closed because the login succeeded."""
        return self._approved.is_set()

    def approve(self) -> None:
        """Called from the poll thread when tokens are received."""
        self._approved.set()
        # Use executebuiltin to close the dialog on the main thread —
        # calling self.close() directly from a background thread is
        # unsafe in Kodi's UI framework.
        import xbmc
        xbmc.executebuiltin("Action(Back)")

    def onAction(self, action) -> None:  # type: ignore[override]
        if action.getId() in _ACTION_CLOSE_IDS:
            self.close()
