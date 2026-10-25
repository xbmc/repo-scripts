"""Core dialog class with initialization and event handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..constants import extract_path_from_action, get_shortcuts_path
from ..conditions import evaluate_condition, suffix_condition
from ..loaders.menu import load_menus
from ..loaders.property import load_properties
from ..localize import resolve_label
from ..log import get_logger
from ..manager import MenuManager
from ..models.menu import ContextMenu, MenuItem
from ..models.property import PropertySchema

_log = get_logger("Dialog")

if TYPE_CHECKING:
    from ..models.menu import IconSource, SubDialog

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
    """The display label for an emitted $LOCALIZE value; user text passes through."""
    return resolve_label(value) if value.startswith("$") else value


@dataclass
class _ListItemValues:
    """Labels, icon and properties a ListItem shows."""

    label: str
    label2: str
    icon: str = ""
    properties: dict[str, str] = field(default_factory=dict)


def _create_listitem(values: _ListItemValues) -> xbmcgui.ListItem:
    """Create a ListItem with the labels, icon and properties set."""
    # offscreen setters skip the GUI lock; a row in the list is replaced, never written
    listitem = xbmcgui.ListItem(label=values.label, label2=values.label2, offscreen=True)
    if values.icon:
        listitem.setArt({"thumb": values.icon, "icon": values.icon})
    for name, value in values.properties.items():
        if value:
            listitem.setProperty(name, value)
    return listitem


class DialogBaseMixin(xbmcgui.WindowXMLDialog):
    """Core dialog functionality: initialization, list management, event routing."""


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
        """Read dialog state; a child reuses the parent's shared objects."""
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
        """Apply the dialog's suffix; slots let one item hold several widgets."""
        if self.property_suffix:
            return f"{name}{self.property_suffix}"
        return name

    def _get_item_property(self, item: MenuItem, name: str) -> str:
        """Get a property value with suffix applied."""
        suffixed = self._suffixed_name(name)
        return item.properties.get(suffixed, "")

    def _list(self, control_id: int) -> xbmcgui.ControlList:
        """The list control, typed as ControlList since Kodi's getControl returns base Control."""
        return self.getControl(control_id)  # type: ignore[return-value]

    def onInit(self):  # noqa: N802
        """Load config and items, then display the list and set the window properties."""
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
            menu = self.manager.working.get(self.menu_id)
            if menu and menu.menu_type == "widgets":
                self.dialog_mode = "widgets"


        if self.property_suffix:
            self.setProperty("skinshortcuts-suffix", self.property_suffix)
        if self.dialog_mode:
            self.setProperty("skinshortcuts-dialog", self.dialog_mode)

        self._mirror_to_home()

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

    def _mirror_to_home(self) -> None:
        """Mirror the dialog mode and suffix to Home, for a native dialog over this one."""
        home = xbmcgui.Window(10000)
        for key, value in (
            ("skinshortcuts-dialog", self.dialog_mode),
            ("skinshortcuts-suffix", self.property_suffix),
        ):
            if value:
                home.setProperty(key, value)
            else:
                home.clearProperty(key)

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
        """Inject a placeholder so an empty list still shows something to click."""
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
        """Display items in the list control, plus the edited item in 212 for a subdialog."""
        self._rebuild_list(focus_index=self._selected_index)

    def _populate_subdialog_list(self, index: int) -> None:
        """Populate 212 with the edited item, else with the row 211 selects."""
        try:
            subdialog_list = self._list(CONTROL_SUBDIALOG_LIST)
        except RuntimeError:
            self._log("Container 212 not found in skin - subdialog list not populated")
            return

        if self._selected_index is not None and 0 <= self._selected_index < len(self.items):
            item = self.items[self._selected_index]
        elif 0 <= index < len(self.items):
            item = self.items[index]
        else:
            return

        stale = subdialog_list.size()
        subdialog_list.addItem(_create_listitem(self._listitem_values(item)))
        # add before remove; an empty 212 hides the controls reading it and drops their focus
        for _ in range(stale):
            subdialog_list.removeItem(0)
        subdialog_list.selectItem(0)
        self._log(f"Populated subdialog list (212) with item: {item.name}")

    def _rebuild_list(self, focus_index: int | None = None) -> None:
        """Rebuild the list from self.items on the given row or row 0, plus 212 in a subdialog."""
        try:
            list_control = self._list(CONTROL_LIST)
        except RuntimeError:
            return

        # build first; list shows empty from reset() until addItems()
        listitems: list[str | xbmcgui.ListItem] = [
            _create_listitem(self._listitem_values(item)) for item in self.items
        ]

        list_control.reset()
        list_control.addItems(listitems)

        if focus_index is not None and 0 <= focus_index < len(self.items):
            list_control.selectItem(focus_index)
        else:
            focus_index = 0
        if self.dialog_mode:
            self._populate_subdialog_list(focus_index)

    def _listitem_values(self, item: MenuItem) -> _ListItemValues:
        """Everything a ListItem shows for a MenuItem."""
        props: dict[str, str] = {}

        def put(name: str, value: str) -> None:
            props[name.lower()] = value

        put("name", item.name)
        put("action", item.action or "")
        put("path", extract_path_from_action(item.action) if item.action else "")
        put("originalAction", item.original_action or item.action or "")
        put("skinshortcuts-disabled", "True" if item.disabled else "False")
        put("skinshortcuts-isRequired", "True" if item.required else "False")
        put("skinshortcuts-isProtected", "True" if item.protection else "False")

        widget_name = item.properties.get("widget", "")
        has_widget = bool(widget_name or item.properties.get("widgetPath"))
        if has_widget:
            put("widget", widget_name)
            put("widgetLabel", _display_label(item.properties.get("widgetLabel", "")))
            put("widgetPath", item.properties.get("widgetPath", ""))
            put("widgetType", item.properties.get("widgetType", ""))
            put("widgetTarget", item.properties.get("widgetTarget", ""))
            put("widgetSource", item.properties.get("widgetSource", ""))
        else:
            put("widget", "")
            put("widgetLabel", "")
            put("widgetPath", "")
            put("widgetType", "")
            put("widgetTarget", "")
            put("widgetSource", "")

        background_name = item.properties.get("background", "")
        if background_name:
            put("background", background_name)
            put("backgroundLabel", _display_label(item.properties.get("backgroundLabel", "")))
            put("backgroundPath", item.properties.get("backgroundPath", ""))
        else:
            put("background", "")
            put("backgroundLabel", "")
            put("backgroundPath", "")

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
                    put(prop_name, "")
                    put(f"{prop_name}Label", "")
                    continue
            if prop_name.split(".")[0].endswith("Label"):
                prop_value = _display_label(prop_value)
            put(prop_name, prop_value)
            resolved_label = self._get_property_label(prop_name, prop_value)
            if resolved_label:
                put(f"{prop_name}Label", resolved_label)

        if self.manager:
            template = (
                self.manager.config.get_default_menu(item.submenu)
                if item.submenu
                else None
            )
            instance = self.manager.working.get(self.manager.submenu_key(self.menu_id, item.name))
            effective = instance if instance is not None else template
            if effective and any(not entry.is_placeholder for entry in effective.items):
                put("hasSubmenu", "true")
                put("submenu", item.submenu or "")

            is_modified = self.manager.is_item_modified(self.menu_id, item.name)
            put("isResettable", "true" if is_modified else "")

        return _ListItemValues(
            label=resolve_label(item.label),
            label2=item.action or "",
            icon=_display_label(item.icon) if item.icon else "",
            properties=props,
        )

    def _is_widget_dependent(self, prop_name: str) -> bool:
        """Whether a property depends on a widget being set."""
        if not self.property_schema:
            return False
        widget_requires = ("widget", "widgetPath", "widgetStyle")
        base_name = prop_name.split(".")[0] if "." in prop_name else prop_name
        prop = self.property_schema.get_property(base_name)
        if prop and prop.requires in widget_requires:
            return True
        for button in self.property_schema.buttons.values():
            if button.property_name == base_name and button.requires in widget_requires:
                return True
        return False

    def _refresh_selected_item(self) -> None:
        """Refresh the list on the selected item, or a subdialog's edited item plus 212."""
        if self.dialog_mode and self._selected_index is not None:
            index = self._selected_index
        else:
            index = self._get_selected_index()
        if index < 0 or index >= len(self.items):
            return

        self._rebuild_list(focus_index=index)

    def _get_selected_index(self) -> int:
        """Get the currently selected list index."""
        try:
            list_control = self._list(CONTROL_LIST)
            return list_control.getSelectedPosition()
        except RuntimeError:
            return -1

    def _get_selected_item(self) -> MenuItem | None:
        """Get the currently selected MenuItem; a subdialog trusts _selected_index over 211."""
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
                    condition = suffix_condition(condition, self.property_suffix)
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
                menu = self.manager.working.get(self.menu_id)
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
        """Handle a cancel action by closing, or a context action by opening the menu."""
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
        """Close the dialog, saving any changes and clearing the Home properties set in onInit."""
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
        """Set item label - implemented by ItemsMixin."""
        raise NotImplementedError

    def _set_icon(self) -> None:
        """Set item icon - implemented by ItemsMixin."""
        raise NotImplementedError

    def _set_action(self) -> None:
        """Set item action - implemented by ItemsMixin."""
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
