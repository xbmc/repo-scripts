# -*- coding: utf-8 -*-
"""
kodiswift.module
-----------------

This module contains the Module Class.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

from kodiswift import setup_log
from kodiswift.xbmcmixin import XBMCMixin

__all__ = ['Module']


class Module(XBMCMixin):
    """Modules are basically mini plugins except they don't have any
    functionality until they are registered with a Plugin.
    """

    def __init__(self, namespace):
        # Get rid of package prefixes
        self._namespace = namespace.split('.')[-1]
        self._view_functions = {}
        self._routes = []
        self._register_funcs = []
        self._plugin = None
        self._url_prefix = None
        self._log = setup_log(namespace)

    @property
    def plugin(self):
        """Returns the plugin this module is registered to, or

        Returns:
            kodiswift.Plugin:

        Raises:
            RuntimeError: If not registered
        """
        if self._plugin is None:
            raise RuntimeError('Module must be registered in order to call'
                               'this method.')
        return self._plugin

    @plugin.setter
    def plugin(self, value):
        self._plugin = value

    @property
    def cache_path(self):
        """Returns the module's cache_path."""
        return self.plugin.storage_path

    @property
    def addon(self):
        """Returns the module's addon"""
        return self.plugin.addon

    @property
    def added_items(self):
        """Returns this module's added_items"""
        return self.plugin.added_items

    @property
    def handle(self):
        """Returns this module's handle"""
        return self.plugin.handle

    @property
    def request(self):
        """Returns the current request"""
        return self.plugin.request

    @property
    def log(self):
        """Returns the registered plugin's log."""
        return self._log

    @property
    def url_prefix(self):
        """Sets or gets the url prefix of the module.

        Raises an Exception if this module is not registered with a
        Plugin.

        Returns:
            str:

        Raises:
            RuntimeError:
        """
        if self._url_prefix is None:
            raise RuntimeError(
                'Module must be registered in order to call this method.')
        return self._url_prefix

    @url_prefix.setter
    def url_prefix(self, value):
        self._url_prefix = value

    @property
    def register_funcs(self):
        return self._register_funcs

    def route(self, url_rule, name=None, options=None):
        """A decorator to add a route to a view. name is used to
        differentiate when there are multiple routes for a given view."""
        def decorator(func):
            """Adds a url rule for the provided function"""
            view_name = name or func.__name__
            self.add_url_rule(url_rule, func, name=view_name, options=options)
            return func
        return decorator

    def url_for(self, endpoint, explicit=False, **items):
        """Returns a valid Kodi plugin URL for the given endpoint name.
        endpoint can be the literal name of a function, or it can
        correspond to the name keyword arguments passed to the route
        decorator.

        Currently, view names must be unique across all plugins and
        modules. There are not namespace prefixes for modules.
        """
        # TODO: Enable items to be passed with keywords of other var names
        #       such as endpoing and explicit
        # TODO: Figure out how to handle the case where a module wants to
        #       call a parent plugin view.
        if not explicit and not endpoint.startswith(self._namespace):
            endpoint = '%s.%s' % (self._namespace, endpoint)
        return self._plugin.url_for(endpoint, **items)

    def add_url_rule(self, url_rule, view_func, name, options=None):
        """This method adds a URL rule for routing purposes. The
        provided name can be different from the view function name if
        desired. The provided name is what is used in url_for to build
        a URL.

        The route decorator provides the same functionality.
        """
        name = '%s.%s' % (self._namespace, name)

        def register_rule(plugin, url_prefix):
            """Registers a url rule for the provided plugin and
            url_prefix.
            """
            full_url_rule = url_prefix + url_rule
            plugin.add_url_rule(full_url_rule, view_func, name, options)

        # Delay actual registration of the url rule until this module is
        # registered with a plugin
        self._register_funcs.append(register_rule)
