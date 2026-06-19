"""Menu manager for dialog operations."""

from __future__ import annotations

import copy
import uuid
from pathlib import Path

from .config import SkinConfig
from .log import get_logger
from .models import Action, Menu, MenuItem
from .playlists import cleanup_orphan_playlists
from .userdata import (
    MenuItemOverride,
    MenuOverride,
    UserData,
    _check_dialog_visible,
    save_userdata,
)

log = get_logger("MenuManager")


class MenuManager:
    """Manages menu operations with working copy and diff-based save.

    Architecture:
    - defaults: Immutable skin defaults (from config.default_menus)
    - working: Mutable working copy (all edits happen here)
    - Save diffs working against defaults to generate minimal userdata
    """

    def __init__(self, shortcuts_path: str | Path, userdata_path: str | None = None):
        """Initialize manager.

        Args:
            shortcuts_path: Path to skin's shortcuts folder
            userdata_path: Optional path to userdata file (for testing)
        """
        self.shortcuts_path = Path(shortcuts_path)
        self.userdata_path = userdata_path

        self.config = SkinConfig.load(shortcuts_path, load_user=True, userdata_path=userdata_path)

        # Submenu templates referenced by an item (via submenu="..." or name match)
        # are seed sources only - per-item working copies live under f"{parent}/{item}" keys.
        referenced_templates = self._referenced_submenu_templates()

        self.working: dict[str, Menu] = {}
        for menu in self.config.menus:
            if menu.is_submenu and menu.name in referenced_templates:
                continue
            self.working[menu.name] = copy.deepcopy(menu)
        for menu in self.working.values():
            self.config.resolve_item_properties(menu)

        self._changed = False

    def _referenced_submenu_templates(self) -> set[str]:
        """Set of submenu template names referenced by any item (defaults or userdata).

        A referenced template is used only as a seed source for per-item submenu
        working copies. Non-referenced submenu entries (standalone named templates)
        remain in working storage under their template name.
        """
        referenced: set[str] = set()
        for menu in self.config.default_menus:
            for item in menu.items:
                if item.submenu:
                    referenced.add(item.submenu)
        for menu_override in self.config.userdata.menus.values():
            for item_override in menu_override.items:
                if item_override.submenu:
                    referenced.add(item_override.submenu)
        submenu_names = {m.name for m in self.config.default_menus if m.is_submenu}
        return referenced & submenu_names

    def get_menu_ids(self) -> list[str]:
        """Get all available menu names."""
        return [menu.name for menu in self.config.menus]

    def get_all_menus(self) -> list[Menu]:
        """Get all menus from working copy.

        Returns:
            List of Menu objects ready for building includes
        """
        return list(self.working.values())

    def get_menu_items(self, menu_id: str) -> list[MenuItem]:
        """Get items for a menu from working copy."""
        if menu_id in self.working:
            return self.working[menu_id].items
        return []

    def get_widgets(self) -> list[tuple[str, str]]:
        """Get available widgets as (name, label) tuples."""
        return [(w.name, w.label) for w in self.config.widgets]

    def get_backgrounds(self) -> list[tuple[str, str]]:
        """Get available backgrounds as (name, label) tuples."""
        return [(b.name, b.label) for b in self.config.backgrounds]

    def _get_working_item(self, menu_id: str, item_name: str) -> MenuItem | None:
        """Get item from working copy."""
        if menu_id in self.working:
            for item in self.working[menu_id].items:
                if item.name == item_name:
                    return item
        return None

    def _ensure_working_menu(self, menu_id: str) -> Menu:
        """Ensure menu exists in working copy, create if needed."""
        if menu_id not in self.working:
            self.working[menu_id] = Menu(name=menu_id, is_submenu=True)
        return self.working[menu_id]

    @staticmethod
    def submenu_key(parent_menu_name: str, item_name: str) -> str:
        """Per-item submenu working key for a given item."""
        return f"{parent_menu_name}/{item_name}"

    @staticmethod
    def submenu_template(item: MenuItem) -> str:
        """Template name to seed this item's submenu from. Empty if no explicit binding."""
        return item.submenu or ""

    def ensure_item_submenu(self, parent_menu_name: str, item: MenuItem) -> Menu:
        """Return the per-item submenu, seeding from template on first access."""
        key = self.submenu_key(parent_menu_name, item.name)
        if key not in self.working:
            template_name = self.submenu_template(item)
            default = self.config.get_default_menu(template_name)
            if default is not None:
                seeded = copy.deepcopy(default)
                seeded.name = key
                self.working[key] = seeded
                self.config.resolve_item_properties(self.working[key])
            else:
                self.working[key] = Menu(name=key, is_submenu=True)
        return self.working[key]

    def drop_per_item_submenu(self, parent_menu_name: str, item_name: str) -> None:
        """Discard the per-item submenu so the next access reseeds from the template.

        Needed when the item's shortcut or submenu reference changes.
        """
        key = self.submenu_key(parent_menu_name, item_name)
        if key in self.working:
            del self.working[key]
            self._changed = True

    def _generate_unique_id(self, prefix: str = "user") -> str:
        """Generate a unique ID that doesn't exist in any menu or as a menu name."""
        existing_items = {item.name for menu in self.working.values() for item in menu.items}
        existing_menus = set(self.working.keys())
        existing = existing_items | existing_menus
        while True:
            name = f"{prefix}-{uuid.uuid4().hex[:8]}"
            if name not in existing:
                return name

    def create_custom_widget_menu(self, menu_id: str, item_id: str, suffix: str = "") -> str:
        """Create a custom widget menu for an item and store the reference.

        Args:
            menu_id: Menu containing the item
            item_id: Item to attach custom widget to
            suffix: Widget slot suffix (e.g., ".2" for second slot)

        Returns:
            The new menu ID, or empty string if item not found
        """
        item = self._get_working_item(menu_id, item_id)
        if not item:
            return ""

        cw_menu_id = self._generate_unique_id("custom")
        self.working[cw_menu_id] = Menu(name=cw_menu_id, is_submenu=True, menu_type="widgets")

        prop_name = f"customWidget{suffix}"
        item.properties[prop_name] = cw_menu_id
        item.is_placeholder = False
        self._changed = True

        return cw_menu_id

    def get_custom_widget_menu(self, menu_id: str, item_id: str, suffix: str = "") -> str:
        """Get the custom widget menu ID for an item.

        Args:
            menu_id: Menu containing the item
            item_id: Item to get custom widget for
            suffix: Widget slot suffix (e.g., ".2" for second slot)

        Returns:
            The menu ID, or empty string if not set
        """
        item = self._get_working_item(menu_id, item_id)
        if not item:
            return ""
        prop_name = f"customWidget{suffix}"
        return item.properties.get(prop_name, "")

    def clear_custom_widget(self, menu_id: str, item_id: str, suffix: str = "") -> bool:
        """Clear a custom widget menu and remove the reference.

        Args:
            menu_id: Menu containing the item
            item_id: Item to clear custom widget from
            suffix: Widget slot suffix (e.g., ".2" for second slot)

        Returns:
            True if cleared successfully
        """
        item = self._get_working_item(menu_id, item_id)
        if not item:
            return False

        prop_name = f"customWidget{suffix}"
        cw_menu_id = item.properties.get(prop_name)

        if cw_menu_id:
            if cw_menu_id in self.working:
                self.working[cw_menu_id].items.clear()
            del item.properties[prop_name]
            item.is_placeholder = False
            self._changed = True
            return True

        return False

    def add_item(
        self,
        menu_id: str,
        after_index: int | None = None,
        label: str = "",
        item: MenuItem | None = None,
    ) -> MenuItem:
        """Add a new item to a menu.

        Args:
            menu_id: Menu to add item to
            after_index: Insert after this index (None = append)
            label: Initial label for the item
            item: Optional pre-created MenuItem to add

        Returns:
            The newly created or provided MenuItem
        """
        menu = self._ensure_working_menu(menu_id)

        if item:
            new_item = item
            if not new_item.name or self._item_name_exists(menu, new_item.name):
                prefix = "sub" if menu.is_submenu else "user"
                new_item.name = self._generate_unique_id(prefix)
        else:
            prefix = "sub" if menu.is_submenu else "user"
            item_name = self._generate_unique_id(prefix)
            new_item = MenuItem(
                name=item_name,
                label=label or "$ADDON[script.skinshortcuts 32129]",
                actions=[Action(action="noop")],
                is_placeholder=not label,
            )

        if after_index is not None and 0 <= after_index < len(menu.items):
            menu.items.insert(after_index + 1, new_item)
        else:
            menu.items.append(new_item)

        self._changed = True
        return new_item

    def _item_name_exists(self, menu: Menu, name: str) -> bool:
        """Check if an item name already exists in a menu."""
        return any(item.name == name for item in menu.items)

    def remove_item(self, menu_id: str, item_id: str) -> bool:
        """Remove an item from a menu.

        Args:
            menu_id: Menu containing the item
            item_id: ID of item to remove

        Returns:
            True if item was removed
        """
        if menu_id not in self.working:
            return False

        menu = self.working[menu_id]
        for i, item in enumerate(menu.items):
            if item.name == item_id:
                menu.items.pop(i)
                self._changed = True
                return True

        return False

    def restore_item(self, menu_id: str, item: MenuItem) -> bool:
        """Restore a previously deleted item.

        Args:
            menu_id: Menu to restore item to
            item: The MenuItem to restore (will be deep copied)

        Returns:
            True if item was restored
        """
        menu = self._ensure_working_menu(menu_id)

        menu.items[:] = [i for i in menu.items if not (i.is_placeholder and not i.actions)]

        restored = copy.deepcopy(item)
        menu.items.append(restored)
        self._changed = True
        return True

    def reset_item(self, menu_id: str, item_id: str) -> bool:
        """Reset an item to its skin default values.

        Args:
            menu_id: Menu containing the item
            item_id: ID of item to reset

        Returns:
            True if item was reset
        """
        default_menu = self.config.get_default_menu(menu_id)
        if default_menu is None and "/" in menu_id:
            default_menu = self._template_for_submenu_key(menu_id)
        if not default_menu:
            return False

        default_item = None
        for item in default_menu.items:
            if item.name == item_id:
                default_item = item
                break

        if not default_item:
            return False

        if menu_id not in self.working:
            return False

        for i, item in enumerate(self.working[menu_id].items):
            if item.name == item_id:
                self.working[menu_id].items[i] = copy.deepcopy(default_item)
                self._changed = True
                return True

        return False

    def reset_menu(self, menu_id: str) -> bool:
        """Reset a menu to its skin default values.

        For skin-defined menus, restores all items to defaults.
        For per-item submenu keys (parent/item), re-seeds from the item's template.
        For custom menus (user-created), clears all items.

        Args:
            menu_id: ID of menu to reset

        Returns:
            True if menu was reset
        """
        default_menu = self.config.get_default_menu(menu_id)

        if default_menu:
            self.working[menu_id] = copy.deepcopy(default_menu)
            self._changed = True
            return True

        if "/" in menu_id:
            parent_name, _, item_name = menu_id.partition("/")
            parent = self.working.get(parent_name)
            if parent:
                for item in parent.items:
                    if item.name == item_name:
                        template_name = self.submenu_template(item)
                        template = self.config.get_default_menu(template_name)
                        if template is not None:
                            seeded = copy.deepcopy(template)
                            seeded.name = menu_id
                            self.working[menu_id] = seeded
                        elif menu_id in self.working:
                            self.working[menu_id].items.clear()
                        else:
                            self.working[menu_id] = Menu(name=menu_id, is_submenu=True)
                        self._changed = True
                        return True

        if menu_id in self.working:
            self.working[menu_id].items.clear()
            self._changed = True
            return True

        return False

    def reset_menu_tree(self, menu_id: str, _visited: set[str] | None = None) -> bool:
        """Reset a menu and all its submenus by following submenu references.

        Recursively resets the specified menu and any menus referenced by
        item submenu properties.

        Args:
            menu_id: ID of root menu to reset
            _visited: Internal set to prevent infinite loops

        Returns:
            True if any menus were reset
        """
        if _visited is None:
            _visited = set()

        if menu_id in _visited:
            return False
        _visited.add(menu_id)

        menu = self.working.get(menu_id)
        submenu_refs = []
        if menu:
            for item in menu.items:
                template_name = self.submenu_template(item)
                if self.config.get_default_menu(template_name):
                    submenu_refs.append(self.submenu_key(menu_id, item.name))

        changed = self.reset_menu(menu_id)

        for submenu_id in submenu_refs:
            if self.reset_menu_tree(submenu_id, _visited):
                changed = True

        return changed

    def reset_all_submenus(self) -> bool:
        """Reset all submenus (menus defined with <submenu> tag).

        Returns:
            True if any menus were reset
        """
        changed = False
        for menu in self.working.values():
            if menu.is_submenu and self.reset_menu(menu.name):
                changed = True
        return changed

    def is_item_modified(self, menu_id: str, item_id: str) -> bool:
        """Check if an item differs from its skin default.

        Args:
            menu_id: Menu containing the item
            item_id: ID of item to check

        Returns:
            True if item is modified from defaults
        """
        working_item = self._get_working_item(menu_id, item_id)
        if not working_item:
            return False

        default_menu = self.config.get_default_menu(menu_id)
        if default_menu is None and "/" in menu_id:
            default_menu = self._template_for_submenu_key(menu_id)
        if not default_menu:
            return False

        default_item = None
        for item in default_menu.items:
            if item.name == item_id:
                default_item = item
                break

        if not default_item:
            return False

        if working_item.label != default_item.label:
            return True
        if working_item.actions != default_item.actions:
            return True
        if working_item.icon != default_item.icon:
            return True
        if working_item.disabled != default_item.disabled:
            return True

        return working_item.properties != default_item.properties

    def get_removed_items(self, menu_id: str) -> list[MenuItem]:
        """Get default items that have been removed from working copy.

        Args:
            menu_id: Menu to check

        Returns:
            List of MenuItems that can be restored
        """
        default_menu = self.config.get_default_menu(menu_id)
        if default_menu is None and "/" in menu_id:
            default_menu = self._template_for_submenu_key(menu_id)
        if not default_menu:
            return []

        working_menu = self.working.get(menu_id)
        if not working_menu:
            return list(default_menu.items)

        working_names = {item.name for item in working_menu.items}
        removed = []
        for item in default_menu.items:
            if item.name in working_names:
                continue
            if item.dialog_visible and not _check_dialog_visible(item.dialog_visible):
                continue
            removed.append(item)
        return removed

    def has_removed_items(self, menu_id: str) -> bool:
        """Check if menu has removed items that can be restored."""
        return bool(self.get_removed_items(menu_id))

    def move_item(self, menu_id: str, item_id: str, direction: int) -> bool:
        """Move an item up or down in the menu.

        Args:
            menu_id: Menu containing the item
            item_id: ID of item to move
            direction: -1 for up, 1 for down

        Returns:
            True if item was moved
        """
        if menu_id not in self.working:
            return False

        items = self.working[menu_id].items
        if not items:
            return False

        current_index = None
        for i, item in enumerate(items):
            if item.name == item_id:
                current_index = i
                break

        if current_index is None:
            return False

        new_index = current_index + direction
        if new_index < 0 or new_index >= len(items):
            return False

        items[current_index], items[new_index] = items[new_index], items[current_index]

        self._changed = True
        return True

    def set_label(self, menu_id: str, item_id: str, label: str) -> bool:
        """Set the label for an item."""
        return self._set_item_property(menu_id, item_id, "label", label)

    def set_action(self, menu_id: str, item_id: str, action: str | list[str]) -> bool:
        """Set the action(s) for an item.

        Args:
            menu_id: Menu containing the item
            item_id: ID of item to update
            action: Single action string or list of actions
        """
        if isinstance(action, str):
            actions = [action]
        else:
            actions = action
        return self._set_item_property(menu_id, item_id, "actions", actions)

    def set_icon(self, menu_id: str, item_id: str, icon: str) -> bool:
        """Set the icon for an item."""
        return self._set_item_property(menu_id, item_id, "icon", icon)

    def set_submenu(self, menu_id: str, item_id: str, submenu: str | None) -> bool:
        """Set or clear the submenu template reference for an item."""
        return self._set_item_property(menu_id, item_id, "submenu", submenu)

    def set_widget(self, menu_id: str, item_id: str, widget: str | None) -> bool:
        """Set the widget for an item.

        Widget is stored as a property in the properties dict.
        """
        return self.set_custom_property(menu_id, item_id, "widget", widget)

    def set_background(self, menu_id: str, item_id: str, background: str | None) -> bool:
        """Set the background for an item.

        Background is stored as a property in the properties dict.
        """
        return self.set_custom_property(menu_id, item_id, "background", background)

    def set_disabled(self, menu_id: str, item_id: str, disabled: bool) -> bool:
        """Set the disabled state for an item."""
        return self._set_item_property(menu_id, item_id, "disabled", disabled)

    def set_visible(self, menu_id: str, item_id: str, visible: str) -> bool:
        """Set the runtime visibility condition for an item."""
        return self._set_item_property(menu_id, item_id, "visible", visible)

    def set_custom_property(
        self, menu_id: str, item_id: str, prop_name: str, value: str | None
    ) -> bool:
        """Set a custom property on an item (stored in properties dict)."""
        item = self._get_working_item(menu_id, item_id)
        if not item:
            return False

        if value:
            item.properties[prop_name] = value
        elif prop_name in item.properties:
            del item.properties[prop_name]

        item.is_placeholder = False
        self._changed = True
        return True

    def _set_item_property(
        self, menu_id: str, item_id: str, prop: str, value: str | bool | list[str] | None
    ) -> bool:
        """Set a property on an item in working copy."""
        item = self._get_working_item(menu_id, item_id)
        if not item:
            return False

        if prop == "actions" and isinstance(value, list):
            item.actions = [Action(action=a) for a in value]
        else:
            setattr(item, prop, value)

        item.is_placeholder = False
        self._changed = True
        return True

    def has_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self._changed

    def save(self) -> bool:
        """Save userdata to disk by diffing working copy against defaults."""
        if not self._changed:
            return True

        userdata = self._generate_userdata()
        success = save_userdata(userdata, self.userdata_path)
        if success:
            self._changed = False
            self._cleanup_source_playlists()
        return success

    def _cleanup_source_playlists(self) -> None:
        """Remove generated source playlists no surviving shortcut points at."""
        actions = [
            act.action
            for menu in self.working.values()
            for item in menu.items
            for act in item.actions
        ]
        cleanup_orphan_playlists(actions)

    def reload(self) -> None:
        """Reload config and userdata from disk, rebuild working copy."""
        self.config = SkinConfig.load(
            self.shortcuts_path, load_user=True, userdata_path=self.userdata_path
        )
        referenced_templates = self._referenced_submenu_templates()
        self.working = {}
        for menu in self.config.menus:
            if menu.is_submenu and menu.name in referenced_templates:
                continue
            self.working[menu.name] = copy.deepcopy(menu)
        self._changed = False

    def _cleanup_orphaned_menus(self) -> None:
        """Remove menus that are not in defaults and have no parent reference."""
        default_menu_names = {m.name for m in self.config.default_menus}

        referenced_menus: set[str] = set()
        for menu in self.working.values():
            for item in menu.items:
                referenced_menus.add(self.submenu_key(menu.name, item.name))
                for key, value in item.properties.items():
                    if key.startswith("customWidget") and value:
                        referenced_menus.add(value)

        # Subdialog menu patterns like {item}.1 create menus named e.g. "music.1"
        # that aren't in defaults or referenced by submenu/customWidget properties.
        for subdialog in self.config.subdialogs:
            if subdialog.menu and "{item}" in subdialog.menu:
                for menu in self.working.values():
                    for item in menu.items:
                        resolved = subdialog.menu.replace("{item}", item.name)
                        referenced_menus.add(resolved)

        orphaned = [
            menu_id for menu_id in self.working
            if menu_id not in default_menu_names and menu_id not in referenced_menus
        ]

        for menu_id in orphaned:
            log.debug(f"Removing orphaned menu: {menu_id}")
            del self.working[menu_id]

    def _generate_userdata(self) -> UserData:
        """Generate userdata by diffing working copy against defaults."""
        self._cleanup_orphaned_menus()

        userdata = UserData()

        default_menus = {m.name: m for m in self.config.default_menus}

        for menu_id, working_menu in self.working.items():
            default_menu = default_menus.get(menu_id)
            if default_menu is None and "/" in menu_id:
                default_menu = self._template_for_submenu_key(menu_id)
            menu_override = self._diff_menu(working_menu, default_menu)
            if menu_override:
                userdata.menus[menu_id] = menu_override

        return userdata

    def _template_for_submenu_key(self, key: str) -> Menu | None:
        """Resolve the submenu template a per-item working key was seeded from."""
        parent_name, _, item_name = key.partition("/")
        parent = self.working.get(parent_name)
        if not parent:
            return None
        for item in parent.items:
            if item.name == item_name:
                template_name = self.submenu_template(item)
                return self.config.get_default_menu(template_name)
        return None

    def _diff_menu(self, working: Menu, default: Menu | None) -> MenuOverride | None:
        """Generate diff for a single menu."""
        override = MenuOverride()

        if default is None:
            for idx, item in enumerate(working.items):
                if item.is_placeholder:
                    continue
                item_override = self._item_to_override(item, is_new=True)
                item_override.position = idx
                override.items.append(item_override)
            return override if override.items else None

        default_items = {item.name: item for item in default.items}
        working_items = {item.name: item for item in working.items if not item.is_placeholder}

        for name, default_item in default_items.items():
            if name not in working_items:
                # Skip items filtered by dialog_visible - they weren't user-removed
                if default_item.dialog_visible and not _check_dialog_visible(
                    default_item.dialog_visible
                ):
                    continue
                override.removed.append(name)

        for idx, working_item in enumerate(working.items):
            if working_item.is_placeholder:
                continue
            default_item = default_items.get(working_item.name)

            if default_item is None:
                item_override = self._item_to_override(working_item, is_new=True)
                item_override.position = idx
                override.items.append(item_override)
            else:
                default_idx = next(
                    (i for i, d in enumerate(default.items) if d.name == working_item.name),
                    None
                )
                position_changed = default_idx != idx
                item_diff = self._diff_item(working_item, default_item)

                if item_diff or position_changed:
                    if item_diff is None:
                        item_diff = MenuItemOverride(name=working_item.name)
                    item_diff.position = idx
                    override.items.append(item_diff)

        if not override.items and not override.removed:
            return None
        return override

    def _diff_item(self, working: MenuItem, default: MenuItem) -> MenuItemOverride | None:
        """Generate diff for a single item - only include changed fields."""
        diff = MenuItemOverride(name=working.name)
        has_changes = False

        if working.label != default.label:
            diff.label = working.label
            has_changes = True

        if working.actions != default.actions:
            diff.actions = working.actions
            has_changes = True

        if working.icon != default.icon:
            diff.icon = working.icon
            has_changes = True

        if working.disabled != default.disabled:
            diff.disabled = working.disabled
            has_changes = True

        if working.properties != default.properties:
            diff_props = {
                k: v for k, v in working.properties.items()
                if default.properties.get(k) != v
            }
            if diff_props:
                diff.properties = diff_props
                has_changes = True

        if working.submenu != default.submenu:
            diff.submenu = working.submenu or ""
            has_changes = True

        if working.visible != default.visible:
            diff.visible = working.visible
            has_changes = True

        return diff if has_changes else None

    def _item_to_override(self, item: MenuItem, is_new: bool = False) -> MenuItemOverride:
        """Convert full item to override format."""
        return MenuItemOverride(
            name=item.name,
            label=item.label,
            actions=item.actions,
            icon=item.icon,
            disabled=item.disabled if item.disabled else None,
            properties=item.properties.copy() if item.properties else {},
            is_new=is_new,
            submenu=item.submenu,
            visible=item.visible if item.visible else None,
        )
