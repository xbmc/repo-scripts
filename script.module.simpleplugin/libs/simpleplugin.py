# -*- coding: utf-8 -*-
# Created on: 03.06.2015
"""
SimplePlugin micro-framework for Kodi content plugins

**Author**: Roman Miroshnychenko aka Roman V.M.

**License**: `GPL v.3 <https://www.gnu.org/copyleft/gpl.html>`_
"""

import os
import sys
import re
from datetime import datetime, timedelta
from cPickle import dump, load, PickleError
from urlparse import parse_qs
from urllib import urlencode
import xbmcaddon
import xbmc
import xbmcplugin
import xbmcgui


class PluginError(Exception):
    """Custom exception"""
    pass


class Storage(object):
    """
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

    .. note:: After exiting :keyword:`with` block a :class:`Storage` instance is invalidated.
    """
    def __init__(self, storage_dir, filename='storage.pcl'):
        """
        Class constructor
        """
        self._storage = {}
        filename = os.path.join(storage_dir, filename)
        if os.path.exists(filename):
            mode = 'r+b'
        else:
            mode = 'w+b'
        self._file = open(filename, mode)
        try:
            self._storage = load(self._file)
        except (PickleError, EOFError):
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        return False

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        self._storage[key] = value

    def __delitem__(self, key):
        del self._storage[key]

    def __contains__(self, item):
        return item in self._storage

    def __iter__(self):
        return self.iterkeys()

    def get(self, key, default=None):
        return self._storage.get(key, default)

    def iteritems(self):
        return self._storage.iteritems()

    def iterkeys(self):
        return self._storage.iterkeys()

    def itervalues(self):
        return self._storage.itervalues()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def flush(self):
        """
        Flush storage contents to disk

        This method saves all :class:`Storage` contents to disk
        and invalidates the Storage instance.
        """
        self._file.seek(0)
        dump(self._storage, self._file)
        self._file.truncate()
        self._file.close()
        del self._file
        del self._storage


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
        """
        self._addon = xbmcaddon.Addon(id_)
        self._configdir = xbmc.translatePath(self._addon.getAddonInfo('profile')).decode('utf-8')
        if not os.path.exists(self._configdir):
            os.mkdir(self._configdir)

    def __getattr__(self, item):
        """
        Get addon setting as an Addon instance attribute

        E.g. addon.my_setting is equal to addon.get_setting('my_setting')

        :param item:
        :type item: str
        """
        return self.get_setting(item)

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
        :rtype: str
        """
        return self._addon.getAddonInfo('path').decode('utf-8')

    @property
    def icon(self):
        """
        Addon icon

        :return: path to the addon icon image
        :rtype: str
        """
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
        fanart = os.path.join(self.path, 'fanart.jpg')
        if os.path.exists(fanart):
            return fanart
        else:
            return ''

    @property
    def config_dir(self):
        """
        Addon config dir

        :return: path to the addon config dir
        :rtype: str
        """
        return self._configdir

    def get_localized_string(self, id_):
        """
        Get localized UI string

        :param id_: UI string ID
        :type id_: int
        :return: UI string in the current language
        :rtype: unicode
        """
        return self._addon.getLocalizedString(id_).encode('utf-8')

    def get_setting(self, id_, convert=True):
        """
        Get addon setting

        If ``convert=True``, 'bool' settings are converted to Python :class:`bool` values,
        and numeric strings to Python :class:`long` or :class:`float` depending on their format.

        .. note:: Settings can also be read via :class:`Addon` instance poperties named as the respective settings.
            I.e. ``addon.foo`` is equal to ``addon.get_setting('foo')``.

        :param id_: setting ID
        :type id_: str
        :param convert: try to guess and convert the setting to an appropriate type
            E.g. ``'1.0'`` will be converted to float ``1.0`` number, ``'true'`` to ``True`` and so on.
        :type convert: bool
        :return: setting value
        """
        setting = self._addon.getSetting(id_)
        if convert:
            if setting == 'true':
                return True  # Convert boolean strings to bool
            elif setting == 'false':
                return False
            elif re.search(r'^\-?\d+$', setting) is not None:
                return long(setting)  # Convert numeric strings to long
            elif re.search(r'^\-?\d+\.\d+$', setting) is not None:
                return float(setting)  # Convert numeric strings with a dot to float
        return setting

    def set_setting(self, id_, value):
        """
        Set addon setting

        Python :class:`bool` type are converted to ``'true'`` or ``'false'``
        Non-string/non-unicode values are converted to strings.

        .. warning:: Setting values via :class:`Addon` instance properties is not supported!
            Values can only be set using :meth:`Addon.set_setting` method.

        :param id_: setting ID
        :type id_: str
        :param value: setting value
        """
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        elif not isinstance(value, (str, unicode)):
            value = str(value)
        self._addon.setSetting(id_, value)

    def log(self, message, level=0):
        """
        Add message to Kodi log starting with Addon ID

        :param message: message to be written into the Kodi log
        :type message: str
        :param level: log level. :mod:`xbmc` module provides the necessary symbolic constants.
            Default: ``xbmc.LOGDEBUG``
        :type level: int
        """
        xbmc.log('{0}: {1}'.format(self.id, message), level)

    def get_storage(self, filename='storage.pcl'):
        """
        Get a persistent :class:`Storage` instance for storing arbitrary values between addon calls.

        A :class:`Storage` instance can be used as a context manager.

        Example::

            with plugin.get_storage() as storage:
                storage['param1'] = value1
                value2 = storage['param2']

        .. note:: After exiting :keyword:`with` block a :class:`Storage` instance is invalidated.

        :param filename: the name of a storage file (optional)
        :type filename: str
        :return: Storage object
        :rtype: Storage
        """
        return Storage(self.config_dir, filename)

    def cached(self, duration=10):
        """
        Cached decorator

        Used to cache function return data

        Usage::

            @plugin.cached(30)
            def my_func(*args, **kwargs):
                # Do some stuff
                return value

        :param duration: cache time in min, negative value -- cache indefinitely
        :type duration: int
        """
        def outer_wrapper(func):
            def inner_wrapper(*args, **kwargs):
                with self.get_storage(filename='cache.pcl') as cache:
                    current_time = datetime.now()
                    key = func.__name__ + str(args) + str(kwargs)
                    try:
                        data, timestamp = cache[key]
                        if duration > 0 and current_time - timestamp > timedelta(minutes=duration):
                            raise KeyError
                    except KeyError:
                        data = func(*args, **kwargs)
                        cache[key] = (data, current_time)
                return data
            return inner_wrapper
        return outer_wrapper


