# -*- coding:utf-8 -*-
#
# Copyright (C) 2012, Guillaume Espanel <guillaume@lolnet.org>
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

from  grooveshark.const import *

class Playlist(object):
    """
    Represents an playlist.
    Do not use this class directly.
        
    :param id: internal playlist id
    :param name: name
    :param cover_url: playlist's cover to generate an :class:`Playlist` object
    :param connection: underlying :class:`Connection` object
    """
    def __init__(self, id, name, cover_url, connection):
        self._connection = connection
        self._id = id
        self._name = name
        self._cover_url = cover_url
        if not self._cover_url:
            self._cover_url = NO_COVER_URL
        self._songs = None
        self._cover = None

    def __str__(self):
        return '%s' % (self.name)
    
    @classmethod
    def from_export(cls, export, connection):
        return cls(export['id'], export['name'], export['cover'], connection)
    
    @property
    def id(self):
        """
        internal playlist id
        """
        return self._id
    
    @property
    def name(self):
        """
        playlist's name
        """
        return self._name
    
    @property
    def cover(self):
        """
        playlist cover as :class:`Picture` object
        """
        if not self._cover:
            self._cover = Picture(self._cover_url, self._connection)
        return self._cover
    
    @property
    def songs(self):
        """
        iterator over playlist's songs as :class:`Song` objects
        """
        if self._songs is None:
            self._songs = [Song.from_response(song, self._connection) for song in \
                           self._connection.request('playlistGetSongs', {'playlistID' : self.id},
                                                    self._connection.header('playlistGetSongs'))[1]['Songs']]
        return iter(self._songs)
    
    def export(self):
        """
        Returns a dictionary with all playlist information.
        Use the :meth:`from_export` method to recreate the
        :class:`Playlist` object.
        """
        return {'id' : self.id, 'name' : self.name, 'cover' : self._cover_url}
    
from grooveshark.classes.song import Song
from grooveshark.classes.picture import Picture
