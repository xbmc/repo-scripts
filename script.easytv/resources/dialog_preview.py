#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialog Preview Script — quickly cycle through all custom dialogs.

Usage from Kodi:
    RunScript(script.easytv,dialog_preview)
    RunScript(script.easytv,dialog_preview,script.easytv.kids)

Or from the Kodi debug console / JSON-RPC:
    {"jsonrpc":"2.0","method":"Addons.ExecuteAddon",
     "params":{"addonid":"script.easytv","params":["dialog_preview"]},"id":1}

The optional third argument overrides the addon ID, so dialogs use
that addon's name, theme, and skin path (useful for testing clones).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union, cast

import xbmcgui
import xbmcaddon

dialog = xbmcgui.Dialog()

# Resolved at init() time — overridable via Main(override_addon_id)
addon_id = ""
addon_name = ""
script_path = ""
_notify_title = ""

# Module-level caches so "All Dialogs" doesn't re-query
_cached_shows: Optional[List[Tuple[str, int, str]]] = None
_cached_browse_data: Optional[List[list]] = None


def _fetch_all_shows() -> List[Tuple[str, int, str]]:
    """Fetch all TV shows with art for the show selector.

    Returns cached result on subsequent calls.
    Each tuple is (show_name, show_id, thumbnail).
    """
    global _cached_shows
    if _cached_shows is not None:
        return _cached_shows

    from resources.lib.utils import json_query
    from resources.lib.data.queries import get_all_shows_query, build_shows_art_query

    # Get all shows
    result = json_query(get_all_shows_query())
    shows = result.get("tvshows", [])

    # Get art for all shows
    art_result = json_query(build_shows_art_query())
    art_shows = art_result.get("tvshows", [])
    art_map: Dict[int, str] = {}
    for s in art_shows:
        sid = s.get("tvshowid", 0)
        art = s.get("art", {})
        if isinstance(art, dict):
            art_map[sid] = art.get("poster", "")

    # Build tuples
    all_shows: List[Tuple[str, int, str]] = []
    for show in shows:
        show_id = show.get("tvshowid", 0)
        title = show.get("title", "")
        thumbnail = art_map.get(show_id, "")
        all_shows.append((title, show_id, thumbnail))

    all_shows.sort(key=lambda x: x[0].lower())
    _cached_shows = all_shows
    return all_shows


def _fetch_browse_data() -> Optional[List[list]]:
    """Fetch browse data using the same path as the real browse mode.

    Returns cached result on subsequent calls.
    Returns None if the service is not running or has no show data.
    Each entry is [lastplayed_timestamp, showid, episodeid].
    """
    global _cached_browse_data
    if _cached_browse_data is not None:
        return _cached_browse_data

    from resources.lib.data.shows import fetch_unwatched_shows

    try:
        data = fetch_unwatched_shows(sort_by=1, sort_reverse=False, language='English')
    except SystemExit:
        return None

    if not data:
        return None

    _cached_browse_data = data
    return data


def _get_show_poster() -> str:
    """Find a show poster from window properties for preview dialogs."""
    data = _fetch_browse_data()
    if not data:
        return ""

    from resources.lib.constants import KODI_HOME_WINDOW_ID
    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)

    for show in data:
        show_id = show[1]
        poster = window.getProperty("EasyTV.%s.Art(tvshow.poster)" % show_id)
        if poster:
            return poster
    return ""


def preview_confirm() -> None:
    """Show the themed ConfirmDialog."""
    from resources.lib.ui.dialogs import show_confirm
    result = show_confirm(
        "Confirm Dialog Preview",
        "This is a test message.\nDo you want to continue?",
        yes_label="Accept",
        no_label="Decline",
        addon_id=addon_id,
    )
    dialog.notification(_notify_title, "Confirm result: %s" % result)


