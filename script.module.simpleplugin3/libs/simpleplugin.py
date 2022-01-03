# -*- coding: utf-8 -*-
# Created on: 03.06.2015
"""
SimplePlugin micro-framework for Kodi content plugins

**Author**: Roman Miroshnychenko aka Roman V.M.

**License**: `GPL v.3 <https://www.gnu.org/copyleft/gpl.html>`_
"""

from __future__ import unicode_literals
from future.builtins import (zip, super,
                             bytes, dict, int, list, object, str)
from future.utils import (PY2, PY3, iteritems, itervalues,
                          python_2_unicode_compatible)
# from future.standard_library import install_aliases
# install_aliases()

if PY3:
    basestring = str
    long = int

import os
import sys
import re
import inspect
import time
import hashlib
import pickle
from collections import namedtuple
from copy import deepcopy
from functools import wraps
from shutil import copyfile
from contextlib import contextmanager
from pprint import pformat
from platform import uname
if PY3:
    from urllib.parse import urlencode, quote_plus, urlparse, unquote_plus, parse_qs
    from typing import MutableMapping
else:
    from future.backports.urllib.parse import urlencode, quote_plus, urlparse, unquote_plus
    from urlparse import parse_qs
    from collections import MutableMapping

import xbmcaddon
import xbmc
import xbmcgui
import xbmcvfs

__all__ = ['SimplePluginError', 'Storage', 'MemStorage', 'Addon', 'Plugin',
           'RoutedPlugin', 'Params', 'log_exception', 'py2_encode',
           'py2_decode', 'translate_path']

if PY3:
    getargspec = inspect.getfullargspec
else:
    getargspec = inspect.getargspec

Route = namedtuple('Route', ['pattern', 'func'])


class SimplePluginError(Exception):
    """Custom exception"""
    pass


class TimeoutError(SimplePluginError):
    pass


def _format_vars(variables):
    """
    Format variables dictionary

    :param variables: variables dict
    :type variables: dict
    :return: formatted string with sorted ``var = val`` pairs
    :rtype: str
    """
    var_list = [(var, val) for var, val in iteritems(variables)]
    lines = []
    for var, val in sorted(var_list, key=lambda i: i[0]):
        if not (var.startswith('__') or var.endswith('__')):
            lines.append('{0} = {1}'.format(var, pformat(val)))
    return '\n'.join(lines)


def py2_encode(s, encoding='utf-8'):
    """
    Encode Python 2 ``unicode`` to ``str``

    In Python 3 the string is not changed.
    """
    if PY2 and isinstance(s, str):
        s = s.encode(encoding)
    return s


def py2_decode(s, encoding='utf-8'):
    """
    Decode Python 2 ``str`` to ``unicode``

    In Python 3 the string is not changed.
    """
    if PY2 and isinstance(s, bytes):
        s = s.decode(encoding)
    return s

def _kodi_major_version():
    kodi_version = xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]
    return kodi_version.split('.')[0]

def translate_path(*args, **kwargs):
    if _kodi_major_version() < '19':
        return xbmc.translatePath(*args, **kwargs)
    else:
        return xbmcvfs.translatePath(*args, **kwargs)


@contextmanager
def log_exception(logger=None):
    """
    Diagnostic helper context manager

    It controls execution within its context and writes extended
    diagnostic info to the Kodi log if an unhandled exception
    happens within the context. The info includes the following items:

    - System info
    - Kodi version
    - Module path.
    - Code fragment where the exception has happened.
    - Global variables.
    - Local variables.

    After logging the diagnostic info the exception is re-raised.

    Example::

        with log_exception():
            # Some risky code
            raise RuntimeError('Fatal error!')

    :param logger: logger function which must accept a single argument
        which is a log message. By default it is :func:`xbmc.log`
        with ``ERROR`` level.
    """
    try:
        yield
    except:
        if logger is None:
            logger = lambda msg: xbmc.log(py2_encode(msg), xbmc.LOGERROR)
        frame_info = inspect.trace(5)[-1]
        logger('Unhandled exception detected!')
        logger('*** Start diagnostic info ***')
        logger('System info: {0}'.format(uname()))
        logger('OS info: {0}'.format(py2_decode(xbmc.getInfoLabel('System.OSVersionInfo'))))
        logger('Kodi version: {0}'.format(
            xbmc.getInfoLabel('System.BuildVersion'))
        )
        logger('File: {0}'.format(frame_info[1]))
        context = ''
        if frame_info[4] is not None:
            for i, line in enumerate(frame_info[4], frame_info[2] - frame_info[5]):
                if i == frame_info[2]:
                    context += '{0}:>{1}'.format(str(i).rjust(5), line)
                else:
                    context += '{0}: {1}'.format(str(i).rjust(5), line)
        logger('Code context:\n' + context)
        logger('Global variables:\n' + _format_vars(frame_info[0].f_globals))
        logger('Local variables:\n' + _format_vars(frame_info[0].f_locals))
        logger('**** End diagnostic info ****')
        raise


