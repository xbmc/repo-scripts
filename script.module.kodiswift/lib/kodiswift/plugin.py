# -*- coding: utf-8 -*-
"""
kodiswift.plugin
-----------------

This module contains the Plugin class. This class handles all of the url
routing and interaction with Kodi for a plugin.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

import collections
import inspect
import os
import sys

import kodiswift
from kodiswift import xbmc, xbmcaddon, Request
from kodiswift.logger import log, setup_log
from kodiswift.urls import UrlRule, NotFoundException, AmbiguousUrlException
from kodiswift.xbmcmixin import XBMCMixin

__all__ = ['Plugin']


class Plugin(XBMCMixin):
    """The Plugin objects encapsulates all the properties and methods necessary
    for running an Kodi plugin. The plugin instance is a central place for
    registering view functions and keeping track of plugin state.

    Usually the plugin instance is created in the main plugin.py file for the
    plugin. Typical creation looks like this::

        >>> from kodiswift import Plugin
        >>> plugin = Plugin('Hello Kodi')
    """

    def __init__(self, name=None, addon_id=None, plugin_file=None,
                 info_type=None):
        """
        Args:
            name (Optional[str]): The name of the plugin, e.g. 'Hello Kodi'.
            addon_id (Optional[str): The Kodi addon ID for the plugin,
                e.g. 'plugin.video.hellokodi'. This parameter is now optional
                and is really only useful for testing purposes. If it is not
                provided, the correct value will be parsed from the
                addon.xml file.
            plugin_file (Optional[str]): If provided, it should be the path
                to the plugin.py file in the root of the addon directory.
                This only has an effect when kodiswift is running on the
                command line. Will default to the current working directory
                since kodiswift requires execution in the root addon directory
                anyway. The parameter still exists to ease testing.
            info_type (Optional[str):
        """
        self._name = name
        self._routes = []
        self._view_functions = {}
        self._addon = xbmcaddon.Addon()

        self._addon_id = addon_id or self._addon.getAddonInfo('id')
        self._name = name or self._addon.getAddonInfo('name')

        self._info_type = info_type
        if not self._info_type:
            types = {
                'video': 'video',
                'audio': 'music',
                'image': 'pictures',
            }
            self._info_type = types.get(self._addon_id.split('.')[1], 'video')

        # Keeps track of the added list items
        self._current_items = []

        # Gets initialized when self.run() is called
        self._request = None

        # A flag to keep track of a call to xbmcplugin.endOfDirectory()
        self._end_of_directory = False

        # Keep track of the update_listing flag passed to
        # xbmcplugin.endOfDirectory()
        self._update_listing = False

        # The plugin's named logger
        self._log = setup_log(self._addon_id)

        # The path to the storage directory for the addon
        self._storage_path = xbmc.translatePath(
            'special://profile/addon_data/%s/.storage/' % self._addon_id)
        if not os.path.isdir(self._storage_path):
            os.makedirs(self._storage_path)

        # If we are running in CLI, we need to load the strings.xml manually
        # Since kodiswift currently relies on execution from an addon's root
        # directly, we can rely on cwd for now...
        if kodiswift.CLI_MODE:
            from kodiswift.mockxbmc import utils
            if plugin_file:
                plugin_dir = os.path.dirname(plugin_file)
            else:
                plugin_dir = os.getcwd()
            strings_fn = os.path.join(
                plugin_dir, 'resources', 'language', 'English', 'strings.po')
            utils.load_addon_strings(self._addon, strings_fn)

    @property
    def info_type(self):
        return self._info_type

    @property
    def log(self):
        """The log instance for the plugin.

        Returns an instance of the stdlib's ``logging.Logger``.
        This log will print to STDOUT when running in CLI mode and will
        forward messages to Kodi's log when running in Kodi.

        Examples:
            ``plugin.log.debug('Debug message')``
            ``plugin.log.warning('Warning message')``
            ``plugin.log.error('Error message')``

        Returns:
            logging.Logger:
        """
        return self._log

    @property
    def id(self):
        """The id for the addon instance.
        """
        return self._addon_id

    @property
    def storage_path(self):
        """A full path to the storage folder for this plugin's addon data.
        """
        return self._storage_path

    @property
    def addon(self):
        """This addon's wrapped instance of xbmcaddon.Plugin.
        """
        return self._addon

    @property
    def added_items(self):
        """The list of currently added items.

        Even after repeated calls to :meth:`~kodiswift.Plugin.add_items`, this
        property will contain the complete list of added items.
        """
        return self._current_items

    @property
    def handle(self):
        """The current plugin's handle. Equal to ``plugin.request.handle``.
        """
        return self.request.handle

    @property
    def request(self):
        """The current :class:`~kodiswift.Request`.

        Raises:
            Exception: if the request hasn't been initialized yet via
                :meth:`~kodiswift.Plugin.run()`.

        Returns:
            kodiswift.Request:
        """
        if self._request is None:
            raise Exception('It seems the current request has not been '
                            'initialized yet. Please ensure that '
                            '`plugin.run()` has been called before attempting '
                            'to access the current request.')
        return self._request

    @property
    def name(self):
        """The addon's name.

        Returns:
            str:
        """
        return self._name

    def clear_added_items(self):
        self._current_items = []

    def register_module(self, module, url_prefix):
        """Registers a module with a plugin. Requires a url_prefix that will
        then enable calls to url_for.

        Args:
            module (kodiswift.Module):
            url_prefix (str): A url prefix to use for all module urls,
                e.g. '/mymodule'
        """
        module.plugin = self
        module.url_prefix = url_prefix
        for func in module.register_funcs:
            func(self, url_prefix)

    def cached_route(self, url_rule, name=None, options=None, ttl=None):
        """A decorator to add a route to a view and also apply caching. The
        url_rule, name and options arguments are the same arguments for the
        route function. The TTL argument if given will passed along to the
        caching decorator.
        """
        route_decorator = self.route(url_rule, name=name, options=options)
        if ttl:
            cache_decorator = self.cached(ttl)
        else:
            cache_decorator = self.cached()

        def new_decorator(func):
            return route_decorator(cache_decorator(func))

        return new_decorator

    def route(self, url_rule=None, name=None, root=False, options=None):
        """A decorator to add a route to a view. name is used to
        differentiate when there are multiple routes for a given view."""

        def decorator(f):
            view_name = name or f.__name__
            if root:
                url = '/'
            elif not url_rule:
                url = '/' + view_name + '/'
                args = inspect.getargspec(f)[0]
                if args:
                    url += '/'.join('%s/<%s>' % (p, p) for p in args)
            else:
                url = url_rule
            self.add_url_rule(url, f, name=view_name, options=options)
            return f

        return decorator

    def add_url_rule(self, url_rule, view_func, name, options=None):
        """This method adds a URL rule for routing purposes. The
        provided name can be different from the view function name if
        desired. The provided name is what is used in url_for to build
        a URL.

        The route decorator provides the same functionality.
        """
        rule = UrlRule(url_rule, view_func, name, options)
        if name in self._view_functions.keys():
            # TODO: Raise exception for ambiguous views during registration
            log.warning('Cannot add url rule "%s" with name "%s". There is '
                        'already a view with that name', url_rule, name)
            self._view_functions[name] = None
        else:
            log.debug('Adding url rule "%s" named "%s" pointing to function '
                      '"%s"', url_rule, name, view_func.__name__)
            self._view_functions[name] = rule
        self._routes.append(rule)

    def url_for(self, endpoint, **items):
        """Returns a valid Kodi plugin URL for the given endpoint name.
        endpoint can be the literal name of a function, or it can
        correspond to the name keyword arguments passed to the route
        decorator.

        Raises AmbiguousUrlException if there is more than one possible
        view for the given endpoint name.
        """
        try:
            rule = self._view_functions[endpoint]
        except KeyError:
            try:
                rule = (rule for rule in self._view_functions.values()
                        if rule.view_func == endpoint).next()
            except StopIteration:
                raise NotFoundException(
                    '%s does not match any known patterns.' % endpoint)

        # rule can be None since values of None are allowed in the
        # _view_functions dict. This signifies more than one view function is
        # tied to the same name.
        if not rule:
            # TODO: Make this a regular exception
            raise AmbiguousUrlException

        path_qs = rule.make_path_qs(items)
        return 'plugin://%s%s' % (self._addon_id, path_qs)

    def redirect(self, url):
        """Used when you need to redirect to another view, and you only
        have the final plugin:// url."""
        # TODO: Should we be overriding self.request with the new request?
        new_request = self._parse_request(url=url, handle=self.request.handle)
        log.debug('Redirecting %s to %s', self.request.path, new_request.path)
        return self._dispatch(new_request.path)

    def run(self):
        """The main entry point for a plugin."""
        self._request = self._parse_request()
        log.debug('Handling incoming request for %s', self.request.path)
        items = self._dispatch(self.request.path)

        # Close any open storages which will persist them to disk
        if hasattr(self, '_unsynced_storage'):
            for storage in self._unsynced_storage.values():
                log.debug('Saving a %s storage to disk at "%s"',
                          storage.file_format, storage.file_path)
                storage.close()

        return items

    def _dispatch(self, path):
        for rule in self._routes:
            try:
                view_func, items = rule.match(path)
            except NotFoundException:
                continue
            log.info('Request for "%s" matches rule for function "%s"',
                     path, view_func.__name__)
            resp = view_func(**items)

            # Only call self.finish() for UI container listing calls to plugin
            # (handle will be >= 0). Do not call self.finish() when called via
            # RunPlugin() (handle will be -1).
            if not self._end_of_directory and self.handle >= 0:
                if isinstance(resp, dict):
                    resp['items'] = self.finish(**resp)
                elif isinstance(resp, collections.Iterable):
                    resp = self.finish(items=resp)
            return resp

        raise NotFoundException('No matching view found for %s' % path)

    @staticmethod
    def _parse_request(url=None, handle=None):
        """Handles setup of the plugin state, including request
        arguments, handle, mode.

        This method never needs to be called directly. For testing, see
        plugin.test()
        """
        # To accommodate self.redirect, we need to be able to parse a full
        # url as well
        if url is None:
            url = sys.argv[0]
            if len(sys.argv) == 3:
                url += sys.argv[2]
        if handle is None:
            handle = sys.argv[1]
        return Request(url, handle)
