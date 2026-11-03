"""Kodi settings manipulation utilities for skin integration."""
from __future__ import annotations

import xbmc
import xbmcgui
from lib.kodi.client import request
from lib.kodi.utilities import set_window_prop, clear_window_prop

# settings Kodi resets on a skin change, the only ones that may skip the confirmation
SKIN_SCOPED_SETTINGS = frozenset({
    'lookandfeel.skincolors',
    'lookandfeel.skintheme',
    'lookandfeel.font',
})


def _setting_label(setting: str) -> str:
    """Localized label for a Kodi setting, falling back to the id."""
    result = request('Settings.GetSettings', {'level': 'expert'})
    if result and 'result' in result:
        for item in result['result'].get('settings', []):
            if item.get('id') == setting and item.get('label'):
                return item['label']
    return setting


def _confirm(setting: str, value_text: str) -> bool:
    """Ask the user to confirm a setting change, naming the setting."""
    heading = xbmc.getLocalizedString(5)  # Settings
    are_you_sure = xbmc.getLocalizedString(750)  # Are you sure?
    message = f'{_setting_label(setting)}: {value_text}\n{are_you_sure}'
    return xbmcgui.Dialog().yesno(heading, message)


def get_setting(setting: str, prefix: str = 'SkinInfo', window: str = 'home') -> None:
    """Get a Kodi setting's value into a `Setting.*` window property."""
    result = request('Settings.GetSettingValue', {'setting': setting})
    prop_name = f'{prefix}.Setting.{setting}'

    if result and 'result' in result and 'value' in result['result']:
        value = result['result']['value']
        set_window_prop(prop_name, value, window)
    else:
        clear_window_prop(prop_name, window)


def set_setting(setting: str, value: str | int | bool, noconfirm: bool = False) -> None:
    """Set a Kodi setting once the user confirms; a skin-scoped one may skip the prompt."""
    if isinstance(value, bool):
        value_text = xbmc.getLocalizedString(305 if value else 13106)  # Enabled / Disabled
    else:
        value_text = str(value)
    if (noconfirm and setting in SKIN_SCOPED_SETTINGS) or _confirm(setting, value_text):
        request('Settings.SetSettingValue', {'setting': setting, 'value': value})


def toggle_setting(setting: str, noconfirm: bool = False) -> None:
    """Toggle a boolean Kodi setting once the user confirms; a skin-scoped one may skip it."""
    result = request('Settings.GetSettingValue', {'setting': setting})
    if not (result and 'result' in result and 'value' in result['result']):
        return

    current_value = result['result']['value']
    if not isinstance(current_value, bool):
        return

    new_value = not current_value
    state_label = xbmc.getLocalizedString(305 if new_value else 13106)  # Enabled / Disabled
    if (noconfirm and setting in SKIN_SCOPED_SETTINGS) or _confirm(setting, state_label):
        request('Settings.SetSettingValue', {'setting': setting, 'value': new_value})


def reset_setting(setting: str, noconfirm: bool = False) -> None:
    """Reset a Kodi setting to its default once the user confirms; a skin-scoped one may skip it."""
    if (noconfirm and setting in SKIN_SCOPED_SETTINGS) or _confirm(
        setting, xbmc.getLocalizedString(571)  # Default
    ):
        request('Settings.ResetSettingValue', {'setting': setting})