@python_2_unicode_compatible
class Params(dict):
    """
    Params(**kwargs)

    A class that stores parsed plugin call parameters

    Parameters can be accessed both through :class:`dict` keys and
    instance properties.

    .. note:: For a missing parameter an instance property returns ``None``.

    Example:

    .. code-block:: python

        @plugin.action('foo')
        def action(params):
            foo = params['foo']  # Access by key
            bar = params.bar  # Access through property. Both variants are equal
    """
    def __getattr__(self, key):
        return self.get(key)

    def __str__(self):
        return '<Params {0}>'.format(super(Params, self).__str__())


@python_2_unicode_compatible
class Storage(MutableMapping):
    """
    Storage(storage_dir, filename='storage.pcl')

    Persistent storage for arbitrary data with a dictionary-like interface

    It is designed as a context manager and better be used
    with 'with' statement.

    :param storage_dir: directory for storage
    :type storage_dir: str
    :param filename: the name of a storage file (optional)
    :type filename: str

    Usage::

        with Storage('/foo/bar/storage/') as storage:
            storage['key1'] = value1
            value2 = storage['key2']

    .. note:: After exiting :keyword:`with` block a :class:`Storage` instance
        is invalidated. Storage contents are saved to disk only for
        a new storage or if the contents have been changed.
    """
    def __init__(self, storage_dir, filename='storage.pcl'):
        """
        Class constructor

        :type storage_dir: str
        :type filename: str
        """
        self._storage = {}
        self._hash = None
        self._filename = os.path.join(storage_dir, filename)
        try:
            with open(self._filename, 'rb') as fo:
                contents = fo.read()
            self._storage = pickle.loads(contents)
            self._hash = hashlib.md5(contents).hexdigest()
        except (IOError, pickle.PickleError, EOFError, AttributeError):
            pass

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.flush()

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        self._storage[key] = value

    def __delitem__(self, key):
        del self._storage[key]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

    def __str__(self):
        return '<Storage {0}>'.format(self._storage)

    def flush(self):
        """
        Save storage contents to disk

        This method saves new and changed :class:`Storage` contents to disk
        and invalidates the Storage instance. Unchanged Storage is not saved
        but simply invalidated.
        """
        contents = pickle.dumps(self._storage, protocol=2)
        if self._hash is None or hashlib.md5(contents).hexdigest() != self._hash:
            tmp = self._filename + '.tmp'
            start = time.time()
            while os.path.exists(tmp):
                if time.time() - start > 2.0:
                    raise TimeoutError(
                        'Exceeded timeout for saving {0} contents!'.format(self)
                    )
                xbmc.sleep(100)
            try:
                with open(tmp, 'wb') as fo:
                    fo.write(contents)
                copyfile(tmp, self._filename)
            finally:
                os.remove(tmp)
        del self._storage

    def copy(self):
        """
        Make a copy of storage contents

        .. note:: this method performs a *deep* copy operation.

        :return: a copy of storage contents
        :rtype: dict
        """
        return deepcopy(self._storage)


