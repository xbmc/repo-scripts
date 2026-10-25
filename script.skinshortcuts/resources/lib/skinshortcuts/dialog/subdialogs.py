"""Subdialog management mixin - submenu editing, widget slots, onclose handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..conditions import evaluate_condition
from ..localize import LANGUAGE
from ..models.menu import MenuItem

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models.menu import ContextMenu, IconSource, SubDialog
    from ..models.property import PropertySchema
    from ..providers.content import ContentProvider


class SubdialogsMixin:
    """Mixin providing subdialog management - submenu editing, widget slots."""

    menu_id: str
    shortcuts_path: str
    manager: MenuManager | None
    items: list[MenuItem]
    property_schema: PropertySchema | None
    icon_sources: list[IconSource]
    context_menu: ContextMenu
    _subdialogs: dict[int, SubDialog]
    _dialog_xml: str
    _skin_path: str

    if TYPE_CHECKING:
        def _get_selected_index(self) -> int: ...
        def _get_selected_item(self) -> MenuItem | None: ...
        def _get_item_properties(self, item: MenuItem) -> dict[str, str]: ...
        def _refresh_selected_item(self) -> None: ...
        def _rebuild_list(self, focus_index: int | None = None) -> None:
            """Rebuild the list on the given row or row 0, plus 212 in a subdialog."""
        def _mirror_to_home(self) -> None:
            """Mirror the dialog mode and suffix to Home, for a native dialog over this one."""
        def _log(self, msg: str) -> None: ...
        def _get_content_provider(self) -> ContentProvider: ...

        def setProperty(self, key: str, value: str) -> None: ...
        def clearProperty(self, key: str) -> None: ...

    def _run_child_dialog(self, menu_id: str, dialog_mode: str = "", **kwargs) -> None:
        """Run a child ManagementDialog on this dialog's objects, then restore its Home mirror."""
        if self.manager and menu_id not in self.manager.working:
            self.manager._ensure_working_menu(menu_id)

        from . import ManagementDialog

        child = ManagementDialog(
            self._dialog_xml,
            self._skin_path,
            "Default",
            menu_id=menu_id,
            shortcuts_path=self.shortcuts_path,
            manager=self.manager,
            content_provider=self._get_content_provider(),
            property_schema=self.property_schema,
            icon_sources=self.icon_sources,
            context_menu=self.context_menu,
            subdialogs=list(self._subdialogs.values()),
            dialog_mode=dialog_mode,
            **kwargs,
        )
        self.setProperty("additionalDialog", "true")
        try:
            child.doModal()
        finally:
            del child
            self.clearProperty("additionalDialog")
            self._mirror_to_home()

    def _edit_submenu(self) -> None:
        """Edit the item's submenu in a widget or shortcut child dialog, then refresh its row."""
        item = self._get_selected_item()
        if not item:
            return

        if not self.manager:
            return

        menu = self.manager.working.get(self.menu_id)
        if menu and menu.is_submenu:
            self._log(f"No submenu for '{item.name}': submenus are one level deep")
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
        self._refresh_selected_item()

    def _spawn_subdialog(self, subdialog: SubDialog) -> None:
        """Spawn a subdialog, then run its onclose actions; a menu-only one just opens the menu."""
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
        if not self._open_subdialog(subdialog, item):
            return

        if subdialog.onclose:
            self._handle_onclose(subdialog, item)

    def _handle_onclose(self, subdialog: SubDialog, item: MenuItem) -> None:
        """Handle a closed subdialog's onclose actions, running the first whose condition holds."""
        if not self.manager:
            return

        current_item = next((entry for entry in self.items if entry.name == item.name), None)
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
        """Resolve an onclose menu reference, creating a custom widget menu the first time."""
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
        """Open a menu from an onclose action."""
        if not self.manager:
            return

        self._log(f"Opening onclose menu: {menu_name}")

        if subdialog.mode:
            dialog_mode = f"custom-{subdialog.mode}"
        else:
            dialog_mode = "customwidget"

        self._run_child_dialog(menu_name, dialog_mode)
        self._refresh_selected_item()

    def _open_subdialog(self, subdialog: SubDialog, item: MenuItem) -> bool:
        """Open the subdialog for the item, then refocus it; False when the subdialog deleted it."""
        index = self._get_selected_index()
        self._run_child_dialog(
            self.menu_id,
            subdialog.mode,
            property_suffix=subdialog.suffix,
            setfocus=subdialog.setfocus,
            selected_index=index,
        )
        moved = next((i for i, entry in enumerate(self.items) if entry.name == item.name), -1)
        self._rebuild_list(focus_index=moved if moved >= 0 else min(index, len(self.items) - 1))
        return moved >= 0