class Plugin(Addon):
    """
    Plugin class

    :param id_: plugin's id, e.g. 'plugin.video.foo' (optional)
    :type id_: str

    This class provides a simplified API to create virtual directories of playable items
    for Kodi content plugins.
    :class:`simpleplugin.Plugin` uses a concept of callable plugin actions (functions or methods)
    that are mapped to 'action' parameters via actions instance property.
    A Plugin instance must have at least one action for its root section
    mapped to 'root' string.

    Minimal example::

        from simpleplugin import Plugin

        plugin = Plugin()

        def root_action(params):
            return [{'label': 'Foo',
                    'url': plugin.get_url(action='some_action', param='Foo')},
                    {'label': 'Bar',
                    'url': plugin.get_url(action='some_action', param='Bar')}]

        def some_action(params):
            return [{'label': params['param']}]

        plugin.actions['root'] = root_action  # Mandatory item!
        plugin.actions['some_action'] = some_action
        plugin.run()

    .. warning:: You need to map function or method objects without round brackets!

    E.g.::

        plugin.actions['some_action'] = some_action  # Correct :)
        plugin.actions['some_action'] = some_action()  # Wrong! :(

    An action callable receives 1 parameter -- params.
    params is a dict containing plugin call parameters (including action string)
    The action callable can return
    either a list of dictionaries representing Kodi virtual directory items
    or a resolved playable path (:class:`str` or :obj:`unicode`) for Kodi to play.

    Example 1::

        def list_action(params):
            listing = get_listing(params)  # Some external function to create listing
            return listing

    Example 2::

        def play_action(params):
            path = get_path(params)  # Some external function to get a playable path
            return path

    listing is a Python list of dict items.

    Each dict item can contain the following properties:

    - label -- item's label (default: ``''``).
    - label2 -- item's label2 (default: ``''``).
    - thumb -- item's thumbnail (default: ``''``).
    - icon -- item's icon (default: ``''``).
    - path -- item's path (default: ``''``).
    - fanart -- item's fanart (optional).
    - art -- a dict containing all item's graphic (see :meth:`xbmcgui.ListItem.setArt` for more info) -- optional.
    - stream_info -- a dictionary of ``{stream_type: {param: value}}`` items
      (see :meth:`xbmcgui.ListItem.addStreamInfo`) -- optional.
    - info --  a dictionary of ``{media: {param: value}}`` items
      (see :meth:`xbmcgui.ListItem.setInfo`) -- optional
    - context_menu - a list or a tuple. A list must contain 2-item tuples ``('Menu label', 'Action')``.
      If a list is provided then the items from the tuples are added to the item's context menu.
      Alternatively, context_menu can be a 2-item tuple. The 1-st item is a list as described above,
      and the 2-nd is a boolean value for replacing items. If ``True``, context menu will contain only
      the provided items, if ``False`` - the items are added to an existing context menu.
      context_menu param is optional.
    - url -- a callback URL for this list item.
    - is_playable -- if ``True``, then this item is playable and must return a playable path or
     be resolved via :meth:`Plugin.resolve_url` (default: ``False``).
    - is_folder -- if ``True`` then the item will open a lower-level sub-listing. if ``False``,
      the item either is a playable media or a general-purpose script
      which neither creates a virtual folder nor points to a playable media (default: C{True}).
      if ``'is_playable'`` is set to ``True``, then ``'is_folder'`` value automatically assumed to be ``False``.
    - subtitles -- the list of paths to subtitle files (optional).
    - mime -- item's mime type (optional).
    - list_item -- an 'class:`xbmcgui.ListItem` instance (optional).
      It is used when you want to set all list item properties by yourself.
      If ``'list_item'`` property is present, all other properties,
      except for ``'url'`` and ``'is_folder'``, are ignored.

    Example::

        listing = [{    'label': 'Label',
                        'label2': 'Label 2',
                        'thumb': 'thumb.png',
                        'icon': 'icon.png',
                        'fanart': 'fanart.jpg',
                        'art': {'clearart': 'clearart.png'},
                        'stream_info': {'video': {'codec': 'h264', 'duration': 1200},
                                        'audio': {'codec': 'ac3', 'language': 'en'}},
                        'info': {'video': {'genre': 'Comedy', 'year': 2005}},
                        'context_menu': ([('Menu Item', 'Action')], True),
                        'url': 'plugin:/plugin.video.test/?action=play',
                        'is_playable': True,
                        'is_folder': False,
                        'subtitles': ['/path/to/subtitles.en.srt', '/path/to/subtitles.uk.srt'],
                        'mime': 'video/mp4'
                        }]

    Alternatively, an action callable can use :meth:`Plugin.create_listing` and :meth:`Plugin.resolve_url`
    static methods to set additional parameters for Kodi.

    Example 3::

        def list_action(params):
            listing = get_listing(params)  # Some external function to create listing
            return Plugin.create_listing(listing, sort_methods=(2, 10, 17), view_mode=500)

    Example 4::

        def play_action(params):
            path = get_path(params)  # Some external function to get a playable path
            return Plugin.resolve_url(path, succeeded=True)

    If an action callable performs any actions other than creating a listing or
    resolving a playable URL, it must return ``None``.
    """
    def __init__(self, id_=''):
        """
        Class constructor
        """
        super(Plugin, self).__init__(id_)
        self._url = 'plugin://{0}/'.format(self.id)
        self._handle = None
        self.actions = {}

    @staticmethod
    def get_params(paramstring):
        """
        Convert a URL-encoded paramstring to a Python dict

        :param paramstring: URL-encoded paramstring
        :type paramstring: str
        :return: parsed paramstring
        :rtype: dict
        """
        params = parse_qs(paramstring)
        for key, value in params.iteritems():
            params[key] = value[0] if len(value) == 1 else value
        return params

    def get_url(self, plugin_url='', **kwargs):
        """
        Construct a callable URL for a virtual directory item

        If plugin_url is empty, a current plugin URL is used.
        kwargs are converted to a URL-encoded string of plugin call parameters
        To call a plugin action, 'action' parameter must be used,
        if 'action' parameter is missing, then the plugin root action is called
        If the action is not added to :class:`Plugin` actions, :class:`PluginError` will be raised.

        :param plugin_url: plugin URL with trailing / (optional)
        :type plugin_url: str
        :param kwargs: pairs of key=value items
        :return: a full plugin callback URL
        :rtype: str
        """
        url = plugin_url or self._url
        if kwargs:
            return '{0}?{1}'.format(url, urlencode(kwargs))
        return url

    def run(self, category=''):
        """
        Run plugin

        :param category: str - plugin sub-category, e.g. 'Comedy'.
            See :func:`xbmcplugin.setPluginCategory` for more info.
        :type category: str
        """
        self._handle = int(sys.argv[1])
        if category:
            xbmcplugin.setPluginCategory(self._handle, category)
        params = self.get_params(sys.argv[2][1:])
        action = params.get('action', 'root')
        self.log('Actions: {0}'.format(str(self.actions.keys())))
        self.log('Called action "{0}" with params "{1}"'.format(action, str(params)))
        try:
            action_callable = self.actions[action]
        except KeyError:
            raise PluginError('Invalid action: "{0}"!'.format(action))
        else:
            result = action_callable(params)
            self.log('Action return value: {0}'.format(str(result)), xbmc.LOGDEBUG)
            if isinstance(result, list):
                self._add_directory_items(self.create_listing(result))
            elif isinstance(result, (str, unicode)):
                self._set_resolved_url(self.resolve_url(result))
            elif isinstance(result, dict) and result.get('listing') is not None:
                self._add_directory_items(result)
            elif isinstance(result, dict) and result.get('path') is not None:
                self._set_resolved_url(result)
            else:
                self.log('The action "{0}" has not returned any valid data to process.'.format(action), xbmc.LOGWARNING)

    @staticmethod
    def create_listing(listing, succeeded=True, update_listing=False, cache_to_disk=False, sort_methods=None,
                       view_mode=None, content=None):
        """
        Create and return a context dict for a virtual folder listing

        :param listing: the list of the plugin virtual folder items
        :type listing: list
        :param succeeded: if ``False`` Kodi won't open a new listing and stays on the current level.
        :type succeeded: bool
        :param update_listing: if ``True``, Kodi won't open a sub-listing but refresh the current one.
        :type update_listing: bool
        :param cache_to_disk: cache this view to disk.
        :type cache_to_disk: bool
        :param sort_methods: the list of integer constants representing virtual folder sort methods.
        :type sort_methods: tuple
        :param view_mode: a numeric code for a skin view mode.
            View mode codes are different in different skins except for ``50`` (basic listing).
        :type view_mode: int
        :param content: string - current plugin content, e.g. 'movies' or 'episodes'.
            See :func:`xbmcplugin.setContent` for more info.
        :type content: str
        :return: context dictionary containing necessary parameters
            to create virtual folder listing in Kodi UI.
        :rtype: dict
        """
        return {'listing': listing, 'succeeded': succeeded, 'update_listing': update_listing,
                'cache_to_disk': cache_to_disk, 'sort_methods': sort_methods, 'view_mode': view_mode,
                'content': content}

    @staticmethod
    def resolve_url(path='', play_item=None, succeeded=True):
        """
        Create and return a context dict to resolve a playable URL

        :param path: the path to a playable media.
        :type path: str or unicode
        :param play_item: a dict of item properties as described in the class docstring.
            It allows to set additional properties for the item being played, like graphics, metadata etc.
            if ``play_item`` parameter is present, then ``path`` value is ignored, and the path must be set via
            ``'path'`` property of a ``play_item`` dict.
        :type play_item: dict
        :param succeeded: if ``False``, Kodi won't play anything
        :type succeeded: bool
        :return: context dictionary containing necessary parameters
            for Kodi to play the selected media.
        :rtype: dict
        """
        return {'path': path, 'play_item': play_item, 'succeeded': succeeded}

    @staticmethod
    def create_list_item(item):
        """
        Create an :class:`xbmcgui.ListItem` instance from an item dict

        :param item: a dict of ListItem properties
        :type item: dict
        :return: ListItem instance
        :rtype: xbmcgui.ListItem
        """
        list_item = xbmcgui.ListItem(label=item.get('label', ''),
                                     label2=item.get('label2', ''),
                                     path=item.get('path', ''))
        if int(xbmc.getInfoLabel('System.BuildVersion')[:2]) >= 16:
            art = item.get('art', {})
            art['thumb'] = item.get('thumb', '')
            art['icon'] = item.get('icon', '')
            art['fanart'] = item.get('fanart', '')
            item['art'] = art
        else:
            list_item.setThumbnailImage(item.get('thumb', ''))
            list_item.setIconImage(item.get('icon', ''))
            list_item.setProperty('fanart_image', item.get('fanart', ''))
        if item.get('art'):
            list_item.setArt(item['art'])
        if item.get('stream_info'):
            for stream, stream_info in item['stream_info'].iteritems():
                list_item.addStreamInfo(stream, stream_info)
        if item.get('info'):
            for media, info in item['info'].iteritems():
                list_item.setInfo(media, info)
        if item.get('context_menu') and isinstance(item['context_menu'], list):
            list_item.addContextMenuItems(item['context_menu'])
        elif item.get('context_menu') and isinstance(item['context_menu'], tuple):
            list_item.addContextMenuItems(item['context_menu'][0], item['context_menu'][1])
        if item.get('subtitles'):
            list_item.setSubtitles(item['subtitles'])
        if item.get('mime'):
            list_item.setMimeType(item['mime'])
        return list_item

    def _add_directory_items(self, context):
        """
        Create a virtual folder listing

        :param context: context dictionary
        :type context: dict
        """
        self.log('Creating listing from {0}'.format(str(context)), xbmc.LOGDEBUG)
        if context.get('content'):
            xbmcplugin.setContent(self._handle, context['content'])  # This must be at the beginning
        listing = []
        for item in context['listing']:
            if item.get('list_item') is not None:
                list_item = item['list_item']
                is_folder = item.get('is_folder', True)
            else:
                list_item = self.create_list_item(item)
                if item.get('is_playable'):
                    list_item.setProperty('IsPlayable', 'true')
                    is_folder = False
                else:
                    is_folder = item.get('is_folder', True)
            listing.append((item['url'], list_item, is_folder))
        xbmcplugin.addDirectoryItems(self._handle, listing, len(listing))
        if context['sort_methods'] is not None:
            [xbmcplugin.addSortMethod(self._handle, method) for method in context['sort_methods']]
        xbmcplugin.endOfDirectory(self._handle,
                                  context['succeeded'],
                                  context['update_listing'],
                                  context['cache_to_disk'])
        if context['view_mode'] is not None:
            xbmc.executebuiltin('Container.SetViewMode({0})'.format(context['view_mode']))

    def _set_resolved_url(self, context):
        """
        Resolve a playable URL

        :param context: context dictionary
        :type context: dict
        """
        self.log('Resolving URL from {0}'.format(str(context)), xbmc.LOGDEBUG)
        if context.get('play_item') is None:
            list_item = xbmcgui.ListItem(path=context['path'])
        else:
            list_item = self.create_list_item(context['play_item'])
        xbmcplugin.setResolvedUrl(self._handle, context['succeeded'], list_item)
