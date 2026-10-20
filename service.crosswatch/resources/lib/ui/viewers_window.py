# SPDX-License-Identifier: GPL-2.0-only
"""What the viewers window shows and returns, free of Kodi windows.

Each row carries its viewer's whole panel as list item properties, so the panel follows the
highlighted row inside Kodi and no Python runs on a focus move.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from resources.lib.ui import panel
from resources.lib.ui.panel import PanelLine

# Text slots below the route line. The XML has one set of controls per slot;
# tests/test_skin_xml.py checks the two agree.
PANEL_SLOTS = 13

ROUTE_ACCEPTED = "accepted"
ROUTE_REFUSED = "refused"


@dataclass(frozen=True)
class ViewerRow:
    key: str
    lines: tuple[PanelLine, ...] = ()
    # "" when CrossWatch made no claim about this name: unpaired, not asked yet, no reply.
    route: str = ""
    # The name belongs to a CrossWatch person, so renaming it here would only be undone.
    linked: bool = False

    @property
    def warn(self) -> bool:
        return self.route == ROUTE_REFUSED or any(line.warn for line in self.lines)


@dataclass(frozen=True, kw_only=True)
class ViewersRequest:
    heading: str
    count: str
    rows: tuple[ViewerRow, ...]
    more: str
    route_ok: str
    route_missing: str


@dataclass(frozen=True)
class ViewersResult:
    # "playlists", "profiles", "rename", "remove", "add" or "close"
    action: str
    # The highlighted viewer, also for add and close, so the screen can reopen on it.
    key: str = ""


def properties(row: ViewerRow, request: ViewersRequest) -> dict[str, str]:
    route_text = {ROUTE_ACCEPTED: request.route_ok, ROUTE_REFUSED: request.route_missing}
    props = {
        "warn": "true" if row.warn else "",
        "route": row.route,
        "linked": "true" if row.linked else "",
        "route_text": route_text.get(row.route, ""),
    }
    return props | panel.slot_properties(row.lines, request.more, PANEL_SLOTS)


def start_position(rows: Sequence[ViewerRow], key: str) -> int:
    return next((index for index, row in enumerate(rows) if row.key == key), 0)
