"""Menu and MenuItem models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .override import Override
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import xbmc
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

if TYPE_CHECKING:
    from typing import Union

    GroupContent = Union["Shortcut", "ShortcutGroup", "Content", "Input"]


def skin_has_image(path: str) -> bool:
    """Whether the skin can draw this texture, packed into an xbt or loose on disk."""
    if not path:
        return False
    if not IN_KODI:
        return Path(path).exists()
    if "://" in path or path.startswith("/"):
        return xbmcvfs.exists(path)
    return bool(xbmc.skinHasImage(path))


@dataclass
class IconOverrides:
    """Kodi default icon names mapped to the replacements a skin ships.

    An expression source resolves for the lookup and stays unresolved in the output.
    """

    source: str = ""
    explicit: dict[str, str] = field(default_factory=dict)
    _tested: dict[str, str] = field(default_factory=dict, repr=False)

    def __bool__(self) -> bool:
        return bool(self.source or self.explicit)

    def __contains__(self, name: str) -> bool:
        return bool(self.get(name))

    def __getitem__(self, name: str) -> str:
        found = self.get(name)
        if not found:
            raise KeyError(name)
        return found

    def get(self, name: str, default: str = "") -> str:
        """The skin's replacement for a default icon name, if it has one."""
        if name in self.explicit:
            return self.explicit[name]
        if not self.source or not name.startswith("Default"):
            return default
        if name not in self._tested:
            from ..localize import resolve_label

            candidate = self.source + name
            self._tested[name] = candidate if skin_has_image(resolve_label(candidate)) else ""
        return self._tested[name] or default


@dataclass
class IconSource:
    """A source for browsing icons."""

    label: str
    path: str  # Path to browse, or "browse" for free file browser
    condition: str = ""
    visible: str = ""
    icon: str = ""


@dataclass
class Input:
    """User input prompt in groupings."""

    label: str
    type: str = "text"
    for_: str = "action"
    condition: str = ""
    visible: str = ""
    icon: str = "DefaultFile.png"


@dataclass
class Content:
    """Dynamic content reference for groupings."""

    source: str
    target: str = ""
    path: str = ""
    condition: str = ""
    visible: str = ""
    icon: str = ""
    label: str = ""
    folder: str = ""


@dataclass
class Action:
    """An action with optional condition."""

    action: str
    condition: str = ""


@dataclass
class IncludeRef:
    """A reference to an include, output as <include>name</include>."""

    name: str
    condition: str = ""
    position: str = "end"


@dataclass
class Protection:
    """Protection rule for a menu item."""

    type: str = "all"  # "delete", "action", "disable", or "all"
    heading: str = ""
    message: str = ""

    def protects_delete(self) -> bool:
        """Return True if this protection applies to deletion."""
        return self.type in ("delete", "all")

    def protects_action(self) -> bool:
        """Return True if this protection applies to action changes."""
        return self.type in ("action", "all")

    def protects_disable(self) -> bool:
        """Return True if this protection applies to disabling."""
        return self.type in ("disable", "all")


@dataclass
class Shortcut:
    """A shortcut option in groupings (for picker dialog)."""

    name: str
    label: str
    actions: list[str] = field(default_factory=list)
    primary_action: str = ""  # Action marked primary="true", for display props
    path: str = ""
    browse: str = ""
    type: str = ""
    icon: str = "DefaultShortcut.png"
    condition: str = ""
    visible: str = ""
    item_visible: str = ""  # runtime condition for the picked menu item, not a picker filter
    action_play: str = ""
    action_party: str = ""
    source_media: str = ""  # originating file source's media; drives the source playlist flow

    @property
    def action(self) -> str:
        """Primary action for display. Uses explicit primary, falls back to last action."""
        if self.primary_action:
            return self.primary_action
        return self.actions[-1] if self.actions else ""

    def get_action(self) -> str:
        """Get the resolved primary action string."""
        if self.browse and self.path:
            from ..constants import WINDOW_MAP

            window = WINDOW_MAP.get(self.browse.lower(), "Videos")
            return f"ActivateWindow({window},{self.path},return)"
        return self.action


@dataclass
class ShortcutGroup:
    """A group/category of shortcuts in groupings."""

    name: str
    label: str
    condition: str = ""  # Property condition (evaluated against item properties)
    visible: str = ""  # Kodi visibility condition (evaluated at runtime)
    icon: str = ""
    items: list[GroupContent] = field(default_factory=list)
    flat: bool = False  # No folder header; children render at parent level
    path: str = ""  # Real browsable path, set on content folders only