@python_2_unicode_compatible
class MemStorage(MutableMapping):
    """
    MemStorage(storage_id)

    In-memory storage with dict-like interface

    The data is stored in the Kodi core so contents of a MemStorage instance
    with the same ID can be shared between different Python processes.

    .. note:: Keys are case-insensitive

    .. warning:: :class:`MemStorage` does not allow to modify mutable objects
        in place! You need to assign them to variables first, modify and
        store them back to a MemStorage instance.

    Example:

    .. code-block:: python

        storage = MemStorage('foo')
        some_list = storage['bar']
        some_list.append('spam')
        storage['bar'] = some_list

    :param storage_id: ID of this storage instance
    :type storage_id: str
    :param window_id: the ID of a Kodi Window object where storage contents
        will be stored.
    :type window_id: int
    """
    def __init__(self, storage_id, window_id=10000):
        """
        :type storage_id: str
        :type window_id: int
        """
        self._id = storage_id
        self._window = xbmcgui.Window(window_id)
        try:
            self['__keys__']
        except KeyError:
            self['__keys__'] = []

    def _check_key(self, key):
        """
        :type key: str
        """
        if not isinstance(key, basestring):
            raise TypeError('Storage key must be of str type!')

    def _format_contents(self):
        """
        :rtype: str
        """
        lines = []
        for key, val in iteritems(self):
            lines.append('{0}: {1}'.format(repr(key), repr(val)))
        return ', '.join(lines)

    def __str__(self):
        return '<MemStorage {{{0}}}>'.format(self._format_contents())

    def __getitem__(self, key):
        self._check_key(key)
        full_key = py2_encode('{0}__{1}'.format(self._id, key))
        raw_item = self._window.getProperty(full_key)
        if raw_item:
            try:
                return pickle.loads(bytes(raw_item))
            except TypeError as e:
                return pickle.loads(bytes(raw_item, 'utf-8', errors='surrogateescape'))
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self._check_key(key)
        full_key = py2_encode('{0}__{1}'.format(self._id, key))
        # protocol=0 is needed for safe string handling in Python 3
        self._window.setProperty(full_key, pickle.dumps(value, protocol=0))
        if key != '__keys__':
            keys = self['__keys__']
            keys.append(key)
            self['__keys__'] = keys

    def __delitem__(self, key):
        self._check_key(key)
        full_key = py2_encode('{0}__{1}'.format(self._id, key))
        item = self._window.getProperty(full_key)
        if item:
            self._window.clearProperty(full_key)
            if key != '__keys__':
                keys = self['__keys__']
                keys.remove(key)
                self['__keys__'] = keys
        else:
            raise KeyError(key)

    def __contains__(self, key):
        self._check_key(key)
        full_key = py2_encode('{0}__{1}'.format(self._id, key))
        item = self._window.getProperty(full_key)
        return bool(item)

    def __iter__(self):
        return iter(self['__keys__'])

    def __len__(self):
        return len(self['__keys__'])


