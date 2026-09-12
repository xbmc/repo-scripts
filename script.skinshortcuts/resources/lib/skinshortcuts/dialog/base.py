"""Core dialog class with initialization and event handling."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

try:
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..constants import extract_path_from_action, get_shortcuts_path
from ..loaders import evaluate_condition, load_menus, load_properties
from ..loaders.base import apply_suffix_transform
from ..localize import resolve_label
from ..log import get_logger
from ..manager import MenuManager
from ..models import MenuItem, PropertySchema
from ..models.menu import ContextMenu

_log = get_logger("Dialog")

if TYPE_CHECKING:
    from ..models import IconSource
    from ..models.menu import SubDialog

CONTROL_LIST = 211
CONTROL_SUBDIALOG_LIST = 212
CONTROL_ADD = 301
CONTROL_DELETE = 302
CONTROL_MOVE_UP = 303
CONTROL_MOVE_DOWN = 304
CONTROL_SET_LABEL = 305
CONTROL_SET_ICON = 306
CONTROL_SET_ACTION = 307
CONTROL_RESTORE_DELETED = 311
CONTROL_RESET_ITEM = 312
CONTROL_TOGGLE_DISABLED = 313
CONTROL_CHOOSE_SHORTCUT = 401
CONTROL_EDIT_SUBMENU = 405

ACTION_CANCEL = (9, 10, 92, 216, 247, 257, 275, 61467, 61448)
ACTION_CONTEXT = (117,)


def _display_label(value: str) -> str:
    """Resolve an emitted $LOCALIZE label for the dialog; user text passes through."""
    return resolve_label(value) if value.startswith("$") else value


class DialogBaseMixin(xbmcgui.WindowXMLDialog):
    """Core dialog functionality - initialization, list management, event routing.

    Inherits WindowXMLDialog for typing; the runtime class does too, so the MRO holds.
    """


    menu_id: str
    shortcuts_path: str
    manager: MenuManager | None
    items: list[MenuItem]
    property_schema: PropertySchema | None
    icon_sources: list[IconSource]
    context_menu: ContextMenu
    dialog_mode: str
    property_suffix: str
    is_child: bool
    changes_saved: bool
    _shared_manager: MenuManager | None
    _shared_schema: PropertySchema | None
    _shared_icon_sources: list[IconSource] | None
    _shared_context_menu: ContextMenu | None
    _shared_subdialogs: list[SubDialog] | None
    _subdialogs: dict[int, SubDialog]
    _setfocus: int | None
    _selected_index: int | None
    _dialog_xml: str
    _skin_path: str

    def __init__(self, *args, **kwargs):
        """Read dialog state from kwargs; a child reuses the parent's shared objects."""
        super().__init__(*args)
        self.menu_id = kwargs.get("menu_id", "mainmenu")
        self.shortcuts_path = kwargs.get("shortcuts_path", get_shortcuts_path())

        self._shared_manager = kwargs.get("manager")
        self.manager = None
        self.items = []

        self._content_provider = kwargs.get("content_provider")

        self._shared_schema = kwargs.get("property_schema")
        self.property_schema = None

        self._shared_icon_sources = kwargs.get("icon_sources")
        self.icon_sources = []

        self._shared_context_menu = kwargs.get("context_menu")
        self.context_menu = ContextMenu()

        self._shared_subdialogs = kwargs.get("subdialogs")
        self._subdialogs = {}
        self.dialog_mode = kwargs.get("dialog_mode", "")
        self.property_suffix = kwargs.get("property_suffix", "")

        self._setfocus = kwargs.get("setfocus")
        self._selected_index = kwargs.get("selected_index")
        self.is_child = self._shared_manager is not None

        self._dialog_xml = args[0] if args else "script-skinshortcuts.xml"
        self._skin_path = args[1] if len(args) > 1 else ""

        self.changes_saved = False

    def _suffixed_name(self, name: str) -> str:
        """Apply the dialog's suffix; slots let one item hold several widgets (widgetArt.2)."""
        if self.property_suffix:
            return f"{name}{self.property_suffix}"
        return name

    def _get_item_property(self, item: MenuItem, name: str) -> str:
        """Get a property value with suffix applied."""
        suffixed = self._suffixed_name(name)
        return item.properties.get(suffixed, "")

    def _list(self, control_id: int) -> xbmcgui.ControlList:
        """getControl typed as ControlList; Kodi's getControl returns base Control."""
        return self.getControl(control_id)  # type: ignore[return-value]

    def onInit(self):  # noqa: N802
        """Called when dialog is initialized."""
        self._log(f"onInit: shortcuts_path={self.shortcuts_path}, menu_id={self.menu_id}")

        if self.manager is None:
            if self._shared_manager:
                self.manager = self._shared_manager
            else:
                self.manager = MenuManager(self.shortcuts_path)

            menu_ids = self.manager.get_menu_ids()
            self._log(f"Loaded menus: {menu_ids}")

        if self.property_schema is None:
            if self._shared_schema:
                self.property_schema = self._shared_schema
            else:
                schema_path = Path(self.shortcuts_path) / "properties.xml"
                self.property_schema = load_properties(schema_path)

        if not self.icon_sources:
            if self._shared_icon_sources is not None:
                self.icon_sources = self._shared_icon_sources
                self.context_menu = self._shared_context_menu or ContextMenu()
                if self._shared_subdialogs:
                    self._subdialogs = {sd.button_id: sd for sd in self._shared_subdialogs}
            else:
                menus_path = Path(self.shortcuts_path) / "menus.xml"
                menu_config = load_menus(menus_path)
                self.icon_sources = menu_config.icon_sources
                self.context_menu = menu_config.context_menu
                self._subdialogs = {sd.button_id: sd for sd in menu_config.subdialogs}

        if not self.dialog_mode and self.manager:
            menu = self.manager.config.get_menu(self.menu_id)
            if menu and menu.menu_type == "widgets":
                self.dialog_mode = "widgets"


        if self.property_suffix:
            self.setProperty("skinshortcuts-suffix", self.property_suffix)
        if self.dialog_mode:
            self.setProperty("skinshortcuts-dialog", self.dialog_mode)

        # Mirror to Home so visibility checks work when a native dialog takes focus
        if self.dialog_mode:
            home = xbmcgui.Window(10000)
            home.setProperty("skinshortcuts-dialog", self.dialog_mode)
            if self.property_suffix:
                home.setProperty("skinshortcuts-suffix", self.property_suffix)

        self._load_items()
        self._log(f"Loaded {len(self.items)} items for menu '{self.menu_id}'")
        self._display_items()
        self._update_window_properties()

        if self._setfocus:
            try:
                self.setFocusId(self._setfocus)
                self._log(f"Set focus to control {self._setfocus}")
            except RuntimeError:
                pass

    def _log(self, msg: str) -> None:
        """Log debug message."""
        _log.debug(msg)

    def _load_items(self) -> None:
        """Load menu items from manager."""
        if self.manager:
            self.items = self.manager.get_menu_items(self.menu_id)

            if not self.items:
                self._inject_empty_placeholder()

    def _inject_empty_placeholder(self) -> None:
        """Add a placeholder so an empty list still shows something to click."""
        if self.menu_id.startswith("user-"):
            menu_suffix = self.menu_id[5:]
        else:
            menu_suffix = self.menu_id
        placeholder = MenuItem(
            name=f"sub-{menu_suffix[:8]}",
            label="$ADDON[script.skinshortcuts 32129]",
            is_placeholder=True,
        )
        self.items.append(placeholder)

    def _display_items(self) -> None:
        """Display items in the list control. Called once during onInit."""
        self._rebuild_list(focus_index=self._selected_index)
        if self.dialog_mode:
            self._populate_subdialog_list()

    def _populate_subdialog_list(self) -> None:
        """Populate Container 212 with current item for subdialog variable access.

        Separate container so widget settings controls don't fight the parent's 211.
        """
        try:
            subdialog_list = self._list(CONTROL_SUBDIALOG_LIST)
        except RuntimeError:
            self._log("Container 212 not found in skin - subdialog list not populated")
            return

        subdialog_list.reset()

        # Use _selected_index directly - list control may not have updated yet after selectItem()
        item = None
        if self._selected_index is not None and 0 <= self._selected_index < len(self.items):
            item = self.items[self._selected_index]
        else:
            item = self._get_selected_item()
        if item:
            listitem = self._create_listitem(item)
            subdialog_list.addItem(listitem)
            subdialog_list.selectItem(0)
            self._log(f"Populated subdialog list (212) with item: {item.name}")

    def _clear_subdialog_list(self) -> None:
        """Clear Container 212 after subdialog closes."""
        try:
            subdialog_list = self._list(CONTROL_SUBDIALOG_LIST)
            subdialog_list.reset()
        except RuntimeError:
            pass

    def _rebuild_list(self, focus_index: int | None = None) -> None:
        """Rebuild the list control from self.items.

        Structural changes only; a property change wants _refresh_selected_item.
        """
        try:
            list_control = self._list(CONTROL_LIST)
        except RuntimeError:
            return

        list_control.reset()

        # addItem re-sends the whole list on every call
        list_control.addItems([self._create_listitem(item) for item in self.items])

        if focus_index is not None and 0 <= focus_index < len(self.items):
            list_control.selectItem(focus_index)

    def _create_listitem(self, item: MenuItem) -> xbmcgui.ListItem:
        """Create a ListItem from a MenuItem."""
        display_label = resolve_label(item.label)
        # not offscreen: _refresh_selected_item rewrites these in place while bound
        listitem = xbmcgui.ListItem(label=display_label)
        self._populate_listitem(listitem, item)
        return listitem

    def _populate_listitem(self, listitem: xbmcgui.ListItem, item: MenuItem) -> None:
        """Populate a ListItem with all properties from a MenuItem."""
        listitem.setLabel(resolve_label(item.label))
        listitem.setLabel2(item.action or "")
        listitem.setProperty("name", item.name)
        listitem.setProperty("action", item.action or "")
        listitem.setProperty("path", extract_path_from_action(item.action) if item.action else "")
        listitem.setProperty("originalAction", item.original_action or item.action or "")
        listitem.setProperty("skinshortcuts-disabled", "True" if item.disabled else "False")
        listitem.setProperty("skinshortcuts-isRequired", "True" if item.required else "False")
        listitem.setProperty("skinshortcuts-isProtected", "True" if item.protection else "False")

        if item.icon:
            icon = _display_label(item.icon)
            listitem.setArt({"thumb": icon, "icon": icon})

        widget_name = item.properties.get("widget", "")
        has_widget = bool(widget_name or item.properties.get("widgetPath"))
        if has_widget:
            listitem.setProperty("widget", widget_name)
            listitem.setProperty(
                "widgetLabel", _display_label(item.properties.get("widgetLabel", ""))
            )
            listitem.setProperty("widgetPath", item.properties.get("widgetPath", ""))
            listitem.setProperty("widgetType", item.properties.get("widgetType", ""))
            listitem.setProperty("widgetTarget", item.properties.get("widgetTarget", ""))
            listitem.setProperty("widgetSource", item.properties.get("widgetSource", ""))
        else:
            listitem.setProperty("widget", "")
            listitem.setProperty("widgetLabel", "")
            listitem.setProperty("widgetPath", "")
            listitem.setProperty("widgetType", "")
            listitem.setProperty("widgetTarget", "")
            listitem.setProperty("widgetSource", "")

        background_name = item.properties.get("background", "")
        if background_name:
            listitem.setProperty("background", background_name)
            listitem.setProperty(
                "backgroundLabel", _display_label(item.properties.get("backgroundLabel", ""))
            )
            listitem.setProperty("backgroundPath", item.properties.get("backgroundPath", ""))
        else:
            listitem.setProperty("background", "")
            listitem.setProperty("backgroundLabel", "")
            listitem.setProperty("backgroundPath", "")

        effective_props = self._get_effective_properties(item)
        for prop_name, prop_value in effective_props.items():
            if prop_name in (
                "widget",
                "widgetPath",
                "widgetType",
                "widgetTarget",
                "widgetSource",
                "widgetLabel",
                "background",
                "backgroundLabel",
                "backgroundPath",
                "name",
                "label",
                "disabled",
            ):
                continue
            if self._is_widget_dependent(prop_name):
                if "." in prop_name:
                    suffix = "." + prop_name.split(".", 1)[-1]
                    slot_widget = item.properties.get(f"widget{suffix}", "")
                else:
                    slot_widget = has_widget
                if not slot_widget:
                    listitem.setProperty(prop_name, "")
                    listitem.setProperty(f"{prop_name}Label", "")
                    continue
            if prop_name.split(".")[0].endswith("Label"):
                prop_value = _display_label(prop_value)
            listitem.setProperty(prop_name, prop_value)
            resolved_label = self._get_property_label(prop_name, prop_value)
            if resolved_label:
                listitem.setProperty(f"{prop_name}Label", resolved_label)

        if self.manager:
            template = (
                self.manager.config.get_default_menu(item.submenu)
                if item.submenu
                else None
            )
            instance_key = self.manager.submenu_key(self.menu_id, item.name)
            instance = self.manager.config.get_menu(instance_key)
            effective = instance if (instance and instance.items) else template
            if effective and effective.items:
                listitem.setProperty("hasSubmenu", "true")
                listitem.setProperty("submenu", item.submenu or "")

            is_modified = False
            if self.manager:
                is_modified = self.manager.is_item_modified(self.menu_id, item.name)
            listitem.setProperty("isResettable", "true" if is_modified else "")

    def _is_widget_dependent(self, prop_name: str) -> bool:
        """Check if a property depends on a widget being set."""
        if not self.property_schema:
            return False
        widget_requires = ("widget", "widgetPath", "widgetStyle")
        base_name = prop_name.split(".")[0] if "." in prop_name else prop_name
        prop = self.property_schema.properties.get(base_name)
        if prop and prop.requires in widget_requires:
            return True
        for button in self.property_schema.buttons.values():
            if button.property_name == base_name and button.requires in widget_requires:
                return True
        return False

    def _get_selected_listitem(self) -> xbmcgui.ListItem | None:
        """Get the currently selected ListItem from the control."""
        try:
            list_control = self._list(CONTROL_LIST)
            return list_control.getSelectedItem()
        except RuntimeError:
            return None

    def _refresh_selected_item(self) -> None:
        """Refresh the selected item's ListItem from our local item state."""
        index = self._get_selected_index()
        if index < 0 or index >= len(self.items):
            return

        listitem = self._get_selected_listitem()
        if listitem:
            self._populate_listitem(listitem, self.items[index])

        if self.dialog_mode:
            self._populate_subdialog_list()

    def _get_selected_index(self) -> int:
        """Get the currently selected list index."""
        try:
            list_control = self._list(CONTROL_LIST)
            return list_control.getSelectedPosition()
        except RuntimeError:
            return -1

    def _get_selected_item(self) -> MenuItem | None:
        """Get the currently selected MenuItem.

        Subdialog mode reads _selected_index; Container 211 may be focused elsewhere.
        """
        if (
            self.dialog_mode
            and self._selected_index is not None
            and 0 <= self._selected_index < len(self.items)
        ):
            return self.items[self._selected_index]
        index = self._get_selected_index()
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def _get_item_properties(self, item: MenuItem) -> dict[str, str]:
        """Get all properties of an item as a dict for condition evaluation."""
        props = dict(item.properties)
        props["name"] = item.name
        props["label"] = resolve_label(item.label)
        props["disabled"] = "True" if item.disabled else "False"

        return props

    def _get_effective_properties(self, item: MenuItem) -> dict[str, str]:
        """Get item properties with fallbacks applied."""
        props = self._get_item_properties(item)

        if not self.property_schema:
            return props

        for prop_name, fallback in self.property_schema.fallbacks.items():
            effective_prop_name = prop_name
            if self.property_suffix:
                effective_prop_name = f"{prop_name}{self.property_suffix}"

            if effective_prop_name in props and props[effective_prop_name]:
                continue

            for rule in fallback.rules:
                condition = rule.condition
                if condition and self.property_suffix:
                    condition = apply_suffix_transform(condition, self.property_suffix)
                if not condition or evaluate_condition(condition, props):
                    props[effective_prop_name] = rule.value
                    break

        return props

    def _get_property_label(self, prop_name: str, prop_value: str) -> str | None:
        """Get the resolved display label for a property value."""
        if not self.property_schema:
            return None

        prop = self.property_schema.get_property(prop_name)
        if not prop:
            return None

        for opt in prop.options:
            if opt.value == prop_value:
                return resolve_label(opt.label)

        return None

    def _update_deleted_property(self) -> None:
        """Update window property to indicate if deleted items exist for current menu."""
        has_deleted = self.manager.has_removed_items(self.menu_id) if self.manager else False
        self.setProperty("skinshortcuts-hasdeleted", "true" if has_deleted else "")

    def _update_window_properties(self) -> None:
        """Update window properties for skin to show current context."""
        try:
            self.setProperty("menuname", self.menu_id)

            if self.manager:
                menu = self.manager.config.get_menu(self.menu_id)
                if menu:
                    allow = menu.allow
                    self.setProperty("disableWidgets", "true" if not allow.widgets else "")
                    self.setProperty("disableBackgrounds", "true" if not allow.backgrounds else "")
                    self.setProperty("disableSubmenus", "true" if not allow.submenus else "")

                    if menu.menu_type:
                        menu_type = menu.menu_type
                    elif menu.is_submenu:
                        menu_type = "submenu"
                    else:
                        menu_type = ""
                    self.setProperty("skinshortcuts-menutype", menu_type)

            self._update_deleted_property()

        except RuntimeError:
            pass

    def onClick(self, control_id: int):  # noqa: N802
        """Handle control clicks - routes to appropriate handler."""
        if not self.manager:
            return

        if control_id == CONTROL_ADD:
            self._add_item()
        elif control_id == CONTROL_DELETE:
            self._delete_item()
        elif control_id == CONTROL_MOVE_UP:
            self._move_item(-1)
        elif control_id == CONTROL_MOVE_DOWN:
            self._move_item(1)
        elif control_id == CONTROL_SET_LABEL:
            self._set_label()
        elif control_id == CONTROL_SET_ICON:
            self._set_icon()
        elif control_id == CONTROL_SET_ACTION:
            self._set_action()
        elif control_id == CONTROL_TOGGLE_DISABLED:
            self._toggle_disabled()
        elif control_id == CONTROL_CHOOSE_SHORTCUT:
            self._choose_shortcut()
        elif control_id == CONTROL_RESTORE_DELETED:
            self._restore_deleted_item()
        elif control_id == CONTROL_RESET_ITEM:
            self._reset_current_item()
        elif control_id == CONTROL_EDIT_SUBMENU:
            self._edit_submenu()
        elif control_id in self._subdialogs:
            self._spawn_subdialog(self._subdialogs[control_id])
        else:
            self._handle_property_button(control_id)

    def onAction(self, action):  # noqa: N802
        """Handle actions."""
        action_id = action.getId()
        if action_id in ACTION_CANCEL:
            self._log(
                f"Back/Cancel received (action_id={action_id}), menu={self.menu_id}, "
                f"mode={self.dialog_mode}, is_child={self.is_child}"
            )
            self.close()
        elif action_id in ACTION_CONTEXT and self._context_menu_allowed():
            self._show_context_menu()

    def _context_menu_allowed(self) -> bool:
        """Whether the context action opens the menu with the current focus."""
        if not self.context_menu.enabled:
            return False
        if not self.context_menu.enable_on:
            return True
        try:
            return self.getFocusId() in self.context_menu.enable_on
        except RuntimeError:
            return False

    def close(self) -> None:
        """Save changes and close dialog.

        Clears Home skinshortcuts-dialog/suffix properties this dialog set,
        so they don't leak after the dialog closes.
        """
        if self.dialog_mode:
            home = xbmcgui.Window(10000)
            home.clearProperty("skinshortcuts-dialog")
            home.clearProperty("skinshortcuts-suffix")
        if not self.is_child and self.manager and self.manager.has_changes():
            self.manager.save()
            self.changes_saved = True
        xbmcgui.WindowXMLDialog.close(self)

    def _add_item(self) -> None:
        """Add a new item - implemented by ItemsMixin."""
        raise NotImplementedError

    def _delete_item(self) -> None:
        """Delete selected item - implemented by ItemsMixin."""
        raise NotImplementedError

    def _move_item(self, direction: int) -> None:
        """Move item up/down - implemented by ItemsMixin."""
        raise NotImplementedError

    def _set_label(self) -> None:
        """Change item label - implemented by ItemsMixin."""
        raise NotImplementedError

    def _set_icon(self) -> None:
        """Change item icon - implemented by ItemsMixin."""
        raise NotImplementedError

    def _set_action(self) -> None:
        """Change item action - implemented by ItemsMixin."""
        raise NotImplementedError

    def _toggle_disabled(self) -> None:
        """Toggle disabled state - implemented by ItemsMixin."""
        raise NotImplementedError

    def _restore_deleted_item(self) -> None:
        """Restore deleted item - implemented by ItemsMixin."""
        raise NotImplementedError

    def _reset_current_item(self) -> None:
        """Reset item to defaults - implemented by ItemsMixin."""
        raise NotImplementedError

    def _choose_shortcut(self) -> None:
        """Choose shortcut from groupings - implemented by PickersMixin."""
        raise NotImplementedError

    def _handle_property_button(self, button_id: int) -> bool:
        """Handle property button - implemented by PropertiesMixin."""
        raise NotImplementedError

    def _edit_submenu(self) -> None:
        """Edit submenu - implemented by SubdialogsMixin."""
        raise NotImplementedError

    def _spawn_subdialog(self, subdialog: SubDialog) -> None:
        """Spawn subdialog - implemented by SubdialogsMixin."""
        raise NotImplementedError

    def _show_context_menu(self) -> None:
        """Show context menu - implemented by ItemsMixin."""
        raise NotImplementedError
