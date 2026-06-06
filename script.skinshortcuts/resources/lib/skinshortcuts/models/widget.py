"""Widget model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union

    from .menu import Content

    WidgetGroupContent = Union["Widget", "WidgetGroup", "Content"]


@dataclass
class Widget:
    """A widget that can be assigned to menu items.

    For custom widgets (type="custom"), the slot attribute specifies which
    widget property slot this custom widget applies to (e.g., "widget", "widget.2").
    When selected, the dialog opens an item editor for the custom menu.
    """

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
        """Convert to property dictionary for skin access.

        Core properties only - skins extend via properties.xml.
        """
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


@dataclass
class WidgetConfig:
    """Widget configuration including widgets, groupings, and settings.

    Groupings can contain WidgetGroup (folders), standalone Widget items, and
    Content references at the top level.
    """

    widgets: list[Widget] = field(default_factory=list)
    groupings: list[WidgetGroupContent] = field(default_factory=list)
