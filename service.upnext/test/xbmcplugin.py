# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' This file implements the Kodi xbmcplugin module, either using stubs or alternative functionality '''

# pylint: disable=invalid-name,unused-argument
from __future__ import absolute_import, division, print_function, unicode_literals

from xbmc import log
from xbmcextra import kodi_to_ansi, uri_to_path

try:  # Python 3
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
except ImportError:  # Python 2
    from urllib2 import HTTPError, Request, urlopen

SORT_METHOD_NONE = 0
SORT_METHOD_LABEL = 1
SORT_METHOD_LABEL_IGNORE_THE = 2
SORT_METHOD_DATE = 3
SORT_METHOD_SIZE = 4
SORT_METHOD_FILE = 5
SORT_METHOD_DURATION = 8
SORT_METHOD_TITLE = 9
SORT_METHOD_TITLE_IGNORE_THE = 10
SORT_METHOD_GENRE = 16
SORT_METHOD_COUNTRY = 17
SORT_METHOD_DATEADDED = 21
SORT_METHOD_PROGRAM_COUNT = 22
SORT_METHOD_EPISODE = 24
SORT_METHOD_VIDEO_TITLE = 25
SORT_METHOD_VIDEO_SORT_TITLE = 26
SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE = 27
SORT_METHOD_STUDIO = 33
SORT_METHOD_STUDIO_IGNORE_THE = 34
SORT_METHOD_FULLPATH = 35
SORT_METHOD_LABEL_IGNORE_FOLDERS = 36
SORT_METHOD_LASTPLAYED = 37
SORT_METHOD_PLAYCOUNT = 38
SORT_METHOD_UNSORTED = 40
SORT_METHOD_CHANNEL = 41
SORT_METHOD_BITRATE = 43
SORT_METHOD_DATE_TAKEN = 44


def addDirectoryItem(handle, path, listitem, isFolder=False):
    ''' A reimplementation of the xbmcplugin addDirectoryItems() function '''
    label = kodi_to_ansi(listitem.label)
    path = uri_to_path(path) if path else ''
    # perma = kodi_to_ansi(listitem.label)  # FIXME: Add permalink
    bullet = '»' if isFolder else '·'
    print('{bullet} {label}{path}'.format(bullet=bullet, label=label, path=path))
    return True


def addDirectoryItems(handle, listing, length):
    ''' A reimplementation of the xbmcplugin addDirectoryItems() function '''
    for item in listing:
        addDirectoryItem(handle, item[0], item[1], item[2])
    return True


def addSortMethod(handle, sortMethod):
    ''' A stub implementation of the xbmcplugin addSortMethod() function '''


def endOfDirectory(handle, succeeded=True, updateListing=True, cacheToDisc=True):
    ''' A stub implementation of the xbmcplugin endOfDirectory() function '''
    # print(kodi_to_ansi('[B]-=( [COLOR cyan]--------[/COLOR] )=-[/B]'))


def setContent(handle, content):
    ''' A stub implementation of the xbmcplugin setContent() function '''


def setPluginFanart(handle, image, color1=None, color2=None, color3=None):
    ''' A stub implementation of the xbmcplugin setPluginFanart() function '''


def setPluginCategory(handle, category):
    ''' A reimplementation of the xbmcplugin setPluginCategory() function '''
    print(kodi_to_ansi('[B]-=( [COLOR cyan]%s[/COLOR] )=-[/B]' % category))


def setResolvedUrl(handle, succeeded, listitem):
    ''' A stub implementation of the xbmcplugin setResolvedUrl() function '''
    request = Request(listitem.path)
    request.get_method = lambda: 'HEAD'
    try:
        response = urlopen(request)
        log('Stream playing successfully: %s' % response.code, 'Info')
    except HTTPError as exc:
        log('Playing stream returned: %s' % exc, 'Fatal')
