"""
EasyMovie Clone Creation.

Creates independent "clones" of EasyMovie with separate settings.
Useful for pre-configured instances like "Kids Movies", "Action Night", etc.

Clone Lifecycle:
    1. Creation:
       - User triggers via "Create clone addon..." in EasyMovie settings
       - Confirmation dialog explains what cloning does
       - Keyboard dialog prompts for a name
       - Progress dialog shows each step

    2. File Structure:
       - Copies entire addon to temp folder first (atomic)
       - Removes clone-only files (clone.py, templates)
       - Replaces addon.xml and settings.xml with clone versions
       - Updates addon ID in Python scripts, skin XMLs, language files

    3. Registration:
       - UpdateLocalAddons + disable/enable cycle
       - Clone appears in Video Addons with the user's name

    4. Usage:
       - Each clone has independent settings (in userdata)
       - Clones are updated via update_clone.py when parent updates

Logging:
    Logger: 'clone'
    Key events:
        - clone.create (INFO): Clone created successfully
        - clone.fail (ERROR): Clone creation failed
        - clone.name_fallback (WARNING): Name sanitized to fallback
    See LOGGING.md for full guidelines.
"""
import os
import shutil
from typing import List, Tuple
from xml.etree import ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.constants import ADDON_ID, ADDON_NAME
from resources.lib.utils import get_logger, lang
from resources.lib.ui.dialogs import show_confirm_dialog

log = get_logger('clone')


def _sanitize_filename(dirty_string: str) -> str:
    """Sanitize a string for use as an addon ID component."""
    import string as string_module
    dirty_string = dirty_string.strip()
    valid_chars = f"-_.(){string_module.ascii_letters}{string_module.digits} "
    sanitized = ''.join(c for c in dirty_string if c in valid_chars)
    sanitized = sanitized.replace(' ', '_').lower()
    return sanitized


