import os
import sys
import time
import shelve
from datetime import timedelta
from functools import wraps

import xbmcswift2
from xbmcswift2 import xbmc, xbmcaddon, xbmcplugin
from xbmcswift2.storage import TimedStorage
from xbmcswift2.logger import log
from xbmcswift2.constants import VIEW_MODES, SortMethod
from common import Modes, DEBUG_MODES
from request import Request


class XBMCMixin(object):
    '''A mixin to add XBMC helper methods. In order to use this mixin,
    the child class must implement the following methods and
    properties:

        # Also, the child class is responsible for ensuring that this path
        # exists.
        self.storage_path  

        self.added_items

        self.request

        self.addon

        _end_of_directory = False

        self.handle

    # optional 
    self.info_type: should be in ['video', 'music', 'pictures']
    _memoized_storage = None
    _unsynced_storages = None
    # TODO: Ensure above is implemented
    '''
    def cached(self, TTL=60 * 24):
        '''A decorator that will cache the output of the wrapped function. The
        key used for the cache is the function name as well as the `*args` and
        `**kwargs` passed to the function.

        :param TTL: time to live in minutes

        .. note:: For route caching, you should use
                  :meth:`xbmcswift2.Plugin.cached_route`.
        '''
        def decorating_function(function):
            # TODO test this method
            storage = self.get_storage('.functions', file_format='pickle',
                                       TTL=TTL)
            kwd_mark = 'f35c2d973e1bbbc61ca60fc6d7ae4eb3'

            @wraps(function)
            def wrapper(*args, **kwargs):
                key = (function.__name__, kwd_mark,) + args
                if kwargs:
                    key += (kwd_mark,) + tuple(sorted(kwargs.items()))

                try:
                    result = storage[key]
                    #log.debug('Cache hit for key "%s"' % (key, ))
                    log.debug('Storage hit for function "%s" with args "%s" '
                              'and kwargs "%s"' % (function.__name__, args,
                                                   kwargs))
                except KeyError:
                    log.debug('Storage miss for function "%s" with args "%s" '
                              'and kwargs "%s"' % (function.__name__, args,
                                                   kwargs))
                    result = function(*args, **kwargs)
                    storage[key] = result
                storage.sync()
                return result
            return wrapper
        return decorating_function

    def list_storages(self):
        '''Returns a list of existing stores. The returned names can then be
        used to call get_storage().
        '''
        # Filter out any storages used by xbmcswift2 so caller doesn't corrupt
        # them.
        return [name for name in os.listdir(self.storage_path)
                if not name.startswith('.')]

    def get_storage(self, name='main', file_format='pickle', TTL=None):
        '''Returns a storage for the given name. The returned storage is a
        fully functioning python dictionary and is designed to be used that
        way. It is usually not necessary for the caller to load or save the
        storage manually. If the storage does not already exist, it will be
        created.  

        .. seealso:: :class:`xbmcswift2.TimedStorage` for more details.

        :param name: The name  of the storage to retrieve.
        :param file_format: Choices are 'pickle', 'csv', and 'json'. Pickle is
                            recommended as it supports python objects.

                            .. note:: If a storage already exists for the given
                                      name, the file_format parameter is
                                      ignored. The format will be determined by
                                      the existing storage file.
        :param TTL: The time to live for storage items specified in minutes or None
                    for no expiration. Since storage items aren't expired until a
                    storage is loaded form disk, it is possible to call
                    get_storage() with a different TTL than when the storage was
                    created. The currently specified TTL is always honored.
        '''

        if not hasattr(self, '_unsynced_storages'):
            self._unsynced_storages = {}
        filename = os.path.join(self.storage_path, name)
        try:
            storage = self._unsynced_storages[filename]
            log.debug('Loaded storage "%s" from memory' % name)
        except KeyError:
            if TTL:
                TTL = timedelta(minutes=TTL)
            storage = TimedStorage(filename, file_format, TTL)
            self._unsynced_storages[filename] = storage
            log.debug('Loaded storage "%s" from disk' % name)
        return storage

    def temp_fn(self, path):
        return os.path.join(xbmc.translatePath('special://temp/'), path)

    def get_string(self, stringid):
        '''Returns the localized string from strings.xml for the given
        stringid.
        '''
        return self.addon.getLocalizedString(stringid)

    def set_content(self, content):
        '''Sets the content type for the plugin.'''
        # TODO: Change to a warning instead of an assert. Otherwise will have
        # to keep this list in sync with
        #       any XBMC changes.
        #contents = ['files', 'songs', 'artists', 'albums', 'movies',
        #'tvshows', 'episodes', 'musicvideos']
        #assert content in contents, 'Content type "%s" is not valid' % content
        xbmcplugin.setContent(self.handle, content)

    def get_setting(self, key):
        #TODO: allow pickling of settings items?
        # TODO: STUB THIS OUT ON CLI
        return self.addon.getSetting(id=key)

    def set_setting(self, key, val):
        # TODO: STUB THIS OUT ON CLI
        return self.addon.setSetting(id=key, value=val)

    def open_settings(self):
        '''Opens the settings dialog within XBMC'''
        self.addon.openSettings()

    def add_to_playlist(self, items, playlist='video'):
        '''Adds the provided list of items to the specified playlist.
        Available playlists include *video* and *music*.
        '''
        playlists = {'music': 0, 'video': 1}
        assert playlist in playlists.keys(), ('Playlist "%s" is invalid.' %
                                              playlist)
        selected_playlist = xbmc.PlayList(playlists[playlist])

        _items = []
        for item in items:
            if not hasattr(item, 'as_xbmc_listitem'):
                if 'info_type' in item.keys():
                    log.warning('info_type key has no affect for playlist '
                                'items as the info_type is inferred from the '
                                'playlist type.')
                # info_type has to be same as the playlist type
                item['info_type'] = playlist
                item = xbmcswift2.ListItem.from_dict(**item)
            _items.append(item)
            selected_playlist.add(item.get_path(), item.as_xbmc_listitem())
        return _items

    def get_view_mode_id(self, view_mode):
        '''Attempts to return a view_mode_id for a given view_mode
        taking into account the current skin. If not view_mode_id can
        be found, None is returned. 'thumbnail' is currently the only
        suppported view_mode.
        '''
        view_mode_ids = VIEW_MODES.get(view_mode.lower())
        if view_mode_ids:
            return view_mode_ids.get(xbmc.getSkinDir())
        return None

    def set_view_mode(self, view_mode_id):
        '''Calls XBMC's Container.SetViewMode. Requires an integer
        view_mode_id'''
        xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)

    def notify(self, msg='', title=None, delay=5000, image=''):
        '''Displays a temporary notification message to the user. If
        title is not provided, the plugin name will be used. To have a
        blank title, pass '' for the title argument. The delay argument
        is in milliseconds.
        '''
        if not msg:
            log.warning('Empty message for notification dialog')
        if title is None:
            title = self.addon.getAddonInfo('name')
        xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s", "%s")' %
                            (msg, title, delay, image))

    def set_resolved_url(self, url):
        item = xbmcswift2.ListItem(path=url)
        item.set_played(True)
        xbmcplugin.setResolvedUrl(self.handle, True, item.as_xbmc_listitem())
        return [item]

    def play_video(self, item, player=xbmc.PLAYER_CORE_DVDPLAYER):
        if not hasattr(item, 'as_xbmc_listitem'):
            if 'info_type' not in item.keys():
                item['info_type'] = 'video'
            item = xbmcswift2.ListItem.from_dict(**item)
        item.set_played(True)
        xbmc.Player(player).play(item.get_path(), item.as_xbmc_listitem())
        return [item]

    def add_items(self, items):
        '''Adds ListItems to the XBMC interface. Each item in the
        provided list should either be instances of xbmcswift2.ListItem,
        or regular dictionaries that will be passed to
        xbmcswift2.ListItem.from_dict. Returns the list of ListItems.

        :param items: An iterable of items where each item is either a
                      dictionary with keys/values suitable for passing to
                      :meth:`xbmcswift2.ListItem.from_dict` or an instance of
                      :class:`xbmcswift2.ListItem`.
        '''
        # For each item if it is not already a list item, we need to create one
        _items = []
        info_type = self.info_type if hasattr(self, 'info_type') else 'video'

        # Create ListItems for anything that is not already an instance of
        # ListItem
        for item in items:
            if not isinstance(item, xbmcswift2.ListItem):
                if 'info_type' not in item.keys():
                    item['info_type'] = info_type
                item = xbmcswift2.ListItem.from_dict(**item)
            _items.append(item)

        tuples = [item.as_tuple() for item in _items]
        xbmcplugin.addDirectoryItems(self.handle, tuples, len(tuples))

        # We need to keep track internally of added items so we can return them
        # all at the end for testing purposes
        self.added_items.extend(_items)

        # Possibly need an if statement if only for debug mode
        return _items

    def end_of_directory(self, succeeded=True, update_listing=False,
                         cache_to_disc=True):
        '''Wrapper for xbmcplugin.endOfDirectory. Records state in
        self._end_of_directory.

        Typically it is not necessary to call this method directly, as
        calling :meth:`~xbmcswift2.Plugin.finish` will call this method.
        '''
        if not self._end_of_directory:
            self._end_of_directory = True
            # Finalize the directory items
            return xbmcplugin.endOfDirectory(self.handle, succeeded,
                                             update_listing, cache_to_disc)
        assert False, 'Already called endOfDirectory.'

    def add_sort_method(self, sort_method, label2_mask=None):
        '''A wrapper for `xbmcplugin.addSortMethod()
        <http://mirrors.xbmc.org/docs/python-docs/xbmcplugin.html#-addSortMethod>`_.
        You can use ``dir(xbmcswift2.SortMethod)`` to list all available sort
        methods.

        :param sort_method: A valid sort method. You can provided the constant
                            from xbmcplugin, an attribute of SortMethod, or a
                            string name. For instance, the following method
                            calls are all equivalent:
        
                            * ``plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)``
                            * ``plugin.add_sort_metohd(SortMethod.TITLE)``
                            * ``plugin.add_sort_method('title')``
        :param label2_mask: A mask pattern for label2. See the `XBMC
                            documentation
                            <http://mirrors.xbmc.org/docs/python-docs/xbmcplugin.html#-addSortMethod>`_
                            for more information.
        '''
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

    def finish(self, items=None, sort_methods=None, succeeded=True,
               update_listing=False, cache_to_disc=True, view_mode=None):
        '''Adds the provided items to the XBMC interface. 

        :param items: an iterable of items where each item is either a
            dictionary with keys/values suitable for passing to
            :meth:`xbmcswift2.ListItem.from_dict` or an instance of
            :class:`xbmcswift2.ListItem`.
        :param sort_methods: a list of valid XBMC sort_methods. Each item in
                             the list can either be a sort method or a tuple of
                             ``sort_method, label2_mask``. See
                             :meth:`add_sort_method` for
                             more detail concerning valid sort_methods.

                             Example call with sort_methods::

                                sort_methods = ['label', 'title', ('date', '%D')]
                                plugin.finish(items, sort_methods=sort_methods)
                                
        :param view_mode: can either be an integer (or parseable integer
            string) corresponding to a view_mode or the name of a type of view.
            Currrently the only view type supported is 'thumbnail'.
        :returns: a list of all ListItems added to the XBMC interface.
        '''
        # If we have any items, add them. Items are optional here.
        if items:
            self.add_items(items)
        if sort_methods:
            for sort_method in sort_methods:
                if not isinstance(sort_method, basestring) and hasattr(sort_method, '__len__'):
                    self.add_sort_method(*sort_method)
                else: 
                    self.add_sort_method(sort_method)

        # Attempt to set a view_mode if given
        if view_mode is not None:
            # First check if we were given an integer or parseable integer
            try:
                view_mode_id = int(view_mode)
            except ValueError:
                # Attempt to lookup a view mode
                view_mode_id = self.get_view_mode_id(view_mode)

            if view_mode_id is not None:
                self.set_view_mode(view_mode_id)

        # Finalize the directory items
        self.end_of_directory(succeeded, update_listing, cache_to_disc)

        # Close any open storages which will persist them to disk
        if hasattr(self, '_unsynced_storages'):
            for storage in self._unsynced_storages.values():
                log.debug('Saving a %s storage to disk at "%s"' % (storage.file_format, storage.filename))
                storage.close()

        # Return the cached list of all the list items that were added
        return self.added_items
