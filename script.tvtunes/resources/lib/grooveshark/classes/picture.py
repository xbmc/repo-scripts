# -*- coding:utf-8 -*-
#
# Copyright (C) 2012, Maximilian Köhl <linuxmaxi@googlemail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys

import contextlib

#if sys.version_info.major == 3:
#    import urllib.request as urllib
#else:
import urllib2 as urllib

from grooveshark.const import *

class Picture(object):
    """
    Could be an album cover or a user picture.
    Do not use this class directly.
        
    :param url: image url
    """
    def __init__(self, url, connection):
        self._url = url
        self._connection = connection
        self._data = None
        self._type = self._url.split('.').pop()
    
    @property
    def type(self):
        """
        image type for example png or jpg
        """
        return self._type
    
    @property
    def data(self):
        """
        raw image data
        """
        if self._data is None:
            request = urllib.Request(self._url, headers={'User-Agent' : USER_AGENT})
            with contextlib.closing(self._connection.urlopen(request)) as response:
                self._data = response.read()
        return self._data