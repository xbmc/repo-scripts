# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Original VRT NU kodiutils.py as GPLv3 by @dagwieers and @mediaminister
"""All functionality that requires Kodi imports"""

from __future__ import absolute_import, division, unicode_literals

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()


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


def addon_path():
    """Return add-on path"""
    return get_addon_info('path')


def addon_id():
    """Return add-on ID"""
    return get_addon_info('id')


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


def get_setting_int(key, default=None):
    """Get an add-on setting as integer"""
    try:
        return ADDON.getSettingInt(key)
    except (AttributeError, TypeError):  # On Krypton or older, or when not an integer
        value = get_setting(key, default)
        try:
            return int(value)
        except ValueError:
            return default
    except RuntimeError:  # Occurs when the add-on is disabled
        return default


def get_global_setting(key):
    """Get a Kodi setting"""
    result = jsonrpc(method='Settings.GetSettingValue', params=dict(setting=key))
    return result.get('result', {}).get('value')


def get_addon_info(key):
    """Return addon information"""
    return to_unicode(ADDON.getAddonInfo(key))


def log(level=1, message='', **kwargs):
    """Log info messages to Kodi"""
    debug_logging = get_global_setting('debug.showloginfo')  # Returns a boolean
    max_log_level = get_setting_int('max_log_level', default=0)
    if not debug_logging and not (level <= max_log_level and max_log_level != 0):
        return
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    xbmc.log(from_unicode(message), level % 3 if debug_logging else 2)


def log_error(message, **kwargs):
    """Log error messages to Kodi"""
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    xbmc.log(from_unicode(message), 4)


def jsonrpc(*args, **kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    # We do not accept both args and kwargs
    if args and kwargs:
        log_error('Wrong use of jsonrpc()')
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
