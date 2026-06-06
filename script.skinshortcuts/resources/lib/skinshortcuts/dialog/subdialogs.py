"""Subdialog management mixin - submenu editing, widget slots, onclose handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..loaders import evaluate_condition
from ..localize import LANGUAGE
from ..models import MenuItem

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models import IconSource, PropertySchema
    from ..models.menu import SubDialog


class SubdialogsMixin:
    """Mixin providing subdialog management - submenu editing, widget slots.

    This mixin implements:
    - Edit submenu spawning
    - Subdialog spawning with mode/suffix
    - Onclose action handling
    - Custom widget menu creation

    Requires DialogBaseMixin to be mixed in first.
    """

    menu_id: str
    shortcuts_path: str
    manager: MenuManager | None
    property_schema: PropertySchema | None
    icon_sources: list[IconSource]
    show_context_menu: bool
    _subdialogs: dict[int, SubDialog]
    _dialog_xml: str
    _skin_path: str

    if TYPE_CHECKING:
        def _get_selected_index(self) -> int: ...
        def _get_selected_item(self) -> MenuItem | None: ...
        def _get_item_properties(self, item: MenuItem) -> dict[str, str]: ...
        def _refresh_selected_item(self) -> None: ...
        def _clear_subdialog_list(self) -> None: ...
        def _log(self, msg: str) -> None: ...

        def setProperty(self, key: str, value: str) -> None: ...
        def clearProperty(self, key: str) -> None: ...

    def _run_child_dialog(self, menu_id: str, dialog_mode: str = "", **kwargs) -> None:
        """Create, run, and clean up a child ManagementDialog."""
        if self.manager and menu_id not in self.manager.working:
            self.manager._ensure_working_menu(menu_id)

        self.setProperty("additionalDialog", "true")

        from . import ManagementDialog

        child = ManagementDialog(
            self._dialog_xml,
            self._skin_path,
            "Default",
            menu_id=menu_id,
            shortcuts_path=self.shortcuts_path,
            manager=self.manager,
            property_schema=self.property_schema,
            icon_sources=self.icon_sources,
            show_context_menu=self.show_context_menu,
            subdialogs=list(self._subdialogs.values()),
            dialog_mode=dialog_mode,
            **kwargs,
        )
        child.doModal()
        del child

        self.clearProperty("additionalDialog")

    def _edit_submenu(self) -> None:
        """Spawn child dialog to edit submenu for selected item.

        Context-aware: checks the submenu's type attribute to determine behavior.
        - type="widgets" → widget picker mode, requires allow.widgets
        - no type → shortcut picker mode, requires allow.submenus
        """
        item = self._get_selected_item()
        if not item:
            return

        if not self.manager:
            return

        template = (
            self.manager.config.get_default_menu(item.submenu) if item.submenu else None
        )
        is_widget_submenu = template and template.menu_type == "widgets"

        menu = self.manager.config.get_menu(self.menu_id)
        if is_widget_submenu:
            if menu and not menu.allow.widgets:
                xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32144))
                return
        else:
            if menu and not menu.allow.submenus:
                xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32145))
                return

        self.manager.ensure_item_submenu(self.menu_id, item)
        submenu_id = self.manager.submenu_key(self.menu_id, item.name)
        self._run_child_dialog(submenu_id, "widgets" if is_widget_submenu else "")

    def _spawn_subdialog(self, subdialog: SubDialog) -> None:
        """Spawn a child dialog for a subdialog definition.

        If subdialog has `menu` but no `mode`, opens the menu directly.
        Otherwise opens the subdialog, and after it closes, evaluates onclose actions.

        Args:
            subdialog: The subdialog definition containing the mode, menu, suffix, and onclose
        """
        item = self._get_selected_item()
        if not item:
            return

        if subdialog.menu and not subdialog.mode:
            self._log(f"Direct menu open: {subdialog.menu}")
            menu_name = self._resolve_menu_reference(subdialog.menu, item, subdialog)
            if menu_name:
                self._open_onclose_menu(menu_name, subdialog)
            return

        self._log(f"Spawning subdialog with mode: {subdialog.mode}, suffix: {subdialog.suffix}")
        self._open_subdialog(subdialog)

        if subdialog.onclose:
            self._handle_onclose(subdialog, item)

    def _handle_onclose(self, subdialog: SubDialog, item: MenuItem) -> None:
        """Handle onclose actions after a subdialog closes.

        Evaluates each onclose action's condition against the current item state.
        The first matching action is executed.

        Args:
            subdialog: The subdialog definition with onclose actions
            item: The original menu item (used as fallback)
        """
        if not self.manager:
            return

        current_item = self._get_selected_item()
        if not current_item:
            return

        item_props = self._get_item_properties(current_item)

        for action in subdialog.onclose:
            if action.condition and not evaluate_condition(action.condition, item_props):
                continue

            if action.action == "menu" and action.menu:
                menu_name = self._resolve_menu_reference(action.menu, current_item, subdialog)
                if menu_name:
                    self._log(f"Onclose: opening menu {menu_name}")
                    self._open_onclose_menu(menu_name, subdialog)
                return

    def _resolve_menu_reference(
        self, menu_ref: str, item: MenuItem, subdialog: SubDialog
    ) -> str:
        """Resolve a menu reference from an onclose action.

        Handles special placeholders:
        - {customWidget} or {customWidget.N} - get/create custom widget menu
        - {item}.X - legacy format, converted to explicit reference

        Args:
            menu_ref: The menu reference string from onclose action
            item: The current menu item
            subdialog: The subdialog definition

        Returns:
            Resolved menu name/ID
        """
        if not self.manager:
            return ""

        if menu_ref.startswith("{customWidget"):
            suffix = ""
            if "." in menu_ref:
                suffix = "." + menu_ref.split(".")[1].rstrip("}")
            else:
                suffix = subdialog.suffix or ""

            prop_name = f"customWidget{suffix}"
            menu_id = item.properties.get(prop_name)

            if not menu_id:
                menu_id = self.manager.create_custom_widget_menu(
                    self.menu_id, item.name, suffix
                )
                self._log(f"Created custom widget menu: {menu_id}")

            return menu_id

        # Handle legacy {item}.customwidget format - convert to explicit reference
        if "{item}" in menu_ref and ".customwidget" in menu_ref:
            resolved = menu_ref.replace("{item}", item.name)
            suffix = ""
            if ".customwidget." in resolved:
                suffix = "." + resolved.split(".customwidget.")[1]
            elif resolved.endswith(".customwidget"):
                suffix = ""
            else:
                suffix = subdialog.suffix or ""

            prop_name = f"customWidget{suffix}"
            menu_id = item.properties.get(prop_name)

            if not menu_id:
                menu_id = self.manager.create_custom_widget_menu(
                    self.menu_id, item.name, suffix
                )
                self._log(f"Created custom widget menu (legacy): {menu_id}")

            return menu_id

        resolved = menu_ref.replace("{item}", item.name)

        # flat ref aliases the per-item submenu; route there or edits fork to a shadow copy
        if item.submenu and resolved == item.submenu:
            self.manager.ensure_item_submenu(self.menu_id, item)
            return self.manager.submenu_key(self.menu_id, item.name)

        return resolved

    def _open_onclose_menu(self, menu_name: str, subdialog: SubDialog) -> None:
        """Open a menu from an onclose action.

        Args:
            menu_name: Name of the menu to open (already resolved)
            subdialog: The parent subdialog definition (for dialog mode)
        """
        if not self.manager:
            return

        self._log(f"Opening onclose menu: {menu_name}")

        if subdialog.mode:
            dialog_mode = f"custom-{subdialog.mode}"
        else:
            dialog_mode = "customwidget"

        self._run_child_dialog(menu_name, dialog_mode)
        self._refresh_selected_item()

    def _open_subdialog(self, subdialog: SubDialog) -> None:
        """Open the subdialog for widget/property editing.

        Args:
            subdialog: The subdialog definition
        """
        self._run_child_dialog(
            self.menu_id,
            subdialog.mode,
            property_suffix=subdialog.suffix,
            setfocus=subdialog.setfocus,
            selected_index=self._get_selected_index(),
        )
        self._clear_subdialog_list()
        self._refresh_selected_item()
