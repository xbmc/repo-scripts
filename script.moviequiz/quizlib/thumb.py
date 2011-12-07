import xbmc
import os

__author__ = 'tommy'

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