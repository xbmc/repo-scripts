"""View selection dialogs."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import xbmc
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from ..localize import LANGUAGE, resolve_label
from ..log import get_logger

if TYPE_CHECKING:
    from ..models.views import ViewConfig, ViewContent
    from ..userdata import UserData

log = get_logger("ViewDialog")


def show_view_browser(
    config: ViewConfig,
    userdata: UserData,
) -> bool:
    """Show hierarchical view browser for managing all view settings.

    Opens a dialog with:
    - Library > (content types)
    - Plugins > (content types + Add Plugin Override)
    - Reset Library Views
    - Reset Plugin Views

    Args:
        config: View configuration from views.xml
        userdata: User data for reading/writing selections

    Returns:
        True if any changes were made
    """
    if not IN_KODI or not config.content_rules:
        return False

    _set_dialog_property(True)
    try:
        changed = _browse_main_menu(config, userdata)
        return changed
    finally:
        _set_dialog_property(False)


def show_view_picker(
    config: ViewConfig,
    userdata: UserData,
    content: str,
    plugin: str = "",
) -> bool:
    """Show view picker for a specific content type.

    Opens a dialog to select a view for the specified content.

    Args:
        config: View configuration from views.xml
        userdata: User data for reading/writing selections
        content: Content type name (e.g., "movies")
        plugin: Optional plugin ID for plugin-specific override

    Returns:
        True if a change was made
    """
    if not IN_KODI:
        return False

    content_rule = config.get_content(content)
    if not content_rule:
        log.warning(f"Unknown content type: {content}")
        return False

    _set_dialog_property(True)
    try:
        source = plugin if plugin else "library"
        return _pick_view_for_content(config, userdata, content_rule, source)
    finally:
        _set_dialog_property(False)


def _set_dialog_property(active: bool) -> None:
    """Set/clear the SkinShortcuts.ViewDialog window property."""
    if not IN_KODI:
        return
    home = xbmcgui.Window(10000)
    if active:
        home.setProperty("SkinShortcuts.ViewDialog", "true")
    else:
        home.clearProperty("SkinShortcuts.ViewDialog")


def _browse_main_menu(config: ViewConfig, userdata: UserData) -> bool:
    """Show the main browse menu."""
    changed = False

    while True:
        items = [
            xbmcgui.ListItem(f"{xbmc.getLocalizedString(14022)} >"),
            xbmcgui.ListItem(f"{xbmc.getLocalizedString(24001)} >"),
        ]
        items[0].setArt({"icon": "DefaultFolder.png"})
        items[1].setArt({"icon": "DefaultAddonProgram.png"})

        plugin_overrides = _get_all_addon_overrides(userdata)
        if plugin_overrides:
            for plugin_id in sorted(plugin_overrides):
                item = xbmcgui.ListItem(f"{LANGUAGE(32189) % plugin_id} >")
                item.setArt({"icon": "DefaultAddonVideo.png"})
                items.append(item)

        reset_library = xbmcgui.ListItem(LANGUAGE(32164))
        reset_library.setArt({"icon": "DefaultIconWarning.png"})
        items.append(reset_library)

        reset_plugins = xbmcgui.ListItem(LANGUAGE(32165))
        reset_plugins.setArt({"icon": "DefaultIconWarning.png"})
        items.append(reset_plugins)

        selected = xbmcgui.Dialog().select(
            LANGUAGE(32185), items, useDetails=True
        )

        if selected == -1:
            break

        if selected == 0:
            if _browse_source_menu(config, userdata, "library", xbmc.getLocalizedString(14022)):
                changed = True
        elif selected == 1:
            if _browse_plugins_menu(config, userdata):
                changed = True
        elif selected < 2 + len(plugin_overrides):
            plugin_id = sorted(plugin_overrides)[selected - 2]
            if _confirm_reset(LANGUAGE(32198) % plugin_id):
                _clear_plugin_views(userdata, plugin_id)
                changed = True
        elif selected == 2 + len(plugin_overrides):
            if _confirm_reset(LANGUAGE(32187)):
                userdata.views.pop("library", None)
                changed = True
        else:
            if _confirm_reset(LANGUAGE(32188)):
                _clear_all_addon_views(userdata)
                changed = True

    return changed


def _browse_source_menu(
    config: ViewConfig,
    userdata: UserData,
    source: str,
    title: str,
) -> bool:
    """Browse content types for a source (library or plugins)."""
    changed = False

    while True:
        items = []
        for content in config.content_rules:
            current_view = userdata.get_view(source, content.name)

            if source == "library":
                default_id = content.library_default
            else:
                default_id = content.plugin_default or content.library_default

            view_id = current_view or default_id
            view_label = ""
            if view_id:
                view = config.get_view(view_id)
                if view:
                    view_label = resolve_label(view.label)

            item = xbmcgui.ListItem(resolve_label(content.label))
            item.setLabel2(view_label)
            item.setArt({"icon": content.icon or "DefaultFolder.png"})
            items.append(item)

        selected = xbmcgui.Dialog().select(title, items, useDetails=True)

        if selected == -1:
            break

        content = config.content_rules[selected]
        if _pick_view_for_content(config, userdata, content, source):
            changed = True

    return changed


def _browse_plugins_menu(config: ViewConfig, userdata: UserData) -> bool:
    """Browse plugins submenu with add override option."""
    changed = False

    while True:
        items = []

        for content in config.content_rules:
            current_view = userdata.get_view("plugins", content.name)
            default_id = content.plugin_default or content.library_default

            view_id = current_view or default_id
            view_label = ""
            if view_id:
                view = config.get_view(view_id)
                if view:
                    view_label = resolve_label(view.label)

            item = xbmcgui.ListItem(resolve_label(content.label))
            item.setLabel2(view_label)
            item.setArt({"icon": content.icon or "DefaultFolder.png"})
            items.append(item)

        add_override = xbmcgui.ListItem(f"{LANGUAGE(32166)} >")
        add_override.setArt({"icon": "DefaultAddonProgram.png"})
        items.append(add_override)

        selected = xbmcgui.Dialog().select(xbmc.getLocalizedString(24001), items, useDetails=True)

        if selected == -1:
            break

        if selected < len(config.content_rules):
            content = config.content_rules[selected]
            if _pick_view_for_content(config, userdata, content, "plugins"):
                changed = True
        else:
            if _add_plugin_override(config, userdata):
                changed = True

    return changed


def _add_plugin_override(config: ViewConfig, userdata: UserData) -> bool:
    """Add a plugin override by browsing installed addons."""
    addons = _get_video_addons()
    if not addons:
        xbmcgui.Dialog().notification(LANGUAGE(32167), LANGUAGE(32168))
        return False

    items = []
    for addon_id, addon_name in addons:
        item = xbmcgui.ListItem(addon_name)
        item.setArt({"icon": f"special://home/addons/{addon_id}/icon.png"})
        item.setProperty("addon_id", addon_id)
        items.append(item)

    selected = xbmcgui.Dialog().select(LANGUAGE(32169), items, useDetails=True)
    if selected == -1:
        return False

    plugin_id = addons[selected][0]

    content_items = []
    for content in config.content_rules:
        item = xbmcgui.ListItem(resolve_label(content.label))
        item.setArt({"icon": content.icon or "DefaultFolder.png"})
        content_items.append(item)

    content_selected = xbmcgui.Dialog().select(
        LANGUAGE(32186), content_items, useDetails=True
    )
    if content_selected == -1:
        return False

    content = config.content_rules[content_selected]
    return _pick_view_for_content(config, userdata, content, plugin_id)


def _pick_view_for_content(
    config: ViewConfig,
    userdata: UserData,
    content: ViewContent,
    source: str,
) -> bool:
    """Show view picker dialog for a content type.

    Returns True if a selection was made.
    """
    views = config.get_views_for_content(content.name)
    if not views:
        return False

    current_view = userdata.get_view(source, content.name)

    if source == "library":
        default_view = content.library_default
    elif source == "plugins":
        default_view = content.plugin_default or content.library_default
    else:
        generic_view = userdata.get_view("plugins", content.name)
        default_view = generic_view or content.plugin_default or content.library_default

    preselect = -1
    items = []

    for i, view in enumerate(views):
        label = resolve_label(view.label)
        is_current = view.id == current_view
        is_default_fallback = view.id == default_view and preselect == -1
        if is_current or is_default_fallback:
            preselect = i

        item = xbmcgui.ListItem(label)
        if view.id == default_view:
            item.setLabel2(xbmc.getLocalizedString(571))
        icon = view.icon or "DefaultFolder.png"
        item.setArt({"icon": icon, "thumb": icon})
        items.append(item)

    title = LANGUAGE(32199) % resolve_label(content.label)
    selected = xbmcgui.Dialog().select(title, items, useDetails=True, preselect=preselect)

    if selected == -1:
        return False

    view = views[selected]
    userdata.set_view(source, content.name, view.id)
    log.debug(f"Set view for {source}.{content.name} = {view.id}")
    return True


def _get_video_addons() -> list[tuple[str, str]]:
    """Get list of installed video addons."""
    if not IN_KODI:
        return []

    import json

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Addons.GetAddons",
        "params": {
            "type": "xbmc.python.pluginsource",
            "content": "video",
            "properties": ["name"],
        },
    }

    response = xbmc.executeJSONRPC(json.dumps(request))
    data = json.loads(response)

    addons = []
    if "result" in data and "addons" in data["result"]:
        for addon in data["result"]["addons"]:
            addons.append((addon["addonid"], addon["name"]))

    return sorted(addons, key=lambda x: x[1].lower())


def _get_all_addon_overrides(userdata: UserData) -> list[str]:
    """Get list of addon IDs with view overrides."""
    addons = []
    for source in userdata.views:
        if source not in ("library", "plugins"):
            addons.append(source)
    return addons


def _clear_plugin_views(userdata: UserData, plugin_id: str) -> None:
    """Clear all view selections for a specific plugin."""
    userdata.views.pop(plugin_id, None)


def _clear_all_addon_views(userdata: UserData) -> None:
    """Clear generic plugin default and all addon-specific overrides."""
    userdata.views.pop("plugins", None)
    addons = [k for k in userdata.views if k not in ("library", "plugins")]
    for addon_id in addons:
        del userdata.views[addon_id]


def _confirm_reset(message: str) -> bool:
    """Show confirmation dialog for reset action."""
    if not IN_KODI:
        return False
    return xbmcgui.Dialog().yesno(LANGUAGE(32170), message)
