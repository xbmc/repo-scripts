# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements Kodi Helper functions"""

from __future__ import absolute_import, division, unicode_literals
from contextlib import contextmanager
import xbmc
import xbmcaddon
from xbmcgui import DialogProgress, DialogProgressBG
from .unicodes import from_unicode, to_unicode

# NOTE: We need to explicitly add the add-on id here!
ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')


class progress_dialog(DialogProgress, object):  # pylint: disable=invalid-name,useless-object-inheritance
    """Show Kodi's Progress dialog"""

    def __init__(self):
        """Initialize a new progress dialog"""
        # Wait for previous Progress dialog to close
        # Progress dialog Window ID is 10101: https://kodi.wiki/view/Window_IDs
        while get_current_window_id() == 10101:
            xbmc.sleep(100)
        super(progress_dialog, self).__init__()

    def create(self, heading, message=''):  # pylint: disable=arguments-differ
        """Create and show a progress dialog"""
        if kodi_version_major() < 19:
            lines = message.split('\n', 2)
            line1, line2, line3 = (lines + [None] * (3 - len(lines)))
            return super(progress_dialog, self).create(heading, line1=line1, line2=line2, line3=line3)
        return super(progress_dialog, self).create(heading, message=message)

    def update(self, percent, message=''):  # pylint: disable=arguments-differ
        """Update the progress dialog"""
        if kodi_version_major() < 19:
            lines = message.split('\n', 2)
            line1, line2, line3 = (lines + [None] * (3 - len(lines)))
            return super(progress_dialog, self).update(percent, line1=line1, line2=line2, line3=line3)
        return super(progress_dialog, self).update(percent, message=message)


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
    return to_unicode(xbmc.translatePath(from_unicode(path)))


def get_addon_info(key):
    """Return addon information"""
    return to_unicode(ADDON.getAddonInfo(key))


def addon_id():
    """Cache and return add-on ID"""
    return get_addon_info('id')


def addon_profile():
    """Cache and return add-on profile"""
    return translate_path(get_addon_info('profile'))


def addon_version():
    """Cache and return add-on version"""
    return get_addon_info('version')


def browsesingle(type, heading, shares='', mask='', useThumbs=False, treatAsFolder=False, defaultt=None):  # pylint: disable=invalid-name,redefined-builtin
    """Show a Kodi browseSingle dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return to_unicode(Dialog().browseSingle(type=type, heading=heading, shares=shares, mask=mask, useThumbs=useThumbs,
                                            treatAsFolder=treatAsFolder, defaultt=defaultt))


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
    if kodi_version_major() < 19:
        return Dialog().ok(heading=heading, line1=message)
    return Dialog().ok(heading=heading, message=message)


def select_dialog(heading='', opt_list=None, autoclose=0, preselect=-1, useDetails=False):  # pylint: disable=invalid-name
    """Show Kodi's Select dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().select(heading, opt_list, autoclose=autoclose, preselect=preselect, useDetails=useDetails)


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
    if kodi_version_major() < 19:
        return Dialog().yesno(heading=heading, line1=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)
    return Dialog().yesno(heading=heading, message=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


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
    """Get an add-on setting as float"""
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


def get_current_window_id():
    """Get current window id"""
    result = jsonrpc(method='GUI.GetProperties', params=dict(properties=['currentwindow']))
    if result.get('error'):
        return None
    return result.get('result', {}).get('currentwindow').get('id')


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


def log(level=0, message='', **kwargs):
    """Log info messages to Kodi"""
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    xbmc.log(from_unicode(message), level)


def jsonrpc(*args, **kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    # We do not accept both args and kwargs
    if args and kwargs:
        log(4, 'ERROR: Wrong use of jsonrpc()')
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


@contextmanager
def open_file(path, flags='r'):
    """Open a file (using xbmcvfs)"""
    from xbmcvfs import File
    fdesc = File(path, flags)
    yield fdesc
    fdesc.close()


def copy(src, dest):
    """Copy a file (using xbmcvfs)"""
    from xbmcvfs import copy as vfscopy
    log(2, "Copy file '{src}' to '{dest}'.", src=src, dest=dest)
    return vfscopy(from_unicode(src), from_unicode(dest))


def delete(path):
    """Remove a file (using xbmcvfs)"""
    from xbmcvfs import delete as vfsdelete
    log(2, "Delete file '{path}'.", path=path)
    return vfsdelete(from_unicode(path))


def exists(path):
    """Whether the path exists (using xbmcvfs)"""
    # File or folder (folder must end with slash or backslash)
    from xbmcvfs import exists as vfsexists
    return vfsexists(from_unicode(path))


def listdir(path):
    """Return all files in a directory (using xbmcvfs)"""
    from xbmcvfs import listdir as vfslistdir
    dirs, files = vfslistdir(from_unicode(path))
    return [to_unicode(item) for items in (dirs, files) for item in items]


def mkdir(path):
    """Create a directory (using xbmcvfs)"""
    from xbmcvfs import mkdir as vfsmkdir
    log(2, "Create directory '{path}'.", path=path)
    return vfsmkdir(from_unicode(path))


def mkdirs(path):
    """Create directory including parents (using xbmcvfs)"""
    from xbmcvfs import mkdirs as vfsmkdirs
    log(2, "Recursively create directory '{path}'.", path=path)
    return vfsmkdirs(from_unicode(path))


def stat_file(path):
    """Return information about a file (using xbmcvfs)"""
    from xbmcvfs import Stat
    return Stat(from_unicode(path))


def bg_progress_dialog():
    """Show Kodi's Background Progress dialog"""
    return DialogProgressBG()
