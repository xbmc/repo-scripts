'''
    xbmcswift2.actions
    ------------------

    This module contains wrapper functions for KODI built-in functions.

    :copyright: (c) 2012 by Jonathan Beluch
    :license: GPLv3, see LICENSE for more details.
'''


def background(url):
    '''This action will run an addon in the background for the provided URL.

    See 'RunPlugin()' at
    https://codedocs.xyz/xbmc/xbmc/page__list_of_built_in_functions.html.
    '''
    return 'RunPlugin(%s)' % url


def update_view(url):
    '''This action will update the current container view with provided url.

    See 'Container.Update()' at
    https://codedocs.xyz/xbmc/xbmc/page__list_of_built_in_functions.html.
    '''
    return 'Container.Update(%s)' % url
