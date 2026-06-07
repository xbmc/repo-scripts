"""Background model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union

    from .menu import Content

    BackgroundGroupContent = Union["Background", "BackgroundGroup", "Content"]


class BackgroundType(Enum):
    STATIC = auto()
    PLAYLIST = auto()
    BROWSE = auto()
    MULTI = auto()
    PROPERTY = auto()
    LIVE = auto()
    LIVE_PLAYLIST = auto()


@dataclass
class PlaylistSource:
    """A source path for playlist scanning."""

    label: str
    path: str
    icon: str = "DefaultPlaylist.png"


@dataclass
class BrowseSource:
    """A source path for browse dialogs.

    Used by browse/multi background types to provide multiple
    conditional starting paths for file browsing.

    Attributes:
        condition: Property condition (evaluated against item properties)
        visible: Kodi visibility condition (evaluated at runtime)
    """

    label: str
    path: str  # Path to browse from, or "browse" for free file browser
    condition: str = ""
    visible: str = ""
    icon: str = ""


@dataclass
class Background:
    """A background that can be assigned to menu items."""

    name: str
    label: str
    path: str = ""  # Optional for browse/multi/playlist types
    type: BackgroundType = BackgroundType.STATIC
    icon: str = ""
    condition: str = ""  # Property condition (evaluated against item properties)
    visible: str = ""  # Kodi visibility condition (evaluated at runtime)
    sources: list[PlaylistSource] = field(default_factory=list)  # For playlist types
    browse_sources: list[BrowseSource] = field(default_factory=list)  # For browse/multi

    @property
    def type_name(self) -> str:
        """Return normalized type name matching XML attribute values."""
        return self.type.name.lower().replace("_", "-")

    def to_properties(self) -> dict[str, str]:
        """Convert to property dictionary for skin access."""
        return {
            "background": self.name,
            "backgroundPath": self.path,
            "backgroundLabel": self.label,
            "backgroundType": self.type_name,
        }


@dataclass
class BackgroundGroup:
    """A group/category of backgrounds in the picker."""

    name: str
    label: str
    condition: str = ""  # Property condition (evaluated against item properties)
    visible: str = ""  # Kodi visibility condition (evaluated at runtime)
    icon: str = ""  # Optional icon for group display
    items: list[BackgroundGroupContent] = field(default_factory=list)
    flat: bool = False  # No folder header; children render at parent level


@dataclass
class BackgroundConfig:
    """Background configuration including backgrounds, groupings, and settings.

    Groupings can contain both BackgroundGroup (folders) and standalone Background items
    at the top level for flexibility.
    """

    backgrounds: list[Background] = field(default_factory=list)
    groupings: list[BackgroundGroup | Background] = field(default_factory=list)
