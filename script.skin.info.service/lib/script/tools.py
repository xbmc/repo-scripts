"""Tools main menu - unified entry for artwork, texture, ratings, IDs, and Top 250 workflows."""
from __future__ import annotations

import xbmcgui
from lib.infrastructure.menus import Menu, MenuItem
from lib.kodi.client import ADDON
_HOME = xbmcgui.Window(10000)


def _lazy_run_ratings_menu() -> None:
    from lib.rating.menu import run_ratings_menu
    run_ratings_menu()


def _lazy_run_artwork_manager() -> None:
    from lib.artwork.manager import run_artwork_manager
    run_artwork_manager()


def _lazy_run_texture_maintenance() -> None:
    from lib.texture.menu import run_texture_maintenance
    run_texture_maintenance()


def _lazy_run_download_menu() -> None:
    from lib.download.menu import run_download_menu
    run_download_menu()


def _lazy_run_scanner() -> None:
    from lib.artwork.animated import run_scanner
    run_scanner()


def _lazy_run_fix_library_ids() -> None:
    from lib.rating.ids import run_fix_library_ids
    run_fix_library_ids()


def _lazy_run_top250_update() -> None:
    from lib.script.top250 import run_top250_update
    run_top250_update()


def run_tools() -> None:
    """Show the main Tools menu and dispatch to the selected tool."""
    from lib.infrastructure import tasks as task_manager

    task_manager.cleanup_stale_tasks()

    menu = Menu(ADDON.getLocalizedString(32530), [
        MenuItem(ADDON.getLocalizedString(32300), _lazy_run_ratings_menu, loop=True),
        MenuItem(ADDON.getLocalizedString(32273), _lazy_run_artwork_manager, loop=True),
        MenuItem(ADDON.getLocalizedString(32082), _lazy_run_texture_maintenance, loop=True),
        MenuItem(ADDON.getLocalizedString(32522), _lazy_run_download_menu, loop=True),
        MenuItem(ADDON.getLocalizedString(32192), _lazy_run_scanner, loop=True),
        MenuItem(ADDON.getLocalizedString(32532), _lazy_run_fix_library_ids, loop=True),
        MenuItem(ADDON.getLocalizedString(32600), _lazy_run_top250_update, loop=True),
    ], is_main_menu=True)

    _HOME.setProperty("SkinInfo.ToolsMenuActive", "true")
    try:
        menu.show()
    finally:
        _HOME.clearProperty("SkinInfo.ToolsMenuActive")
