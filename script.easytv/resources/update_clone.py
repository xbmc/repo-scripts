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
EasyTV Clone Update

This module updates an existing clone to match the current main EasyTV version.

Update Process:
    1. Trigger:
       - When a clone is launched, it compares its version to the service version
       - If out of date, user is prompted to update
       - This script is called with: src_path, new_path, san_name, clone_name
       
    2. Preserve Settings:
       - Clone settings are stored in Kodi's userdata folder (not the addon folder)
       - By deleting and recreating the addon folder, settings remain intact
       
    3. File Operations:
       - Delete the existing clone addon folder
       - Copy fresh files from main EasyTV installation
       - Remove service.py, clone.py (clones don't need these)
       - Replace addon.xml and settings.xml with clone versions
       - Update addon ID references in Python files to match clone ID
       
    4. Re-registration:
       - Disable and re-enable the addon via JSON-RPC
       - This ensures Kodi recognizes the updated files
       
    5. Update Flag:
       - Sets window property 'EasyTV.UpdateComplete.{addon_id}' = '{version}'
       - Stores the target version (not just 'true') so we can detect if another
         update happened between setting the flag and the clone launching
       - Kodi's addon metadata cache may not refresh immediately, so the clone
         might still report the old version on next launch
       - default.py checks for this flag and skips the version check only if the
         flag version matches the current service version

Arguments (via sys.argv):
    1. src_path: Path to main EasyTV installation
    2. new_path: Path to clone addon folder
    3. san_name: Sanitized addon ID (e.g., script.easytv.kids)
    4. clone_name: Human-readable name (e.g., "Kids Shows")

Note:
    This script is self-contained and does NOT import from resources.lib.
    This is required because RunScript() executes from the resources/ folder
    context, which breaks the normal import paths used elsewhere in the addon.

Logging:
    Uses xbmc.log() directly (not StructuredLogger) due to import constraints.
"""

import shutil
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import sys
import os
from typing import Optional
from xml.etree import ElementTree as et

# Constants (inlined to avoid import issues)
ADDON_ENABLE_DELAY_MS = 1000

# Parse arguments
src_path   = sys.argv[1]
new_path   = sys.argv[2]
san_name   = sys.argv[3]
clone_name = sys.argv[4]

# Get main addon for localized strings and version info
__addon__ = xbmcaddon.Addon('script.easytv')
dialog = xbmcgui.Dialog()


def _log(message, level=xbmc.LOGINFO):
    """Simple logging wrapper."""
    xbmc.log(f"[EasyTV.update_clone] {message}", level)


def _lang(string_id):
    """Get localized string from main addon."""
    return __addon__.getLocalizedString(string_id)


def errorHandle(exception: Exception, trace: object, path_to_clean: Optional[str] = None) -> None:
    """Handle errors during update."""
    _log(f"Clone update failed: {exception}", xbmc.LOGERROR)

    # 32148 = "Clone update failed"
    # 32141 = "Please check the log for details"
    dialog.ok('EasyTV', _lang(32148) + '\n' + _lang(32141))
    if path_to_clean:
        shutil.rmtree(path_to_clean, ignore_errors=True)
    sys.exit()


def Main():
    # Show modal progress dialog during file operations
    progress = xbmcgui.DialogProgress()
    progress.create("EasyTV", "Updating clone...")
    
    try:
        progress.update(10, "Removing old files...")
        # Remove the existing clone (settings are preserved in userdata folder)
        shutil.rmtree(new_path)

        progress.update(25, "Copying addon files...")
        # Copy current addon to new location
        IGNORE_PATTERNS = ('.pyc', 'CVS', '.git', 'tmp', '.svn', '__pycache__')
        shutil.copytree(src_path, new_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))

        progress.update(35, "Configuring clone...")
        # Remove unneeded files
        addon_file = os.path.join(new_path, 'addon.xml')

        os.remove(os.path.join(new_path, 'service.py'))
        os.remove(addon_file)
        os.remove(os.path.join(new_path, 'resources', 'settings.xml'))
        os.remove(os.path.join(new_path, 'resources', 'clone.py'))

        # Replace settings file and addon file with clone versions
        shutil.move(os.path.join(new_path, 'resources', 'addon_clone.xml'), addon_file)
        shutil.move(os.path.join(new_path, 'resources', 'settings_clone.xml'),
                    os.path.join(new_path, 'resources', 'settings.xml'))

        progress.update(45, "Updating settings...")
        # Update all script.easytv references in settings.xml to match clone addon id
        # This includes: section id, RunScript() calls for selector/playlist/exporter
        # Without this, settings actions would invoke the main addon instead of the clone
        settings_file = os.path.join(new_path, 'resources', 'settings.xml')
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(content.replace('script.easytv', san_name))

        progress.update(55, "Updating language files...")
        # Update strings.po header in ALL language folders to match clone addon id
        # Without this, Kodi 21+ won't load language strings for the clone
        language_dir = os.path.join(new_path, 'resources', 'language')
        for lang_folder in os.listdir(language_dir):
            strings_file = os.path.join(language_dir, lang_folder, 'strings.po')
            if os.path.isfile(strings_file):
                with open(strings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = content.replace('# Addon Name: EasyTV', f'# Addon Name: {clone_name}')
                content = content.replace('# Addon id: script.easytv', f'# Addon id: {san_name}')
                with open(strings_file, 'w', encoding='utf-8') as f:
                    f.write(content)

    except Exception as e:
        _, _, tb = sys.exc_info()
        progress.close()
        errorHandle(e, tb, new_path)

    progress.update(65, "Updating addon metadata...")
    # Get parent version to use for clone
    parent_version = __addon__.getAddonInfo('version')

    # Edit the addon.xml to set clone id, name, and version
    tree = et.parse(addon_file)
    root = tree.getroot()
    root.set('id', san_name)
    root.set('name', clone_name)
    root.set('version', parent_version)
    summary_elem = tree.find('.//summary')
    if summary_elem is not None:
        summary_elem.text = clone_name
    tree.write(addon_file)

    progress.update(75, "Updating scripts...")
    # Replace the addon id in Python files to avoid access violations
    py_files = [
        os.path.join(new_path, 'resources', 'selector.py'),
        os.path.join(new_path, 'resources', 'playlists.py'),
        os.path.join(new_path, 'resources', 'update_clone.py'),
        os.path.join(new_path, 'resources', 'episode_exporter.py')
    ]

    for py in py_files:
        with open(py, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(py, 'w', encoding='utf-8') as f:
            f.write(content.replace('script.easytv', san_name))

    progress.update(85, "Updating skins...")
    # Update skin XML files to use clone's addon ID for language strings
    # Without this, $ADDON[script.easytv ...] won't resolve in clones
    skin_files = [
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-main.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-BigScreenList.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-cardlist.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-splitlist.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-confirm.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-select.xml'),
        os.path.join(new_path, 'resources', 'skins', 'Default', '1080i', 'script-easytv-showselector.xml'),
    ]

    for skin_file in skin_files:
        if os.path.isfile(skin_file):
            with open(skin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(skin_file, 'w', encoding='utf-8') as f:
                f.write(content.replace('$ADDON[script.easytv ', f'$ADDON[{san_name} '))

    # Restore custom icon if one was set before the update
    custom_icon_path = xbmcvfs.translatePath(
        f'special://profile/addon_data/{san_name}/custom_icon.png'
    )
    if os.path.isfile(custom_icon_path):
        shutil.copy2(custom_icon_path, os.path.join(new_path, 'icon.png'))
        _log(f"Restored custom icon for {san_name}")

    # Force Kodi to re-scan the addons directory and re-read addon.xml from disk,
    # refreshing the in-memory metadata cache before the disable/enable cycle
    try:
        progress.update(85, "Scanning for changes...")
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(3000)

        progress.update(92, "Registering with Kodi...")
        _log(f"Toggling addon registration: {san_name}")
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
            f'"id":1,"params":{{"addonid":"{san_name}","enabled":false}}}}'
        )
        xbmc.sleep(ADDON_ENABLE_DELAY_MS)
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
            f'"id":1,"params":{{"addonid":"{san_name}","enabled":true}}}}'
        )
    except Exception:
        _log(f"Addon re-registration failed: {san_name}", xbmc.LOGWARNING)

    progress.update(95, "Finalizing...")
    # Set flag to skip version check on next launch
    # Kodi's addon metadata cache may not refresh immediately after disable/enable,
    # so the clone might still report the old version. This flag tells the clone
    # to skip the version check on its next launch.
    # Store the target version (not just 'true') so we can detect if another update
    # happened between setting the flag and the clone launching.
    xbmcgui.Window(10000).setProperty(f'EasyTV.UpdateComplete.{san_name}', parent_version)
    _log(f"Set update complete flag for: {san_name} -> {parent_version}")

    progress.update(100, "Complete!")
    xbmc.sleep(500)  # Brief pause to show completion
    progress.close()

    # 32149 = "Clone updated successfully"
    dialog.ok('EasyTV', _lang(32149))


if __name__ == "__main__":
    _log(f"Clone update started: {clone_name}")
    
    Main()
    
    _log(f"Clone update completed: {clone_name} -> {__addon__.getAddonInfo('version')}")
