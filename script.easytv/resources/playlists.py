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
Playlist Selection Entry Point for EasyTV

This module provides the entry point for selecting video smart playlists
from the user's Kodi profile. It is invoked from EasyTV settings when
the user wants to set a default playlist for filtering content.

Entry Point:
    Main(playlist_type=None) - Show playlist selection dialog and save result

Playlist Types:
    - None or 'tvshows': TV show playlist filter (user_playlist_path setting)
    - 'movies': Movie playlist filter (movie_user_playlist_path setting)

The selected playlist path is saved to the appropriate setting and can
be used to filter which content appears in EasyTV features.

Logging:
    Module: playlists
    Events:
        - playlist.save (INFO): Playlist selection saved successfully
"""

import os
from typing import Optional

import xbmcaddon
import xbmcgui

from resources.lib.ui.dialogs import show_playlist_selection
from resources.lib.utils import get_logger

# Module logger
log = get_logger('playlists')


def Main(playlist_type: Optional[str] = None) -> None:
    """
    Main entry point for playlist selection.
    
    Shows a dialog for selecting a video smart playlist and saves the
    selection to the appropriate addon setting based on playlist_type.
    
    Args:
        playlist_type: Type of playlist to select:
            - None or 'tvshows': TV show playlist (default)
            - 'movies': Movie playlist
    """
    addon = xbmcaddon.Addon()
    
    log.debug("Playlist selection opened", playlist_type=playlist_type)
    
    # Show the playlist selection dialog
    pl = show_playlist_selection(
        dialog=xbmcgui.Dialog(),
        logger=log,
        playlist_type=playlist_type
    )
    
    if pl != 'empty':
        # Determine which settings to update based on playlist type
        if playlist_type == 'movies':
            path_setting = "movie_user_playlist_path"
            display_setting = "movie_playlist_file_display"
        else:
            path_setting = "user_playlist_path"
            display_setting = "playlist_file_display"
        
        # Save the playlist path
        addon.setSetting(id=path_setting, value=pl)
        
        # Update display setting with filename only
        filename = os.path.basename(pl)
        if filename.endswith('.xsp'):
            filename = filename[:-4]
        addon.setSetting(id=display_setting, value=filename)
        
        # Also mirror to Advanced settings for tvshows playlists
        if playlist_type != 'movies':
            addon.setSetting(id="smartplaylist_filter_display", value=filename)
        
        log.info("Playlist saved", event="playlist.save", path=pl,
                 display=filename, playlist_type=playlist_type)