def _replace_in_file(filepath: str, replacements: List[Tuple[str, str]]) -> None:
    """Perform string replacements in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def create_clone() -> None:
    """Create a clone of the EasyMovie addon."""
    dialog = xbmcgui.Dialog()

    # Pre-creation confirmation
    confirmed = show_confirm_dialog(
        ADDON_NAME,
        lang(32700) + '\n' + lang(32701) + '\n' + lang(32702),
        yes_label=lang(32716),  # "Continue"
        no_label=lang(32301),   # "Cancel"
    )
    if not confirmed:
        return

    # Get clone name from user
    keyboard = xbmc.Keyboard(lang(32703))  # "EasyMovie - "
    keyboard.doModal()

    if not keyboard.isConfirmed():
        return

    clone_name = keyboard.getText().strip()
    if not clone_name:
        clone_name = 'Clone'

    sanitized = _sanitize_filename(clone_name)

    # Fallback if sanitization yields empty/non-alphanumeric
    if not sanitized or not any(c.isalnum() for c in sanitized):
        sanitized = 'clone'
        log.warning("Clone name sanitized to fallback",
                    event="clone.name_fallback", original=clone_name)

    clone_id = f"script.easymovie.{sanitized}"

    # Get parent addon info
    addon = xbmcaddon.Addon(ADDON_ID)
    addon_path = addon.getAddonInfo('path')
    parent_version = addon.getAddonInfo('version')
    addons_dir = xbmcvfs.translatePath('special://home/addons')
    clone_path = os.path.join(addons_dir, clone_id)

    # Prevent overwriting parent addon
    if clone_id == ADDON_ID:
        log.error("Invalid clone name would overwrite parent",
                  event="clone.fail", clone_id=clone_id)
        dialog.ok(ADDON_NAME, lang(32704))
        addon.openSettings()
        return

    # Check if clone already exists
    if os.path.isdir(clone_path):
        log.warning("Clone name already in use",
                    event="clone.fail", clone_id=clone_id)
        dialog.ok(ADDON_NAME, lang(32704))
        addon.openSettings()
        return

    # Use temp folder for atomic operation
    temp_base = xbmcvfs.translatePath('special://temp/')
    temp_path = os.path.join(temp_base, f'easymovie_clone_{clone_id}')

    # Show modal progress dialog
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Creating clone...")

    try:
        # Clean up any leftover temp folder
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
        shutil.copytree(addon_path, temp_path, ignore=ignore)

        # Restore default icon
        default_icon = os.path.join(temp_path, 'icon_default.png')
        if os.path.isfile(default_icon):
            shutil.copy2(default_icon, os.path.join(temp_path, 'icon.png'))

        progress.update(25, "Configuring clone...")
        # Remove original addon.xml and settings.xml (will be replaced by templates)
        os.remove(os.path.join(temp_path, 'addon.xml'))
        os.remove(os.path.join(temp_path, 'resources', 'settings.xml'))

        # Move clone templates into place
        addon_xml = os.path.join(temp_path, 'addon.xml')
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
        # Update addon.xml via ElementTree (overwrites template tokens)
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
        _replace_in_file(settings_file, [('script.easymovie', clone_id)])

        progress.update(55, "Updating language files...")
        language_dir = os.path.join(temp_path, 'resources', 'language')
        for lang_folder in os.listdir(language_dir):
            strings_file = os.path.join(language_dir, lang_folder, 'strings.po')
            if os.path.isfile(strings_file):
                _replace_in_file(strings_file, [
                    ('# Addon Name: EasyMovie', f'# Addon Name: {clone_name}'),
                    ('# Addon id: script.easymovie', f'# Addon id: {clone_id}'),
                ])

        progress.update(65, "Updating scripts...")
        # Rewrite default.py with clone addon ID
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
                '        log.exception("Unhandled error in EasyMovie clone", event="launch.crash")\n'
                '    except Exception:\n'
                '        import traceback\n'
                '        import xbmc\n'
                '        xbmc.log(\n'
                '            f"[EasyMovie] Unhandled error: {traceback.format_exc()}",\n'
                '            xbmc.LOGERROR,\n'
                '        )\n'
            )

        # Update selector.py addon ID references
        selector_py = os.path.join(temp_path, 'resources', 'selector.py')
        if os.path.isfile(selector_py):
            _replace_in_file(selector_py, [('script.easymovie', clone_id)])

        progress.update(75, "Updating skins...")
        skin_dir = os.path.join(
            temp_path, 'resources', 'skins', 'Default', '1080i'
        )
        for filename in os.listdir(skin_dir):
            if filename.endswith('.xml'):
                skin_file = os.path.join(skin_dir, filename)
                _replace_in_file(skin_file, [
                    ('$ADDON[script.easymovie ', f'$ADDON[{clone_id} '),
                ])

        progress.update(85, "Installing clone...")
        shutil.move(temp_path, clone_path)

    except Exception:
        log.exception("Clone creation failed", event="clone.fail",
                      clone_id=clone_id)
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)
        progress.close()
        dialog.ok(ADDON_NAME, lang(32707) + '\n' + lang(32708))
        return

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
        xbmc.sleep(500)
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
            f'"id":1,"params":{{"addonid":"{clone_id}","enabled":true}}}}'
        )
        xbmc.sleep(1000)

        progress.update(100, "Complete!")
        xbmc.sleep(500)
    except Exception:
        log.warning("Addon registration may have failed",
                    event="clone.fail", clone_id=clone_id)
    finally:
        progress.close()

    log.info("Clone created successfully", event="clone.create",
             clone_id=clone_id, name=clone_name, version=parent_version)

    dialog.ok(ADDON_NAME, lang(32705) + '\n' + lang(32706))


if __name__ == '__main__':
    log.info("Clone creation started", event="clone.start")
    create_clone()
    log.info("Clone creation completed", event="clone.complete")
