"""Override model, shared by the config files that declare an <overrides> block."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Override:
    """A name or action the skin replaced, and what it became; empty value clears it."""

    replace: str
    value: str = ""
