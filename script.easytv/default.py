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
EasyTV Main Entry Point - UI for browsing episodes and creating random playlists.

Modernized for Kodi 21+ (Nexus/Omega).

Logging:
    Module: default
    Events:
        - ui.start (INFO): Addon UI started
        - ui.stop (INFO): Addon UI finished
        - playlist.save (INFO): Playlist saved to file
        - version.mismatch (WARNING): Addon/service version mismatch
        - clone.outdated (WARNING): Clone addon needs update
        - clone.update_flag_cleared (INFO): Skipped version check after recent update
        - clone.update_flag_stale (INFO): Update flag outdated, another update occurred
        - service.missing (WARNING): EasyTV service not running
"""

import ast
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID, ADDON_RESTART_DELAY_MS,
    SERVICE_POLL_SLEEP_MS, SERVICE_POLL_TIMEOUT_TICKS,
)
from resources.lib.utils import (
    lang, get_logger, get_bool_setting, get_int_setting,
    parse_version, compare_versions
)
from resources.lib.ui.dialogs import show_playlist_selection
from resources.lib.playback.browse_mode import EpisodeListConfig, build_episode_list
from resources.lib.playback.random_player import (
    RandomPlaylistConfig, build_random_playlist
)


def _get_population(filter_enabled, populate_by, playlist_source,
                    user_playlist_path, selected_shows, dialog, log):
    """Build population filter based on settings."""
    if not filter_enabled:
        return {'none': ''}
    if populate_by == '1':
        if playlist_source == '0':
            # Ask each time - pass tvshows filter for TV show playlists
            return {'playlist': show_playlist_selection(
                dialog=dialog, logger=log, playlist_type='tvshows'
            )}
        # Use default playlist - check file exists first
        if user_playlist_path and user_playlist_path != 'none':
            if not xbmcvfs.exists(user_playlist_path):
                log.warning("TV show playlist file not found", 
                           event="playlist.missing", path=user_playlist_path)
                # 32607 = "TV show playlist not found. Please update your settings."
                dialog.ok("EasyTV", lang(32607))
                sys.exit()
            return {'playlist': user_playlist_path}
        return {'none': ''}
    return {'usersel': selected_shows}


def _get_skin_setting(addon):
    """Get skin style setting, handling legacy values."""
    view_style = addon.getSetting('view_style')
    if view_style == 'true':
        addon.setSetting('view_style', '1')
        return 1
    if view_style in ('false', '32073'):
        addon.setSetting('view_style', '1')
        return 0
    try:
        return int(view_style)
    except (ValueError, TypeError):
        return 0


def main_entry(addon, log):
    """Main entry point - determines mode and launches appropriate functionality."""
    log.debug("Main entry point")

    dialog = xbmcgui.Dialog()
    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    script_path = addon.getAddonInfo('path')

    # Load settings
    primary_function = addon.getSetting('primary_function')
    filter_enabled = get_bool_setting('filter_enabled')
    sort_by = get_int_setting('sort_by')
    sort_reverse = get_bool_setting('sort_reverse')

    try:
        selected_shows = ast.literal_eval(window.getProperty("EasyTV.selection"))
    except (ValueError, SyntaxError):
        selected_shows = []

    try:
        random_order_shows = ast.literal_eval(window.getProperty("EasyTV.random_order_shows"))
    except (ValueError, SyntaxError):
        random_order_shows = []

    population = _get_population(
        filter_enabled, addon.getSetting('populate_by'),
        addon.getSetting('playlist_source'), addon.getSetting('user_playlist_path'),
        selected_shows, dialog, log
    )

    # Determine mode: 0=browse, 1=random playlist, 2=ask
    if primary_function == '2':
        choice = dialog.yesno('EasyTV', lang(32100) + '\n\n' + lang(32101),
                              nolabel=lang(32102), yeslabel=lang(32103))
        if choice < 0:
            sys.exit()
    else:
        choice = int(primary_function) if primary_function in ('0', '1') else 0

    language = xbmc.getInfoLabel('System.Language')

    if choice == 1:
        # Random playlist mode
        playlist_content = get_int_setting('playlist_content')
        
        # Get movie playlist setting if movies are included
        movie_playlist = None
        # playlist_content: 0=TV only, 1=mixed, 2=movies only
        if playlist_content != 0:  # Not TV-only mode
            movie_playlist_path = addon.getSetting('movie_user_playlist_path')
            if movie_playlist_path and movie_playlist_path not in ('none', 'empty', ''):
                # Check file exists
                if not xbmcvfs.exists(movie_playlist_path):
                    log.warning("Movie playlist file not found", 
                               event="playlist.missing", path=movie_playlist_path)
                    # 32606 = "Movie playlist not found. Please update your settings."
                    dialog.ok("EasyTV", lang(32606))
                    sys.exit()
                movie_playlist = movie_playlist_path
        
        build_random_playlist(
            population=population,
            random_order_shows=random_order_shows,
            config=RandomPlaylistConfig(
                length=get_int_setting('length'),
                playlist_content=playlist_content,
                episode_selection=get_int_setting('episode_selection'),
                movie_selection=get_int_setting('movie_selection'),
                movie_chance=get_int_setting('movie_chance'),
                start_partials_tv=get_bool_setting('start_partials_tv'),
                start_partials_movies=get_bool_setting('start_partials_movies'),
                premieres=get_bool_setting('premieres'),
                season_premieres=get_bool_setting('season_premieres'),
                multiple_shows=get_bool_setting('multiple_shows'),
                sort_by=sort_by, sort_reverse=sort_reverse, language=language,
                movie_playlist=movie_playlist,
                unwatched_ratio=get_int_setting('unwatched_ratio'),
                duration_filter_enabled=get_bool_setting('duration_filter_enabled'),
                duration_min=get_int_setting('duration_min'),
                duration_max=get_int_setting('duration_max')
            ),
            logger=log,
            addon_id=addon.getAddonInfo('id')
        )
    else:
        # Browse mode - data fetching and filtering handled internally by build_episode_list
        build_episode_list(
            population=population,
            random_order_shows=random_order_shows,
            config=EpisodeListConfig(
                skin=_get_skin_setting(addon),
                limit_shows=get_bool_setting('limit_shows'),
                window_length=get_int_setting('window_length'),
                skin_return=get_bool_setting('skin_return'),
                excl_random_order_shows=get_bool_setting('excl_random_order_shows'),
                script_path=script_path,
                duration_filter_enabled=get_bool_setting('duration_filter_enabled'),
                duration_min=get_int_setting('duration_min'),
                duration_max=get_int_setting('duration_max'),
                sort_by=sort_by,
                sort_reverse=sort_reverse,
                language=language,
                include_series_premieres=get_bool_setting('premieres'),
                include_season_premieres=get_bool_setting('season_premieres')
            ),
            monitor=xbmc.Monitor(),
            logger=log
        )


def _handle_special_modes(mode, addon, log):
    """Handle special invocation modes (from settings actions)."""
    if mode == 'playlist':
        # Parse optional playlist type from argv[2]
        playlist_type = sys.argv[2] if len(sys.argv) > 2 else None
        log.debug("Playlist selection mode", playlist_type=playlist_type)
        from resources import playlists
        playlists.Main(playlist_type)
        
        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        # Use addon's own ID so clones reopen their own settings, not main addon's
        addon_id = addon.getAddonInfo('id')
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'selector':
        log.debug("Selector mode")
        from resources import selector
        selector.Main()
        
        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        # Use addon's own ID so clones reopen their own settings, not main addon's
        addon_id = addon.getAddonInfo('id')
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'clone':
        log.debug("Clone creation mode")
        from resources import clone
        clone.Main()

    elif mode == 'exporter':
        log.debug("Exporter mode")
        from resources import episode_exporter
        episode_exporter.Main()

    elif mode == 'clear_sync_data':
        log.debug("Clear sync data mode")
        from resources import clear_sync_data
        clear_sync_data.main()


def _check_service_running(window, log):
    """Check if EasyTV service is running. Returns True if running."""
    window.setProperty('EasyTV_service_running', 'marco')
    count = 0
    while window.getProperty('EasyTV_service_running') == 'marco':
        count += 1
        if count > SERVICE_POLL_TIMEOUT_TICKS:
            return False
        xbmc.sleep(SERVICE_POLL_SLEEP_MS)
    return True


def _handle_version_mismatch(addon_version, addon_version_str, addon_id, script_path, script_name, window, dialog, log):
    """Check version compatibility. Returns True if OK to proceed."""
    try:
        service_version_str = window.getProperty("EasyTV.Version")
        if not service_version_str:
            service_version = (0, 0, 0, 0, 0)
            service_version_str = "0.0.0"
        else:
            service_version = parse_version(service_version_str)
    except (ValueError, SyntaxError):
        service_version = (0, 0, 0, 0, 0)
        service_version_str = "0.0.0"

    if addon_version != service_version and addon_id == "script.easytv":
        log.warning("Version mismatch", event="version.mismatch", 
                    addon_version=addon_version_str, service_version=service_version_str)
        dialog.ok('EasyTV', lang(32108))
        return False

    # Check if clone is older than service (compare_versions returns -1 if v1 < v2)
    if compare_versions(addon_version_str, service_version_str) < 0 and addon_id != "script.easytv":
        # Check if we just completed an update - Kodi's addon cache may still report old version
        # Flag contains the target version we updated to, so we can detect if another update
        # happened after the flag was set (service moved past the flagged version)
        update_flag = f'EasyTV.UpdateComplete.{addon_id}'
        update_flag_version = window.getProperty(update_flag)
        if update_flag_version:
            if update_flag_version == service_version_str:
                # Don't clear the flag — Kodi's addon cache may still be stale.
                # Window properties clear naturally on Kodi restart, at which
                # point the cache is also refreshed.
                log.info("Clone update flag detected, skipping version check",
                         event="clone.update_flag_cleared", addon_id=addon_id,
                         flag_version=update_flag_version)
                return True
            else:
                # Flag is for an older version — another update happened.
                window.clearProperty(update_flag)
                log.info("Clone update flag outdated, proceeding with version check",
                         event="clone.update_flag_stale", addon_id=addon_id,
                         flag_version=update_flag_version, service_version=service_version_str)
        
        log.warning("Clone addon out of date", event="clone.outdated",
                    clone_version=addon_version_str, service_version=service_version_str)
        if dialog.yesno('EasyTV', lang(32110) + '\n' + lang(32111)) == 1:
            import os
            # Use main addon's update_clone.py, not the clone's old version
            # This ensures clones get the latest update logic (e.g., fixed settings replacement)
            service_path = window.getProperty("EasyTV.ServicePath")
            update_script = os.path.join(service_path, 'resources', 'update_clone.py')
            xbmc.executebuiltin(
                f'RunScript({update_script},{service_path},'
                f'{script_path},{addon_id},{script_name})'
            )
            return False
    return True


if __name__ == "__main__":
    addon = xbmcaddon.Addon()
    addon_version_str = addon.getAddonInfo('version')
    addon_version = parse_version(addon_version_str)
    addon_id = addon.getAddonInfo('id')
    script_path = addon.getAddonInfo('path')
    script_name = addon.getAddonInfo('Name')

    log = get_logger('default')
    log.info("EasyTV addon started", event="ui.start", addon_id=addon_id, version=addon_version_str)

    # Handle special modes from command line
    if len(sys.argv) > 1:
        _handle_special_modes(sys.argv[1], addon, log)
        sys.exit()

    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    dialog = xbmcgui.Dialog()

    # Check service status
    if window.getProperty('EasyTV_service_running') == 'starting':
        dialog.ok("EasyTV", lang(32115) + '\n' + lang(32116))
        sys.exit()

    if not _check_service_running(window, log):
        log.warning("EasyTV service not running", event="service.missing")
        if dialog.yesno('EasyTV', lang(32106) + '\n' + lang(32107)) == 1:
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                '"id":1,"params":{"addonid":"script.easytv","enabled":false}}'
            )
            xbmc.sleep(ADDON_RESTART_DELAY_MS)
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                '"id":1,"params":{"addonid":"script.easytv","enabled":true}}'
            )
        sys.exit()

    # Check version compatibility
    if not _handle_version_mismatch(addon_version, addon_version_str, addon_id, script_path, script_name, window, dialog, log):
        sys.exit()

    main_entry(addon, log)
    log.info("EasyTV addon finished", event="ui.stop")
