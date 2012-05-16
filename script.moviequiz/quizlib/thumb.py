#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmc
import os

def _getFilename(path, filename = None):
    if filename is not None and filename[0:8] == 'stack://':
        commaPos = filename.find(' , ')
        file = filename[8:commaPos].strip()
    elif filename is not None:
        file = os.path.join(path, filename)
    else:
        file = path

    return file

def _getCachedThumb(path, filename = None):
    crc = xbmc.getCacheThumbName(_getFilename(path, filename).lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/%s/%s' % (crc[0], crc))

def getCachedVideoThumb(path, filename):
    return _getCachedThumb(path, filename)

def getCachedVideoFanart(path, filename):
    crc = xbmc.getCacheThumbName(_getFilename(path, filename).lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/Fanart/%s' % crc)


def getCachedActorThumb(name):
    return _getCachedThumb('actor' + name)

def getCachedSeasonThumb(path, label):
    """
    Keyword arguments:
    label - the localized string representation of the season.
            for English this can be Specials, Season 1, Season 10, etc

    """
    return _getCachedThumb('season' + path + label)

def getCachedTVShowThumb(path):
    return _getCachedThumb(path)