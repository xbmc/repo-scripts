# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' This file implements the Kodi xbmcvfs module, either using stubs or alternative functionality '''

# pylint: disable=invalid-name

from __future__ import absolute_import, division, print_function, unicode_literals
import os


def File(path, flags='r'):
    ''' A reimplementation of the xbmcvfs File() function '''
    return open(path, flags)


def Stat(path):
    ''' A reimplementation of the xbmcvfs Stat() function '''

    class stat:  # pylint: disable=too-few-public-methods
        ''' A reimplementation of the xbmcvfs stat class '''

        def __init__(self, path):
            ''' The constructor xbmcvfs stat class '''
            self._stat = os.stat(path)

        def st_mtime(self):
            ''' The xbmcvfs stat class st_mtime method '''
            return self._stat.st_mtime

    return stat(path)


def delete(path):
    ''' A reimplementation of the xbmcvfs delete() function '''
    try:
        os.remove(path)
    except OSError:
        pass


def exists(path):
    ''' A reimplementation of the xbmcvfs exists() function '''
    return os.path.exists(path)


def listdir(path):
    ''' A reimplementation of the xbmcvfs listdir() function '''
    files = []
    dirs = []
    for filename in os.listdir(path):
        if os.path.isfile(filename):
            files.append(filename)
        if os.path.isdir(filename):
            dirs.append(filename)
    return dirs, files


def mkdir(path):
    ''' A reimplementation of the xbmcvfs mkdir() function '''
    return os.mkdir(path)


def mkdirs(path):
    ''' A reimplementation of the xbmcvfs mkdirs() function '''
    return os.makedirs(path)


def rmdir(path):
    ''' A reimplementation of the xbmcvfs rmdir() function '''
    return os.rmdir(path)
