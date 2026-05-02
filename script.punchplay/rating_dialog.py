"""
rating_dialog.py — Star-slider rating dialog.

Left/Right arrows change the rating (1–10), OK confirms, Back cancels.
Stars fill with gold as the rating increases.
"""

from __future__ import annotations

import xbmcgui

# Action IDs
_ACTION_LEFT = 1
_ACTION_RIGHT = 2
_ACTION_SELECT = 7
_ACTION_PARENT_DIR = 9
_ACTION_PREVIOUS_MENU = 10
_ACTION_PARENT_DIR2 = 13
_ACTION_NAV_BACK = 92

_FILLED = "★"   # ★
_EMPTY = "★"    # ★ (same char, different colour)
_GOLD = "FFE8B923"
_GREY = "FF555555"


class RatingDialog(xbmcgui.WindowDialog):
    """Full-screen star-slider rating dialog."""

    def __init__(
        self,
        *,
        bg_path: str,
        heading: str,
        initial: int = 5,
    ):
        self._rating = max(1, min(10, initial))
        self._confirmed = False

        # Backdrop
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, bg_path))

        # Heading
        self.addControl(
            xbmcgui.ControlLabel(
                0, 200, 1280, 40,
                "[B]" + heading + "[/B]",
                font="font25",
                alignment=2,
                textColor="FFFFFFFF",
            )
        )

        # Stars label (updated dynamically)
        self._stars_label = xbmcgui.ControlLabel(
            0, 290, 1280, 60,
            self._render_stars(),
            font="font45",
            alignment=2,
        )
        self.addControl(self._stars_label)

        # Rating number
        self._number_label = xbmcgui.ControlLabel(
            0, 370, 1280, 40,
            f"[B]{self._rating}/10[/B]",
            font="font20",
            alignment=2,
            textColor="FFFFFFFF",
        )
        self.addControl(self._number_label)

        # Arrow hints
        self.addControl(
            xbmcgui.ControlLabel(
                0, 440, 1280, 30,
                "◄  ─────────  ►",
                font="font13",
                alignment=2,
                textColor="FF777777",
            )
        )

        # Footer
        self.addControl(
            xbmcgui.ControlLabel(
                0, 620, 1280, 30,
                "OK to confirm  ·  Back to skip",
                font="font12",
                alignment=2,
                textColor="FF777777",
            )
        )

    def _render_stars(self) -> str:
        filled = f"[COLOR {_GOLD}]{_FILLED * self._rating}[/COLOR]"
        empty = f"[COLOR {_GREY}]{_EMPTY * (10 - self._rating)}[/COLOR]"
        return filled + empty

    def _update_display(self) -> None:
        self._stars_label.setLabel(self._render_stars())
        self._number_label.setLabel(f"[B]{self._rating}/10[/B]")

    @property
    def confirmed(self) -> bool:
        return self._confirmed

    @property
    def rating(self) -> int:
        return self._rating

    def onAction(self, action) -> None:  # type: ignore[override]
        action_id = action.getId()

        if action_id == _ACTION_RIGHT:
            if self._rating < 10:
                self._rating += 1
                self._update_display()
        elif action_id == _ACTION_LEFT:
            if self._rating > 1:
                self._rating -= 1
                self._update_display()
        elif action_id == _ACTION_SELECT:
            self._confirmed = True
            self.close()
        elif action_id in (_ACTION_PARENT_DIR, _ACTION_PREVIOUS_MENU,
                           _ACTION_PARENT_DIR2, _ACTION_NAV_BACK):
            self.close()
