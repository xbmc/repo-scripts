# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements Kodi Helper functions"""

from __future__ import absolute_import, division, unicode_literals
import xbmc
import xbmcaddon
from .utils import from_unicode, to_unicode

# NOTE: We need to add the add-on id in here explicitly !
ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')


class SafeDict(dict):
    """A safe dictionary implementation that does not break down on missing keys"""
    def __missing__(self, key):
        """Replace missing keys with the original placeholder"""
        return '{' + key + '}'


def kodi_version():
    """Returns full Kodi version as string"""
    return xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]


def kodi_version_major():
    """Returns major Kodi version as integer"""
    return int(kodi_version().split('.')[0])


def translate_path(path):
    """Translate special xbmc paths"""
    return to_unicode(xbmc.translatePath(path))


def get_addon_info(key):
    """Return addon information"""
    return to_unicode(ADDON.getAddonInfo(key))


def addon_id():
    """Cache and return add-on ID"""
    return get_addon_info('id')


def addon_profile():
    """Cache and return add-on profile"""
    return translate_path(ADDON.getAddonInfo('profile'))


def addon_version():
    """Cache and return add-on version"""
    return get_addon_info('version')


def browsesingle(type, heading, shares='', mask='', useThumbs=False, treatAsFolder=False, defaultt=None):  # pylint: disable=invalid-name,redefined-builtin
    """Show a Kodi browseSingle dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().browseSingle(type=type, heading=heading, shares=shares, mask=mask, useThumbs=useThumbs, treatAsFolder=treatAsFolder, defaultt=defaultt)


def notification(heading='', message='', icon='info', time=4000):
    """Show a Kodi notification"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().notification(heading=heading, message=message, icon=icon, time=time)


def ok_dialog(heading='', message=''):
    """Show Kodi's OK dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().ok(heading=heading, line1=message)


def select_dialog(heading='', opt_list=None, autoclose=0, preselect=-1, useDetails=False):  # pylint: disable=invalid-name
    """Show Kodi's Select dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().select(heading, opt_list, autoclose=autoclose, preselect=preselect, useDetails=useDetails)


def progress_dialog():
    """Show Kodi's Progress dialog"""
    from xbmcgui import DialogProgress
    return DialogProgress()


def textviewer(heading='', text='', usemono=False):
    """Show a Kodi textviewer dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    if kodi_version_major() < 18:
        return Dialog().textviewer(heading=heading, text=text)
    return Dialog().textviewer(heading=heading, text=text, usemono=usemono)


def yesno_dialog(heading='', message='', nolabel=None, yeslabel=None, autoclose=0):
    """Show Kodi's Yes/No dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().yesno(heading=heading, line1=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


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


def get_global_setting(key):
    """Get a Kodi setting"""
    result = jsonrpc(method='Settings.GetSettingValue', params=dict(setting=key))
    return result.get('result', {}).get('value')


def has_socks():
    """Test if socks is installed, and use a static variable to remember"""
    if hasattr(has_socks, 'cached'):
        return getattr(has_socks, 'cached')
    try:
        import socks  # noqa: F401; pylint: disable=unused-variable,unused-import,useless-suppression
    except ImportError:
        has_socks.cached = False
        return None  # Detect if this is the first run
    has_socks.cached = True
    return True


def get_proxies():
    """Return a usable proxies dictionary from Kodi proxy settings"""
    usehttpproxy = get_global_setting('network.usehttpproxy')
    if usehttpproxy is not True:
        return None

    try:
        httpproxytype = int(get_global_setting('network.httpproxytype'))
    except ValueError:
        httpproxytype = 0

    socks_supported = has_socks()
    if httpproxytype != 0 and not socks_supported:
        # Only open the dialog the first time (to avoid multiple popups)
        if socks_supported is None:
            ok_dialog('', localize(30042))  # Requires PySocks
        return None

    proxy_types = ['http', 'socks4', 'socks4a', 'socks5', 'socks5h']

    proxy = dict(
        scheme=proxy_types[httpproxytype] if 0 <= httpproxytype < 5 else 'http',
        server=get_global_setting('network.httpproxyserver'),
        port=get_global_setting('network.httpproxyport'),
        username=get_global_setting('network.httpproxyusername'),
        password=get_global_setting('network.httpproxypassword'),
    )

    if proxy.get('username') and proxy.get('password') and proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{username}:{password}@{server}:{port}'.format(**proxy)
    elif proxy.get('username') and proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{username}@{server}:{port}'.format(**proxy)
    elif proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{server}:{port}'.format(**proxy)
    elif proxy.get('server'):
        proxy_address = '{scheme}://{server}'.format(**proxy)
    else:
        return None

    return dict(http=proxy_address, https=proxy_address)


def log(msg, level=xbmc.LOGDEBUG, **kwargs):
    """InputStream Helper log method"""
    xbmc.log(msg=from_unicode('[{addon}] {msg}'.format(addon=addon_id(), msg=msg.format(**kwargs))), level=level)


def jsonrpc(*args, **kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    # We do not accept both args and kwargs
    if args and kwargs:
        log('ERROR: Wrong use of jsonrpc()')
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


def kodi_to_ascii(string):
    """Convert Kodi format tags to ascii"""
    if string is None:
        return None
    string = string.replace('[B]', '')
    string = string.replace('[/B]', '')
    string = string.replace('[I]', '')
    string = string.replace('[/I]', '')
    string = string.replace('[COLOR gray]', '')
    string = string.replace('[COLOR yellow]', '')
    string = string.replace('[/COLOR]', '')
    return string
