#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialog Preview Script — quickly cycle through all custom dialogs.

Usage from Kodi:
    RunScript(script.easymovie,dialog_preview)
    RunScript(script.easymovie,dialog_preview,script.easymovie.kids)

Or from the Kodi debug console / JSON-RPC:
    {"jsonrpc":"2.0","method":"Addons.ExecuteAddon",
     "params":{"addonid":"script.easymovie","params":["dialog_preview"]},"id":1}

The optional third argument overrides the addon ID, so dialogs use
that addon's name, theme, and skin path (useful for testing clones).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, cast

import xbmcgui
import xbmcaddon

dialog = xbmcgui.Dialog()

# Resolved at init() time — overridable via Main(override_addon_id)
addon_id = ""
addon_name = ""
script_path = ""
_notify_title = ""

# Module-level cache so "All Dialogs" doesn't re-query
_cached_movies: Optional[List[Dict[str, Any]]] = None


def _fetch_preview_movies(count: int = 20) -> List[Dict[str, Any]]:
    """Fetch random movies with art from the library.

    Returns cached result on subsequent calls.
    """
    global _cached_movies
    if _cached_movies is not None:
        return _cached_movies

    from resources.lib.utils import json_query

    query = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {
            "properties": [
                "title", "genre", "year", "rating", "runtime",
                "mpaa", "set", "setid", "playcount", "dateadded",
                "plot", "art", "file", "resume", "lastplayed",
            ],
            "sort": {"method": "random"},
            "limits": {"end": count},
        },
        "id": 1,
    }
    result = json_query(query)
    movies = result.get("movies", [])
    _cached_movies = movies
    return movies


