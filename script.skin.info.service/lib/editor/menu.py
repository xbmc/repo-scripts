"""Entry point and menu structure for metadata editor."""
from __future__ import annotations

from typing import Any

import xbmc
import xbmcgui

from lib.infrastructure.dialogs import show_notification
from lib.infrastructure.menus import Menu, MenuItem
from lib.kodi.client import log, ADDON
from lib.editor.config import (
    MEDIA_TYPE_FIELDS,
    FieldType,
    get_display_name,
    get_field_def,
    get_fields_for_media_type,
)
from lib.editor.handlers import (
    handle_date,
    handle_duration,
    handle_integer,
    handle_lastplayed,
    handle_list,
    handle_ratings,
    handle_runtime,
    handle_status,
    handle_text,
    handle_uniqueids,
    handle_userrating,
)
from lib.editor.operations import get_item_for_editing, save_field
from lib.editor.utilities import (
    format_duration_for_edit,
    format_runtime_display,
    format_value_for_display,
)


def run_editor(dbid: str | None = None, dbtype: str | None = None) -> None:
    """Main entry point for metadata editor."""
    if not dbid:
        dbid = xbmc.getInfoLabel("ListItem.DBID")
    if not dbtype:
        dbtype = xbmc.getInfoLabel("ListItem.DBType")

    if not dbid or dbid == "-1" or not dbtype:
        show_notification(
            ADDON.getLocalizedString(32258),
            ADDON.getLocalizedString(32259),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    media_type = dbtype.lower()

    if media_type not in MEDIA_TYPE_FIELDS:
        show_notification(
            ADDON.getLocalizedString(32258),
            ADDON.getLocalizedString(32263).format(media_type),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    dbid_int = int(dbid)

    item = get_item_for_editing(dbid_int, media_type)
    if not item:
        show_notification(
            ADDON.getLocalizedString(32258),
            ADDON.getLocalizedString(32262),
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )
        return

    title = item.get("title") or item.get("artist") or "Unknown"
    log("Editor", f"Editing {media_type} '{title}' (dbid={dbid_int})", xbmc.LOGDEBUG)

    _show_main_menu(dbid_int, media_type, item, title)


def _show_main_menu(
    dbid: int, media_type: str, item: dict[str, Any], title: str
) -> None:
    """Show flattened field menu with all editable fields."""
    fields = get_fields_for_media_type(media_type)
    last_selected = 0
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        menu_items = []
        for field in fields:
            field_def = get_field_def(field)
            if not field_def:
                continue

            current = item.get(field_def["get_property"])
            display_name = get_display_name(field_def)
            field_type = field_def["field_type"]

            if field == "runtime":
                value_display = format_runtime_display(current or 0)
            elif field == "duration":
                value_display = format_duration_for_edit(current or 0)
            elif field == "lastplayed":
                value_display = (current or "").split(" ")[0]
            else:
                value_display = format_value_for_display(current, field_type)

            if field_type in (FieldType.RATINGS, FieldType.UNIQUEIDS):
                label = f"{display_name}..."
            else:
                label = f"{display_name}: {value_display}"

            menu_items.append(MenuItem(
                label,
                lambda f=field: _edit_field(dbid, media_type, item, f),
            ))

        menu = Menu(ADDON.getLocalizedString(32560).format(title), menu_items, is_main_menu=True)
        result = menu.show(preselect=last_selected)

        if result is None:
            break

        last_selected = menu._last_selected_idx or 0


# Per-field overrides for INTEGER fields that need a specialized handler.
_INTEGER_FIELD_OVERRIDES = {
    "runtime": lambda dn, cur, _mt, _f: handle_runtime(dn, cur),
    "duration": lambda dn, cur, _mt, _f: handle_duration(dn, cur),
    "year": lambda dn, cur, _mt, _f: handle_integer(dn, cur, validator="year"),
    "top250": lambda dn, cur, _mt, _f: handle_integer(dn, cur, validator="top250"),
}


def _dispatch_integer(display_name: str, current, media_type: str, field: str, _item):
    handler = _INTEGER_FIELD_OVERRIDES.get(field)
    if handler:
        return handler(display_name, current, media_type, field)
    return handle_integer(display_name, current)


_FIELD_TYPE_HANDLERS = {
    FieldType.TEXT:       lambda dn, cur, _mt, _f, _it: handle_text(dn, cur),
    FieldType.TEXT_LONG:  lambda dn, cur, _mt, _f, _it: handle_text(dn, cur),
    FieldType.INTEGER:    _dispatch_integer,
    FieldType.NUMBER:     lambda dn, cur, _mt, _f, _it: handle_integer(dn, cur),
    FieldType.DATE:       lambda dn, cur, _mt, _f, _it: handle_date(dn, cur),
    FieldType.DATETIME:   lambda dn, cur, _mt, _f, _it: handle_lastplayed(dn, cur),
    FieldType.LIST:       lambda dn, cur, mt, f, _it: handle_list(dn, cur, mt, f),
    FieldType.USERRATING: lambda dn, cur, _mt, _f, _it: handle_userrating(dn, cur),
    FieldType.RATINGS:    lambda dn, cur, _mt, _f, _it: handle_ratings(dn, cur),
    FieldType.STATUS:     lambda dn, cur, _mt, _f, _it: handle_status(dn, cur),
    FieldType.UNIQUEIDS:  lambda dn, cur, _mt, _f, it: handle_uniqueids(
        dn, cur, it.get("imdbnumber")),
}


def _edit_field(
    dbid: int, media_type: str, item: dict[str, Any], field: str
) -> bool:
    """Edit a single field. Returns True to keep menu open."""
    field_def = get_field_def(field)
    if not field_def:
        return True

    current = item.get(field_def["get_property"])
    display_name = get_display_name(field_def)
    field_type = field_def["field_type"]

    handler = _FIELD_TYPE_HANDLERS.get(field_type)
    if not handler:
        show_notification(ADDON.getLocalizedString(32258), ADDON.getLocalizedString(32250),
                          xbmcgui.NOTIFICATION_WARNING)
        return True

    new_value, cancelled = handler(display_name, current, media_type, field, item)

    if cancelled:
        return True

    if new_value == current:
        return True

    if save_field(dbid, media_type, field, new_value, item):
        stored = new_value
        if field_type == FieldType.UNIQUEIDS and isinstance(new_value, dict):
            # Nulls tell Kodi to remove
            stored = {k: v for k, v in new_value.items() if v is not None}
        item[field_def["get_property"]] = stored
        # Also update premiered in local item when year changes since Kodi links them
        if field == "year" and isinstance(new_value, int):
            original = item.get("premiered", "")
            if original and len(original) >= 10:
                item["premiered"] = f"{new_value}{original[4:10]}"
            else:
                item["premiered"] = f"{new_value}-01-01"
        show_notification(ADDON.getLocalizedString(32258), f"{display_name} updated",
                          xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin("Container.Refresh")

        from lib.editor.nfo import write_nfo
        write_nfo(media_type, dbid)
    else:
        show_notification(ADDON.getLocalizedString(32258), ADDON.getLocalizedString(32251),
                          xbmcgui.NOTIFICATION_ERROR, 3000)

    return True
