# coding=utf-8
import os
import fnmatch


def fast_glob(pathname):
    return list(fast_iglob(pathname))


def fast_iglob(pathname):
    """
    Minimal glob on Kodi>18 (os.walk now uses scandir on Python3.5+)
    """
    dirname, basename = os.path.split(pathname)
    for _, _, files in os.walk(dirname):
        for f in files:
            if fnmatch.fnmatch(f, basename):
                yield f