@dataclass
class MenuItem:
    """A single item in a menu."""

    name: str
    label: str
    actions: list[Action] = field(default_factory=list)
    label2: str = ""
    icon: str = "DefaultShortcut.png"
    thumb: str = ""
    visible: str = ""  # Output to includes.xml (<visible> element)
    dialog_visible: str = ""  # Filter in management dialog (visible= attribute)
    disabled: bool = False
    required: bool = False  # If True, item cannot be deleted
    protection: Protection | None = None  # Optional protection against delete/modify

    properties: dict[str, str] = field(default_factory=dict)
    submenu: str | None = None
    original_action: str = ""  # Set from defaults, not saved to userdata
    includes: list[IncludeRef] = field(default_factory=list)
    is_placeholder: bool = False  # empty placeholder, dropped from save until edited

    @property
    def action(self) -> str:
        """Primary action for display (last unconditional action)."""
        last = ""
        for act in self.actions:
            if not act.condition:
                last = act.action
        return last or (self.actions[0].action if self.actions else "")

    @action.setter
    def action(self, value: str) -> None:
        """Set primary action (last unconditional action)."""
        for act in reversed(self.actions):
            if not act.condition:
                act.action = value
                return
        self.actions.append(Action(action=value))


@dataclass
class DefaultAction:
    """A default action applied to all items in a menu."""

    action: str
    when: str = "before"  # "before" or "after"
    condition: str = ""


@dataclass
class MenuDefaults:
    """Default properties and actions for items in a menu."""

    properties: dict[str, str] = field(default_factory=dict)
    actions: list[DefaultAction] = field(default_factory=list)
    includes: list[IncludeRef] = field(default_factory=list)


@dataclass
class MenuAllow:
    """Configuration for what features are allowed in a menu."""

    widgets: bool = True
    backgrounds: bool = True
    submenus: bool = True


@dataclass
class Menu:
    """A menu containing menu items."""

    name: str
    items: list[MenuItem] = field(default_factory=list)
    defaults: MenuDefaults = field(default_factory=MenuDefaults)
    allow: MenuAllow = field(default_factory=MenuAllow)
    container: str | None = None
    is_submenu: bool = False
    menu_type: str | None = None
    controltype: str = ""
    icons: bool = True
    startid: int = 1
    template_only: str = ""  # "submenu"=skip combined submenu include
    build: str = "true"
    action: str = ""
    template_origin: str = ""  # For per-item submenu instances: the template they were seeded from
    standalone: bool = True  # <submenu>: emit skinshortcuts-{name} per-template include
    submenu_path: str = ""  # submenuPath="all": also emit numbered submenuPath.N on the parent

    def get_item(self, item_name: str) -> MenuItem | None:
        """Get item by name."""
        for item in self.items:
            if item.name == item_name:
                return item
        return None

    def add_item(self, item: MenuItem, position: int | None = None) -> None:
        """Add item at position (or end if None)."""
        if position is None:
            self.items.append(item)
        else:
            self.items.insert(position, item)

    def remove_item(self, item_name: str) -> bool:
        """Remove item by name. Returns True if found."""
        for i, item in enumerate(self.items):
            if item.name == item_name:
                self.items.pop(i)
                return True
        return False

    def move_item(self, item_name: str, direction: int) -> bool:
        """Move item up (-1) or down (+1). Returns True if moved."""
        for i, item in enumerate(self.items):
            if item.name == item_name:
                new_pos = i + direction
                if 0 <= new_pos < len(self.items):
                    self.items.pop(i)
                    self.items.insert(new_pos, item)
                    return True
                return False
        return False


@dataclass
class OnCloseAction:
    """An action to execute when a subdialog closes."""

    action: str  # "menu"
    menu: str = ""  # For action="menu": menu name (supports {item} placeholder)
    condition: str = ""


@dataclass
class SubDialog:
    """A sub-dialog definition for the management dialog."""

    button_id: int
    mode: str = ""
    menu: str = ""
    setfocus: int | None = None
    suffix: str = ""
    onclose: list[OnCloseAction] = field(default_factory=list)


@dataclass
class ContextMenuButton:
    """A row in the management dialog context menu."""

    button_id: int
    label: str = ""
    condition: str = ""
    visible: str = ""


@dataclass
class ContextMenu:
    """Context menu settings from <contextmenu>."""

    enabled: bool = True
    enable_on: list[int] = field(default_factory=list)
    buttons: list[ContextMenuButton] = field(default_factory=list)


@dataclass
class MenuConfig:
    """Menu configuration including menus, groupings, and icon sources."""

    menus: list[Menu] = field(default_factory=list)
    groupings: list[Shortcut | ShortcutGroup | Content | Input] = field(default_factory=list)
    icon_sources: list[IconSource] = field(default_factory=list)
    subdialogs: list[SubDialog] = field(default_factory=list)
    action_overrides: list[Override] = field(default_factory=list)
    icon_overrides: IconOverrides = field(default_factory=IconOverrides)
    context_menu: ContextMenu = field(default_factory=ContextMenu)
    submenu_path_all: bool = False  # <submenuPath>all</submenuPath>: numbers every widget submenu
