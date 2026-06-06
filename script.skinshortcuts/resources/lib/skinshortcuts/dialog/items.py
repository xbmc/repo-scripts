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

from ..localize import LANGUAGE, resolve_label
from ..models import Action, BrowseSource, IconSource, MenuItem

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models import PropertySchema


class ItemsMixin:
    """Mixin providing item operations - add, delete, move, label, icon, action.

    This mixin implements:
    - Add/delete/move items
    - Set label, icon, action
    - Toggle disabled state
    - Restore deleted items
    - Reset item to defaults
    - Context menu
    - File/image browsing with sources

    Requires DialogBaseMixin to be mixed in first.
    """

    menu_id: str
    manager: MenuManager | None
    items: list[MenuItem]
    property_schema: PropertySchema | None
    icon_sources: list[IconSource]
    shortcuts_path: str
    dialog_mode: str

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

        if self.dialog_mode in ("widgets", "customwidget") or self.dialog_mode.startswith("custom-widget"):
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
            properties["widgetLabel"] = resolve_label(widget.label)

        return MenuItem(
            name=widget.name,
            label=widget.label,
            icon=widget.icon or "DefaultFolder.png",
            properties=properties,
        )

    def _make_unique_item_name(self, base_name: str) -> str:
        """Generate a unique item name by appending a counter suffix if needed.

        If an item with the same name already exists in the current menu,
        appends -2, -3, etc. until a unique name is found.
        """
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
            # widgetLabel is seeded from label for widget submenus; sync on edit so list 211 and widget output match
            # custom widget menus only exist in working[]
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
        # <icons>path</icons> simple mode is parsed as one unlabeled source; treat as direct browse start
        sources = self.icon_sources
        default_path = ""
        if len(sources) == 1 and not sources[0].label:
            default_path = sources[0].path
            sources = []
        icon = self._browse_with_sources(
            sources=sources,
            title=xbmc.getLocalizedString(1030),  # "Choose icon"
            browse_type=2,  # Image file
            mask=".png|.jpg|.gif",
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
        selected = xbmcgui.Dialog().select(LANGUAGE(32137), labels)

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
        mask: str = "",
        item_properties: dict[str, str] | None = None,
        default_path: str = "",
    ) -> str | None:
        """Browse for a file using configured sources.

        Args:
            sources: List of IconSource or BrowseSource objects
            title: Dialog title
            browse_type: Kodi browse type (0=folder, 2=image file)
            mask: File mask for filtering (e.g., ".png|.jpg")
            item_properties: Current item properties for condition evaluation
            default_path: Starting path when sources is empty (direct browse mode)

        Returns:
            Selected path, or None if cancelled
        """
        from ..conditions import evaluate_condition

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
                result = xbmcgui.Dialog().browse(
                    browse_type, title, "files", mask, False, False, default_path
                )
                return result if isinstance(result, str) and result != default_path else None
            result = xbmcgui.Dialog().browse(browse_type, title, "files", mask)
            return result if isinstance(result, str) else None

        while True:
            listitems = []
            for source in visible_sources:
                label = resolve_label(source.label) if source.label else source.path
                listitem = xbmcgui.ListItem(label)
                if source.icon:
                    listitem.setArt({"icon": source.icon})
                listitems.append(listitem)

            selected = xbmcgui.Dialog().select(title, listitems, useDetails=True)

            if selected == -1:
                return None  # Cancelled

            source = visible_sources[selected]
            path = source.path

            if path.lower() == "browse":
                result = xbmcgui.Dialog().browse(browse_type, title, "files", mask)
            else:
                result = xbmcgui.Dialog().browse(
                    browse_type, title, "files", mask, False, False, path
                )

            if result and isinstance(result, str) and result != path:
                return result

    def _show_context_menu(self) -> None:
        """Show context menu for selected item."""
        item = self._get_selected_item()
        if not item:
            return

        options = [
            (LANGUAGE(32171), self._set_label),
            (LANGUAGE(32172), self._set_action),
            (LANGUAGE(32173), self._set_icon),
            (LANGUAGE(32139), self._edit_submenu),
            (xbmc.getLocalizedString(117), self._delete_item),
        ]

        labels = [opt[0] for opt in options]
        selected = xbmcgui.Dialog().contextmenu(labels)

        if selected >= 0:
            options[selected][1]()

    def _set_item_property(
        self,
        item: MenuItem,
        name: str,
        value: str | None,
        related: Mapping[str, str | None] | None = None,
        apply_suffix: bool = True,
    ) -> None:
        """Unified property setter for menu items.

        All properties (including widget and background) are stored in item.properties.
        Updates both the manager (for persistence) and local item state (for UI).

        Args:
            item: The menu item to update
            name: Property name (e.g., "widget", "background", "widgetStyle")
            value: Property value, or None/empty string to clear
            related: Optional dict of related properties to auto-populate
                     (e.g., {"widgetLabel": "Movies", "widgetPath": "..."})
            apply_suffix: If True, apply property_suffix to name and related props.
                         Set to False for shared properties like widget/background.
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
