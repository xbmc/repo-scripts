# -*- coding: utf-8 -*-
"""
kodiswift.actions
------------------

This module contains wrapper functions for Kodi built-in functions.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""

__all__ = ['background', 'update_view']


def background(url):
    """This action will run an addon in the background for the provided URL.

    See 'RunPlugin()' at
    http://kodi.wiki/view/List_of_built-in_functions

    Args:
        url (str): Full path must be specified.
            Does not work for folder plugins.

    Returns:
        str: String of the builtin command
    """
    return 'RunPlugin(%s)' % url


def update_view(url):
    """This action will update the current container view with provided url.

    See 'Container.Update()' at
    http://kodi.wiki/view/List_of_built-in_functions
    """
    return 'Container.Update(%s)' % url
