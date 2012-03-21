#import modules
import socket
import xbmc
import xbmcgui
import xbmcaddon
import unicodedata
import urllib2
import sys

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import json as simplejson
else:
    import simplejson

### get addon info
__addon__       = ( sys.modules[ "__main__" ].__addon__ )
__addonname__   = ( sys.modules[ "__main__" ].__addonname__ )
__icon__        = ( sys.modules[ "__main__" ].__icon__ )
__localize__    = ( sys.modules[ "__main__" ].__localize__ )
__addonprofile__= ( sys.modules[ "__main__" ].__addonprofile__ )

### import libraries
from urllib2 import HTTPError, URLError, urlopen
from resources.lib.script_exceptions import *

# Commoncache plugin import
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

cache = StorageServer.StorageServer("ArtworkDownloader",96)

### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)
### Declare dialog
dialog = xbmcgui.DialogProgress()


# Fixes unicode problems
def string_unicode( text, encoding='utf-8' ):
    try:
        text = unicode( text, encoding )
    except:
        pass
    return text

def normalize_string( text ):
    try:
        text = unicodedata.normalize( 'NFKD', string_unicode( text ) ).encode( 'ascii', 'ignore' )
    except:
        pass
    return text

# Define log messages
def log(txt, severity=xbmc.LOGDEBUG):
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
def dialog_msg(action, percentage = 0, line0 = '', line1 = '', line2 = '', line3 = '', background = False, nolabel = __localize__(32026), yeslabel = __localize__(32025) ):
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
            dialog.create( __addonname__, line1, line2, line3 )
        if action == 'update':
            dialog.update( percentage, line1, line2, line3 )
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
            xbmc.executebuiltin("XBMC.Notification(%s, %s, 7500, %s)" % (line0, msg, __icon__))

# Retrieve JSON data from cache function
def get_json(url):
    log('API: %s'% url)
    try:
        result = cache.cacheFunction( get_json_new, url )
    except:
        result = 'Empty'
    if len(result) == 0:
        result = 'Empty'
        return result
    else:
        return result

# Retrieve JSON data from site
def get_json_new(url):
    log('Cache expired. Retrieving new data')
    parsed_json = []
    try:
        request = urllib2.Request(url)
        # TMDB needs a header to be able to read the data
        if url.startswith("http://api.themoviedb.org"):
            request.add_header("Accept", "application/json")
        # Add some delay to stop trashing the fanart.tv server for now
        elif url.startswith("http://fanart.tv/"):
            xbmc.sleep(2000)
        req = urllib2.urlopen(request)
        json_string = req.read()
        req.close()
        try:
            parsed_json = simplejson.loads(json_string)
        except:
            parsed_json = 'Empty'
    except HTTPError, e:
        # Add an empty cache to stop trashing the fanart.tv server for now
        if url.startswith("http://fanart.tv/"):
            parsed_json = 'Empty'
        elif e.code == 404:
            raise HTTP404Error(url)
        elif e.code == 503:
            raise HTTP503Error(url)
        else:
            raise DownloadError(str(e))
    except:
        parsed_json = 'Empty'
    return parsed_json

# Retrieve XML data from cache function
def get_xml(url):
    log('API: %s'% url)
    result = cache.cacheFunction( get_xml_new, url )
    if len(result) == 0:
        result = []
        return result
    else:
        return result

# Retrieve XML data from site
def get_xml_new(url):
    log('Cache expired. Retrieving new data')
    try:
        client  = urlopen(url)
        data    = client.read()
        client.close()
        return data
    except HTTPError, e:
        if e.code   == 404:
            raise HTTP404Error( url )
        elif e.code == 503:
            raise HTTP503Error( url )
        elif e.code == 400:
            raise HTTP400Error( url )
        else:
            raise DownloadError( str(e) )
    except URLError:
        raise HTTPTimeout( url )
    except socket.timeout, e:
        raise HTTPTimeout( url )

# Clean filenames for illegal character in the safest way for windows
def clean_filename( filename ):
    illegal_char = '<>:"/\|?*'
    for char in illegal_char:
        filename = filename.replace( char , '' )
    return filename
    
def save_nfo_file( data, target ):
    try:
        # open source path for writing
        file_object = open( target.encode( "utf-8" ), "w" )
        # write xmlSource
        file_object.write( data.encode( "utf-8" ) )
        # close file object
        file_object.close()
        # return successful
        return True
    except Exception, e:
        # oops, notify user what error occurred
        log( str( e ), xbmc.LOGERROR )
        # return failed
        return False