def _find_set_movie(movies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find a movie that belongs to a set, or fall back to first movie."""
    for m in movies:
        if m.get("set") and m.get("setid", 0) > 0:
            return m
    if movies:
        # Fake set info on first movie
        fake = dict(movies[0])
        fake["set"] = "Preview Collection"
        fake["setid"] = 999
        return fake
    return {
        "movieid": 0, "title": "Preview Movie", "year": 2024,
        "genre": ["Drama"], "rating": 7.5, "runtime": 7200,
        "mpaa": "PG-13", "plot": "A preview movie.",
        "set": "Preview Collection", "setid": 999,
        "art": {}, "playcount": 0,
    }


# Module-level cache for set pair
_cached_set_pair: Optional[Dict[str, Any]] = None


def _fetch_set_pair() -> Dict[str, Any]:
    """Fetch two consecutive movies from the same set.

    Returns dict with keys: finished, next_movie, set_name.
    Uses cached result on subsequent calls.
    """
    global _cached_set_pair
    if _cached_set_pair is not None:
        return _cached_set_pair

    from resources.lib.utils import json_query
    from resources.lib.data.queries import (
        get_all_movie_sets_query,
        get_movie_set_details_query,
    )

    # Find a set with at least 2 movies
    sets_result = json_query(get_all_movie_sets_query())
    for movie_set in sets_result.get("sets", []):
        set_id = movie_set.get("setid", 0)
        if not set_id:
            continue
        details = json_query(get_movie_set_details_query(set_id))
        set_details = details.get("setdetails", details)
        set_movies = set_details.get("movies", [])
        if len(set_movies) >= 2:
            _cached_set_pair = {
                "finished": set_movies[0],
                "next_movie": set_movies[1],
                "set_name": set_details.get("title", movie_set.get("title", "")),
            }
            return _cached_set_pair

    # Fallback: no sets with 2+ movies
    _cached_set_pair = {
        "finished": {"title": "The Dark Knight", "year": 2008, "art": {}},
        "next_movie": {"title": "The Dark Knight Rises", "year": 2012, "art": {}},
        "set_name": "The Dark Knight Collection",
    }
    return _cached_set_pair


def preview_confirm() -> None:
    """Show the themed ConfirmDialog."""
    from resources.lib.ui.dialogs import show_confirm_dialog
    result = show_confirm_dialog(
        "Confirm Dialog Preview",
        "This is a test message.\nDo you want to continue?",
        yes_label="Accept",
        no_label="Decline",
        addon_id=addon_id,
    )
    dialog.notification(_notify_title, "Confirm result: %s" % result)


def preview_confirm_single() -> None:
    """Show the themed ConfirmDialog in OK-only mode."""
    from resources.lib.ui.dialogs import show_confirm_dialog
    result = show_confirm_dialog(
        "Confirm (OK Only) Preview",
        "This is an information message.\nOnly an OK button is shown.",
        yes_label="OK",
        no_label="",
        addon_id=addon_id,
    )
    dialog.notification(_notify_title, "OK-only result: %s" % result)


def preview_select_single() -> None:
    """Show the themed SelectDialog in single-select mode."""
    from resources.lib.ui.dialogs import show_select_dialog
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
    result = show_select_dialog(
        "Single Select Preview", items,
        multi_select=False, addon_id=addon_id,
    )
    dialog.notification(_notify_title, "Selected: %s" % result)


def preview_select_multi() -> None:
    """Show the themed SelectDialog in multi-select mode."""
    from resources.lib.ui.dialogs import show_select_dialog
    items = [
        "Action",
        "Comedy",
        "Drama",
        "Horror",
        "Sci-Fi",
        "Thriller",
        "Animation",
        "Documentary",
    ]
    result = show_select_dialog(
        "Multi Select Preview", items,
        multi_select=True, preselected=[1, 3, 5],
        addon_id=addon_id,
    )
    dialog.notification(_notify_title, "Selected: %s" % result)


def preview_browse() -> None:
    """Show the BrowseWindow — lets user pick which view style to preview."""
    movies = _fetch_preview_movies()
    if not movies:
        dialog.ok(_notify_title,
                   "No movies found in the library.\n"
                   "Browse preview requires a populated movie library.")
        return

    from resources.lib.ui.browse_window import BrowseWindow, VIEW_XML_MAP
    from resources.lib.constants import (
        VIEW_SHOWCASE, VIEW_CARD_LIST, VIEW_POSTERS,
        VIEW_BIG_SCREEN, VIEW_SPLIT_VIEW,
    )

    view_names = [
        "Showcase",
        "Card List",
        "Posters",
        "Big Screen",
        "Split View",
    ]
    view_values = [
        VIEW_SHOWCASE, VIEW_CARD_LIST, VIEW_POSTERS,
        VIEW_BIG_SCREEN, VIEW_SPLIT_VIEW,
    ]

    choice = dialog.select("Browse View Style",
                           cast(List[Union[str, xbmcgui.ListItem]], view_names))
    if choice < 0:
        return

    addon = xbmcaddon.Addon(addon_id)
    try:
        theme_index = int(addon.getSetting('theme') or '0')
    except (ValueError, TypeError):
        theme_index = 0

    xml_file = VIEW_XML_MAP.get(view_values[choice], VIEW_XML_MAP[VIEW_SHOWCASE])
    addon_path = addon.getAddonInfo('path')
    window = BrowseWindow(xml_file, addon_path, 'Default', '1080i')
    window.set_movies(movies)
    window.set_addon_id(addon_id)
    window.set_preview_mode(theme_index)
    window.doModal()

    result = window.result
    if result is None:
        dialog.notification(_notify_title, "Browse: closed")
    elif isinstance(result, dict):
        title = result.get("title", result.get("movie", {}).get("title", ""))
        dialog.notification(_notify_title, "Browse: %s" % title)
    else:
        dialog.notification(_notify_title, "Browse: %s" % result)


def preview_context_menu() -> None:
    """Show the ContextMenuWindow with a movie that has a set."""
    movies = _fetch_preview_movies()
    movie = _find_set_movie(movies)

    from resources.lib.ui.context_menu import show_context_menu
    result = show_context_menu(movie, addon_id=addon_id)
    dialog.notification(_notify_title, "Context: %s" % result)


def preview_continuation() -> None:
    """Show the ContinuationDialog with countdown (playlist continuation)."""
    from resources.lib.playback.playback_monitor import ContinuationDialog
    from resources.lib.utils import lang

    pair = _fetch_set_pair()
    finished_title = pair["finished"].get("title", "Preview Movie")
    next_movie = pair["next_movie"]
    next_title = next_movie.get("title", "Next Movie")
    set_name = pair["set_name"]
    art = next_movie.get("art", {})
    poster = art.get("poster", "") if isinstance(art, dict) else ""

    cd = ContinuationDialog(
        'script-easymovie-continuation.xml',
        script_path, 'Default', '1080i',
        message=f"{lang(32333)}[CR][B]{finished_title}[/B]",
        subtitle=f"{lang(32332)} [B]{set_name}[/B]:[CR]{next_title}",
        yes_label=lang(32330),
        no_label=lang(32331),
        poster=poster,
        duration=15,
        default_yes=True,
        heading=addon_name,
        addon_id=addon_id,
    )
    cd.doModal()
    dialog.notification(
        _notify_title,
        "Continuation: result=%s" % cd.result
    )
    del cd


def preview_set_warning() -> None:
    """Show the ContinuationDialog as set warning (no countdown)."""
    from resources.lib.playback.playback_monitor import ContinuationDialog
    from resources.lib.utils import lang

    pair = _fetch_set_pair()
    movie = pair["finished"]
    title = movie.get("title", "Preview Movie")
    year = str(movie.get("year", 2024))
    set_name = pair["set_name"]
    art = movie.get("art", {})
    poster = art.get("poster", "") if isinstance(art, dict) else ""

    cd = ContinuationDialog(
        'script-easymovie-setwarning.xml',
        script_path, 'Default', '1080i',
        message=(
            f"[B]{title}[/B] ({year})[CR]"
            f"{lang(32340)} [B]{set_name}[/B][CR]"
            f"{lang(32341)}"
        ),
        subtitle=lang(32342),
        yes_label=lang(32300),
        no_label=lang(32301),
        poster=poster,
        duration=0,
        default_yes=True,
        heading=addon_name,
        addon_id=addon_id,
    )
    cd.doModal()
    dialog.notification(
        _notify_title,
        "Set warning: result=%s" % cd.result
    )
    del cd


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
            "2. Confirm Dialog (OK only)",
            "3. Select Dialog (single)",
            "4. Select Dialog (multi)",
            "5. Browse Window",
            "6. Context Menu",
            "7. Continuation Dialog (countdown)",
            "8. Set Warning Dialog (no countdown)",
            "9. All Dialogs (cycle through)",
        ]

        menu_title = "%s Dialog Preview [%s]" % (addon_name, addon_id)
        choice = dialog.select(menu_title, options)  # type: ignore[arg-type]

        previews = [
            preview_confirm,
            preview_confirm_single,
            preview_select_single,
            preview_select_multi,
            preview_browse,
            preview_context_menu,
            preview_continuation,
            preview_set_warning,
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
