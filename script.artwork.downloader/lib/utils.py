#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
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

#import modules
import lib.common
import socket
import xbmc
import xbmcgui
import unicodedata
import urllib2
import sys

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
# Commoncache plugin import
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

### import libraries
from lib.script_exceptions import *
from urllib2 import HTTPError, URLError

### get addon info
__addon__        = lib.common.__addon__
__localize__     = lib.common.__localize__
__addonname__    = lib.common.__addonname__
__icon__         = lib.common.__icon__

cache = StorageServer.StorageServer("ArtworkDownloader",240)

### Adjust default timeout to stop script hanging
socket.setdefaulttimeout(20)
### Cache bool
CACHE_ON = True

### Declare dialog
dialog = xbmcgui.DialogProgress()


# Fixes unicode problems
def string_unicode(text, encoding='utf-8'):
    try:
        text = unicode( text, encoding )
    except:
        pass
    return text

def normalize_string(text):
    try:
        text = unicodedata.normalize('NFKD', string_unicode(text)).encode('ascii', 'ignore')
    except:
        pass
    return text

# Define log messages
def log(txt, severity=xbmc.LOGDEBUG):
    if severity == xbmc.LOGDEBUG and not __addon__.getSetting("debug_enabled") == 'true':
        pass
    else:
        try:
            message = ('%s: %s' % (__addonname__,txt) )
            xbmc.log(msg=message, level=severity)
        except UnicodeEncodeError:
            try:
                message = normalize_string('%s: %s' % (__addonname__,txt) )
                xbmc.log(msg=message, level=severity)
            except:
                message = ('%s: UnicodeEncodeError' %__addonname__)
                xbmc.log(msg=message, level=xbmc.LOGWARNING)

# Define dialogs
def dialog_msg(action,
               percentage = 0,
               line0 = '',
               line1 = '',
               line2 = '',
               line3 = '',
               background = False,
               nolabel = __localize__(32026),
               yeslabel = __localize__(32025),
               cancelled = False):
    # Fix possible unicode errors 
    line0 = line0.encode( 'utf-8', 'ignore' )
    line1 = line1.encode( 'utf-8', 'ignore' )
    line2 = line2.encode( 'utf-8', 'ignore' )
    line3 = line3.encode( 'utf-8', 'ignore' )

    # Dialog logic
    if not line0 == '':
        line0 = __addonname__ + line0
    else:
        line0 = __addonname__
    if not background:
        if action == 'create':
            dialog.create(__addonname__, line1, line2, line3)
        if action == 'update':
            dialog.update(percentage, line1, line2, line3)
        if action == 'close':
            dialog.close()
        if action == 'iscanceled':
            if dialog.iscanceled():
                return True
            else:
                return False
        if action == 'okdialog':
            xbmcgui.Dialog().ok(line0, line1, line2, line3)
        if action == 'yesno':
            return xbmcgui.Dialog().yesno(line0, line1, line2, line3, nolabel, yeslabel)
    if background:
        if (action == 'create' or action == 'okdialog'):
            if line2 == '':
                msg = line1
            else:
                msg = line1 + ': ' + line2
            if cancelled == False:
                xbmc.executebuiltin("XBMC.Notification(%s, %s, 7500, %s)" % (line0, msg, __icon__))

# Retrieve JSON data from cache function
def get_data(url, data_type ='json'):
    log('API: %s'% url)
    if CACHE_ON:
        result = cache.cacheFunction(get_data_new, url, data_type)
    else:
        result = get_data_new(url, data_type)    
    if not result:
        result = 'Empty'
    return result

# Retrieve JSON data from site
def get_data_new(url, data_type):
    log('Cache expired. Retrieving new data')
    data = []
    try:
        request = urllib2.Request(url)
        # TMDB needs a header to be able to read the data
        if url.startswith("http://api.themoviedb.org"):
            request.add_header("Accept", "application/json")
        req = urllib2.urlopen(request)
        if data_type == 'json':
            data = json.loads(req.read())
            if not data:
                data = 'Empty'
        else:
            data = req.read()
        req.close()
    except HTTPError, e:
        if e.code == 400:
            raise HTTP400Error(url)
        elif e.code == 404:
            raise HTTP404Error(url)
        elif e.code == 503:
            raise HTTP503Error(url)
        else:
            raise DownloadError(str(e))
    except URLError:
        raise HTTPTimeout(url)
    except socket.timeout, e:
        raise HTTPTimeout(url)
    except:
        data = 'Empty'
    return data

# Clean filenames for illegal character in the safest way for windows
def clean_filename(filename):
    illegal_char = '<>:"/\|?*'
    for char in illegal_char:
        filename = filename.replace( char , '' )
    return filename

def save_nfo_file(data, target):
    try:
        # open source path for writing and write xmlSource
        file_object = open(target.encode("utf-8"), "w")
        file_object.write(data.encode( "utf-8" ))
        file_object.close()
        return True
    except Exception, e:
        log(str(e), xbmc.LOGERROR)
        return False