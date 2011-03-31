import xbmc
import os

__author__ = 'tommy'

def getCachedThumb(file):
    if file[0:8] == 'stack://':
        commaPos = file.find(' , ')
        file = file[8:commaPos].strip()

    crc = xbmc.getCacheThumbName(file.lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/%s/%s' % (crc[0], crc))

def getCachedVideoThumb(path, filename):
    if filename[0:8] == 'stack://':
        videoFile = filename
    else:
        videoFile = os.path.join(path, filename)
        
    return getCachedThumb(videoFile)


def getCachedActorThumb(name):
    return getCachedThumb('actor' + name)

def getCachedSeasonThumb(path, label):
    """
    Keyword arguments:
    label - the localized string representation of the season.
            for English this can be Specials, Season 1, Season 10, etc

    """
    return getCachedThumb('season' + path + label)

def getCachedTVShowThumb(path):
    return getCachedThumb(path)