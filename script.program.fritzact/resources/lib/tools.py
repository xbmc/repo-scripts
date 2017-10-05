#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import os
import random

__addon__ = xbmcaddon.Addon()
__addonID__ = __addon__.getAddonInfo('id')
__path__ = __addon__.getAddonInfo('path')
__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'lib', 'media', 'default.png'))


# de-/encrypt passwords, simple algorithm, but prevent for sniffers and script kiddies

def crypt( pw, key, token):
    _pw = __addon__.getSetting(pw)
    if _pw == '' or _pw == '*':
        _key = __addon__.getSetting(key)
        _token = __addon__.getSetting(token)
        if len(_key) > 2: return "".join([chr(ord(_token[i]) ^ ord(_key[i])) for i in range(int(_key[-2:]))])
        return ''
    else:
        _key = ''
        for d in range((len(pw) / 16) + 1):
            _key += ('%016d' % int(random.random() * 10 ** 16))
        _key = _key[:-2] + ('%02d' % len(_pw))
        _tpw = _pw.ljust(len(_key), 'a')
        _token = "".join([chr(ord(_tpw[i]) ^ ord(_key[i])) for i in range(len(_key))])

        __addon__.setSetting(key, _key)
        __addon__.setSetting(token, _token)
        __addon__.setSetting(pw, '*')

        return _pw

# get parameter hash, convert into parameter/value pairs, return dictionary

def paramsToDict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters.split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

# write log messages

def writeLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonID__, message.encode('utf-8')), level)

# OSD notification (DialogKaiToast)

def notifyOSD(header, message, icon=__IconDefault__, time=5000):
    xbmcgui.Dialog().notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)