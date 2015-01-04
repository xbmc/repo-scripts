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

if sys.version[0] == '3':
    import urllib.request as urllib
    from urllib.parse import quote_plus, urlencode
else:
    import urllib2 as urllib
    from urllib import quote_plus, urlencode

from grooveshark.const import *

class Stream(object):
    """
    Get song's raw data.
    Do not use this class directly.

    :param ip: streaming server address
    :param key: streaming key required to get the stream
    :param connection: underlying :class:`Connection` object
    """
    def __init__(self, ip, key, connection):
        self._ip = ip
        self._key = key
        self._connection = connection
        self._data = None
        self._size = None

    def _request(self):
        request = urllib.Request('http://%s/stream.php' % (self._ip), data=urlencode({'streamKey' : self._key}).encode('utf-8'),
                                         headers={'User-Agent' : USER_AGENT})
        self._data = self._connection.urlopen(request)
        self._size = int(self.data.info()['Content-Length'])

    @property
    def ip(self):
        """
        stream server IP
        """
        return self._ip

    @property
    def key(self):
        """
        stream key
        """
        return self._key

    @property
    def url(self):
        """
        stream URL
        """
        return 'http://%s/stream.php?streamKey=%s' % (self._ip, quote_plus(self._key))

    @property
    def data(self):
        """
        a file-like object containing song's raw data
        """
        if not self._data:
            self._request()
        return self._data

    @property
    def size(self):
        """
        size of the song's raw data in bytes
        """
        if not self._size:
            self._request()
        return self._size
