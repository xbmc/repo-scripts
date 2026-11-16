"""Lead rows for Presenter._position_list.

The lead is counted against the page a list scrolls by. For a list resized at
runtime, that is its authored page up to Kodi 22.0 beta 2, and the rows it
shows from 22.0 RC1.
"""

import functools
from typing import Optional, Tuple

import xbmc

# System.BuildVersionCode of Kodi 22.0 RC1.
PAGE_FOLLOWS_HEIGHT_FROM = (21, 90, 901)


def _version_code(text: str) -> Optional[Tuple[int, int, int]]:
    """System.BuildVersionCode ("21.90.901") as a tuple, or None."""
    parts = text.strip().split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


@functools.lru_cache(maxsize=None)
def page_follows_height() -> bool:
    """Whether a list resized at runtime scrolls by its new height.

    Assumed when the version cannot be read.
    """
    code = _version_code(xbmc.getInfoLabel("System.BuildVersionCode"))
    return code is None or code >= PAGE_FOLLOWS_HEIGHT_FROM


def middle_row(visible: int) -> int:
    """The row the sung line settles on in ``visible`` rows."""
    return (visible - 1) // 2


def lead_rows(visible: int, authored: int) -> int:
    """The lead that settles the sung line on middle_row(visible).

    ``authored`` is the page the list was authored with.
    """
    page = visible if page_follows_height() else authored
    return max(1, (page - 1) - middle_row(visible))
