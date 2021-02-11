# -*- coding: utf-8 -*-
"""All functionality that requires Kodi imports"""

from __future__ import absolute_import, division, unicode_literals

import logging

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()

_LOGGER = logging.getLogger(__name__)


class SafeDict(dict):
    """A safe dictionary implementation that does not break down on missing keys"""

    def __missing__(self, key):
        """Replace missing keys with the original placeholder"""
        return '{' + key + '}'


def to_unicode(text, encoding='utf-8', errors='strict'):
    """Force text to unicode"""
    if isinstance(text, bytes):
        return text.decode(encoding, errors=errors)
    return text


def from_unicode(text, encoding='utf-8', errors='strict'):
    """Force unicode to text"""
    import sys
    if sys.version_info.major == 2 and isinstance(text, unicode):  # noqa: F821; pylint: disable=undefined-variable
        return text.encode(encoding, errors)
    return text


def addon_icon(addon=None):
    """Cache and return add-on icon"""
    return get_addon_info('icon', addon)


def addon_id(addon=None):
    """Cache and return add-on ID"""
    return get_addon_info('id', addon)


def addon_name(addon=None):
    """Cache and return add-on name"""
    return get_addon_info('name', addon)


def addon_path(addon=None):
    """Cache and return add-on path"""
    return get_addon_info('path', addon)


def addon_profile(addon=None):
    """Return add-on profile"""
    if not addon:
        addon = ADDON
    try:  # Kodi 19
        return to_unicode(xbmcvfs.translatePath(addon.getAddonInfo('profile')))
    except AttributeError:  # Kodi 18
        return to_unicode(xbmc.translatePath(addon.getAddonInfo('profile')))


def ok_dialog(heading='', message=''):
    """Show Kodi's OK dialog"""
    if not heading:
        heading = addon_name()
    if kodi_version_major() < 19:
        # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
        return xbmcgui.Dialog().ok(heading=heading, line1=message)
    return xbmcgui.Dialog().ok(heading=heading, message=message)


