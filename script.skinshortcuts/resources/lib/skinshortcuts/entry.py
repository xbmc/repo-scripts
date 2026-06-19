"""Entry point for Skin Shortcuts."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs

try:
    import xbmc
    import xbmcgui
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .config import SkinConfig
from .constants import INCLUDES_FILE, MENUS_FILE, VIEWS_FILE, get_shortcuts_path
from .hashing import generate_config_hashes, hash_file, needs_rebuild, write_hashes
from .localize import LANGUAGE
from .log import get_logger
from .userdata import get_userdata_path

log = get_logger("Entry")


def get_output_paths() -> list[str]:
    """Get paths for includes.xml output by parsing skin's addon.xml."""
    if not IN_KODI:
        return []

    addon_xml_path = xbmcvfs.translatePath("special://skin/addon.xml")
    if not xbmcvfs.exists(addon_xml_path):
        log.warning("Could not find skin addon.xml")
        return []

    try:
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()

        paths = []
        for ext in root.findall("extension"):
            if ext.get("point") == "xbmc.gui.skin":
                for res in ext.findall("res"):
                    folder = res.get("folder")
                    if folder:
                        path = xbmcvfs.translatePath(f"special://skin/{folder}/")
                        if xbmcvfs.exists(path):
                            paths.append(path)
                break

        return paths
    except ET.ParseError as e:
        log.error(f"Error parsing addon.xml: {e}")
        return []


def _unsupported_marker() -> Path:
    """Per-skin marker; present means the user chose to ignore the unsupported-skin warning."""
    data = xbmcvfs.translatePath("special://profile/addon_data/script.skinshortcuts/")
    return Path(data) / f"{xbmc.getSkinDir()}.unsupported-ack"


def _warn_unsupported(marker: Path) -> None:
    """Modal once per session: switch skins, ignore (marks the skin so it never warns again), or cancel."""
    win = xbmcgui.Window(10000)
    if win.getProperty("skinshortcuts-unsupported-warned"):
        return
    win.setProperty("skinshortcuts-unsupported-warned", "1")
    choice = xbmcgui.Dialog().yesnocustom(
        "Skin Shortcuts", LANGUAGE(32200),
        customlabel=LANGUAGE(32202), nolabel=xbmc.getLocalizedString(222), yeslabel=LANGUAGE(32201),
    )
    if choice == 1:
        xbmc.executebuiltin("ActivateWindow(Settings)")
    elif choice == 2:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()


def _skin_supported(shortcuts_path: str, *, menus_only: bool = False) -> bool:
    """True if the skin has v3 config; otherwise warn (unless ignored) and return False.

    Clears a stale ignore marker once the skin is supported.
    menus_only: manage edits menus only; views.xml is a separate runscript.
    """
    path = Path(shortcuts_path)
    marker = _unsupported_marker()
    if (path / MENUS_FILE).exists() or (not menus_only and (path / VIEWS_FILE).exists()):
        marker.unlink(missing_ok=True)
        return True
    if not marker.exists():
        _warn_unsupported(marker)
    return False


