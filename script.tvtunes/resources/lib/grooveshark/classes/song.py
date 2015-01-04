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

import os
import threading

from grooveshark.const import *

class Song(object):
    """
    Represents a song.
    Do not use this class directly.

    :param id: internal song id
    :param name: name
    :param artist_id: artist's id to generate an :class:`Artist` object
    :param artist_name: artist's name to generate an :class:`Artist` object
    :param album_id: album's id to generate an :class:`Album` object
    :param album_name: album's name to generate an :class:`Album` object
    :param cover_url: album's cover to generate an :class:`Album` object
    :param track: track number
    :param duration: estimate song duration
    :param popularity: popularity
    :param connection: underlying :class:`Connection` object
    """
    def __init__(self, id, name, artist_id, artist_name, album_id, album_name, cover_url, track, duration, popularity, connection):
        self._connection = connection
        self._id = id
        self._name = name
        self._artist_id = artist_id
        self._artist_name = artist_name
        self._album_id = album_id
        self._album_name = album_name
        self._cover_url = cover_url
        if not self._cover_url:
            self._cover_url = NO_COVER_URL
        self._track = track
        self._duration = duration
        self._popularity = popularity
        self._artist = None
        self._album = None

    def __str__(self):
        return '%s - %s - %s' % (self.name, self.artist.name, self.album.name)

    @classmethod
    def from_response(cls, song, connection):
        return cls(song['SongID'], song['Name'] if 'Name' in song else song['SongName'], song['ArtistID'], song['ArtistName'], song['AlbumID'], song['AlbumName'],
                   ALBUM_COVER_URL + song['CoverArtFilename'] if song['CoverArtFilename'] else None, song['TrackNum'], song['EstimateDuration'], song['Popularity'], connection)

    @classmethod
    def from_export(cls, export, connection):
        return cls(export['id'], export['name'], export['artist_id'], export['artist'], export['album_id'], export['album'], export['cover'],
                   export['track'], export['duration'], export['popularity'], connection)

    @property
    def id(self):
        """
        internal song id
        """
        return self._id

    @property
    def name(self):
        """
        song name
        """
        return self._name

    @property
    def artist(self):
        """
        artist as :class:`Artist` object
        """
        if not self._artist:
            self._artist = Artist(self._artist_id, self._artist_name, self._connection)
        return self._artist

    @property
    def album(self):
        """
        album as :class:`Album` object
        """
        if not self._album:
            self._album = Album(self._album_id, self._album_name, self._artist_id, self._artist_name, self._cover_url, self._connection)
        return self._album

    @property
    def track(self):
        """
        track number
        """
        return self._track

    @property
    def duration(self):
        """
        estimate song duration
        """
        return self._duration

    @property
    def popularity(self):
        """
        popularity
        """
        return self._popularity

    @property
    def stream(self):
        """
        :class:`Stream` object for playing
        """
        # Add song to queue
        self._connection.request('addSongsToQueue',
                                 {'songIDsArtistIDs': [{'artistID': self.artist.id,
                                                        'source': 'user',
                                                        'songID': self.id,
                                                        'songQueueSongID': 1}],
                                  'songQueueID': self._connection.session.queue},
                                 self._connection.header('addSongsToQueue', 'jsqueue'))


        stream_info = self._connection.request('getStreamKeyFromSongIDEx', {'songID' : self.id, 'country' : self._connection.session.country,
                                                                            'prefetch' : False, 'mobile' : False},
                                               self._connection.header('getStreamKeyFromSongIDEx', 'jsqueue'))[1]
        return Stream(stream_info['ip'], stream_info['streamKey'], self._connection)

    def export(self):
        """
        Returns a dictionary with all song information.
        Use the :meth:`from_export` method to recreate the
        :class:`Song` object.
        """
        return {'id' : self.id, 'name' : self.name, 'artist' : self._artist_name, 'artist_id' : self._artist_id,
                'album' : self._album_name, 'album_id' : self._album_id, 'track' : self.track,
                'duration' : self.duration, 'popularity' : self.popularity, 'cover' : self._cover_url}

    def format(self, pattern):
        """
        Format the song according to certain patterns:

        %a: artist title
        %s: song title
        %A: album title
        """
        pattern = pattern.replace('%a', self.artist.name)
        pattern = pattern.replace('%s', self.name)
        pattern = pattern.replace('%A', self.album.name)
        return pattern.replace('/', '').replace('\\', '')

    def download(self, directory='~/Music', song_name='%a - %s - %A'):
        """
        Download a song to a directory.

        :param directory: A system file path.
        :param song_name: A name that will be formatted with :meth:`format`.
        :return: The formatted song name.
        """
        formatted = self.format(song_name)
        path = os.path.expanduser(directory) + os.path.sep + formatted + '.mp3'
        try:
            raw = self.safe_download()
            with open(path, 'wb') as f:
                f.write(raw)
        except:
            raise
        return formatted

    def safe_download(self):
        """Download a song respecting Grooveshark's API.

        :return: The raw song data.
        """
        def _markStreamKeyOver30Seconds(stream):
            self._connection.request('markStreamKeyOver30Seconds',
                                     {'streamServerID': stream.ip,
                                      'artistID': self.artist.id,
                                      'songQueueID': self._connection.session.queue,
                                      'songID': self.id,
                                      'songQueueSongID': 1,
                                      'streamKey': stream.key},
                                     self._connection.header('markStreamKeyOver30Seconds',
                                                             'jsqueue'))

        stream = self.stream
        timer = threading.Timer(30, _markStreamKeyOver30Seconds, [stream])
        timer.start()
        raw = stream.data.read()
        if len(raw) == stream.size:
            timer.cancel()
            self._connection.request('markSongDownloadedEx',
                                     {'streamServerID': stream.ip,
                                      'songID': self.id,
                                      'streamKey': stream.key},
                                     self._connection.header('markSongDownloadedEx',
                                                             'jsqueue'))
            self._connection.request('removeSongsFromQueue',
                                     {'userRemoved':True,
                                      'songQueueID': self._connection.session.queue,
                                      'songQueueSongIDs': [1]},
                                     self._connection.header('removeSongsFromQueue',
                                                             'jsqueue'))
            return raw
        else:
            raise ValueError("Content-Length {}, but read {}"
                             .format(stream.size, len(raw)))


from grooveshark.classes.artist import Artist
from grooveshark.classes.album import Album
from grooveshark.classes.stream import Stream
