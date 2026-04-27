"""
EasyMovie Clone Update.

Updates an existing clone to match the current main EasyMovie version.

This script is self-contained and does NOT import from resources.lib.
RunScript() executes from the resources/ folder context, which breaks
the normal import paths used elsewhere in the addon.

Update Process:
    1. Copy fresh files from main EasyMovie to temp folder
    2. Remove clone-only files, replace with clone templates
    3. Update addon ID references in settings, scripts, skins, language
    4. Remove old clone, move temp to final location
    5. Re-register with Kodi
    6. Set window property flag to prevent update loop

Arguments (via sys.argv):
    1. src_path: Path to main EasyMovie installation
    2. clone_path: Path to clone addon folder
    3. clone_id: Sanitized addon ID (e.g., script.easymovie.kids_movies)
    4. clone_name: Human-readable name (e.g., "Kids Movies")

Logging:
    Uses xbmc.log() directly (not StructuredLogger) due to import constraints.
"""
import os
import shutil
import sys
from typing import Optional
from xml.etree import ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# Constants (inlined to avoid import issues)
ADDON_NAME = "EasyMovie"

# Get main addon for version info and localized strings
_main_addon = xbmcaddon.Addon('script.easymovie')
dialog = xbmcgui.Dialog()


def _log(message: str, level: int = xbmc.LOGINFO) -> None:
    """Simple logging wrapper."""
    xbmc.log(f"[EasyMovie.update_clone] {message}", level)


def _lang(string_id: int) -> str:
    """Get localized string from main addon."""
    return _main_addon.getLocalizedString(string_id)


def _error_and_exit(
    exception: Exception,
    path_to_clean: Optional[str] = None,
) -> None:
    """Handle errors during update."""
    _log(f"Clone update failed: {exception}", xbmc.LOGERROR)
    dialog.ok(ADDON_NAME, _lang(32715) + '\n' + _lang(32708))
    if path_to_clean:
        shutil.rmtree(path_to_clean, ignore_errors=True)
    sys.exit()


