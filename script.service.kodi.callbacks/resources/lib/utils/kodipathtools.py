#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import os
import platform
import re
import stat
import sys

import xbmc
import xbmcaddon


def _translatePathMock(path):
    return kodiTranslatePathMock(path)


try:
    from xbmc import translatePath as kodiTP
except ImportError:
    kodiTP = _translatePathMock
    isStub = True
else:
    if kodiTP('special://home') == u'':
        isStub = True
        kodiTP = _translatePathMock
    else:
        isStub = False

_split = re.compile(r'\0')


def getPlatform():
    if sys.platform.startswith('win'):
        ret = 'win'
    elif platform.system().lower().startswith('darwin'):
        if platform.machine().startswith('iP'):
            ret = 'ios'
        else:
            ret = 'osx'
    elif 'XBMC_ANDROID_SYSTEM_LIBS' in os.environ.keys():
        ret = 'and'
    else:  # Big assumption here
        ret = 'nix'
    return ret


def secure_filename(path):
    return _split.sub('', path)


def translatepath(path):
    ret = []
    if path.lower().startswith(u'special://'):
        special = re.split(ur'\\|/', path[10:])[0]
        if special.startswith(u'addondata'):
            myid = re.findall(ur'addondata\((.+?)\)', special)
            if len(myid) > 0:
                ret.append(addondatapath(myid[0]))
            else:
                ret.append(addondatapath())
        elif special.startswith(u'addon'):
            myid = re.findall(ur'addon\((.+?)\)', special)
            if len(myid) > 0:
                ret.append(addonpath(myid[0]))
            else:
                ret.append(addonpath())
        else:
            ret.append(kodiTP(u'special://%s' % special))
        path = path[10:]
        ret = ret + re.split(ur'\\|/', path)[1:]
    else:
        ret = re.split(ur'\\|/', path)
    if ret[0].endswith(':'):
        ret[0] = u'%s\\' % ret[0]
    for i, r in enumerate(ret):
        ret[i] = secure_filename(r)
    ret = os.path.join(*ret)
    ret = os.path.expandvars(ret)
    ret = os.path.expanduser(ret)
    ret = os.path.normpath(ret)
    if path.startswith('/'):
        ret = u'/%s' % ret

    # if not os.path.supports_unicode_filenames:
    #     ret = ret.decode('utf-8')

    ret = secure_filename(ret)
    return ret


def kodiTranslatePathMock(path):
    ret = []
    special = re.split(ur'\\|/', path[10:])[0]
    if special == u'home':
        ret.append(homepath())
    elif special == u'logpath':
        ret.append(logpath())
    elif special == u'masterprofile' or special == u'userdata':
        ret = ret + [homepath(), u'userdata']
    return os.path.join(*ret)


def addonpath(addon_id=u'script.service.kodi.callbacks'):
    if isStub:
        path = os.path.join(*[homepath(), u'addons', addon_id])
    else:
        try:
            path = unicode(xbmcaddon.Addon(addon_id).getAddonInfo('path'))
        except RuntimeError:
            path = ''
    if path == '':
        path = os.path.join(*[homepath(), u'addons', addon_id])
    return path


def addondatapath(addon_id=u'script.service.kodi.callbacks'):
    if isStub:
        path = os.path.join(*[homepath(), u'userdata', u'addon_data', addon_id])
    else:
        path = os.path.join(*[xbmc.translatePath('special://userdata'), 'addon_data', addon_id])
    return path


def homepath():
    paths = {'win': ur'%APPDATA%\Kodi', 'nix': ur'$HOME/.kodi', 'osx': ur'~/Library/Application Support/Kodi',
             'ios': ur'/private/var/mobile/Library/Preferences/Kodi',
             'and': ur' /sdcard/Android/data/org.xbmc.kodi/files/.kodi/'}
    if isStub:
        return translatepath(paths[getPlatform()])
    else:
        return xbmc.translatePath(u'special://home')


def logpath():
    paths = {'win': ur'%APPDATA%\Kodi\kodi.log', 'nix': ur'$HOME/.kodi/temp/kodi.log', 'osx': ur'~/Library/Logs/kodi.log',
             'ios': ur'/private/var/mobile/Library/Preferences/kodi.log',
             'and': ur'/sdcard/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log'}
    if isStub:
        return translatepath(paths[getPlatform()])
    else:
        return xbmc.translatePath(u'special://logpath')


def setPathExecuteRW(path):
    path = translatepath(path)
    try:
        os.chmod(path, os.stat(
            path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    except OSError:
        pass


def setPathExecute(path):
    path = translatepath(path)
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def setPathRW(path):
    path = translatepath(path)
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    except OSError:
        pass
