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

# time in seconds until a new communication token is needed
TOKEN_TIMEOUT = 1200
# user agent used to access grooveshark
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.2; rv:9.0.1) Gecko/20100101 Firefox/9.0.1'
# url where album covers are located
ALBUM_COVER_URL = 'http://images.grooveshark.com/static/albums/'
# url where playlists covers are located
PLAYLIST_COVER_URL = 'http://images.grooveshark.com/static/playlists/'
# no cover url
NO_COVER_URL = 'http://images.grooveshark.com/static/albums/70_album.png'
# the grooveshark clients - using API tokens from SciLor (scilor.com) now
# because the ones I extracted out of Grooveshark do not work for some reason
# (I meet SciLor, he tells me that they do some type of encryption but don't
# know more) - thanks.
CLIENTS = {'htmlshark' : {'version' : '20130520',
                          'token' : 'nuggetsOfBaller'},
           'jsqueue' : {'version' : '20130520',
                        'token' : 'chickenFingers'}}
# grooveshark country settings
COUNTRY = {'ID': 221, 'CC1': 0, 'CC2': 0, 'CC3': 0, 'CC4': 0, 'DMA': 0, 'IPR': 0}