def preview_select() -> None:
    """Show the themed SelectDialog."""
    from resources.lib.ui.dialogs import show_select
    items = [
        "First Option",
        "Second Option",
        "Third Option",
        "Fourth Option",
        "Fifth Option",
        "Sixth Option",
        "Seventh Option",
        "Eighth Option",
    ]
    result = show_select(
        "Select Dialog Preview", items,
        addon_id=addon_id,
    )
    dialog.notification(_notify_title, "Selected: %s" % result)


def preview_show_selector() -> None:
    """Show the ShowSelectorDialog with real show data."""
    all_shows = _fetch_all_shows()
    if not all_shows:
        dialog.ok(_notify_title,
                  "No TV shows found in the library.\n"
                  "Show selector preview requires a populated TV library.")
        return

    from resources.lib.ui.dialogs import ShowSelectorDialog

    dlg = ShowSelectorDialog(
        'script-easytv-showselector.xml', script_path, 'Default',
        heading="Show Selector Preview",
        all_shows_data=all_shows,
        current_list=[all_shows[0][1]] if all_shows else [],
        addon_id=addon_id,
    )
    dlg.doModal()
    if dlg.saved:
        dialog.notification(_notify_title,
                            "Saved: %d shows" % len(dlg.selected_ids))
    else:
        dialog.notification(_notify_title, "Show selector: cancelled")
    del dlg


def preview_browse() -> None:
    """Show the BrowseWindow — lets user pick which view style to preview."""
    data = _fetch_browse_data()
    if not data:
        dialog.ok(_notify_title,
                  "No show data available.\n"
                  "The EasyTV service must be running with tracked shows.")
        return

    from resources.lib.ui.browse_window import (
        BrowseWindow, BrowseWindowConfig, get_skin_xml_file,
    )

    view_names = [
        "Card List",
        "Posters",
        "Big Screen",
        "Split View",
        "Showcase",
    ]

    choice = dialog.select("Browse View Style",
                           cast(List[Union[str, xbmcgui.ListItem]], view_names))
    if choice < 0:
        return

    # Fetch show art (posters/fanart) into window properties if not yet cached
    from resources.lib.playback.browse_mode import _fetch_show_art
    from resources.lib.utils import get_logger
    _fetch_show_art(get_logger('browse'))

    addon = xbmcaddon.Addon(addon_id)
    theme_index = int(addon.getSetting('theme') or '0')

    skin_xml = get_skin_xml_file(choice)
    config = BrowseWindowConfig(skin=choice)

    bw = BrowseWindow(
        skin_xml, script_path, 'Default',
        data=data,
        config=config,
        script_path=script_path,
    )
    bw.set_preview_mode(theme_index)
    bw.doModal()
    if bw.play_requested:
        dialog.notification(_notify_title, "Browse: play requested")
    else:
        dialog.notification(_notify_title, "Browse: closed")
    del bw


def preview_context_menu() -> None:
    """Show the ContextMenuWindow."""
    from resources.lib.ui.context_menu import ContextMenuWindow

    ctx = ContextMenuWindow(
        'script-easytv-contextwindow.xml', script_path, 'Default',
        multiselect=False,
    )
    ctx.doModal()
    dialog.notification(_notify_title, "Context: %s" % ctx.contextoption)
    del ctx


def preview_next_episode() -> None:
    """Show the CountdownDialog as next episode prompt (with countdown)."""
    from resources.lib.ui.dialogs import CountdownDialog
    from resources.lib.utils import lang

    poster = _get_show_poster()

    dlg = CountdownDialog(
        'script-easytv-nextepisode.xml', script_path, 'Default', '1080i',
        message="Breaking Bad",
        subtitle="S03E07 \u2014 One Minute",
        yes_label=lang(32092),       # "Play"
        no_label=lang(32091),        # "Don't Play"
        duration=15,
        heading=addon_name,
        timer_template=lang(32167),  # "(auto-closing in %s seconds)"
        default_yes=True,
        poster=poster,
        addon_id=addon_id,
    )
    dlg.doModal()
    dialog.notification(
        _notify_title,
        "Next episode: result=%s" % dlg.result,
    )
    del dlg