@python_2_unicode_compatible
class Addon(object):
    """
    Base addon class

    Provides access to basic addon parameters

    :param id_: addon id, e.g. 'plugin.video.foo' (optional)
    :type id_: str
    """
    def __init__(self, id_=''):
        """
        Class constructor

        :type id_: str
        """
        self._addon = xbmcaddon.Addon(id_)
        self._profile_dir = py2_decode(
            translate_path(self._addon.getAddonInfo('profile'))
        )
        self._ui_strings_map = None
        if not os.path.exists(self._profile_dir):
            os.mkdir(self._profile_dir)

    def __str__(self):
        return '<Addon [{0}]>'.format(self.id)

    @property
    def addon(self):
        """
        Kodi Addon instance that represents this Addon

        :return: Addon instance
        :rtype: xbmcaddon.Addon
        """
        return self._addon

    @property
    def id(self):
        """
        Addon ID

        :return: Addon ID, e.g. 'plugin.video.foo'
        :rtype: str
        """
        return self._addon.getAddonInfo('id')

    @property
    def path(self):
        """
        Addon path

        :return: path to the addon folder
        :rtype: unicode
        """
        return py2_decode(self._addon.getAddonInfo('path'))

    @property
    def icon(self):
        """
        Addon icon

        :return: path to the addon icon image
        :rtype: str
        """
        icon = self._addon.getAddonInfo('icon')
        if not icon:
            icon = os.path.join(self.path, 'icon.png')
        if os.path.exists(icon):
            return icon
        else:
            return ''

    @property
    def fanart(self):
        """
        Addon fanart

        :return: path to the addon fanart image
        :rtype: str
        """
        fanart = self._addon.getAddonInfo('fanart')
        if not fanart :
            fanart = os.path.join(self.path, 'fanart.jpg')
        if os.path.exists(fanart):
            return fanart
        else:
            return ''

    @property
    def profile_dir(self):
        """
        Addon config dir

        :return: path to the addon profile dir
        :rtype: str
        """
        return self._profile_dir

    @property
    def version(self):
        """
        Addon version

        :return: addon version
        :rtype: str
        """
        return self._addon.getAddonInfo('version')

    @property
    def name(self):
        """
        Addon name

        :return: addon name
        :rtype: str
        """
        return self._addon.getAddonInfo('name')

    @property
    def author(self):
        """
        Addon author

        :return: addon author
        :rtype: str
        """
        return self._addon.getAddonInfo('author')

    @property
    def changelog(self):
        """
        Addon changelog

        :return: addon changelog
        :rtype: str
        """
        return self._addon.getAddonInfo('changelog')

    @property
    def description(self):
        """
        Addon description

        :return: addon description
        :rtype: str
        """
        return self._addon.getAddonInfo('description')

    @property
    def disclaimer(self):
        """
        Addon disclaimer

        :return: addon disclaimer
        :rtype: str
        """
        return self._addon.getAddonInfo('disclaimer')

    @property
    def stars(self):
        """
        Addon stars

        :return: addon stars
        :rtype: str
        """
        return self._addon.getAddonInfo('stars')

    @property
    def summary(self):
        """
        Addon summary

        :return: addon summary
        :rtype: str
        """
        return self._addon.getAddonInfo('summary')

    @property
    def type(self):
        """
        Addon type

        :return: addon type
        :rtype: str
        """
        return self._addon.getAddonInfo('type')

    def get_localized_string(self, id_):
        """
        Get localized UI string

        :param id_: UI string ID
        :type id_: int
        :return: UI string in the current language
        :rtype: unicode
        """
        return self._addon.getLocalizedString(id_)

    def get_setting(self, id_, convert=True):
        """
        Get addon setting

        If ``convert=True``, 'bool' settings are converted to Python
        :class:`bool` values, and numeric strings to Python :class:`long` or
        :class:`float` depending on their format.

        .. note:: Settings can also be read via :class:`Addon` instance
            poperties named as the respective settings. I.e. ``addon.foo``
            is equal to ``addon.get_setting('foo')``.

        :param id_: setting ID
        :type id_: str
        :param convert: try to guess and convert the setting to an appropriate type
            E.g. ``'1.0'`` will be converted to float ``1.0`` number,
            ``'true'`` to ``True`` and so on.
        :type convert: bool
        :return: setting value
        """
        setting = py2_decode(self._addon.getSetting(id_))
        if convert:
            if setting == 'true':
                return True  # Convert boolean strings to bool
            elif setting == 'false':
                return False
            elif re.search(r'^-?\d+$', setting) is not None:
                return long(setting)  # Convert numeric strings to long
            elif re.search(r'^-?\d+\.\d+$', setting) is not None:
                return float(setting)  # Convert numeric strings with a dot to float
        return setting

    def set_setting(self, id_, value):
        """
        Set addon setting

        Python :class:`bool` type are converted to ``'true'`` or ``'false'``
        Non-string/non-unicode values are converted to strings.

        .. warning:: Setting values via :class:`Addon` instance properties
            is not supported! Values can only be set using
            :meth:`Addon.set_setting` method.

        :param id_: setting ID
        :type id_: str
        :param value: setting value
        """
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        elif not isinstance(value, basestring):
            value = str(value)
        self._addon.setSetting(id_, py2_encode(value))

    def log(self, message, level=xbmc.LOGDEBUG):
        """
        Add message to Kodi log starting with Addon ID

        :param message: message to be written into the Kodi log
        :type message: str
        :param level: log level. :mod:`xbmc` module provides the necessary
            symbolic constants. Default: ``xbmc.LOGDEBUG``
        :type level: int
        """
        xbmc.log(
            py2_encode('{0} [v.{1}]: {2}'.format(self.id, self.version, message)),
            level
        )

    def log_notice(self, message):
        """
        Add NOTICE message to the Kodi log

        :param message: message to write to the Kodi log
        :type message: str
        """
        if _kodi_major_version() < '19':
            self.log(message, xbmc.LOGNOTICE)
        else:
            self.log(message, xbmc.LOGINFO)

    def log_warning(self, message):
        """
        Add WARNING message to the Kodi log

        :param message: message to write to the Kodi log
        :type message: str
        """
        self.log(message, xbmc.LOGWARNING)

    def log_error(self, message):
        """
        Add ERROR message to the Kodi log

        :param message: message to write to the Kodi log
        :type message: str
        """
        self.log(message, xbmc.LOGERROR)

    def log_debug(self, message):
        """
        Add debug message to the Kodi log

        :param message: message to write to the Kodi log
        :type message: str
        """
        self.log(message, xbmc.LOGDEBUG)

    def get_storage(self, filename='storage.pcl'):
        """
        Get a persistent :class:`Storage` instance for storing arbitrary values
        between addon calls.

        A :class:`Storage` instance can be used as a context manager.

        Example::

            with plugin.get_storage() as storage:
                storage['param1'] = value1
                value2 = storage['param2']

        .. note:: After exiting :keyword:`with` block a :class:`Storage`
            instance is invalidated.

        :param filename: the name of a storage file (optional)
        :type filename: str
        :return: Storage object
        :rtype: Storage
        """
        return Storage(self.profile_dir, filename)

    def get_mem_storage(self, storage_id='', window_id=10000):
        """
        Creates an in-memory storage for this addon with :class:`dict`-like
        interface

        The storage can store picklable Python objects as long as
        Kodi is running and storage contents can be shared between
        Python processes. Different addons have separate storages,
        so storages with the same names created with this method
        do not conflict.

        Example::

            addon = Addon()
            storage = addon.get_mem_storage()
            foo = storage['foo']
            storage['bar'] = bar

        :param storage_id: optional storage ID (case-insensitive).
        :type storage_id: str
        :param window_id: the ID of a Kodi Window object where storage contents
            will be stored.
        :type window_id: int
        :return: in-memory storage for this addon
        :rtype: MemStorage
        """
        if storage_id:
            storage_id = '{0}_{1}'.format(self.id, storage_id)
        return MemStorage(storage_id, window_id)

    def _get_cached_data(self, cache, func, duration, *args, **kwargs):
        """
        Get data from a cache object

        :param cache: cache object
        :param func: function to cache
        :param duration: cache duration
        :param args: function args
        :param kwargs: function kwargs
        :return: function return data
        """
        if duration <= 0:
            raise ValueError('Caching duration cannot be zero or negative!')
        current_time = time.time()
        key = func.__name__ + str(args) + str(kwargs)
        try:
            data, timestamp = cache[key]
            if current_time - timestamp > duration * 60:
                raise KeyError
            self.log_debug('Cache hit: {0}'.format(key))
        except KeyError:
            self.log_debug('Cache miss: {0}'.format(key))
            data = func(*args, **kwargs)
            cache[key] = (data, current_time)
        return data

    def cached(self, duration=10):
        """
        Cached decorator

        Used to cache function return data

        Usage::

            @plugin.cached(30)
            def my_func(*args, **kwargs):
                # Do some stuff
                return value

        :param duration: caching duration in min (positive values only)
        :type duration: int
        :raises ValueError: if duration is zero or negative
        """
        def outer_wrapper(func):
            @wraps(func)
            def inner_wrapper(*args, **kwargs):
                with self.get_storage('__cache__.pcl') as cache:
                    return self._get_cached_data(cache, func, duration,
                                                 *args, **kwargs)
            return inner_wrapper
        return outer_wrapper

    def mem_cached(self, duration=10):
        """
        In-memory cache decorator

        Usage::

            @plugin.mem_cached(30)
            def my_func(*args, **kwargs):
                # Do some stuff
                return value

        :param duration: caching duration in min (positive values only)
        :type duration: int
        :raises ValueError: if duration is zero or negative
        """
        def outer_wrapper(func):
            @wraps(func)
            def inner_wrapper(*args, **kwargs):
                cache = self.get_mem_storage('***cache***')
                return self._get_cached_data(cache, func, duration,
                                             *args, **kwargs)
            return inner_wrapper
        return outer_wrapper

    def gettext(self, ui_string):
        """
        Get a translated UI string from addon localization files.

        This function emulates GNU Gettext for more convenient access
        to localized addon UI strings. To reduce typing this method object
        can be assigned to a ``_`` (single underscore) variable.

        For using gettext emulation :meth:`Addon.initialize_gettext` method
        needs to be called first. See documentation for that method for more
        info about Gettext emulation.

        :param ui_string: a UI string from English :file:`strings.po`.
        :type ui_string: str
        :return: a UI string from translated :file:`strings.po`.
        :rtype: unicode
        :raises SimplePluginError: if :meth:`Addon.initialize_gettext`
            wasn't called first or if a string is not found in
            English :file:`strings.po`.
        """
        if self._ui_strings_map is not None:
            try:
                return self.get_localized_string(
                    self._ui_strings_map['strings'][ui_string]
                )
            except KeyError:
                raise SimplePluginError(
                    'UI string "{0}" is not found in strings.po!'.format(
                        ui_string)
                    )
        else:
            raise SimplePluginError('Addon localization is not initialized!')

    def initialize_gettext(self):
        """
        Initialize GNU gettext emulation in addon

        Kodi localization system for addons is not very convenient
        because you need to operate with numeric string codes instead
        of UI strings themselves which reduces code readability and
        may lead to errors. The :class:`Addon` class provides facilities
        for emulating GNU Gettext localization system.

        This allows to use UI strings from addon's English :file:`strings.po`
        file instead of numeric codes to return localized strings from
        respective localized :file:`.po` files.

        This method returns :meth:`Addon.gettext` method object that
        can be assigned to a short alias to reduce typing. Traditionally,
        ``_`` (a single underscore) is used for this purpose.

        Example::

            addon = simpleplugin.Addon()
            _ = addon.initialize_gettext()

            xbmcgui.Dialog().notification(_('Warning!'), _('Something happened'))

        In the preceding example the notification strings will be replaced
        with localized versions if these strings are translated.

        :return: :meth:`Addon.gettext` method object
        :raises SimplePluginError: if the addon's English :file:`strings.po`
            file is missing
        """
        strings_po = os.path.join(self.path, 'resources', 'language',
                                  'resource.language.en_gb', 'strings.po')
        if not os.path.exists(strings_po):
            strings_po = os.path.join(self.path, 'resources', 'language',
                                      'English', 'strings.po')
        if os.path.exists(strings_po):
            with open(strings_po, 'rb') as fo:
                raw_strings = fo.read()
            raw_strings_hash = hashlib.md5(raw_strings).hexdigest()
            ui_strings_map = self.get_mem_storage('__gettext__')
            if raw_strings_hash != ui_strings_map.get('hash', ''):
                ui_strings = self._parse_po(
                    raw_strings.decode('utf-8').split('\n')
                )
                self._ui_strings_map = {
                    'hash': raw_strings_hash,
                    'strings': ui_strings
                }
                ui_strings_map['hash'] = raw_strings_hash
                ui_strings_map['strings'] = ui_strings.copy()
            else:
                self._ui_strings_map = {}
                self._ui_strings_map.update(ui_strings_map)
        else:
            raise SimplePluginError('Unable to initialize localization because '
                                    'of missing English strings.po!')
        return self.gettext

    def _parse_po(self, strings):
        """
        Parses ``strings.po`` file into a dict of {'string': id} items.
        """
        ui_strings = {}
        string_id = None
        for string in strings:
            if string_id is None and 'msgctxt' in string:
                string_id = int(re.search(r'"#(\d+)"', string, re.U).group(1))
            elif string_id is not None and 'msgid' in string:
                ui_strings[re.search(r'"(.*?)"', string, re.U).group(1)] = string_id
                string_id = None
        return ui_strings