def yesno_dialog(heading='', message='', nolabel=None, yeslabel=None, autoclose=0):
    """Show Kodi's Yes/No dialog"""
    if not heading:
        heading = addon_name()
    if kodi_version_major() < 19:
        # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
        return xbmcgui.Dialog().yesno(heading=heading, line1=message, nolabel=nolabel, yeslabel=yeslabel,
                                      autoclose=autoclose)
    return xbmcgui.Dialog().yesno(heading=heading, message=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


class progress(xbmcgui.DialogProgress, object):  # pylint: disable=invalid-name,useless-object-inheritance
    """Show Kodi's Progress dialog"""

    def __init__(self, heading='', message=''):
        """Initialize and create a progress dialog"""
        super(progress, self).__init__()
        if not heading:
            heading = ADDON.getAddonInfo('name')
        self.create(heading, message=message)

    def create(self, heading, message=''):  # pylint: disable=arguments-differ
        """Create and show a progress dialog"""
        if kodi_version_major() < 19:
            lines = message.split('\n', 2)
            line1, line2, line3 = (lines + [None] * (3 - len(lines)))
            # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
            return super(progress, self).create(heading, line1=line1, line2=line2, line3=line3)
        return super(progress, self).create(heading, message=message)

    def update(self, percent, message=''):  # pylint: disable=arguments-differ
        """Update the progress dialog"""
        if kodi_version_major() < 19:
            lines = message.split('\n', 2)
            line1, line2, line3 = (lines + [None] * (3 - len(lines)))
            # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
            return super(progress, self).update(percent, line1=line1, line2=line2, line3=line3)
        return super(progress, self).update(percent, message=message)


def localize(string_id, **kwargs):
    """Return the translated string from the .po language files, optionally translating variables"""
    if kwargs:
        from string import Formatter
        return Formatter().vformat(ADDON.getLocalizedString(string_id), (), SafeDict(**kwargs))
    return ADDON.getLocalizedString(string_id)


def get_setting(key, default=None):
    """Get an add-on setting as string"""
    try:
        value = to_unicode(ADDON.getSetting(key))
    except RuntimeError:  # Occurs when the add-on is disabled
        return default
    if value == '' and default is not None:
        return default
    return value


def get_setting_bool(key, default=None):
    """Get an add-on setting as boolean"""
    try:
        return ADDON.getSettingBool(key)
    except (AttributeError, TypeError):  # On Krypton or older, or when not a boolean
        value = get_setting(key, default)
        if value not in ('false', 'true'):
            return default
        return bool(value == 'true')
    except RuntimeError:  # Occurs when the add-on is disabled
        return default


def get_setting_int(key, default=None):
    """Get an add-on setting as integer"""
    # ADDON.getSettingInt(key) doesn't work in Leia for settings without "number"
    try:
        return int(get_setting(key, default))
    except ValueError:  # Occurs when not an integer
        return default
    except RuntimeError:  # Occurs when the add-on is disabled
        return default


def get_setting_float(key, default=None):
    """Get an add-on setting"""
    try:
        return ADDON.getSettingNumber(key)
    except (AttributeError, TypeError):  # On Krypton or older, or when not a float
        value = get_setting(key, default)
        try:
            return float(value)
        except ValueError:
            return default
    except RuntimeError:  # Occurs when the add-on is disabled
        return default


def set_setting(key, value):
    """Set an add-on setting"""
    return ADDON.setSetting(key, from_unicode(str(value)))


def set_setting_bool(key, value):
    """Set an add-on setting as boolean"""
    try:
        return ADDON.setSettingBool(key, value)
    except (AttributeError, TypeError):  # On Krypton or older, or when not a boolean
        if value in ['false', 'true']:
            return set_setting(key, value)
        if value:
            return set_setting(key, 'true')
        return set_setting(key, 'false')


def set_setting_int(key, value):
    """Set an add-on setting as integer"""
    try:
        return ADDON.setSettingInt(key, value)
    except (AttributeError, TypeError):  # On Krypton or older, or when not an integer
        return set_setting(key, value)


def set_setting_float(key, value):
    """Set an add-on setting"""
    try:
        return ADDON.setSettingNumber(key, value)
    except (AttributeError, TypeError):  # On Krypton or older, or when not a float
        return set_setting(key, value)


def open_settings():
    """Open the add-in settings window, shows Credentials"""
    ADDON.openSettings()


def get_global_setting(key):
    """Get a Kodi setting"""
    result = jsonrpc(method='Settings.GetSettingValue', params=dict(setting=key))
    return result.get('result', {}).get('value')


def set_global_setting(key, value):
    """Set a Kodi setting"""
    return jsonrpc(method='Settings.SetSettingValue', params=dict(setting=key, value=value))


def get_cond_visibility(condition):
    """Test a condition in XBMC"""
    return xbmc.getCondVisibility(condition)


def kodi_version():
    """Returns full Kodi version as string"""
    return xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]


def kodi_version_major():
    """Returns major Kodi version as integer"""
    return int(kodi_version().split('.')[0])


def get_tokens_path():
    """Cache and return the userdata tokens path"""
    if not hasattr(get_tokens_path, 'cached'):
        get_tokens_path.cached = addon_profile() + 'tokens/'
    return getattr(get_tokens_path, 'cached')


def get_cache_path():
    """Cache and return the userdata cache path"""
    if not hasattr(get_cache_path, 'cached'):
        get_cache_path.cached = addon_profile() + 'cache/'
    return getattr(get_cache_path, 'cached')


def get_addon_info(key, addon=None):
    """Return addon information"""
    if not addon:
        addon = ADDON
    return to_unicode(addon.getAddonInfo(key))


def jsonrpc(*args, **kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    # We do not accept both args and kwargs
    if args and kwargs:
        _LOGGER.error('Wrong use of jsonrpc()')
        return None

    # Process a list of actions
    if args:
        for (idx, cmd) in enumerate(args):
            if cmd.get('id') is None:
                cmd.update(id=idx)
            if cmd.get('jsonrpc') is None:
                cmd.update(jsonrpc='2.0')
        return loads(xbmc.executeJSONRPC(dumps(args)))

    # Process a single action
    if kwargs.get('id') is None:
        kwargs.update(id=0)
    if kwargs.get('jsonrpc') is None:
        kwargs.update(jsonrpc='2.0')
    return loads(xbmc.executeJSONRPC(dumps(kwargs)))


def execute_builtin(command, *args):
    """Execute a Kodi builtin function"""
    xbmc.executebuiltin('{command}({params})'.format(command=command, params=",".join(args)))


def get_addon(name):
    """Return an instance of the specified Addon"""
    return xbmcaddon.Addon(name)
