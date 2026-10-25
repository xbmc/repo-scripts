# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

import json
from datetime import date
from re import split as re_split
from xbmc import executeJSONRPC, getCondVisibility, getRegion, log as xlog, LOGDEBUG, LOGINFO
from xbmcaddon import Addon
from xbmcgui import Window

ADDON = Addon()


def get_addon_info(key):
    """Return add-on information"""
    return ADDON.getAddonInfo(key)


def addon_id():
    """Return add-on ID"""
    return get_addon_info('id')


def addon_path():
    """Return add-on path"""
    return get_addon_info('path')


def get_property(key, window_id=10000):
    """Get a Window property"""
    return Window(window_id).getProperty(key)


def set_property(key, value, window_id=10000):
    """Set a Window property"""
    return Window(window_id).setProperty(key, str(value))


def clear_property(key, window_id=10000):
    """Clear a Window property"""
    return Window(window_id).clearProperty(key)


def get_int(obj, key=None, default=-1):
    """Returns an object or value for the given key in object, as an integer.
       Returns default value if key or object is not available.
       Returns value if value cannot be converted to integer."""

    try:
        val = obj.get(key, default) if key else obj
    except (AttributeError, TypeError):
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return val if val else default


def get_setting(key, default=None):
    """Get an add-on setting as string"""
    # We use Addon() here to ensure changes in settings are reflected instantly
    try:
        value = Addon().getSetting(key)
    except RuntimeError:  # Occurs when the add-on is disabled
        return default
    if value == '' and default is not None:
        return default
    return value


def get_setting_bool(key, default=None):
    """Get an add-on setting as boolean"""
    try:
        return Addon().getSettingBool(key)
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
        return Addon().getSettingInt(key)
    except (AttributeError, TypeError):  # On Krypton or older, or when not an integer
        value = get_setting(key, default)
        try:
            return int(value)
        except ValueError:
            return default
    except RuntimeError:  # Occurs when the add-on is disabled
        return default


def encode_data(data, encoding='base64'):
    """Encode data for a notification event"""
    json_data = json.dumps(data).encode()
    if encoding == 'base64':
        from base64 import b64encode
        encoded_data = b64encode(json_data)
    elif encoding == 'hex':
        from binascii import hexlify
        encoded_data = hexlify(json_data)
    else:
        log("Unknown payload encoding type '%s'" % encoding, level=0)
        return None
    return encoded_data.decode('ascii')


def decode_data(encoded):
    """Decode data coming from a notification event"""
    encoding = 'base64'
    from binascii import Error, unhexlify
    try:
        json_data = unhexlify(encoded)
    except (TypeError, Error):
        from base64 import b64decode
        json_data = b64decode(encoded)
    else:
        encoding = 'hex'
    return json.loads(json_data), encoding


def decode_json(data):
    encoded = json.loads(data)
    if not encoded:
        return None, None
    return decode_data(encoded[0])


def event(message, data=None, sender=None, encoding='base64'):
    """Send internal notification event"""
    data = data or {}
    sender = sender or addon_id()

    encoded = encode_data(data, encoding=encoding)
    if not encoded:
        return

    jsonrpc(method='JSONRPC.NotifyAll', params={
        'sender': '%s.SIGNAL' % sender,
        'message': message,
        'data': [encoded],
    })


def log(msg, name=None, level=1):
    """Log information to the Kodi log"""
    log_level = get_setting_int('logLevel', level)
    # A cheap info call instead of a JSON-RPC round trip on every log line
    debug_logging = getCondVisibility('System.GetBool(debug.showloginfo)')
    if not debug_logging and log_level < level:
        return
    level = LOGDEBUG if debug_logging else LOGINFO
    xlog('[%s] %s -> %s' % (addon_id(), name, msg), level=level)


def calculate_progress_steps(period):
    """Calculate a progress step"""
    if int(period) == 0:  # Avoid division by zero
        return 10.0
    return (100.0 / int(period)) / 10


def jsonrpc(**kwargs):
    """Perform JSONRPC calls"""
    if kwargs.get('id') is None:
        kwargs.update(id=0)
    if kwargs.get('jsonrpc') is None:
        kwargs.update(jsonrpc='2.0')
    return json.loads(executeJSONRPC(json.dumps(kwargs)))


def localize(string_id):
    """Return the translated string from the .po language files"""

    return ADDON.getLocalizedString(string_id)


def localize_date(date_string):
    """Localize date format"""
    date_format = getRegion('dateshort')

    try:
        # A number of assumptions are made here about date_string
        # format to avoid having to import dateutil or similar
        date_object = date(*(
            int(part)
            for part in re_split(r'[\W]', date_string)[:3]
        ))
    except (TypeError, ValueError):
        # Not a full date, e.g. a year-only firstaired from an add-on, or no date at all
        return '' if date_string is None else str(date_string)

    return date_object.strftime(date_format)


def localize_time(time):
    """Localize time format"""
    time_format = getRegion('time')

    # Strip off seconds
    time_format = time_format.replace(':%S', '')

    return time.strftime(time_format)