@python_2_unicode_compatible
class Plugin(Addon):
    """
    Plugin class with URL query string routing.

    It provides a simplified plugin call routing mechanism using URL query strings.
    A URL query string must contain "action" parameter that defines which function
    will be invoked during this plugin call.

    :param id_: plugin's id, e.g. 'plugin.video.foo' (optional)
    :type id_: str
    """
    def __init__(self, id_=''):
        """
        Class constructor

        :type id_: str
        """
        super(Plugin, self).__init__(id_)
        self._url = 'plugin://{0}/'.format(self.id)
        self._handle = None
        self.actions = {}
        self._params = None

    def __str__(self):
        return '<Plugin {0}>'.format(sys.argv)

    @property
    def params(self):
        """
        Get plugin call parameters

        :return: plugin call parameters
        :rtype: Params
        """
        return self._params

    @property
    def handle(self):
        """
        Get plugin handle

        :return: plugin handle
        :rtype: int
        """
        return self._handle

    @staticmethod
    def get_params(paramstring):
        """
        Convert a URL-encoded paramstring to a Python dict

        :param paramstring: URL-encoded paramstring
        :type paramstring: str
        :return: parsed paramstring
        :rtype: Params
        """
        raw_params = parse_qs(paramstring)
        params = Params()
        for key, value in iteritems(raw_params):
            param_value = value[0] if len(value) == 1 else value
            params[key] = py2_decode(param_value)
        return params

    def get_url(self, plugin_url='', **kwargs):
        """
        Construct a callable URL for a virtual directory item

        If plugin_url is empty, a current plugin URL is used.
        kwargs are converted to a URL-encoded string of plugin call parameters
        To call a plugin action, 'action' parameter must be used,
        if 'action' parameter is missing, then the plugin root action is called
        If the action is not added to :class:`Plugin` actions,
        :class:`PluginError` will be raised.

        :param plugin_url: plugin URL with trailing / (optional)
        :type plugin_url: str
        :param kwargs: pairs of key=value items
        :return: a full plugin callback URL
        :rtype: str
        """
        url = plugin_url or self._url
        if kwargs:
            return '{0}?{1}'.format(url, urlencode(kwargs, doseq=True))
        return url

    def action(self, name=None):
        """
        Action decorator

        Defines plugin callback action. If action's name is not defined
        explicitly, then the action is named after the decorated function.

        .. warning:: Action's name must be unique.

        A plugin must have at least one action named ``'root'``
        implicitly or explicitly.

        Example:

        .. code-block:: python

            # The action is implicitly named 'root' after the decorated function
            @plugin.action()
            def root(params):
                pass

            @plugin.action('foo')  # The action name is set explicitly
            def foo_action(params):
                pass

        :param name: action's name (optional).
        :type name: str
        :raises SimplePluginError: if the action with such name is already defined.
        """
        def wrap(func, name=name):
            if name is None:
                name = func.__name__
            if name in self.actions:
                raise SimplePluginError(
                    'Action "{0}" already defined!'.format(name)
                )
            self.actions[name] = func
            return func
        return wrap

    def run(self):
        """
        Run plugin

        :raises SimplePluginError: if unknown action string is provided.
        """
        self._handle = int(sys.argv[1])
        self._params = self.get_params(sys.argv[2][1:])
        self.log_debug(str(self))
        result = self._resolve_function()
        if result is not None:
            raise SimplePluginError(
                'A decorated function must not return any value! '
                'It returned {0} instead.'.format(result)
            )

    def _resolve_function(self):
        """
        Resolve action from plugin call params and call the respective callable
        function

        :return: action callable's return value
        """
        self.log_debug('Actions: {0}'.format(str(list(self.actions.keys()))))
        action = self._params.get('action', 'root')
        self.log_debug('Called action {0} with params {1}'.format(
            action, str(self._params))
        )
        try:
            action_callable = self.actions[action]
        except KeyError:
            raise SimplePluginError('Invalid action: "{0}"!'.format(action))
        else:
            with log_exception(self.log_error):
                # inspect.isfunction is needed for tests
                if (inspect.isfunction(action_callable) and
                        not getargspec(action_callable).args):
                    return action_callable()
                else:
                    return action_callable(self._params)


