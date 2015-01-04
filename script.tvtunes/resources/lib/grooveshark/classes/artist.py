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

class Artist(object):
    """
    Represents an artist.
    Do not use this class directly.
        
    :param id: internal artist id
    :param name: name
    :param connection: underlying :class:`Connection` object
    """
    def __init__(self, id, name, connection):
        self._connection = connection
        self._id = id
        self._name = name
        self._similar = None
        self._songs = None
        
    def __str__(self):
        return self.name
    
    @classmethod
    def from_export(cls, export, connection):
        return cls(export['id'], export['name'], connection)

    @property
    def id(self):
        """
        internal artist id
        """
        return self._id
    
    @property
    def name(self):
        """
        artist's name
        """
        return self._name

    @property
    def similar(self):
        """
        iterator over similar artists as :class:`Artist` objects
        """
        if self._similar is None:
            self._similar = [Artist(artist['ArtistID'], artist['Name'], self._connection) for artist in \
                             self._connection.request('artistGetSimilarArtists', {'artistID' : self.id},
                                                      self._connection.header('artistGetSimilarArtists'))[1]['SimilarArtists']]
        return iter(self._similar)
    
    @property
    def songs(self):
        """
        iterator over artist's songs as :class:`Song` objects
        """
        if self._songs is None:
            self._songs = [Song.from_response(song, self._connection) for song in \
                           self._connection.request('artistGetArtistSongs', {'artistID' : self.id},
                                                    self._connection.header('artistGetArtistSongs'))[1]]
        return iter(self._songs)
    
    def export(self):
        """
        Returns a dictionary with all artist information.
        Use the :meth:`from_export` method to recreate the
        :class:`Artist` object.
        """
        return {'id' : self.id, 'name' : self.name}
    
from grooveshark.classes.song import Song