def _replace_in_file(filepath: str, old: str, new: str) -> None:
    """Replace string in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.replace(old, new))


def run_update(
    src_path: str,
    clone_path: str,
    clone_id: str,
    clone_name: str,
) -> None:
    """Run the clone update.

    Args:
        src_path: Path to main EasyMovie installation.
        clone_path: Path to clone addon folder.
        clone_id: Sanitized addon ID (e.g., script.easymovie.kids_movies).
        clone_name: Human-readable name (e.g., "Kids Movies").
    """
    parent_version = _main_addon.getAddonInfo('version')

    # Use temp folder for atomic operation
    temp_base = xbmcvfs.translatePath('special://temp/')
    temp_path = os.path.join(temp_base, f'easymovie_update_{clone_id}')

    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Updating clone...")

    try:
        # Clean up leftover temp
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)

        progress.update(10, "Copying addon files...")
        ignore = shutil.ignore_patterns(
            '.pyc', '.git*', '__pycache__', 'CVS', '.svn',
            'docs', 'tests', '.claude*', '.mcp.json',
            'CLAUDE.md', 'LOGGING.md', 'CONTRIBUTING.md', 'README.md',
            'pyrightconfig.json', '.pyflakes', '.ruff_cache',
            '.pytest_cache', 'conftest.py', 'pytest.ini',
            '_temp', '.worktrees',
        )
        shutil.copytree(src_path, temp_path, ignore=ignore)

        progress.update(25, "Configuring clone...")
        # Remove original addon.xml and settings.xml
        addon_xml = os.path.join(temp_path, 'addon.xml')
        os.remove(addon_xml)
        os.remove(os.path.join(temp_path, 'resources', 'settings.xml'))

        # Move clone templates into place
        shutil.move(
            os.path.join(temp_path, 'resources', 'addon_clone.xml'),
            addon_xml,
        )
        shutil.move(
            os.path.join(temp_path, 'resources', 'settings_clone.xml'),
            os.path.join(temp_path, 'resources', 'settings.xml'),
        )

        # Remove clone-only files (clones don't run background services)
        for remove_file in [
            'resources/clone.py', 'resources/update_clone.py', 'service.py',
        ]:
            path = os.path.join(temp_path, remove_file)
            if os.path.exists(path):
                os.remove(path)

        progress.update(35, "Updating addon metadata...")
        # Parse and update addon.xml
        tree = ET.parse(addon_xml)
        root = tree.getroot()
        root.set('id', clone_id)
        root.set('name', clone_name)
        root.set('version', parent_version)
        summary_elem = tree.find('.//summary')
        if summary_elem is not None:
            summary_elem.text = clone_name
        tree.write(addon_xml, encoding='unicode', xml_declaration=True)

        progress.update(45, "Updating settings...")
        settings_file = os.path.join(temp_path, 'resources', 'settings.xml')
        _replace_in_file(settings_file, 'script.easymovie', clone_id)

        progress.update(55, "Updating language files...")
        language_dir = os.path.join(temp_path, 'resources', 'language')
        for lang_folder in os.listdir(language_dir):
            strings_file = os.path.join(language_dir, lang_folder, 'strings.po')
            if os.path.isfile(strings_file):
                with open(strings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = content.replace(
                    '# Addon Name: EasyMovie', f'# Addon Name: {clone_name}'
                )
                content = content.replace(
                    '# Addon id: script.easymovie', f'# Addon id: {clone_id}'
                )
                with open(strings_file, 'w', encoding='utf-8') as f:
                    f.write(content)

        progress.update(65, "Updating scripts...")
        # Rewrite default.py
        default_py = os.path.join(temp_path, 'default.py')
        with open(default_py, 'w', encoding='utf-8') as f:
            f.write(
                '"""EasyMovie clone entry point."""\n'
                'from resources.lib.ui.main import main, _handle_entry_args\n'
                '\n'
                'try:\n'
                f'    if not _handle_entry_args("{clone_id}"):\n'
                f'        main(addon_id="{clone_id}")\n'
                'except SystemExit:\n'
                '    pass\n'
                'except Exception:\n'
                '    try:\n'
                '        from resources.lib.utils import get_logger\n'
                "        log = get_logger('default')\n"
                '        log.exception("Unhandled error in EasyMovie clone",'
                ' event="launch.crash")\n'
                '    except Exception:\n'
                '        import traceback\n'
                '        import xbmc\n'
                '        xbmc.log(\n'
                '            f"[EasyMovie] Unhandled error:'
                ' {traceback.format_exc()}",\n'
                '            xbmc.LOGERROR,\n'
                '        )\n'
            )

        # Update selector.py
        selector_py = os.path.join(temp_path, 'resources', 'selector.py')
        if os.path.isfile(selector_py):
            _replace_in_file(selector_py, 'script.easymovie', clone_id)

        progress.update(75, "Updating skins...")
        skin_dir = os.path.join(
            temp_path, 'resources', 'skins', 'Default', '1080i'
        )
        for filename in os.listdir(skin_dir):
            if filename.endswith('.xml'):
                skin_file = os.path.join(skin_dir, filename)
                _replace_in_file(
                    skin_file,
                    '$ADDON[script.easymovie ',
                    f'$ADDON[{clone_id} ',
                )

        # Restore custom icon if user had one
        custom_icon = xbmcvfs.translatePath(
            f'special://profile/addon_data/{clone_id}/custom_icon.png'
        )
        if os.path.isfile(custom_icon):
            shutil.copy2(custom_icon, os.path.join(temp_path, 'icon.png'))
            _log(f"Restored custom icon for {clone_id}")

        progress.update(85, "Installing updated clone...")
        # Remove old clone, move new one into place
        if os.path.isdir(clone_path):
            shutil.rmtree(clone_path)
        shutil.move(temp_path, clone_path)

    except Exception as e:
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)
        progress.close()
        _error_and_exit(e, clone_path)

    # Register with Kodi
    try:
        progress.update(90, "Registering with Kodi...")
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(3000)

        progress.update(95, "Enabling clone...")
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
            f'"id":1,"params":{{"addonid":"{clone_id}","enabled":false}}}}'
        )
        xbmc.sleep(1000)
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
            f'"id":1,"params":{{"addonid":"{clone_id}","enabled":true}}}}'
        )
    except Exception:
        _log(f"Addon re-registration failed: {clone_id}", xbmc.LOGWARNING)

    # Set flag to prevent update loop (Kodi cache may still report old version)
    progress.update(95, "Finalizing...")
    xbmcgui.Window(10000).setProperty(
        f'EasyMovie.UpdateComplete.{clone_id}', parent_version
    )
    _log(f"Set update complete flag: {clone_id} -> {parent_version}")

    progress.update(100, "Complete!")
    xbmc.sleep(500)
    progress.close()

    dialog.ok(ADDON_NAME, _lang(32713) + '\n' + _lang(32714))


if __name__ == "__main__":
    _src_path = sys.argv[1]
    _clone_path = sys.argv[2]
    _clone_id = sys.argv[3]
    _clone_name = sys.argv[4]

    _log(f"Clone update started: {_clone_name}")
    run_update(_src_path, _clone_path, _clone_id, _clone_name)
    _log(f"Clone update completed: {_clone_name} -> "
         f"{_main_addon.getAddonInfo('version')}")
