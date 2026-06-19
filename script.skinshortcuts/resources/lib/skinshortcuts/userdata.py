"""User data storage and merging."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import xbmc
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .log import get_logger
from .models import Action, Menu, MenuItem

log = get_logger("UserData")


def get_userdata_path() -> str:
    """Get path to userdata file for current skin."""
    if IN_KODI:
        skin_dir = xbmc.getSkinDir()
        data_path = xbmcvfs.translatePath("special://profile/addon_data/script.skinshortcuts/")
        return str(Path(data_path) / f"{skin_dir}.userdata.json")
    return ""


@dataclass
class MenuItemOverride:
    """User override for a menu item."""

    name: str
    label: str | None = None
    actions: list[Action] | None = None  # List of actions (with optional conditions)
    icon: str | None = None
    disabled: bool | None = None
    properties: dict[str, str] = field(default_factory=dict)  # Includes widget/background
    position: int | None = None  # For reordering
    is_new: bool = False  # True if user-added item
    submenu: str | None = None  # Submenu template reference (picker auto-attach)
    visible: str | None = None  # Runtime visibility condition (baked from picked shortcut)


@dataclass
class MenuOverride:
    """User overrides for a menu."""

    items: list[MenuItemOverride] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # Names of removed items


def _menu_override_to_dict(override: MenuOverride) -> dict[str, Any]:
    """Convert MenuOverride to dict, omitting empty values."""
    result: dict[str, Any] = {}
    if override.items:
        result["items"] = [_item_override_to_dict(item) for item in override.items]
    if override.removed:
        result["removed"] = override.removed
    return result


def _action_to_dict(action: Action) -> dict[str, Any]:
    """Serialize an action, omitting an empty condition (treated as unconditional)."""
    result: dict[str, Any] = {"action": action.action}
    if action.condition:
        result["condition"] = action.condition
    return result


def _item_override_to_dict(item: MenuItemOverride) -> dict[str, Any]:
    """Convert MenuItemOverride to dict, omitting None/empty values."""
    result: dict[str, Any] = {"name": item.name}

    if item.label is not None:
        result["label"] = item.label
    if item.actions is not None:
        result["actions"] = [_action_to_dict(a) for a in item.actions]
    if item.icon is not None:
        result["icon"] = item.icon
    if item.disabled is not None:
        result["disabled"] = item.disabled
    if item.properties:
        result["properties"] = item.properties
    if item.position is not None:
        result["position"] = item.position
    if item.is_new:
        result["is_new"] = item.is_new
    if item.submenu is not None:
        result["submenu"] = item.submenu
    if item.visible is not None:
        result["visible"] = item.visible

    return result


@dataclass
class UserData:
    """All user customizations for a skin.

    The views field stores user view selections:
    source -> content -> view_id
    Sources are: 'library', 'plugins', or 'plugin.video.X' for specific plugins.
    """

    menus: dict[str, MenuOverride] = field(default_factory=dict)
    views: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {}
        if self.menus:
            result["menus"] = {
                menu_id: _menu_override_to_dict(override)
                for menu_id, override in self.menus.items()
            }
        if self.views:
            result["views"] = self.views
        return result

    def get_view(self, source: str, content: str) -> str | None:
        """Get user's selected view for a source and content type."""
        source_views = self.views.get(source)
        if source_views:
            return source_views.get(content)
        return None

    def set_view(self, source: str, content: str, view_id: str) -> None:
        """Set user's view selection for a source and content type."""
        if source not in self.views:
            self.views[source] = {}
        self.views[source][content] = view_id

    def clear_all_views(self) -> None:
        """Clear all view selections."""
        self.views.clear()

    def get_addon_overrides(self, content: str) -> dict[str, str]:
        """Get all addon-specific view overrides for a content type.

        Returns dict of addon_id -> view_id for addons with custom selections.
        Includes any source that isn't 'library' or 'plugins' (generic).
        """
        overrides = {}
        for source, selections in self.views.items():
            if source not in ("library", "plugins") and content in selections:
                overrides[source] = selections[content]
        return overrides

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserData:
        """Create from dictionary."""
        menus = {}
        for menu_id, menu_data in data.get("menus", {}).items():
            items = []
            for item_data in menu_data.get("items", []):
                actions_data = item_data.pop("actions", None)
                actions = None
                if actions_data is not None:
                    actions = []
                    for act in actions_data:
                        if isinstance(act, dict):
                            actions.append(Action(**act))
                        else:
                            # Legacy: plain string action
                            actions.append(Action(action=act))
                items.append(MenuItemOverride(**item_data, actions=actions))
            removed = menu_data.get("removed", [])
            menus[menu_id] = MenuOverride(items=items, removed=removed)
        views: dict[str, dict[str, str]] = data.get("views", {})
        return cls(menus=menus, views=views)


