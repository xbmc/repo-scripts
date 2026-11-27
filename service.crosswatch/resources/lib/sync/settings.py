# SPDX-License-Identifier: GPL-2.0-only
"""The household's library sync choices, as the sync code reads them.

A leaf module, so the rules, the writer and the scripts can all take it without importing
config.py and the Kodi settings behind it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SharedRule = Literal["everyone", "anyone"]


@dataclass(frozen=True)
class SyncSettings:
    # Off by default: an unwatch or a cleared rating made in Kodi removes history on the
    # household's services only when they asked for that.
    send_removals: bool = False
    # A shared item counts as watched in Kodi when every owner watched it, or any owner.
    shared_rule: SharedRule = "everyone"
