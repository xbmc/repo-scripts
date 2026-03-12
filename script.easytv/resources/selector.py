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
    - "Enable All" button (top of list) - Selects all shows
    - "Ignore All" button - Deselects all shows
    - Individual show toggle via click
    - Shows display with poster artwork from library
    - Selected state persisted to addon settings

Logging:
    Module: selector
    Events: None (debug logging only)
"""

import xbmc
import xbmcgui
import xbmcaddon
import ast
import sys
from typing import cast

# Import shared utilities
from resources.lib.utils import lang, json_query, get_logger
from resources.lib.data.shows import generate_sort_key
from resources.lib.constants import (
    ACTION_PREVIOUS_MENU,
    ACTION_NAV_BACK,
    CONTROL_OK_BUTTON,
    CONTROL_HEADING,
    CONTROL_LIST,
    CONTROL_CANCEL_BUTTON,
    CONTROL_EXTRA_BUTTON2,
)

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

class xGUI(xbmcgui.WindowXMLDialog):
    """
    Custom dialog for selecting TV shows.
    
    IMPORTANT: Settings are saved inside onClick() BEFORE close() is called.
    This is required because Kodi may abort scripts launched via RunScript()
    from settings immediately after a modal dialog closes, before any
    post-doModal() code can execute.
    """

    def __init__(self, *args, **kwargs):
        # Extract custom parameters before passing to parent
        self.list_type = kwargs.pop('list_type', 'usersel')
        self.addon = kwargs.pop('addon', None)
        self.primary_list = kwargs.pop('primary_list', [])
        self.all_shows_data = kwargs.pop('all_shows_data', [])
        self.current_list = kwargs.pop('current_list', [])
        self.logger = kwargs.pop('logger', None)
        super().__init__(*args, **kwargs)
        self.new_list = []
        self.saved = False

    def onInit(self):

        # Save button
        self.ok = cast(xbmcgui.ControlButton, self.getControl(CONTROL_OK_BUTTON))
        self.ok.setLabel(lang(32170))

        # Heading
        self.hdg = cast(xbmcgui.ControlButton, self.getControl(CONTROL_HEADING))
        self.hdg.setLabel('EasyTV')
        self.hdg.setVisible(True)

        # Hide unused list frame
        self.x = self.getControl(3)
        self.x.setVisible(False)

        # Populate the list frame
        self.name_list = cast(xbmcgui.ControlList, self.getControl(CONTROL_LIST))
        self.new_list = []

        self.ea = xbmcgui.ListItem(lang(32171))
        self.ia = xbmcgui.ListItem(lang(32172))

        self.name_list.addItem(self.ea)
        self.name_list.addItem(self.ia)

        # Set action when clicking right from the Save button
        self.ok.controlRight(self.name_list)

        # Hide Extra button 2 (ID 8) - appears as blank button in some skins
        try:
            extra_button2 = self.getControl(CONTROL_EXTRA_BUTTON2)
            extra_button2.setVisible(False)
        except RuntimeError:
            pass  # Button may not exist in all skins

        self.item_count = 2

        for show_name, show_id, thumbnail in self.all_shows_data:
            # populate the list - use setArt() instead of deprecated thumbnailImage param
            tmp = xbmcgui.ListItem(show_name)
            tmp.setArt({'thumb': thumbnail})
            self.name_list.addItem(tmp)

            # highlight the already selected shows
            if show_id in self.current_list:
                self.name_list.getListItem(self.item_count).select(True)

            self.item_count += 1

        self.setFocus(self.name_list)

    def onAction(self, action):
        actionID = action.getId()
        if (actionID in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK)):
            self.close()

    def onClick(self, controlID):

        if controlID == CONTROL_OK_BUTTON:
            # Build the list of selected show IDs
            for itm in range(self.item_count):
                if itm != 0 and itm != 1 and self.name_list.getListItem(itm).isSelected():
                    self.new_list.append(self.primary_list[itm-2])
            
            # CRITICAL: Save settings HERE before close()
            # Kodi may abort scripts from RunScript() immediately after doModal() returns,
            # so we must save before calling close() to ensure data is persisted.
            self._save_settings()
            self.close()

        elif controlID == CONTROL_CANCEL_BUTTON:
            # Cancel - close without saving
            self.close()

        else:
            selItem = self.name_list.getSelectedPosition()
            if selItem == 0:
                self.process_itemlist(True)
            elif selItem == 1:
                self.process_itemlist(False)
            else:
                if self.name_list.getSelectedItem().isSelected():
                    self.name_list.getSelectedItem().select(False)
                else:
                    self.name_list.getSelectedItem().select(True)

    def _save_settings(self):
        """
        Save the selection directly to addon settings.
        
        Saves in new format: {"id": "title"} for ID stability protection.
        When Kodi rebuilds its library, show IDs can change. By storing
        titles alongside IDs, we can detect and recover from ID shifts.
        
        With <close>true</close> on the action button, the settings dialog
        is already closed and saved before this script runs, so we can
        safely call setSetting() directly.
        """
        # Build lookup dict from all_shows_data: (name, id, thumb) tuples
        id_to_title = {show_id: name for name, show_id, _ in self.all_shows_data}
        
        # Build the new format dict: {str(id): title}
        selection_dict = {str(show_id): id_to_title.get(show_id, '')
                          for show_id in self.new_list}
        
        if self.list_type == 'random_order_shows':
            self.addon.setSetting(id="random_order_shows", value=str(selection_dict))
            # Update display setting
            count = len(self.new_list)
            display_text = lang(32569) % count if count > 0 else lang(32571)
            self.addon.setSetting(id="random_order_shows_display", value=display_text)
            if self.logger:
                self.logger.info("Random order shows saved", event="selector.save",
                                 count=count, format="id_title_dict")
        else:
            self.addon.setSetting(id="selection", value=str(selection_dict))
            # Update display setting
            count = len(self.new_list)
            display_text = lang(32569) % count if count > 0 else lang(32571)
            self.addon.setSetting(id="selection_display", value=display_text)
            if self.logger:
                self.logger.info("Selected shows saved", event="selector.save",
                                 count=count, format="id_title_dict")
        
        self.saved = True

    def process_itemlist(self, set_to):
        for itm in range(self.item_count):
            if itm != 0 and itm != 1:
                if set_to:
                    self.name_list.getListItem(itm).select(True)
                else:
                    self.name_list.getListItem(itm).select(False)


def Main():
    """
    Main entry point for the show selection dialog.
    
    Queries the Kodi library for all TV shows and displays them in a
    selection dialog. The user's selections are saved to addon settings
    inside the dialog's onClick handler to prevent data loss from script
    abortion.
    """
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

    # Build the primary_list (show IDs in display order)
    primary_list = [var[1] for var in all_variables]

    # Create and launch the custom window with all required parameters
    # Settings are saved inside the dialog's onClick handler
    creation = xGUI(
        "DialogSelect.xml",
        scriptPath,
        'Default',
        list_type=list_type,
        addon=__addon__,
        primary_list=primary_list,
        all_shows_data=all_variables,
        current_list=current_list,
        logger=log
    )
    creation.doModal()
    
    # Note: Settings are saved inside the dialog's onClick handler,
    # NOT here. This is because Kodi may abort scripts launched via
    # RunScript() from settings immediately after doModal() returns.
    
    del creation

# Note: Main() is called explicitly from default.py
# openSettings() is called from default.py after this module finishes
# to ensure consistent behavior with other settings actions
