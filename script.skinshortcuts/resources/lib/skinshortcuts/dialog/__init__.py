"""Management dialog package for skin shortcuts.

This package provides the ManagementDialog class for editing menus,
composed of several mixins for separation of concerns:

- DialogBaseMixin: Core initialization, list management, event routing
- ItemsMixin: Item operations (add, delete, move, label, icon, action)
- PickersMixin: Shortcut and widget picker dialogs
- PropertiesMixin: Property management (widget, background, toggle, options)
- SubdialogsMixin: Subdialog management (submenu editing, onclose handling)

Public API:
- ManagementDialog: The complete dialog class
- show_management_dialog(): Convenience function to show the dialog
- get_shortcuts_path(): Get the current skin's shortcuts folder path
"""

from __future__ import annotations

try:
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .base import (
    ACTION_CANCEL,
    ACTION_CONTEXT,
    CONTROL_ADD,
    CONTROL_CHOOSE_SHORTCUT,
    CONTROL_DELETE,
    CONTROL_EDIT_SUBMENU,
    CONTROL_LIST,
    CONTROL_MOVE_DOWN,
    CONTROL_MOVE_UP,
    CONTROL_RESET_ITEM,
    CONTROL_RESTORE_DELETED,
    CONTROL_SET_ACTION,
    CONTROL_SET_ICON,
    CONTROL_SET_LABEL,
    CONTROL_TOGGLE_DISABLED,
    DialogBaseMixin,
    get_shortcuts_path,
)
from .items import ItemsMixin
from .pickers import PickersMixin
from .properties import PropertiesMixin
from .subdialogs import SubdialogsMixin


class ManagementDialog(
    SubdialogsMixin,
    PropertiesMixin,
    PickersMixin,
    ItemsMixin,
    DialogBaseMixin,
):
    """Dialog for managing menu shortcuts.

    Composes multiple mixins to provide full functionality:
    - DialogBaseMixin: Core initialization, list management, event routing
    - ItemsMixin: Item operations (add, delete, move, label, icon, action)
    - PickersMixin: Shortcut and widget picker dialogs
    - PropertiesMixin: Property management (widget, background, toggle, options)
    - SubdialogsMixin: Subdialog management (submenu editing, onclose handling)

    DialogBaseMixin inherits from xbmcgui.WindowXMLDialog, providing the base.
    """


def show_management_dialog(
    menu_id: str = "mainmenu",
    shortcuts_path: str | None = None,
) -> bool:
    """Show the management dialog.

    Args:
        menu_id: ID of menu to manage
        shortcuts_path: Path to shortcuts folder (auto-detected if None)

    Returns:
        True if changes were saved, False otherwise
    """
    if not IN_KODI:
        return False

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    skin_path = xbmcvfs.translatePath("special://skin/")
    dialog_xml = "script-skinshortcuts.xml"

    dialog = ManagementDialog(
        dialog_xml,
        skin_path,
        "Default",
        menu_id=menu_id,
        shortcuts_path=shortcuts_path,
    )
    dialog.doModal()
    changes_saved = dialog.changes_saved
    del dialog
    return changes_saved


__all__ = [
    "ManagementDialog",
    "show_management_dialog",
    "get_shortcuts_path",
    "CONTROL_LIST",
    "CONTROL_ADD",
    "CONTROL_DELETE",
    "CONTROL_MOVE_UP",
    "CONTROL_MOVE_DOWN",
    "CONTROL_SET_LABEL",
    "CONTROL_SET_ICON",
    "CONTROL_SET_ACTION",
    "CONTROL_RESTORE_DELETED",
    "CONTROL_RESET_ITEM",
    "CONTROL_TOGGLE_DISABLED",
    "CONTROL_CHOOSE_SHORTCUT",
    "CONTROL_EDIT_SUBMENU",
    "ACTION_CANCEL",
    "ACTION_CONTEXT",
]
