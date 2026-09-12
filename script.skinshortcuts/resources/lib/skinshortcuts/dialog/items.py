"""Item operations mixin - add, delete, move, label, icon, action."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

try:
    import xbmc
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..conditions import evaluate_condition
from ..loaders.base import apply_suffix_transform
from ..localize import LANGUAGE, resolve_label
from ..models import Action, BrowseSource, IconSource, MenuItem
from ..models.menu import ContextMenu, ContextMenuButton
from ..providers import normalize_image
from .base import (
    CONTROL_ADD,
    CONTROL_CHOOSE_SHORTCUT,
    CONTROL_DELETE,
    CONTROL_EDIT_SUBMENU,
    CONTROL_MOVE_DOWN,
    CONTROL_MOVE_UP,
    CONTROL_RESET_ITEM,
    CONTROL_RESTORE_DELETED,
    CONTROL_SET_ACTION,
    CONTROL_SET_ICON,
    CONTROL_SET_LABEL,
    CONTROL_TOGGLE_DISABLED,
)
from .pickers import picker_select
from .properties import BUTTON_ONLY_TYPES

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models import PropertySchema
    from ..models.menu import SubDialog

CONTEXT_DEFAULT_BUTTONS = (
    CONTROL_SET_LABEL,
    CONTROL_SET_ACTION,
    CONTROL_SET_ICON,
    CONTROL_EDIT_SUBMENU,
    CONTROL_DELETE,
)


def _default_context_labels(item: MenuItem) -> dict[int, str]:
    """Default label per built-in button the context menu can route."""
    return {
        CONTROL_ADD: LANGUAGE(32000),
        CONTROL_DELETE: xbmc.getLocalizedString(117),
        CONTROL_MOVE_UP: LANGUAGE(32002),
        CONTROL_MOVE_DOWN: LANGUAGE(32003),
        CONTROL_SET_LABEL: LANGUAGE(32171),
        CONTROL_SET_ICON: LANGUAGE(32173),
        CONTROL_SET_ACTION: LANGUAGE(32172),
        CONTROL_RESTORE_DELETED: LANGUAGE(32028),
        CONTROL_RESET_ITEM: LANGUAGE(32104),
        CONTROL_TOGGLE_DISABLED: LANGUAGE(32207 if item.disabled else 32117),
        CONTROL_CHOOSE_SHORTCUT: LANGUAGE(32043),
        CONTROL_EDIT_SUBMENU: LANGUAGE(32139),
    }


def _browse_path(browse_type: int, title: str, start: str = "") -> str:
    """Browse for a file, unwrapping the image:// form Kodi's image browser returns."""
    result = xbmcgui.Dialog().browse(browse_type, title, "files", defaultt=start)
    return normalize_image(result) if isinstance(result, str) else ""