def preview_missed_warning() -> None:
    """Show the CountdownDialog as missed episode warning (no countdown)."""
    from resources.lib.ui.dialogs import CountdownDialog
    from resources.lib.utils import lang

    poster = _get_show_poster()

    dlg = CountdownDialog(
        'script-easytv-missedwarning.xml', script_path, 'Default', '1080i',
        message="Better Call Saul S04E03 was skipped.\nPlay the stored episode instead?",
        subtitle="An earlier episode was expected next",
        yes_label=lang(32078),   # "Yes"
        no_label=lang(32079),    # "No"
        duration=0,
        heading=addon_name,
        poster=poster,
        addon_id=addon_id,
    )
    dlg.doModal()
    dialog.notification(
        _notify_title,
        "Missed warning: result=%s" % dlg.result,
    )
    del dlg


def preview_playlist_continuation() -> None:
    """Show the CountdownDialog as playlist continuation (with countdown)."""
    from resources.lib.ui.dialogs import CountdownDialog
    from resources.lib.utils import lang

    dlg = CountdownDialog(
        'script-easytv-countdown.xml', script_path, 'Default', '1080i',
        message=lang(32618),              # "Playlist finished..."
        yes_label=lang(32619),            # "Generate"
        no_label=lang(32620),             # "Stop"
        duration=15,
        heading=addon_name,
        timer_template=lang(32167),       # "(auto-closing in %s seconds)"
        default_yes=True,
        addon_id=addon_id,
    )
    dlg.doModal()
    dialog.notification(
        _notify_title,
        "Continuation: result=%s" % dlg.result,
    )
    del dlg


def Main(override_addon_id: Optional[str] = None) -> None:
    """Show the dialog preview selection menu.

    Args:
        override_addon_id: If set, use this addon ID for theming and
            name display instead of the running addon's own ID.
            Useful for testing clones.
    """
    global addon_id, addon_name, script_path, _notify_title

    addon = xbmcaddon.Addon(override_addon_id) if override_addon_id else xbmcaddon.Addon()
    addon_id = addon.getAddonInfo('id')
    addon_name = addon.getAddonInfo('name')
    script_path = addon.getAddonInfo('path')
    _notify_title = "%s Preview" % addon_name

    # Theme picker — temporarily override for the preview session
    theme_names = ["Golden Hour", "Ultraviolet", "Ember", "Nightfall"]
    original_theme = addon.getSetting('theme') or '0'
    current_name = theme_names[int(original_theme)] if original_theme.isdigit() and int(original_theme) < len(theme_names) else theme_names[0]

    theme_options = ["Keep current (%s)" % current_name] + theme_names
    theme_choice = dialog.select("Theme Color", theme_options)  # type: ignore[arg-type]
    if theme_choice < 0:
        return
    if theme_choice > 0:
        addon.setSetting('theme', str(theme_choice - 1))

    try:
        options = [
            "1. Confirm Dialog",
            "2. Select Dialog",
            "3. Show Selector",
            "4. Browse Window",
            "5. Context Menu",
            "6. Next Episode (countdown)",
            "7. Missed Episode Warning",
            "8. Playlist Continuation (countdown)",
            "9. All Dialogs (cycle through)",
        ]

        menu_title = "%s Dialog Preview [%s]" % (addon_name, addon_id)
        choice = dialog.select(menu_title, options)  # type: ignore[arg-type]

        previews = [
            preview_confirm,
            preview_select,
            preview_show_selector,
            preview_browse,
            preview_context_menu,
            preview_next_episode,
            preview_missed_warning,
            preview_playlist_continuation,
        ]

        if 0 <= choice < len(previews):
            previews[choice]()
        elif choice == len(previews):
            for fn in previews:
                fn()
    finally:
        # Restore original theme
        if theme_choice > 0:
            addon.setSetting('theme', original_theme)