@python_2_unicode_compatible
class RoutedPlugin(Plugin):
    """
    Plugin class that implements "pretty URL" routing similar to Flask and Bottle
    web-frameworks

    :param id_: plugin's id, e.g. 'plugin.video.foo' (optional)
    :type id_: str
    """
    def __init__(self, id_=''):
        """
        :param id_: plugin's id, e.g. 'plugin.video.foo' (optional)
        :type id_: str
        """
        super(RoutedPlugin, self).__init__(id_)
        self._routes = {}

    def __str__(self):
        return '<RoutedPlugin {0}>'.format(sys.argv)

    def url_for(self, func_, *args, **kwargs):
        """
        Build a URL for a plugin route

        This method performs reverse resolving a plugin callback URL for
        the named route. If route's name is not set explicitly, then the name
        of a decorated function is used as the name of the corresponding route.
        The method can optionally take positional args and kwargs.
        If any positional args are provided their values replace
        variable placeholders by position.

        .. warning:: The number of positional args must not exceed
            the number of variable placeholders!

        If any kwargs are provided their values replace variable placeholders
        by name. If the number of kwargs provided exceeds the number of variable
        placeholders, then the rest of the kwargs are added to the URL
        as a query string.

        .. note:: All :class:`unicode` arguments are encoded with UTF-8 encoding.

        Let's assume that the ID of our plugin is ``plugin.acme``.
        The following examples will show how to use this method to resolve
        callback URLs for this plugin.

        Example 1::

            @plugin.route('/foo')
            def foo():
                pass
            url = plugin.url_for('foo')
            # url = 'plugin://plugin.acme/foo'

        Example 2::

            @plugin.route('/foo/<param>')
            def foo(param):
                pass
            url = plugin.url_for('foo', param='bar')
            # url = 'plugin://plugin.acme/foo/bar'

        Example 3::

            plugin.route('/foo/<param>')
            def foo(param):
                pass
            url = plugin.url_for('foo', param='bar', ham='spam')
            # url = 'plugin://plugin.acme/foo/bar?ham=spam

        :param func_: route's name or a decorated function object.
        :type func_: str or types.FunctionType
        :param args: positional arguments.
        :param kwargs: keyword arguments.
        :return: full plugin call URL for the route.
        :rtype: str
        :raises simpleplugin.SimplePluginError: if a route with such name
            does not exist or on arguments mismatch.
        """
        if isinstance(func_, basestring):
            name = func_
        elif inspect.isfunction(func_) or inspect.ismethod(func_):
            name = func_.__name__
        else:
            raise TypeError('The first argument to url_for must be '
                            'a route\'s name or a route function object!')
        try:
            pattern = self._routes[name].pattern
        except KeyError:
            raise SimplePluginError('Route "{0}" does not exist!'.format(name))
        matches = re.findall(r'/(<\w+?>)', pattern)
        if len(args) + len(kwargs) < len(matches) or len(args) > len(matches):
            raise SimplePluginError(
                'Arguments for the route "{0}" '
                'do not match placeholders!'.format(name)
            )
        if matches:
            for arg, match in zip(args, matches):
                pattern = pattern.replace(
                    match,
                    quote_plus(py2_encode(str(arg)))
                )
            # list allows to manipulate the dict during iteration
            for key, value in list(iteritems(kwargs)):
                for match in matches[len(args):]:

                    match_string = match[1:-1]
                    match_parts = match_string.split('__')
                    if len(match_parts) > 1:
                        match_string = match_parts[1]

                    if key == match_string:
                        pattern = pattern.replace(
                            match, quote_plus(py2_encode(str(value)))
                        )
                        del kwargs[key]
        url = 'plugin://{0}{1}'.format(self.id, pattern)
        if kwargs:
            url += '?' + urlencode(kwargs, doseq=True)
        return url

    get_url = url_for

    def route(self, pattern, name=None):
        """
        Route decorator for plugin callback routes

        The route decorator is used to define plugin callback routes
        similar to a URL routing mechanism in Flask and Bottle Python
        web-frameworks. The plugin routing mechanism calls decorated functions
        by matching a path in a plugin callback URL (passed as ``sys.argv[0]``)
        to a route pattern. A route pattern *must* start with a forward slash
        ``/``. An end slash is optional. A plugin must have at least the root
        route with ``'/'`` pattern. Bu default a route is named by the decorated
        function, but route's name can be set explicitly by providing
        the 2nd optional ``name`` argument.

        .. warning:: Route names must be unique!

        Example 1::

            @plugin.route('/foo')
            def foo_function():
                pass

        In the preceding example ``foo_function`` will be called when the plugin
        is invoked with ``plugin://plugin.acme/foo/`` callback URL.
        A route pattern can contain variable placeholders
        (marked with angular brackets ``<>``) that are used to pass arguments
        to a route function.

        Example 2::

            @plugin.route('/foo/<param>')
            def foo_function(param):
                pass

        In the preceding example the part of a callback path marked with
        ``<param>`` placeholder will be passed to the function as an argument.
        The name of a placeholder must be the same as the name of
        the corresponding parameter. By default arguments are passed as strings.
        The ``int`` and ``float`` prefixes can be used to pass arguments
        as :class:`int` and :class:`float` numbers, for example ``<int:foo>``
        or ``<float:bar>``.

        Example 3::

            @plugin.route('/add/<int:param1>/<int:param2>')
            def addition(param1, param2):
                sum = param1 + param2

        A function can have multiple route decorators. In this case additional
        routes must have explicitly defined names. If a route has less variable
        placeholders than function parameters, "missing" function parameters
        must have default values.

        Example 4::

            @plugin.route('/foo/<param>', name='foo_route')
            @plugin.route('/bar')
            def some_function(param='spam'):
                # Do something

        In the preceding example ``some_function`` can be called through
        2 possible routes. If the function is called through the 1st route
        (``'foo_route'``) ``<param>`` value will be passed as an argument.
        The 2nd route will call the function with the default argument
        ``'spam'`` because this route has no variable placeholders to pass
        arguments to the function. The order of the ``route`` decorators
        does not matter but each route must have a unique name.

        .. note:: A route pattern must start with a forward slash ``/``
            and must not have a slash at the end.

        :param pattern: route matching pattern
        :type pattern: str
        :param name: route's name (optional). If no name is provided,
            the route is named after the decorated function.
            The name must be unique.
        :type name: str
        """
        def wrapper(func, pattern=pattern, name=name):
            if name is None:
                name = func.__name__
            if name in self._routes:
                raise SimplePluginError(
                    'The route "{0}" already exists!'.format(name)
                )
            pattern = pattern.replace('int:', 'int__'
                                      ).replace('float:', 'float__')
            self._routes[name] = Route(pattern, func)
            return func
        return wrapper

    def _resolve_function(self):
        """
        Resolve route from plugin callback path and call the respective
        route function

        :return: route function's return value
        """
        path = urlparse(sys.argv[0]).path
        self.log_debug('Routes: {0}'.format(self._routes))
        for route in itervalues(self._routes):
            if route.pattern == path:
                kwargs = {}
                self.log_debug(
                    'Calling {0} with kwargs {1}'.format(route, kwargs))
                with log_exception(self.log_error):
                    return route.func(**kwargs)

        for route in itervalues(self._routes):
            pattern = route.pattern
            if not pattern.count('/') == path.count('/'):
                continue
            while True:
                pattern, count = re.subn(r'/(<\w+?>)', r'/(?P\1.+?)', pattern)
                if not count:
                    break
            match = re.search(r'^' + pattern + r'$', path)
            if match is not None:
                kwargs = match.groupdict()
                # list allows to manipulate the dict during iteration
                for key, value in list(iteritems(kwargs)):
                    if key.startswith('int__') or key.startswith('float__'):
                        del kwargs[key]
                        if key.startswith('int__'):
                            key = key[5:]
                            value = int(value)
                        else:
                            key = key[7:]
                            value = float(value)
                        kwargs[key] = value
                    else:
                        kwargs[key] = py2_decode(unquote_plus(value))
                self.log_debug(
                    'Calling {0} with kwargs {1}'.format(route, kwargs))
                with log_exception(self.log_error):
                    return route.func(**kwargs)
        raise SimplePluginError(
            'No route matches the path "{0}"!'.format(path)
        )

    def action(self, name=None):
        raise NotImplementedError(
            'RoutedPlugin does not support action decorator. '
            'Use route decorator instead.'
        )
