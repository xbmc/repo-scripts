#/*
# *
# * OpenVPN for Kodi.
# *
# * Copyright (C) 2018 Venus
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *
# */

import xbmc
import xbmcgui
import unicodedata
import urllib

def normalize_unicode(text):
    if text and not isinstance(text, unicode):
        return text
    if not text or len(text) == 0:
        return ''
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')

def check_value(value):
    if value is None:
        return ''
    return normalize_unicode(value)

def get_value(tuple, key):
    if key not in tuple:
        return ''
    return check_value(tuple[key])

def check_int(value):
    if value is None:
        return 0
    return value

def get_int(tuple, key):
    if key not in tuple:
        return 0
    return int(check_value(tuple[key]))

def add_params(root, params):
    return '%s?%s' % (root, urllib.urlencode(params))

def browse(type, heading, shares='files', mask='', enablemultiple=False):
    dialog = xbmcgui.Dialog()
    return dialog.browse(type, heading, shares, mask, enablemultiple)

def browse_files(heading, shares='files', mask='', enablemultiple=False):
    return browse(1, heading, shares, mask, enablemultiple)

def keyboard(default='', heading='', hidden=False):
    kb = xbmc.Keyboard(default, heading, hidden)
    kb.doModal()
    if (kb.isConfirmed() and len(kb.getText()) > 0):
        return kb.getText()
    return None

def notification(header, message, time=5000, image=''):
    command = 'Notification(%s, %s, %s, %s)' % (header, message, time, image)
    xbmc.executebuiltin(command)

def ok(heading, line1, line2='', line3=''):
    dialog = xbmcgui.Dialog()
    dialog.ok(heading, line1, line2, line3)

def select(heading, list):
    dialog = xbmcgui.Dialog()
    return dialog.select(heading, list)

def yesno(heading, line1, line2='', line3=''):
    dialog = xbmcgui.Dialog()
    return dialog.yesno(heading, line1, line2, line3) == 1

def get_params(text):
    param = []
    paramstring = text
    if (len(paramstring) >= 2):
        params = text
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = urllib.unquote_plus(splitparams[1])
    return param
