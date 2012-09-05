'''
    xbmcswift2.plugin
    -----------------

    This module contains the Plugin class. This class handles all of the url
    routing and interaction with XBMC for a plugin.

    :copyright: (c) 2012 by Jonathan Beluch
    :license: GPLv3, see LICENSE for more details.
'''
import os
import sys
import pickle
import xbmcswift2
from urllib import urlencode
from functools import wraps
from optparse import OptionParser
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from listitem import ListItem
from logger import log, setup_log
from common import enum
from common import clean_dict
from urls import UrlRule, NotFoundException, AmbiguousUrlException
from xbmcswift2 import (xbmc, xbmcgui, xbmcplugin, xbmcaddon, Request,)

from xbmcmixin import XBMCMixin
from common import Modes, DEBUG_MODES


class Plugin(XBMCMixin):
    '''The Plugin objects encapsulates all the properties and methods necessary
    for running an XBMC plugin. The plugin instance is a central place for
    registering view functions and keeping track of plugin state.

    Usually the plugin instance is created in the main addon.py file for the
    plugin. Typical creation looks like this::

        from xbmcswift2 import Plugin
        plugin = Plugin('Hello XBMC', 'plugin.video.helloxbmc', __file__)

    :param name: The name of the plugin, e.g. 'Academic Earth'.
    :param addon_id: The XBMC addon ID for the plugin, e.g.
                     'plugin.video.academicearth'
    :param filepath: The path to the addon.py file. In typical usage, the
                     builtin ``__file__`` variable can used.
    '''

    def __init__(self, name, addon_id, filepath):
        self._name = name
        self._filepath = filepath
        self._addon_id = addon_id
        self._routes = []
        self._view_functions = {}
        self._addon = xbmcaddon.Addon(id=self._addon_id)

        # Keeps track of the added list items
        self._current_items = []

        # Gets initialized when self.run() is called
        self._request = None

        # A flag to keep track of a call to xbmcplugin.endOfDirectory()
        self._end_of_directory = False

        # The plugin's named logger
        self._log = setup_log(addon_id)

        # The path to the cache directory for the addon
        self._cache_path = xbmc.translatePath(
            'special://profile/addon_data/%s/.cache/' % self._addon_id)

        # If we are runing in CLI, we need to load the strings.xml manually
        # TODO: a better way to do this. Perhaps allow a user provided filepath
        if xbmcswift2.CLI_MODE:
            from xbmcswift2.mockxbmc import utils
            utils.load_addon_strings(self._addon,
                os.path.join(os.path.dirname(self._filepath), 'resources',
                             'language', 'English', 'strings.xml'))

    @property
    def log(self):
        '''The log instance for the plugin. Returns an instance of the
        stdlib's ``logging.Logger``. This log will print to STDOUT when running
        in CLI mode and will forward messages to XBMC's log when running in
        XBMC.
        '''
        return self._log

    @property
    def id(self):
        '''The id for the addon instance.'''
        return self._addon_id

    @property
    def cache_path(self):
        '''A full path to the cache folder for this plugin's addon data.'''
        return self._cache_path

    @property
    def addon(self):
        '''This plugin's underlying instance of xbmcaddon.Addon.'''
        return self._addon

    @property
    def added_items(self):
        '''The list of currently added items.

        Even after repeated calls to :meth:`~xbmcswift2.Plugin.add_items`, this
        property will contain the complete list of added items.
        '''
        return self._current_items

    def clear_added_items(self):
        # TODO: This shouldn't be exposed probably...
        self._current_items = []

    @property
    def handle(self):
        '''The current plugin's handle. Equal to ``plugin.request.handle``.'''
        return self.request.handle

    @property
    def request(self):
        '''The current :class:`~xbmcswift2.Request`.

        Raises an Exception if the request hasn't been initialized yet via
        :meth:`~xbmcswift2.Plugin.run()`.
        '''
        if self._request is None:
            raise Exception('It seems the current request has not been '
                            'initialized yet. Please ensure that '
                            '`plugin.run()` has been called before attempting '
                            'to access the current request.')
        return self._request

    @property
    def name(self):
        '''The addon's name'''
        return self._name

    def _parse_request(self, url=None, handle=None):
        '''Handles setup of the plugin state, including request
        arguments, handle, mode.

        This method never needs to be called directly. For testing, see
        plugin.test()
        '''
        # To accomdate self.redirect, we need to be able to parse a full url as
        # well
        if url is None:
            url = sys.argv[0]
            if len(sys.argv) == 3:
                url += sys.argv[2]
        if handle is None:
            handle = sys.argv[1]
        return Request(url, handle)

    def register_module(self, module, url_prefix):
        '''Registers a module with a plugin. Requires a url_prefix that
        will then enable calls to url_for.

        :param module: Should be an instance `xbmcswift2.Module`.
        :param url_prefix: A url prefix to use for all module urls,
                           e.g. '/mymodule'
        '''
        module._plugin = self
        module._url_prefix = url_prefix
        for func in module._register_funcs:
            func(self, url_prefix)

    def cached_route(self, url_rule, name=None, options=None):
        '''A decorator to add a route to a view and also apply caching.
        '''
        route_decorator = self.route(url_rule, name=name, options=options)
        cache_decorator = self.cache()
        def new_decorator(func):
            return route_decorator(cache_decorator(func))
        return new_decorator

    def route(self, url_rule, name=None, options=None):
        '''A decorator to add a route to a view. name is used to
        differentiate when there are multiple routes for a given view.'''
        # TODO: change options kwarg to defaults
        def decorator(f):
            view_name = name or f.__name__
            self.add_url_rule(url_rule, f, name=view_name, options=options)
            return f
        return decorator

    def add_url_rule(self, url_rule, view_func, name, options=None):
        '''This method adds a URL rule for routing purposes. The
        provided name can be different from the view function name if
        desired. The provided name is what is used in url_for to build
        a URL.

        The route decorator provides the same functionality.
        '''
        rule = UrlRule(url_rule, view_func, name, options)
        if name in self._view_functions.keys():
            # TODO: Raise exception for ambiguous views during registration
            log.warning('Cannot add url rule "%s" with name "%s". There is already a view with that name' % (url_rule, name))
            self._view_functions[name] = None
        else:
            log.debug('Adding url rule "%s" named "%s" pointing to function "%s"' % (url_rule, name, view_func.__name__))
            self._view_functions[name] = rule
        self._routes.append(rule)

    def url_for(self, endpoint, **items):
        '''Returns a valid XBMC plugin URL for the given endpoint name.
        endpoint can be the literal name of a function, or it can
        correspond to the name keyword arguments passed to the route
        decorator.

        Raises AmbiguousUrlException if there is more than one possible
        view for the given endpoint name.
        '''
        if endpoint not in self._view_functions.keys():
            raise NotFoundException, ('%s doesn\'t match any known patterns.' %
                                      endpoint)

        rule = self._view_functions[endpoint]
        if not rule:
            # TODO: Make this a regular exception
            raise AmbiguousUrlException

        pathqs = rule.make_path_qs(items)
        return 'plugin://%s%s' % (self._addon_id, pathqs)

    def _dispatch(self, path):
        for rule in self._routes:
            try:
                view_func, items = rule.match(path)
            except NotFoundException:
                continue
            log.info('Request for "%s" matches rule for function "%s"' % (path, view_func.__name__))
            listitems = view_func(**items)

            # TODO: Verify the main UI handle is always 0, this check exists so
            #       we don't erroneously call endOfDirectory for alternate
            #       threads
            # Allow the returning of bare dictionaries so we can cache view
            if not self._end_of_directory and self.handle == 0:
                listitems = self.finish(listitems)
            return listitems
        raise NotFoundException, 'No matching view found for %s' % path

    def redirect(self, url):
        '''Used when you need to redirect to another view, and you only
        have the final plugin:// url.'''
        # TODO: Should we be overriding self.request with the new request?
        new_request = self._parse_request(url=url, handle=self.request.handle)
        log.debug('Redirecting %s to %s' % (self.request.path, new_request.path))
        return self._dispatch(new_request.path)

    def run(self, test=False):
        '''The main entry point for a plugin.'''
        self._request = self._parse_request()
        log.debug('Handling incoming request for %s' % (self.request.path))
        return self._dispatch(self.request.path)
