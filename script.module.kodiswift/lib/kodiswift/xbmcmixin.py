# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import warnings
from datetime import timedelta
from functools import wraps

import kodiswift
from kodiswift import xbmc, xbmcplugin, xbmcgui
from kodiswift.constants import SortMethod
from kodiswift.logger import log
from kodiswift.storage import TimedStorage, UnknownFormat

__all__ = ['XBMCMixin']

# TODO(Sinap): Need to either break the single mixin into multiple or just use
#              a parent class.


# noinspection PyUnresolvedReferences,PyAttributeOutsideInit
class XBMCMixin(object):
    """A mixin to add Kodi helper methods. In order to use this mixin,
    the child class must implement the following methods and
    properties:

        # Also, the child class is responsible for ensuring that this path
        # exists.
        self.storage_path

        self.added_items

        self.request

        self.addon

        _end_of_directory = False

        _update_listing

        self.handle

    # optional
    self.info_type: should be in ['video', 'music', 'pictures']
    _memoized_storage = None
    _unsynced_storage = None
    # TODO: Ensure above is implemented
    """

    _function_cache_name = '.functions'

    def cached(self, ttl=60 * 24):
        """A decorator that will cache the output of the wrapped function.

        The key used for the cache is the function name as well as the
        `*args` and `**kwargs` passed to the function.

        Args:
            ttl: Time to live in minutes.

        Notes:
            ttl: For route caching, you should use
                :meth:`kodiswift.Plugin.cached_route`.
        """
        def decorating_function(function):
            storage = self.get_storage(
                self._function_cache_name, file_format='pickle', ttl=ttl)
            kwd_mark = 'f35c2d973e1bbbc61ca60fc6d7ae4eb3'

            @wraps(function)
            def wrapper(*args, **kwargs):
                key = (function.__name__, kwd_mark) + args
                if kwargs:
                    key += (kwd_mark,) + tuple(sorted(kwargs.items()))

                try:
                    result = storage[key]
                    log.debug('Storage hit for function "%s" with args "%s" '
                              'and kwargs "%s"', function.__name__, args,
                              kwargs)
                except KeyError:
                    log.debug('Storage miss for function "%s" with args "%s" '
                              'and kwargs "%s"', function.__name__, args,
                              kwargs)
                    result = function(*args, **kwargs)
                    storage[key] = result
                    storage.sync()
                return result

            return wrapper

        return decorating_function

    def clear_function_cache(self):
        """Clears the storage that caches results when using
        :meth:`kodiswift.Plugin.cached_route` or
        :meth:`kodiswift.Plugin.cached`.
        """
        self.get_storage(self._function_cache_name).clear()

    def list_storage(self):
        """Returns a list of existing stores.

        The returned names can then be used to call get_storage().
        """
        # Filter out any storage used by kodiswift so caller doesn't corrupt
        # them.
        return [name for name in os.listdir(self.storage_path)
                if not name.startswith('.')]

    def get_storage(self, name='main', file_format='pickle', ttl=None):
        """Returns a storage for the given name.

        The returned storage is a fully functioning python dictionary and is
        designed to be used that way. It is usually not necessary for the
        caller to load or save the storage manually. If the storage does
        not already exist, it will be created.

        See Also:
            :class:`kodiswift.TimedStorage` for more details.

        Args:
            name (str): The name  of the storage to retrieve.
            file_format (str): Choices are 'pickle', 'csv', and 'json'.
                Pickle is recommended as it supports python objects.

                Notes: If a storage already exists for the given name, the
                    file_format parameter is ignored. The format will be
                    determined by the existing storage file.

            ttl (int): The time to live for storage items specified in minutes
                or None for no expiration. Since storage items aren't expired
                until a storage is loaded form disk, it is possible to call
                get_storage() with a different TTL than when the storage was
                created. The currently specified TTL is always honored.

        Returns:
            kodiswift.storage.TimedStorage:
        """
        if not hasattr(self, '_unsynced_storage'):
            self._unsynced_storage = {}
        filename = os.path.join(self.storage_path, name)
        try:
            storage = self._unsynced_storage[filename]
            log.debug('Loaded storage "%s" from memory', name)
        except KeyError:
            if ttl:
                ttl = timedelta(minutes=ttl)
            try:
                storage = TimedStorage(filename, ttl, file_format=file_format)
                storage.load()
            except UnknownFormat:
                # Thrown when the storage file is corrupted and can't be read.
                # Prompt user to delete storage.
                choices = ['Clear storage', 'Cancel']
                ret = xbmcgui.Dialog().select(
                    'A storage file is corrupted. It'
                    ' is recommended to clear it.', choices)
                if ret == 0:
                    os.remove(filename)
                    storage = TimedStorage(filename, ttl,
                                           file_format=file_format)
                else:
                    raise Exception('Corrupted storage file at %s' % filename)

            self._unsynced_storage[filename] = storage
            log.debug('Loaded storage "%s" from disk', name)
        return storage

    def get_string(self, string_id):
        """Returns the localized string from strings.po or strings.xml for the
        given string_id.
        """
        string_id = int(string_id)
        if not hasattr(self, '_strings'):
            self._strings = {}
        if string_id not in self._strings:
            self._strings[string_id] = self.addon.getLocalizedString(string_id)
        return self._strings[string_id]

    def set_content(self, content):
        """Sets the content type for the plugin."""
        contents = ['files', 'songs', 'artists', 'albums', 'movies', 'tvshows',
                    'episodes', 'musicvideos']
        if content not in contents:
            self.log.warning('Content type "%s" is not valid', content)
        xbmcplugin.setContent(self.handle, content)

    def get_setting(self, key, converter=None, choices=None):
        """Returns the settings value for the provided key.

        If converter is str, unicode, bool or int the settings value will be
        returned converted to the provided type. If choices is an instance of
        list or tuple its item at position of the settings value be returned.

        Args:
            key (str): The ID of the setting defined in settings.xml.
            converter (Optional[str, unicode, bool, int]): How to convert the
                setting value.
                TODO(Sinap): Maybe this should just be a callable object?
            choices (Optional[list,tuple]):

        Notes:
            converter: It is suggested to always use unicode for
                text-settings because else xbmc returns utf-8 encoded strings.

        Examples:
            * ``plugin.get_setting('per_page', int)``
            * ``plugin.get_setting('password', unicode)``
            * ``plugin.get_setting('force_viewmode', bool)``
            * ``plugin.get_setting('content', choices=('videos', 'movies'))``
        """
        # TODO: allow pickling of settings items?
        # TODO: STUB THIS OUT ON CLI
        value = self.addon.getSetting(key)
        if converter is str:
            return value
        elif converter is unicode:
            return value.decode('utf-8')
        elif converter is bool:
            return value == 'true'
        elif converter is int:
            return int(value)
        elif isinstance(choices, (list, tuple)):
            return choices[int(value)]
        elif converter is None:
            log.warning('No converter provided, unicode should be used, '
                        'but returning str value')
            return value
        else:
            raise TypeError('Acceptable converters are str, unicode, bool and '
                            'int. Acceptable choices are instances of list '
                            ' or tuple.')

    def set_setting(self, key, val):
        # TODO: STUB THIS OUT ON CLI - setSetting takes id=x, value=x throws an error otherwise
        return self.addon.setSetting(id=key, value=val)

    def open_settings(self):
        """Opens the settings dialog within Kodi"""
        self.addon.openSettings()

    @staticmethod
    def add_to_playlist(items, playlist='video'):
        """Adds the provided list of items to the specified playlist.
        Available playlists include *video* and *music*.
        """
        playlists = {'music': 0, 'video': 1}
        if playlist not in playlists:
            raise ValueError('Playlist "%s" is invalid.' % playlist)

        selected_playlist = xbmc.PlayList(playlists[playlist])
        _items = []
        for item in items:
            if not hasattr(item, 'as_xbmc_listitem'):
                if 'info_type' in item:
                    log.warning('info_type key has no affect for playlist '
                                'items as the info_type is inferred from the '
                                'playlist type.')
                # info_type has to be same as the playlist type
                item['info_type'] = playlist
                item = kodiswift.ListItem.from_dict(**item)
            _items.append(item)
            selected_playlist.add(item.get_path(), item.as_xbmc_listitem())
        return _items

    @staticmethod
    def get_view_mode_id(view_mode):
        warnings.warn('get_view_mode_id is deprecated.', DeprecationWarning)
        return None

    @staticmethod
    def set_view_mode(view_mode_id):
        """Calls Kodi's Container.SetViewMode. Requires an integer
        view_mode_id"""
        xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)

    def keyboard(self, default=None, heading=None, hidden=False):
        """Displays the keyboard input window to the user. If the user does not
        cancel the modal, the value entered by the user will be returned.

        :param default: The placeholder text used to prepopulate the input
                        field.
        :param heading: The heading for the window. Defaults to the current
                        addon's name. If you require a blank heading, pass an
                        empty string.
        :param hidden: Whether or not the input field should be masked with
                       stars, e.g. a password field.
        """
        if heading is None:
            heading = self.addon.getAddonInfo('name')
        if default is None:
            default = ''
        keyboard = xbmc.Keyboard(default, heading, hidden)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()

    def notify(self, msg='', title=None, delay=5000, image=''):
        """Displays a temporary notification message to the user. If
        title is not provided, the plugin name will be used. To have a
        blank title, pass '' for the title argument. The delay argument
        is in milliseconds.
        """
        if not msg:
            log.warning('Empty message for notification dialog')
        if title is None:
            title = self.addon.getAddonInfo('name')
        xbmc.executebuiltin('Notification("%s", "%s", "%s", "%s")' %
                            (msg, title, delay, image))

    def set_resolved_url(self, item=None, subtitles=None):
        """Takes a url or a listitem to be played. Used in conjunction with a
        playable list item with a path that calls back into your addon.

        :param item: A playable list item or url. Pass None to alert Kodi of a
                     failure to resolve the item.

                     .. warning:: When using set_resolved_url you should ensure
                                  the initial playable item (which calls back
                                  into your addon) doesn't have a trailing
                                  slash in the URL. Otherwise it won't work
                                  reliably with Kodi's PlayMedia().
        :param subtitles: A URL to a remote subtitles file or a local filename
                          for a subtitles file to be played along with the
                          item.
        """
        if self._end_of_directory:
            raise Exception('Current Kodi handle has been removed. Either '
                            'set_resolved_url(), end_of_directory(), or '
                            'finish() has already been called.')
        self._end_of_directory = True

        succeeded = True
        if item is None:
            # None item indicates the resolve url failed.
            item = {}
            succeeded = False

        if isinstance(item, basestring):
            # caller is passing a url instead of an item dict
            item = {'path': item}

        item = self._listitemify(item)
        item.set_played(True)
        xbmcplugin.setResolvedUrl(self.handle, succeeded,
                                  item.as_xbmc_listitem())

        # call to _add_subtitles must be after setResolvedUrl
        if subtitles:
            self._add_subtitles(subtitles)
        return [item]

    def play_video(self, item, player=None):
        if isinstance(item, dict):
            item['info_type'] = 'video'

        item = self._listitemify(item)
        item.set_played(True)
        if player:
            _player = xbmc.Player(player)
        else:
            _player = xbmc.Player()
        _player.play(item.get_path(), item.as_xbmc_listitem())
        return [item]

    def add_items(self, items):
        """Adds ListItems to the Kodi interface.

        Each item in the provided list should either be instances of
        kodiswift.ListItem, or regular dictionaries that will be passed
        to kodiswift.ListItem.from_dict.

        Args:
            items: An iterable of items where each item is either a
                dictionary with keys/values suitable for passing to
                :meth:`kodiswift.ListItem.from_dict` or an instance of
                :class:`kodiswift.ListItem`.

        Returns:
            kodiswift.ListItem: The list of ListItems.
        """
        _items = [self._listitemify(item) for item in items]
        tuples = [item.as_tuple() for item in _items if hasattr(item, 'as_tuple')]
        xbmcplugin.addDirectoryItems(self.handle, tuples, len(tuples))

        # We need to keep track internally of added items so we can return them
        # all at the end for testing purposes
        self.added_items.extend(_items)

        # Possibly need an if statement if only for debug mode
        return _items

    def add_sort_method(self, sort_method, label2_mask=None):
        """A wrapper for `xbmcplugin.addSortMethod()
        <http://mirrors.xbmc.org/docs/python-docs/xbmcplugin.html#-addSortMethod>`_.
        You can use ``dir(kodiswift.SortMethod)`` to list all available sort
        methods.

        Args:
            sort_method: A valid sort method. You can provided the constant
                from xbmcplugin, an attribute of SortMethod, or a string name.
                For instance, the following method calls are all equivalent:
                 * ``plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)``
                 * ``plugin.add_sort_method(SortMethod.TITLE)``
                 * ``plugin.add_sort_method('title')``
            label2_mask: A mask pattern for label2. See the `Kodi
                documentation <http://mirrors.xbmc.org/docs/python-docs/xbmcplugin.html#-addSortMethod>`_
                for more information.
        """
        try:
            # Assume it's a string and we need to get the actual int value
            sort_method = SortMethod.from_string(sort_method)
        except AttributeError:
            # sort_method was already an int (or a bad value)
            pass

        if label2_mask:
            xbmcplugin.addSortMethod(self.handle, sort_method, label2_mask)
        else:
            xbmcplugin.addSortMethod(self.handle, sort_method)

    def end_of_directory(self, succeeded=True, update_listing=False,
                         cache_to_disc=True):
        """Wrapper for xbmcplugin.endOfDirectory. Records state in
        self._end_of_directory.

        Typically it is not necessary to call this method directly, as
        calling :meth:`~kodiswift.Plugin.finish` will call this method.
        """
        self._update_listing = update_listing
        if not self._end_of_directory:
            self._end_of_directory = True
            # Finalize the directory items
            return xbmcplugin.endOfDirectory(self.handle, succeeded,
                                             update_listing, cache_to_disc)
        else:
            raise Exception('Already called endOfDirectory.')

    def finish(self, items=None, sort_methods=None, succeeded=True,
               update_listing=False, cache_to_disc=True, view_mode=None):
        """Adds the provided items to the Kodi interface.

        Args:
            items (List[Dict[str, str]]]): an iterable of items where each
                item is either a dictionary with keys/values suitable for
                passing to :meth:`kodiswift.ListItem.from_dict` or an
                instance of :class:`kodiswift.ListItem`.

            sort_methods (Union[List[str], str]): A list of valid Kodi
                sort_methods. Each item in the list can either be a sort
                method or a tuple of `sort_method, label2_mask`.
                See :meth:`add_sort_method` for more detail concerning
                valid sort_methods.

            succeeded (bool):
            update_listing (bool):
            cache_to_disc (bool): Whether to tell Kodi to cache this folder
                to disk.
            view_mode (Union[str, int]): Can either be an integer
                (or parsable integer string) corresponding to a view_mode or
                the name of a type of view. Currently the only view type
                supported is 'thumbnail'.

        Returns:
            List[kodiswift.listitem.ListItem]: A list of all ListItems added
                to the Kodi interface.
        """
        # If we have any items, add them. Items are optional here.
        if items:
            self.add_items(items)
        if sort_methods:
            for sort_method in sort_methods:
                if isinstance(sort_method, (list, tuple)):
                    self.add_sort_method(*sort_method)
                else:
                    self.add_sort_method(sort_method)

        # Attempt to set a view_mode if given
        if view_mode is not None:
            # First check if we were given an integer or parsable integer
            try:
                view_mode_id = int(view_mode)
            except ValueError:
                view_mode_id = None
            if view_mode_id is not None:
                self.set_view_mode(view_mode_id)

        # Finalize the directory items
        self.end_of_directory(succeeded, update_listing, cache_to_disc)

        # Return the cached list of all the list items that were added
        return self.added_items

    def _listitemify(self, item):
        """Creates an kodiswift.ListItem if the provided value for item is a
        dict. If item is already a valid kodiswift.ListItem, the item is
        returned unmodified.
        """
        info_type = self.info_type if hasattr(self, 'info_type') else 'video'

        # Create ListItems for anything that is not already an instance of
        # ListItem
        if not hasattr(item, 'as_tuple') and hasattr(item, 'keys'):
            if 'info_type' not in item:
                item['info_type'] = info_type
            item = kodiswift.ListItem.from_dict(**item)
        return item

    @staticmethod
    def _add_subtitles(subtitles):
        """Adds subtitles to playing video.

        Warnings:
            You must start playing a video before calling this method or it
            will raise and Exception after 30 seconds.

        Args:
            subtitles (str): A URL to a remote subtitles file or a local
                filename for a subtitles file.
        """
        # This method is named with an underscore to suggest that callers pass
        # the subtitles argument to set_resolved_url instead of calling this
        # method directly. This is to ensure a video is played before calling
        # this method.
        player = xbmc.Player()
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(30):
                # Abort requested, so exit.
                break
            elif player.isPlaying():
                # No abort requested after 30 seconds and a video is playing
                # so add the subtitles and exit.
                player.setSubtitles(subtitles)
                break
            else:
                raise Exception('No video playing. Aborted after 30 seconds.')
