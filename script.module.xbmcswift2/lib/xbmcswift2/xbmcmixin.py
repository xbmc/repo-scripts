import os
import sys
import time
import shelve
from datetime import timedelta
from functools import wraps

import xbmcswift2
from xbmcswift2 import xbmc, xbmcaddon, xbmcplugin
from xbmcswift2.cache import Cache, TimedCache
from xbmcswift2.logger import log
from xbmcswift2.constants import VIEW_MODES
from common import Modes, DEBUG_MODES
from request import Request


class XBMCMixin(object):
    '''A mixin to add XBMC helper methods. In order to use this mixin,
    the child class must implement the following methods and
    properties:

        def cache_path(self, path)

        self.cache_path
        self.addon
        self.added_items
        self.request
    _end_of_directory = False
    _memoized_cache = None
    _unsynced_caches = None
    # TODO: Ensure above is implemented
    '''
    def cache(self, ttl_hours=24):
        '''View caching decorator. Currently must be closest to the
        view because route decorators don't wrap properly.
        '''
        def decorating_function(function):
            cache = self.get_timed_cache('function_cache', file_format='pickle',
                                         ttl=timedelta(hours=ttl_hours))
            kwd_mark = 'f35c2d973e1bbbc61ca60fc6d7ae4eb3'

            @wraps(function)
            def wrapper(*args, **kwargs):
                key = (function.__name__, kwd_mark,) + args
                if kwargs:
                    key += (kwd_mark,) + tuple(sorted(kwargs.items()))

                try:
                    result = cache[key]
                    #log.debug('Cache hit for key "%s"' % (key, ))
                    log.debug('Cache hit for function "%s" with args "%s" and kwargs "%s"' % (function.__name__, args, kwargs))
                except KeyError:
                    log.debug('Cache miss for function "%s" with args "%s" and kwargs "%s"' % (function.__name__, args, kwargs))
                    result = function(*args, **kwargs)
                    cache[key] = result
                cache.sync()
                return result
            return wrapper
        return decorating_function

    def _get_cache(self, cache_type, cache_name, **kwargs):
        if not hasattr(self, '_unsynced_caches'):
            self._unsynced_caches = {}
        filename = os.path.join(self.cache_path, cache_name)
        try:
            cache = self._unsynced_caches[filename]
            log.debug('Used live cache "%s" located at "%s"' % (cache_name, filename))
        except KeyError:
            cache = cache_type(filename, **kwargs)
            self._unsynced_caches[filename] = cache
            log.debug('Used cold cache "%s" located at "%s"' % (cache_name, filename))
        return cache

    def get_timed_cache(self, cache_name, file_format='pickle', ttl=None):
        return self._get_cache(TimedCache, cache_name, file_format=file_format, ttl=ttl)

    def get_cache(self, cache_name, file_format='pickle'):
        return self._get_cache(TimedCache, cache_name, file_format=file_format)

    def cache_fn(self, path):
        # TODO:
        #if not os.path.exists(self._cache_path):
            #os.mkdir(self._cache_path)
        return os.path.join(self.cache_path, path)

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
            title = self.plugin.name
        xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s", "%s")' %
                            (msg, title, delay, image))

    def set_resolved_url(self, url):
        item = xbmcswift2.ListItem(path=url)
        item.set_played(True)
        xbmcplugin.setResolvedUrl(self.handle, True, item.as_xbmc_listitem())
        return [item]

    def play_video(self, item, player=xbmc.PLAYER_CORE_DVDPLAYER):
        if not isinstance(item, xbmcswift2.ListItem):
            item = xbmcswift2.ListItem.from_dict(**item)
        item.set_played(True)
        xbmc.Player(player).play(item.get_path, item)
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

        # Create ListItems for anything that is not already an instance of
        # ListItem
        for item in items:
            if not isinstance(item, xbmcswift2.ListItem):
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

    def finish(self, items=None, sort_methods=None, succeeded=True,
               update_listing=False, cache_to_disc=True, view_mode=None):
        '''Adds the provided items to the XBMC interface. Each item in
        the provided list should either be an instance of
        xbmcswift2.ListItem or a dictionary that will be passed to
        xbmcswift2.ListItem.from_dict().

        :param items: an iterable of items where each item is either a
            dictionary with keys/values suitable for passing to
            :meth:`xbmcswift2.ListItem.from_dict` or an instance of
            :class:`xbmcswift2.ListItem`.
        :param sort_methods: a list of valid XBMC sort_methods. See
            :attr:`xbmcswift2.SortMethod`.
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
                xbmcplugin.addSortMethod(self.handle, sort_method)

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

        # Close any open caches which will persist them to disk
        if hasattr(self, '_unsynced_caches'):
            for cache in self._unsynced_caches.values():
                log.debug('Saving a %s cache to disk at "%s"' % (cache.file_format, cache.filename))
                cache.close()

        # Return the cached list of all the list items that were added
        return self.added_items
