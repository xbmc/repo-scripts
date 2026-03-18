#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Show Selection Dialog for EasyTV

This module provides a selection dialog for managing TV show lists in two modes:

Selection Modes:
    1. 'selection' - Filter Mode:
       When user clicks "Select TV Shows" in settings, this dialog allows them
       to choose which TV shows should be included in EasyTV features. Shows
       NOT selected here will be excluded from random playlists and the next
       episode list.

    2. 'random_order_shows' (setting key: 'random_order_shows') - Random Order Mode:
       When user clicks "Random Order Shows" in settings, this dialog allows
       them to designate shows for random episode order. For these shows,
       EasyTV will pick any unwatched episode randomly rather than following
       the standard sequential order.

The mode is determined by the command-line argument passed to this script
(sys.argv[1]), which is set by the settings callback.

Dialog Features:
    - Search-as-you-type filtering
    - "Enable All" / "Ignore All" buttons (act on filtered results only)
    - Individual show toggle via click
    - Shows display with poster artwork from library
    - Explicit Cancel + Save buttons
    - Selected state persisted to addon settings

Logging:
    Module: selector
    Events: None (debug logging only)
"""

import xbmc
import xbmcaddon
import ast
import sys

# Import shared utilities
from resources.lib.utils import lang, json_query, get_logger
from resources.lib.data.shows import generate_sort_key

__addon__ = xbmcaddon.Addon('script.easytv')
__addonid__          = __addon__.getAddonInfo('id')
_setting_            = __addon__.getSetting
scriptPath           = __addon__.getAddonInfo('path')

# Get list_type from command line arguments
# When invoked via default.py: argv = [script_path, 'selector', 'usersel'|'random_order_shows']
# So list_type is at argv[2]
if len(sys.argv) > 2 and sys.argv[1] == 'selector':
    list_type = sys.argv[2]
elif len(sys.argv) > 1:
    list_type = sys.argv[1]
else:
    list_type = 'usersel'  # Default fallback

# Module-specific logger
log = get_logger('selector')

show_request         = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"properties": ["art"]},"id": "1"}


def _save_settings(selected_ids, all_shows_data):
    """
    Save the selection directly to addon settings.

    Saves in new format: {"id": "title"} for ID stability protection.
    When Kodi rebuilds its library, show IDs can change. By storing
    titles alongside IDs, we can detect and recover from ID shifts.

    Args:
        selected_ids: List of selected show IDs.
        all_shows_data: List of (name, id, thumb) tuples for all shows.
    """
    # Build lookup dict from all_shows_data: (name, id, thumb) tuples
    id_to_title = {show_id: name for name, show_id, _ in all_shows_data}

    # Build the new format dict: {str(id): title}
    selection_dict = {str(show_id): id_to_title.get(show_id, '')
                      for show_id in selected_ids}

    count = len(selected_ids)
    display_text = lang(32569) % count if count > 0 else lang(32571)

    if list_type == 'random_order_shows':
        __addon__.setSetting(id="random_order_shows", value=str(selection_dict))
        __addon__.setSetting(id="random_order_shows_display", value=display_text)
        log.info("Random order shows saved", event="selector.save",
                 count=count, format="id_title_dict")
    else:
        __addon__.setSetting(id="selection", value=str(selection_dict))
        __addon__.setSetting(id="selection_display", value=display_text)
        log.info("Selected shows saved", event="selector.save",
                 count=count, format="id_title_dict")


def Main():
    """
    Main entry point for the show selection dialog.

    Queries the Kodi library for all TV shows and displays them in a
    ShowSelectorDialog. The user's selections are saved inside the
    dialog's onClick handler to prevent data loss from script abortion.
    """
    try:
        log.debug("Show selector opened", mode=list_type)

        all_shows = json_query(show_request, True)
        if 'tvshows' in all_shows:
            all_s = all_shows['tvshows']
            all_variables = [(x['label'], int(x['tvshowid']), x.get('art', {}).get('poster', '')) for x in all_s]
        else:
            all_variables = []

        all_variables.sort(key=lambda x: generate_sort_key(x[0], xbmc.getInfoLabel('System.Language')))

        log.debug("Available shows loaded", count=len(all_variables))

        try:
            if list_type == 'random_order_shows':
                raw_setting = ast.literal_eval(_setting_('random_order_shows'))
            else:
                raw_setting = ast.literal_eval(_setting_('selection'))

            # Handle both old [id] format and new {id: title} format
            if isinstance(raw_setting, dict):
                # New format: extract integer IDs from string keys
                current_list = [int(k) for k in raw_setting.keys()]
            elif isinstance(raw_setting, list):
                # Old format: use directly
                current_list = raw_setting
            else:
                current_list = []
        except (ValueError, SyntaxError):
            current_list = []

        log.debug("Currently selected shows", count=len(current_list))

        # Determine heading based on mode
        if list_type == 'random_order_shows':
            heading = lang(32731)  # "Random Order Shows"
        else:
            heading = lang(32730)  # "Select TV Shows"

        from resources.lib.ui.dialogs import ShowSelectorDialog

        creation = ShowSelectorDialog(
            "script-easytv-showselector.xml",
            scriptPath,
            'Default',
            heading=heading,
            all_shows_data=all_variables,
            current_list=current_list,
            logger=log,
        )
        creation.doModal()

        # CRITICAL: Save settings HERE after doModal returns.
        # Kodi may abort scripts launched via RunScript() from settings
        # immediately after doModal() returns, but the dialog's onClick
        # sets _saved=True synchronously before close(), so we're safe.
        if creation.saved:
            _save_settings(creation.selected_ids, all_variables)

        del creation
    except SystemExit:
        raise  # Let sys.exit() propagate
    except Exception:
        log.exception("Unhandled error in show selector", event="selector.crash")

# Note: Main() is called explicitly from default.py
# openSettings() is called from default.py after this module finishes
# to ensure consistent behavior with other settings actions