def load_userdata(path: str | None = None) -> UserData:
    """Load user data from JSON file."""
    if path is None:
        path = get_userdata_path()
        log.debug(f"Userdata path: {path}")

    if not path:
        log.warning("No userdata path available")
        return UserData()

    try:
        file_path = Path(path)
        if file_path.exists():
            log.debug(f"Loading userdata from: {file_path}")
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                userdata = UserData.from_dict(data)
                log.debug(f"Loaded {len(userdata.menus)} menu overrides")
                return userdata
        else:
            log.debug(f"Userdata file not found: {file_path}")
    except (OSError, json.JSONDecodeError) as e:
        log.error(f"Failed to load userdata from {path}: {e}")

    return UserData()


def save_userdata(userdata: UserData, path: str | None = None) -> bool:
    """Save user data to JSON file."""
    if path is None:
        path = get_userdata_path()

    if not path:
        return False

    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(userdata.to_dict(), f, indent=2)
        return True
    except OSError as e:
        log.error(f"Failed to save userdata to {path}: {e}")
        return False


def _check_dialog_visible(condition: str) -> bool:
    """Check if a Kodi visibility condition passes for dialog filtering.

    Returns True if condition is empty or passes.
    """
    if not condition:
        return True
    if not IN_KODI:
        return True
    return xbmc.getCondVisibility(condition)


def merge_menu(default_menu: Menu, override: MenuOverride | None) -> Menu:
    """Merge default menu with user overrides."""
    if override is None:
        # No user customization - filter by dialog_visible
        filtered_items = [
            item for item in default_menu.items
            if _check_dialog_visible(item.dialog_visible)
        ]
        return Menu(
            name=default_menu.name,
            items=filtered_items,
            defaults=default_menu.defaults,
            container=default_menu.container,
            allow=default_menu.allow,
            is_submenu=default_menu.is_submenu,
            menu_type=default_menu.menu_type,
            controltype=default_menu.controltype,
            startid=default_menu.startid,
            template_only=default_menu.template_only,
            build=default_menu.build,
            action=default_menu.action,
            standalone=default_menu.standalone,
            submenu_path=default_menu.submenu_path,
        )

    items: list[MenuItem] = []
    for item in default_menu.items:
        if item.name in override.removed and not item.required:
            continue
        if item.dialog_visible and not _check_dialog_visible(item.dialog_visible):
            continue
        items.append(item)

    override_map = {o.name: o for o in override.items}

    for i, item in enumerate(items):
        if item.name in override_map:
            ovr = override_map[item.name]
            items[i] = _apply_override(item, ovr)

    new_items = [o for o in override.items if o.is_new]
    for new_item in new_items:
        items.append(_create_item_from_override(new_item))

    positioned_items: dict[int, MenuItem] = {}
    unpositioned_items: list[MenuItem] = []

    for item in items:
        ovr = override_map.get(item.name)
        if ovr and ovr.position is not None:
            positioned_items[ovr.position] = item
        else:
            unpositioned_items.append(item)

    final_items: list[MenuItem] = []
    unpos_iter = iter(unpositioned_items)

    if positioned_items:
        max_pos = max(positioned_items.keys()) + 1
    else:
        max_pos = len(items)

    for i in range(max_pos):
        if i in positioned_items:
            final_items.append(positioned_items[i])
        else:
            try:
                final_items.append(next(unpos_iter))
            except StopIteration:
                continue

    for item in unpos_iter:
        final_items.append(item)

    return Menu(
        name=default_menu.name,
        items=final_items,
        defaults=default_menu.defaults,
        container=default_menu.container,
        allow=default_menu.allow,
        is_submenu=default_menu.is_submenu,
        menu_type=default_menu.menu_type,
        controltype=default_menu.controltype,
        startid=default_menu.startid,
        template_only=default_menu.template_only,
        build=default_menu.build,
        action=default_menu.action,
        standalone=default_menu.standalone,
        submenu_path=default_menu.submenu_path,
    )


def _apply_override(item: MenuItem, override: MenuItemOverride) -> MenuItem:
    """Apply user override to a menu item."""
    return MenuItem(
        name=item.name,
        label=override.label if override.label is not None else item.label,
        actions=override.actions if override.actions is not None else item.actions,
        label2=item.label2,
        icon=override.icon if override.icon is not None else item.icon,
        thumb=item.thumb,
        visible=override.visible if override.visible is not None else item.visible,
        disabled=override.disabled if override.disabled is not None else item.disabled,
        required=item.required,
        protection=item.protection,
        properties={**item.properties, **override.properties},
        submenu=override.submenu if override.submenu is not None else item.submenu,
        original_action=item.action,  # Store original for protection matching
        includes=item.includes,
    )


def _create_item_from_override(override: MenuItemOverride) -> MenuItem:
    """Create a new menu item from user override."""
    return MenuItem(
        name=override.name,
        label=override.label or "",
        actions=override.actions or [Action(action="noop")],
        icon=override.icon or "DefaultShortcut.png",
        visible=override.visible or "",
        disabled=override.disabled or False,
        properties=override.properties,
        submenu=override.submenu,
    )
