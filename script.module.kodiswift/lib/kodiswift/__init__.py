# -*- coding: utf-8 -*-
"""
kodiswift
----------

A micro framework to enable rapid development of Kodi plugins.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

from types import ModuleType

try:
    import xbmc
    import xbmcgui
    import xbmcplugin
    import xbmcaddon
    import xbmcvfs

    CLI_MODE = False
except ImportError:
    CLI_MODE = True
    import sys
    from kodiswift.logger import log

    # Mock the Kodi modules
    from kodiswift.mockxbmc import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

    class _Module(ModuleType):
        """A wrapper class for a module used to override __getattr__.
        This class will behave normally for any existing module attributes.
        For any attributes which do not exist in the wrapped module, a mock
        function will be returned. This function will also return itself
        enabling multiple mock function calls.
        """

        def __init__(self, wrapped=None):
            self.wrapped = wrapped
            if wrapped:
                self.__dict__.update(wrapped.__dict__)

        def __getattr__(self, name):
            """Returns any existing attr for the wrapped module or returns a
            mock function for anything else. Never raises an AttributeError.
            """
            try:
                return getattr(self.wrapped, name)
            except AttributeError:
                # noinspection PyUnusedLocal
                # pylint disable=unused-argument
                def func(*args, **kwargs):
                    """A mock function which returns itself, enabling chainable
                    function calls.
                    """
                    log.warning('The %s method has not been implemented on '
                                'the CLI. Your code might not work properly '
                                'when calling it.', name)
                    return self

                return func

    xbmc = _Module(xbmc)
    xbmcgui = _Module(xbmcgui)
    xbmcplugin = _Module(xbmcplugin)
    xbmcaddon = _Module(xbmcaddon)
    xbmcvfs = _Module(xbmcvfs)
    for m in (xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs):
        name = reversed(m.__name__.rsplit('.', 1)).next()
        sys.modules[name] = m

from kodiswift.storage import TimedStorage
from kodiswift.request import Request
from kodiswift.common import (kodi_url, clean_dict, pickle_dict, unpickle_args,
                              unpickle_dict, download_page)
from kodiswift.constants import SortMethod
from kodiswift.listitem import ListItem
from kodiswift.logger import setup_log
from kodiswift.module import Module
from kodiswift.urls import AmbiguousUrlException, NotFoundException, UrlRule
from kodiswift.xbmcmixin import XBMCMixin
from kodiswift.plugin import Plugin