def build_includes(
    shortcuts_path: str | None = None,
    output_path: str | None = None,
    force: bool = False,
) -> bool:
    """Build includes.xml from skin config files.

    Args:
        shortcuts_path: Path to shortcuts folder (default: special://skin/shortcuts/)
        output_path: Path to write includes.xml (default: auto-detect from addon.xml)
        force: Force rebuild even if hashes match

    Returns:
        True if built successfully, False otherwise
    """
    log.debug(f"build_includes called: path={shortcuts_path}, output={output_path}, force={force}")

    home = xbmcgui.Window(10000) if IN_KODI else None
    if home and home.getProperty("skinshortcuts-isbuilding") == "True":
        log.debug("Build already in progress, skipping")
        return False

    if home:
        home.setProperty("skinshortcuts-isbuilding", "True")

    try:
        if shortcuts_path is None:
            shortcuts_path = get_shortcuts_path()
            log.debug(f"Auto-detected shortcuts path: {shortcuts_path}")

        if not shortcuts_path:
            log.error("Could not determine skin shortcuts path")
            return False

        if not _skin_supported(shortcuts_path):
            log.error(f"No menus.xml or views.xml found in {shortcuts_path}")
            return False

        if output_path:
            output_paths = [output_path]
        else:
            output_paths = get_output_paths()

        if not force and not needs_rebuild(shortcuts_path, output_paths):
            log.debug("Menu is up to date, skipping rebuild")
            return False

        log.debug(f"Loading config from: {shortcuts_path}")

        config = SkinConfig.load(shortcuts_path)
        log.info(
            f"Loaded {len(config.menus)} menus, "
            f"{len(config.widgets)} widgets, {len(config.backgrounds)} backgrounds"
        )
        for menu in config.menus:
            log.debug(
                f"Loaded {len(menu.items)} items for menu '{menu.name}': "
                f"{[item.name for item in menu.items]}"
            )

        if not config.menus and not config.view_config.content_rules:
            log.error("No menus or view rules found in config")
            return False

        if not output_paths:
            log.error("Could not determine output paths")
            return False

        for out_path in output_paths:
            output_file = Path(out_path) / INCLUDES_FILE
            config.build_includes(str(output_file))
            log.info(f"Generated: {output_file}")

        hashes = generate_config_hashes(shortcuts_path)

        for out_path in output_paths:
            output_file = Path(out_path) / INCLUDES_FILE
            includes_hash = hash_file(output_file)
            if includes_hash:
                hashes[f"includes:{out_path}"] = includes_hash
                log.debug(f"Stored includes hash for {out_path}")

        write_hashes(hashes)
        log.debug("Saved config hashes")

        if IN_KODI:
            xbmc.executebuiltin("ReloadSkin()")

        return True

    except Exception as e:
        log.error(f"Error building includes: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

    finally:
        if home:
            home.clearProperty("skinshortcuts-isbuilding")


def clear_custom_widget(
    menu: str,
    item: str,
    suffix: str = "",
    property_name: str = "",
    shortcuts_path: str | None = None,
) -> bool:
    """Clear a custom widget menu and optionally reset related properties.

    Args:
        menu: Parent menu ID (e.g., "mainmenu")
        item: Item ID to clear custom widget from (e.g., "movies")
        suffix: Widget slot suffix (e.g., ".2" for second slot)
        property_name: Optional property prefix to clear (e.g., "widget")
        shortcuts_path: Path to shortcuts folder

    Returns:
        True if cleared successfully
    """
    if not menu or not item:
        log.warning("clear_custom_widget: menu and item are required")
        return False

    log.debug(f"Clearing custom widget: menu={menu}, item={item}, suffix={suffix}")

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    try:
        from .manager import MenuManager

        manager = MenuManager(shortcuts_path)

        manager.clear_custom_widget(menu, item, suffix)

        if property_name:
            working_item = manager._get_working_item(menu, item)
            if working_item:
                prop_suffix = suffix or ""
                props_to_clear = [
                    f"{property_name}{prop_suffix}",
                    f"{property_name}Name{prop_suffix}",
                    f"{property_name}Path{prop_suffix}",
                    f"{property_name}Type{prop_suffix}",
                    f"{property_name}Target{prop_suffix}",
                    f"{property_name}Label{prop_suffix}",
                ]
                for prop in props_to_clear:
                    if prop in working_item.properties:
                        del working_item.properties[prop]
                manager._changed = True
                log.debug(f"Cleared {property_name} properties on item: {item}")

        if manager.has_changes():
            manager.save()
            log.debug("Saved changes after clearing")
            build_includes(shortcuts_path, force=True)

        return True

    except Exception as e:
        log.error(f"Error clearing custom widget: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


def reset_all_menus(shortcuts_path: str | None = None) -> bool:
    """Reset all menus to skin defaults by deleting skin's userdata.

    Args:
        shortcuts_path: Path to shortcuts folder (for rebuild after reset)

    Returns:
        True if reset successfully
    """
    if not IN_KODI:
        return False

    import xbmcgui

    if not xbmcgui.Dialog().yesno(
        xbmc.getLocalizedString(186),  # "Reset"
        LANGUAGE(32191),
    ):
        return False

    userdata_path = Path(get_userdata_path())
    if userdata_path.exists():
        try:
            userdata_path.unlink()
            log.info(f"Deleted userdata: {userdata_path}")
        except OSError as e:
            log.error(f"Error deleting userdata: {e}")
            return False
    else:
        log.debug("No userdata to reset")

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    build_includes(shortcuts_path, force=True)
    return True


def view_select(
    content: str = "",
    plugin: str = "",
    shortcuts_path: str | None = None,
) -> bool:
    """Show view selection dialog.

    Args:
        content: Optional content type (e.g., "movies") for direct picker
        plugin: Optional plugin ID for plugin-specific override
        shortcuts_path: Path to shortcuts folder

    Returns:
        True if changes were made
    """
    if not IN_KODI:
        return False

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    from .config import SkinConfig
    from .dialog.views import show_view_browser, show_view_picker
    from .userdata import load_userdata, save_userdata

    config = SkinConfig.load(shortcuts_path)
    userdata = load_userdata()

    if content:
        changed = show_view_picker(config.view_config, userdata, content, plugin)
    else:
        changed = show_view_browser(config.view_config, userdata)

    if changed:
        save_userdata(userdata)
        build_includes(shortcuts_path, force=True)

    return changed


def reset_views(shortcuts_path: str | None = None) -> bool:
    """Reset all view selections to defaults.

    Args:
        shortcuts_path: Path to shortcuts folder (for rebuild after reset)

    Returns:
        True if reset successfully
    """
    if not IN_KODI:
        return False

    import xbmcgui

    if not xbmcgui.Dialog().yesno(
        xbmc.getLocalizedString(186),  # "Reset"
        LANGUAGE(32192),
    ):
        return False

    from .userdata import load_userdata, save_userdata

    userdata = load_userdata()
    userdata.clear_all_views()
    save_userdata(userdata)

    log.info("Reset all view selections")

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    build_includes(shortcuts_path, force=True)
    return True


def reset_menus(shortcuts_path: str | None = None) -> bool:
    """Reset all menu selections to defaults (keeps view selections).

    Args:
        shortcuts_path: Path to shortcuts folder (for rebuild after reset)

    Returns:
        True if reset successfully
    """
    if not IN_KODI:
        return False

    import xbmcgui

    if not xbmcgui.Dialog().yesno(
        xbmc.getLocalizedString(186),  # "Reset"
        LANGUAGE(32193),
    ):
        return False

    from .userdata import load_userdata, save_userdata

    userdata = load_userdata()
    userdata.menus.clear()
    save_userdata(userdata)

    log.info("Reset all menus (views preserved)")

    if shortcuts_path is None:
        shortcuts_path = get_shortcuts_path()

    build_includes(shortcuts_path, force=True)
    return True


def main() -> None:
    """Main entry point for RunScript."""
    log.info("Skin Shortcuts started")

    args: dict[str, str] = {}
    prop_names: list[str] = []
    prop_values: list[str] = []

    def _store(key: str, value: str) -> None:
        # prop/value are repeatable and pair by order across the arg list
        if key == "prop":
            prop_names.append(value)
        elif key == "value":
            prop_values.append(value)
        else:
            args[key] = value

    if len(sys.argv) > 1:
        if "&" in sys.argv[1] or len(sys.argv) == 2:
            query = sys.argv[1].lstrip("?")
            for k, values in parse_qs(query).items():
                if k in ("prop", "value"):
                    for v in values:
                        _store(k, v)
                else:
                    _store(k, values[0])
        else:
            for arg in sys.argv[1:]:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    _store(key, value)

    # Pair props with values by position; unpaired prop defaults to "true" (boolean flag)
    window_props = {
        name: prop_values[i] if i < len(prop_values) else "true"
        for i, name in enumerate(prop_names)
    }
    home = xbmcgui.Window(10000) if IN_KODI and window_props else None
    if home is not None:
        for name, value in window_props.items():
            home.setProperty(name, value)

    try:
        _dispatch(args)
    finally:
        if home is not None:
            for name in window_props:
                home.clearProperty(name)


def _dispatch(args: dict[str, str]) -> None:
    action = args.get("type", "buildxml")

    if action == "buildxml":
        shortcuts_path = args.get("path")
        output_path = args.get("output")
        force = args.get("force", "").lower() == "true"
        build_includes(shortcuts_path, output_path, force)
    elif action == "manage":
        shortcuts_path = args.get("path") or get_shortcuts_path()
        if not _skin_supported(shortcuts_path, menus_only=True):
            return

        from .dialog import show_management_dialog

        menu_id = args.get("menu", "mainmenu")
        log.debug(f"Opening management dialog: menu_id={menu_id}, path={shortcuts_path}")
        changes_saved = False
        try:
            changes_saved = show_management_dialog(menu_id=menu_id, shortcuts_path=shortcuts_path)
        except Exception as e:
            log.error(f"Error in management dialog: {e}")
            import traceback
            log.error(traceback.format_exc())
        log.debug(f"Dialog returned changes_saved={changes_saved}")
        if changes_saved:
            log.debug("Changes saved, rebuilding includes")
            result = build_includes(shortcuts_path, force=True)
            log.debug(f"build_includes returned: {result}")
        else:
            log.debug("No changes saved, skipping rebuild")
    elif action == "resetall":
        reset_all_menus(args.get("path"))
    elif action == "resetmenus":
        reset_menus(args.get("path"))
    elif action == "resetviews":
        reset_views(args.get("path"))
    elif action == "viewselect":
        view_select(
            content=args.get("content", ""),
            plugin=args.get("plugin", ""),
            shortcuts_path=args.get("path"),
        )
    elif action == "reset":
        menu = args.get("menu", "")
        if menu:
            import xbmcgui
            include_subs = args.get("submenus", "").lower() == "true"
            prompt_msg = (
                LANGUAGE(32194) % menu
                if include_subs
                else LANGUAGE(32195) % menu
            )
            if xbmcgui.Dialog().yesno(xbmc.getLocalizedString(186), prompt_msg):
                from .manager import MenuManager
                shortcuts_path = args.get("path") or get_shortcuts_path()
                manager = MenuManager(shortcuts_path)
                if include_subs:
                    manager.reset_menu_tree(menu)
                else:
                    manager.reset_menu(menu)
                manager.save()
                build_includes(shortcuts_path, force=True)
    elif action == "resetsubmenus":
        import xbmcgui
        if xbmcgui.Dialog().yesno(
            xbmc.getLocalizedString(186),
            LANGUAGE(32196),
        ):
            from .manager import MenuManager
            shortcuts_path = args.get("path") or get_shortcuts_path()
            manager = MenuManager(shortcuts_path)
            manager.reset_all_submenus()
            manager.save()
            build_includes(shortcuts_path, force=True)
    elif action == "clear":
        clear_custom_widget(
            menu=args.get("menu", ""),
            item=args.get("item", ""),
            suffix=args.get("suffix", ""),
            property_name=args.get("property", ""),
            shortcuts_path=args.get("path"),
        )
    elif action == "skinstring":
        from .skinstring import pick_widget_skinstring

        shortcuts_path = args.get("path") or get_shortcuts_path()
        pick_widget_skinstring(shortcuts_path, args)
    else:
        log.warning(f"Unknown action: {action}")


if __name__ == "__main__":
    main()