class ItemsMixin:
    """Mixin providing item operations - add, delete, move, label, icon, action.

    Requires DialogBaseMixin first.
    """

    menu_id: str
    manager: MenuManager | None
    items: list[MenuItem]
    property_schema: PropertySchema | None
    icon_sources: list[IconSource]
    context_menu: ContextMenu
    shortcuts_path: str
    dialog_mode: str
    property_suffix: str
    _subdialogs: dict[int, SubDialog]

    if TYPE_CHECKING:
        from typing import Literal

        from ..models import Content, Widget, WidgetGroup

        def _get_selected_index(self) -> int: ...
        def _get_selected_item(self) -> MenuItem | None: ...
        def _get_selected_listitem(self) -> xbmcgui.ListItem | None: ...
        def _rebuild_list(self, focus_index: int | None = None) -> None: ...
        def _refresh_selected_item(self) -> None: ...
        def _update_deleted_property(self) -> None: ...
        def _load_items(self) -> None: ...
        def _inject_empty_placeholder(self) -> None: ...
        def _update_window_properties(self) -> None: ...
        def _suffixed_name(self, name: str) -> str: ...
        def _log(self, msg: str) -> None: ...
        def _get_item_properties(self, item: MenuItem) -> dict[str, str]: ...
        def onClick(self, control_id: int) -> None: ...  # noqa: N802
        def _pick_widget_from_groups(
            self,
            items: list[WidgetGroup | Widget | Content],
            item_props: dict[str, str],
            slot: str = "",
        ) -> Widget | None | Literal[False]: ...

    def _add_item(self) -> None:
        """Add a new item after the current selection."""
        if not self.manager:
            return

        index = self._get_selected_index()

        if (
            self.dialog_mode in ("widgets", "customwidget")
            or self.dialog_mode.startswith("custom-widget")
        ):
            widget = self._pick_widget_for_add()
            if not widget:
                return
            new_item = self._create_item_from_widget(widget)
            new_item.name = self._make_unique_item_name(new_item.name)
            self.manager.add_item(self.menu_id, after_index=index, item=new_item)
        else:
            new_item = self.manager.add_item(self.menu_id, after_index=index)

        if new_item:
            insert_pos = index + 1 if index >= 0 else 0
            self._rebuild_list(focus_index=insert_pos)

    def _pick_widget_for_add(self):
        """Pick a widget when adding to a widget submenu."""
        from pathlib import Path

        from ..loaders import load_widgets

        widgets_path = Path(self.shortcuts_path) / "widgets.xml"
        widget_config = load_widgets(widgets_path)

        item = self._get_selected_item()
        item_props = self._get_item_properties(item) if item else {}

        if widget_config.groupings:
            result = self._pick_widget_from_groups(
                widget_config.groupings, item_props
            )
            if result is False:
                return None
            return result
        return None

    def _create_item_from_widget(self, widget) -> MenuItem:
        """Create a MenuItem from a Widget using the standard mapping."""
        from ..models import Widget

        if not isinstance(widget, Widget):
            raise TypeError("Expected Widget instance")

        properties: dict[str, str] = {}
        if widget.path:
            properties["widgetPath"] = widget.path
        if widget.type:
            properties["widgetType"] = widget.type
        if widget.target:
            properties["widgetTarget"] = widget.target
        if widget.limit:
            properties["widgetLimit"] = str(widget.limit)
        if widget.sort_by:
            properties["widgetSortBy"] = widget.sort_by
        if widget.sort_order:
            properties["widgetSortOrder"] = widget.sort_order
        if widget.source:
            properties["widgetSource"] = widget.source
        if widget.label:
            properties["widgetLabel"] = widget.label

        return MenuItem(
            name=widget.name,
            label=widget.label,
            icon=widget.icon or "DefaultFolder.png",
            properties=properties,
        )

    def _make_unique_item_name(self, base_name: str) -> str:
        """Generate a unique item name by appending a counter suffix if needed."""
        existing_names = {item.name for item in self.items}

        if base_name not in existing_names:
            return base_name

        counter = 2
        while f"{base_name}-{counter}" in existing_names:
            counter += 1

        return f"{base_name}-{counter}"

    def _delete_item(self) -> None:
        """Delete the selected item."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        if item.required:
            xbmcgui.Dialog().ok(LANGUAGE(32130), LANGUAGE(32174) % resolve_label(item.label))
            return

        if item.protection and item.protection.protects_delete():
            heading = resolve_label(item.protection.heading) or LANGUAGE(32131)
            label = resolve_label(item.label)
            message = resolve_label(item.protection.message) or LANGUAGE(32175) % label
            if not xbmcgui.Dialog().yesno(heading, message):
                return

        index = self._get_selected_index()
        self.manager.remove_item(self.menu_id, item.name)

        if not self.items:
            self._inject_empty_placeholder()

        self._rebuild_list(focus_index=min(index, len(self.items) - 1))
        self._update_deleted_property()

    def _move_item(self, direction: int) -> None:
        """Move item up (-1) or down (1)."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        index = self._get_selected_index()
        new_index = index + direction
        if self.manager.move_item(self.menu_id, item.name, direction):
            self._rebuild_list(focus_index=new_index)

    def _set_label(self) -> None:
        """Change the label of selected item."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        from ..localize import resolve_label

        current_label = resolve_label(item.label)
        keyboard = xbmc.Keyboard(current_label, xbmc.getLocalizedString(528))
        keyboard.doModal()
        if keyboard.isConfirmed():
            new_label = keyboard.getText()
            if new_label == current_label:
                return
            self.manager.set_label(self.menu_id, item.name, new_label)
            item.label = new_label
            # widget submenus seed widgetLabel from label; keep it in sync on edit
            menu = self.manager.working.get(self.menu_id)
            if menu and menu.menu_type == "widgets":
                self.manager.set_custom_property(self.menu_id, item.name, "widgetLabel", new_label)
                item.properties["widgetLabel"] = new_label
            self._refresh_selected_item()

    def _set_icon(self) -> None:
        """Browse for a new icon using icon sources from menus.xml."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        self._log(f"Opening icon picker, current icon: {item.icon}")
        # simple <icons>path</icons> parses as one unlabeled source; browse straight from it
        sources = self.icon_sources
        default_path = ""
        if len(sources) == 1 and not sources[0].label:
            default_path = sources[0].path
            sources = []
        icon = self._browse_with_sources(
            sources=sources,
            title=xbmc.getLocalizedString(1030),  # "Choose icon"
            browse_type=2,  # Image file
            item_properties=item.properties,
            default_path=default_path,
        )
        self._log(f"Icon picker returned: {icon!r}")
        if icon and isinstance(icon, str):
            self._log(f"Setting icon to: {icon}")
            self.manager.set_icon(self.menu_id, item.name, icon)
            item.icon = icon
            self._refresh_selected_item()
        else:
            self._log(f"Icon unchanged (cancelled), still: {item.icon}")

    def _set_action(self) -> None:
        """Set a custom action."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        if item.protection and item.protection.protects_action():
            heading = resolve_label(item.protection.heading) or LANGUAGE(32132)
            label = resolve_label(item.label)
            message = resolve_label(item.protection.message) or LANGUAGE(32176) % label
            if not xbmcgui.Dialog().yesno(heading, message):
                return

        keyboard = xbmc.Keyboard(item.action or "", LANGUAGE(32197))
        keyboard.doModal()
        if keyboard.isConfirmed():
            action = keyboard.getText()
            self.manager.set_action(self.menu_id, item.name, action or "noop")
            item.actions = [Action(action=action or "noop")]
            self._refresh_selected_item()

    def _toggle_disabled(self) -> None:
        """Toggle the disabled state of the selected item."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        if item.required and not item.disabled:
            xbmcgui.Dialog().ok(LANGUAGE(32133), LANGUAGE(32174) % resolve_label(item.label))
            return

        if not item.disabled and item.protection and item.protection.protects_disable():
            heading = resolve_label(item.protection.heading) or LANGUAGE(32134)
            label = resolve_label(item.label)
            message = resolve_label(item.protection.message) or LANGUAGE(32177) % label
            if not xbmcgui.Dialog().yesno(heading, message):
                return

        new_state = not item.disabled
        self.manager.set_disabled(self.menu_id, item.name, new_state)
        self._refresh_selected_item()

    def _restore_deleted_item(self) -> None:
        """Show picker to restore a previously deleted item."""
        if not self.manager:
            return

        removed = self.manager.get_removed_items(self.menu_id)
        if not removed:
            xbmcgui.Dialog().notification(LANGUAGE(32135), LANGUAGE(32136))
            return

        labels = [resolve_label(item.label) for item in removed]
        selected = picker_select("restore", LANGUAGE(32137), labels)

        if selected < 0:
            return

        item = removed[selected]
        self.manager.restore_item(self.menu_id, item)
        self._load_items()

        restored_index = len(self.items) - 1
        for i, it in enumerate(self.items):
            if it.name == item.name:
                restored_index = i
                break

        self._rebuild_list(focus_index=restored_index)
        self._update_deleted_property()

    def _reset_current_item(self) -> None:
        """Reset current item to skin defaults."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        display_label = resolve_label(item.label)
        if not xbmcgui.Dialog().yesno(LANGUAGE(32138), LANGUAGE(32178) % display_label):
            return

        if not self.manager.reset_item(self.menu_id, item.name):
            return

        index = self._get_selected_index()
        self._rebuild_list(focus_index=index)
        self._update_window_properties()

    def _browse_with_sources(
        self,
        sources: list[IconSource] | list[BrowseSource],
        title: str,
        browse_type: int,
        item_properties: dict[str, str] | None = None,
        default_path: str = "",
    ) -> str | None:
        """Browse for a file using configured sources."""
        props = item_properties or {}

        visible_sources = []
        for source in sources:
            if source.condition and not evaluate_condition(source.condition, props):
                continue
            visible = getattr(source, "visible", "")
            if visible and not xbmc.getCondVisibility(visible):
                continue
            visible_sources.append(source)

        if not visible_sources:
            if default_path:
                result = _browse_path(browse_type, title, default_path)
                return result if result and result != default_path else None
            return _browse_path(browse_type, title) or None

        while True:
            listitems = []
            for source in visible_sources:
                label = resolve_label(source.label) if source.label else source.path
                listitem = xbmcgui.ListItem(label, offscreen=True)
                if source.icon:
                    listitem.setArt({"icon": source.icon})
                row_path = "" if source.path.lower() == "browse" else source.path
                listitem.setProperty("path", row_path)
                listitem.setProperty("name", label)
                listitems.append(listitem)

            selected = picker_select("browse", title, listitems, useDetails=True)

            if selected == -1:
                return None  # Cancelled

            source = visible_sources[selected]
            path = source.path

            if path.lower() == "browse":
                result = _browse_path(browse_type, title)
            else:
                result = _browse_path(browse_type, title, path)

            if result and result != path:
                return result

    def _show_context_menu(self) -> None:
        """Show context menu for selected item."""
        item = self._get_selected_item()
        if not item:
            return

        rows = self._context_menu_rows(item)
        if not rows:
            return

        selected = xbmcgui.Dialog().contextmenu([label for _, label in rows])
        if selected >= 0:
            self.onClick(rows[selected][0])

    def _context_menu_rows(self, item: MenuItem) -> list[tuple[int, str]]:
        """Button ID and label per row, after condition and visibility filtering."""
        buttons = self.context_menu.buttons or [
            ContextMenuButton(button_id=button_id) for button_id in CONTEXT_DEFAULT_BUTTONS
        ]
        props = self._get_item_properties(item)
        defaults = _default_context_labels(item)

        rows = []
        for button in buttons:
            condition = apply_suffix_transform(button.condition, self.property_suffix)
            if condition and not evaluate_condition(condition, props):
                continue
            if button.visible and not xbmc.getCondVisibility(button.visible):
                continue

            if not self._context_button_routes(button.button_id, defaults):
                self._log(f"Context menu button {button.button_id} does nothing, skipping")
                continue

            label = resolve_label(button.label) if button.label else defaults.get(button.button_id)
            if not label:
                self._log(f"Context menu button {button.button_id} has no label, skipping")
                continue

            rows.append((button.button_id, label))

        return rows

    def _context_button_routes(self, button_id: int, builtin_labels: dict[int, str]) -> bool:
        """Whether onClick can route this button ID."""
        if button_id in builtin_labels or button_id in self._subdialogs:
            return True
        if not self.property_schema:
            return False

        prop, mapping = self.property_schema.get_property_for_button(button_id)
        if mapping is None:
            return False
        if prop is not None:
            return True
        return mapping.type in BUTTON_ONLY_TYPES

    def _set_item_property(
        self,
        item: MenuItem,
        name: str,
        value: str | None,
        related: Mapping[str, str | None] | None = None,
        apply_suffix: bool = True,
    ) -> None:
        """Unified property setter for menu items.

        Writes the manager for persistence and the local item for the UI.
        """
        if not self.manager:
            return

        prop_name = self._suffixed_name(name) if apply_suffix else name

        self.manager.set_custom_property(self.menu_id, item.name, prop_name, value)
        if value:
            item.properties[prop_name] = value
        else:
            if prop_name in item.properties:
                del item.properties[prop_name]
            listitem = self._get_selected_listitem()
            if listitem:
                listitem.setProperty(prop_name, "")
                listitem.setProperty(f"{prop_name}Label", "")

        if related:
            for rel_name, rel_value in related.items():
                rel_prop_name = self._suffixed_name(rel_name) if apply_suffix else rel_name
                self.manager.set_custom_property(
                    self.menu_id, item.name, rel_prop_name, rel_value
                )
                if rel_value:
                    item.properties[rel_prop_name] = rel_value
                else:
                    if rel_prop_name in item.properties:
                        del item.properties[rel_prop_name]
                    listitem = self._get_selected_listitem()
                    if listitem:
                        listitem.setProperty(rel_prop_name, "")

    def _edit_submenu(self) -> None:
        """Edit submenu - implemented by SubdialogsMixin."""
        raise NotImplementedError
