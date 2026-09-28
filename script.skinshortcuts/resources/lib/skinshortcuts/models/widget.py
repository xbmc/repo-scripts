"""Widget model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .override import Override
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union

    from .menu import Content

    WidgetGroupContent = Union["Widget", "WidgetGroup", "Content"]


@dataclass
class Widget:
    """A widget that can be assigned to menu items."""

    name: str
    label: str
    path: str
    type: str = ""
    target: str = "videos"
    icon: str = ""
    condition: str = ""  # Property condition (evaluated against item properties)
    visible: str = ""  # Kodi visibility condition (evaluated at runtime)
    limit: int | None = None
    sort_by: str = ""
    sort_order: str = ""
    source: str = ""  # Widget source type (library, playlist, addon, etc.)
    slot: str = ""  # For type="custom": which widget slot (e.g., "widget", "widget.2")
    browse: bool = False  # Opt-in: allow browse-into during picker

    def to_properties(self, prefix: str = "widget") -> dict[str, str]:
        """Convert to property dictionary for the picker's DialogSelect rows."""
        props = {
            f"{prefix}": self.name,
            f"{prefix}Label": self.label,
            f"{prefix}Path": self.path,
            f"{prefix}Target": self.target,
        }
        if self.source:
            props[f"{prefix}Source"] = self.source
        return props


@dataclass
class WidgetGroup:
    """A group/category of widgets in groupings."""

    name: str
    label: str
    condition: str = ""  # Property condition (evaluated against item properties)
    visible: str = ""  # Kodi visibility condition (evaluated at runtime)
    icon: str = ""  # Optional icon for group display
    items: list[WidgetGroupContent] = field(default_factory=list)
    flat: bool = False  # No folder header; children render at parent level
    path: str = ""  # Real browsable path, set on content folders only


@dataclass
class WidgetConfig:
    """Widget configuration including widgets, groupings, and settings."""

    widgets: list[Widget] = field(default_factory=list)
    groupings: list[WidgetGroupContent] = field(default_factory=list)
    overrides: list[Override] = field(default_factory=list)
