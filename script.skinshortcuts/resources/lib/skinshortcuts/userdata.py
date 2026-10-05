"""User data storage and merging."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import xbmc
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .conditions import check_visible
from .constants import DEFAULT_ICON
from .log import get_logger
from .models.menu import Action, IconOverrides, Menu, MenuItem


log = get_logger("UserData")


def get_userdata_path() -> str:
    """Get path to userdata file for current skin."""
    if IN_KODI:
        skin_dir = xbmc.getSkinDir()
        data_path = xbmcvfs.translatePath("special://profile/addon_data/script.skinshortcuts/")
        return str(Path(data_path) / f"{skin_dir}.userdata.json")
    return ""


@dataclass
class MenuItemDiff:
    """User changes to one menu item, as a diff against the skin default."""

    name: str
    label: str | None = None
    actions: list[Action] | None = None
    icon: str | None = None
    disabled: bool | None = None
    properties: dict[str, str] = field(default_factory=dict)  # Includes widget/background
    removed_properties: list[str] = field(default_factory=list)  # Skin defaults the user cleared
    position: int | None = None  # For reordering
    is_new: bool = False  # True if user-added item
    submenu: str | None = None  # Submenu template reference (picker auto-attach)
    visible: str | None = None  # Runtime visibility condition (baked from picked shortcut)


@dataclass
class MenuDiff:
    """User changes to one menu, as a diff against the skin default."""

    items: list[MenuItemDiff] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def _menu_diff_to_dict(diff: MenuDiff) -> dict[str, Any]:
    """Convert MenuDiff to dict, omitting empty values."""
    result: dict[str, Any] = {}
    if diff.items:
        result["items"] = [_item_diff_to_dict(item) for item in diff.items]
    if diff.removed:
        result["removed"] = diff.removed
    return result


def _action_to_dict(action: Action) -> dict[str, Any]:
    """Serialize an action, omitting an empty condition (treated as unconditional)."""
    result: dict[str, Any] = {"action": action.action}
    if action.condition:
        result["condition"] = action.condition
    return result


def _item_diff_to_dict(item: MenuItemDiff) -> dict[str, Any]:
    """Convert MenuItemDiff to dict, omitting None/empty values."""
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
    if item.removed_properties:
        result["removed_properties"] = item.removed_properties
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
    """All user customizations for a skin."""

    menus: dict[str, MenuDiff] = field(default_factory=dict)
    views: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {}
        if self.menus:
            result["menus"] = {
                menu_id: _menu_diff_to_dict(diff)
                for menu_id, diff in self.menus.items()
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

    def get_plugin_overrides(self, content: str) -> dict[str, str]:
        """Get all plugin-specific view overrides for a content type."""
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
                            actions.append(Action(action=act))
                items.append(MenuItemDiff(**item_data, actions=actions))
            removed = menu_data.get("removed", [])
            menus[menu_id] = MenuDiff(items=items, removed=removed)
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
                log.debug(f"Loaded {len(userdata.menus)} menu diffs")
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
        # write beside the target and swap, so a kill mid-write cannot truncate userdata
        temp_path = file_path.with_name(f"{file_path.name}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(userdata.to_dict(), f, indent=2)
        os.replace(temp_path, file_path)
        return True
    except OSError as e:
        log.error(f"Failed to save userdata to {path}: {e}")
        return False


def merge_menu(
    default_menu: Menu, diff: MenuDiff | None,
    icon_overrides: IconOverrides | None = None,
) -> Menu:
    """Merge a default menu with the user's diff."""
    if diff is None:
        # No user customization - filter by dialog_visible
        filtered_items = [
            item for item in default_menu.items
            if check_visible(item.dialog_visible)
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
            icons=default_menu.icons,
            startid=default_menu.startid,
            template_only=default_menu.template_only,
            build=default_menu.build,
            action=default_menu.action,
            standalone=default_menu.standalone,
            submenu_path=default_menu.submenu_path,
        )

    items: list[MenuItem] = []
    for item in default_menu.items:
        if item.name in diff.removed and not item.required:
            continue
        if item.dialog_visible and not check_visible(item.dialog_visible):
            continue
        items.append(item)

    diff_map = {o.name: o for o in diff.items}

    for i, item in enumerate(items):
        if item.name in diff_map:
            item_diff = diff_map[item.name]
            items[i] = _apply_diff(item, item_diff)

    new_items = [o for o in diff.items if o.is_new]
    for new_item in new_items:
        items.append(_create_item_from_diff(new_item, icon_overrides))

    positioned_items: dict[int, MenuItem] = {}
    unpositioned_items: list[MenuItem] = []

    for item in items:
        item_diff = diff_map.get(item.name)
        if item_diff and item_diff.position is not None:
            positioned_items[item_diff.position] = item
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
        icons=default_menu.icons,
        startid=default_menu.startid,
        template_only=default_menu.template_only,
        build=default_menu.build,
        action=default_menu.action,
        standalone=default_menu.standalone,
        submenu_path=default_menu.submenu_path,
    )


def _apply_diff(item: MenuItem, diff: MenuItemDiff) -> MenuItem:
    """Apply a user diff to a menu item."""
    properties = {**item.properties, **diff.properties}
    for key in diff.removed_properties:
        properties.pop(key, None)
    return MenuItem(
        name=item.name,
        label=diff.label if diff.label is not None else item.label,
        actions=diff.actions if diff.actions is not None else item.actions,
        label2=item.label2,
        icon=diff.icon if diff.icon is not None else item.icon,
        thumb=item.thumb,
        visible=diff.visible if diff.visible is not None else item.visible,
        disabled=diff.disabled if diff.disabled is not None else item.disabled,
        required=item.required,
        protection=item.protection,
        properties=properties,
        submenu=diff.submenu if diff.submenu is not None else item.submenu,
        original_action=item.action,  # Store original for protection matching
        includes=item.includes,
    )


def _create_item_from_diff(
    diff: MenuItemDiff, icon_overrides: IconOverrides | None = None
) -> MenuItem:
    """Create a new menu item from a user diff."""
    fallback = (icon_overrides or IconOverrides()).get(DEFAULT_ICON, DEFAULT_ICON)
    return MenuItem(
        name=diff.name,
        label=diff.label or "",
        actions=diff.actions or [Action(action="noop")],
        icon=diff.icon or fallback,
        visible=diff.visible or "",
        disabled=diff.disabled or False,
        properties=diff.properties,
        submenu=diff.submenu,
    )
