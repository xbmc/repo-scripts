# SPDX-License-Identifier: GPL-2.0-only
"""The text panel of a split window: lines fitted into fixed slots, free of Kodi windows.

Kodi does not clip a label to its height, so a window draws a fixed number of one-line
slots and the lines are fitted to them here. Each slot is set on the row's list item, so
the panel follows the highlighted row inside Kodi.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PanelLine:
    text: str
    heading: bool = False
    tag: str = ""
    warn: bool = False


def fit(lines: Sequence[PanelLine], more: str, slots: int) -> tuple[PanelLine, ...]:
    """At most slots lines. Cut lines end in "and N more", N counting what was left out
    except headings, and a heading is not left dangling above it. The cut line carries the
    warning of any line it hides, since a row's icon promises the panel shows the reason."""
    if len(lines) <= slots:
        return tuple(lines)
    kept = list(lines[: slots - 1])
    while kept and kept[-1].heading:
        kept.pop()
    hidden = lines[len(kept):]
    left_out = sum(1 for line in hidden if not line.heading)
    # replace rather than %: a translation that drops the placeholder must not raise.
    return (*kept, PanelLine(more.replace("%s", str(left_out), 1), warn=any(line.warn for line in hidden)))


def slot_properties(lines: Sequence[PanelLine], more: str, slots: int) -> dict[str, str]:
    """Every slot's properties, empty ones included, so the set a window reads is complete."""
    shown = fit(lines, more, slots)
    props: dict[str, str] = {}
    for n in range(1, slots + 1):
        line = shown[n - 1] if n <= len(shown) else PanelLine("")
        props[f"slot{n}_head"] = line.text if line.heading else ""
        props[f"slot{n}"] = "" if line.heading else line.text
        props[f"slot{n}_tag"] = line.tag
        props[f"slot{n}_warn"] = "true" if line.warn else ""
    return props
