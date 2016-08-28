# -*- coding: utf-8 -*-
"""
kodiswift.constants
--------------------

This module contains some helpful constants which ease interaction
with Kodi.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

from kodiswift import xbmcplugin

__all__ = ['SortMethod']


class SortMethod(object):
    """Static class to hold all of the available sort methods. The prefix
    of 'SORT_METHOD_' is stripped.

    e.g. SORT_METHOD_TITLE becomes SortMethod.TITLE
    """
    ALBUM = xbmcplugin.SORT_METHOD_ALBUM
    ALBUM_IGNORE_THE = xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE
    ARTIST = xbmcplugin.SORT_METHOD_ARTIST
    ARTIST_IGNORE_THE = xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE
    BITRATE = xbmcplugin.SORT_METHOD_BITRATE
    CHANNEL = xbmcplugin.SORT_METHOD_CHANNEL
    COUNTRY = xbmcplugin.SORT_METHOD_COUNTRY
    DATE = xbmcplugin.SORT_METHOD_DATE
    DATEADDED = xbmcplugin.SORT_METHOD_DATEADDED
    DATE_TAKEN = xbmcplugin.SORT_METHOD_DATE_TAKEN
    DRIVE_TYPE = xbmcplugin.SORT_METHOD_DRIVE_TYPE
    DURATION = xbmcplugin.SORT_METHOD_DURATION
    EPISODE = xbmcplugin.SORT_METHOD_EPISODE
    FILE = xbmcplugin.SORT_METHOD_FILE
    FULLPATH = xbmcplugin.SORT_METHOD_FULLPATH
    GENRE = xbmcplugin.SORT_METHOD_GENRE
    LABEL = xbmcplugin.SORT_METHOD_LABEL
    LABEL_IGNORE_FOLDERS = xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS
    LABEL_IGNORE_THE = xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE
    LASTPLAYED = xbmcplugin.SORT_METHOD_LASTPLAYED
    LISTENERS = xbmcplugin.SORT_METHOD_LISTENERS
    MPAA_RATING = xbmcplugin.SORT_METHOD_MPAA_RATING
    NONE = xbmcplugin.SORT_METHOD_NONE
    PLAYCOUNT = xbmcplugin.SORT_METHOD_PLAYCOUNT
    PLAYLIST_ORDER = xbmcplugin.SORT_METHOD_PLAYLIST_ORDER
    PRODUCTIONCODE = xbmcplugin.SORT_METHOD_PRODUCTIONCODE
    PROGRAM_COUNT = xbmcplugin.SORT_METHOD_PROGRAM_COUNT
    SIZE = xbmcplugin.SORT_METHOD_SIZE
    SONG_RATING = xbmcplugin.SORT_METHOD_SONG_RATING
    STUDIO = xbmcplugin.SORT_METHOD_STUDIO
    STUDIO_IGNORE_THE = xbmcplugin.SORT_METHOD_STUDIO_IGNORE_THE
    TITLE = xbmcplugin.SORT_METHOD_TITLE
    TITLE_IGNORE_THE = xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE
    TRACKNUM = xbmcplugin.SORT_METHOD_TRACKNUM
    UNSORTED = xbmcplugin.SORT_METHOD_UNSORTED
    VIDEO_RATING = xbmcplugin.SORT_METHOD_VIDEO_RATING
    VIDEO_RUNTIME = xbmcplugin.SORT_METHOD_VIDEO_RUNTIME
    VIDEO_SORT_TITLE = xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE
    VIDEO_SORT_TITLE_IGNORE_THE = xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE
    VIDEO_TITLE = xbmcplugin.SORT_METHOD_VIDEO_TITLE
    VIDEO_USER_RATING = xbmcplugin.SORT_METHOD_VIDEO_USER_RATING
    VIDEO_YEAR = xbmcplugin.SORT_METHOD_VIDEO_YEAR

    @classmethod
    def from_string(cls, sort_method):
        """Returns the sort method specified. sort_method is case insensitive.
        Will raise an AttributeError if the provided sort_method does not
        exist.

        >>> SortMethod.from_string('title')
        """
        return getattr(cls, sort_method.upper())
