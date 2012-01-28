#import modules
import socket
import xbmc
import xbmcgui
import xbmcaddon
import unicodedata
import simplejson
import urllib2
import sys

### get addon info
__addon__       = ( sys.modules[ "__main__" ].__addon__ )
__addonid__     = ( sys.modules[ "__main__" ].__addonid__ )
__addonname__   = ( sys.modules[ "__main__" ].__addonname__ )
__icon__        = ( sys.modules[ "__main__" ].__icon__ )
__localize__    = ( sys.modules[ "__main__" ].__localize__ )
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )

### import libraries
from urllib2 import HTTPError, URLError, urlopen
from resources.lib.script_exceptions import *
#HTTP404Error, HTTP503Error, DownloadError, HTTPTimeout

### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)
### Declare dialog
dialog = xbmcgui.DialogProgress()


# Fixes unicode problems
def _unicode( text, encoding='utf-8' ):
    try:
        text = unicode( text, encoding )
    except:
        pass
    return text

def _normalize_string( text ):
    try:
        text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except:
        pass
    return text

# Define log messages
def _log(txt, severity=xbmc.LOGDEBUG):
    try:
        message = ('%s: %s' % (__addonname__,txt) )
        xbmc.log(msg=message, level=severity)
    except UnicodeEncodeError:
        try:
            message = _normalize_string('%s: %s' % (__addonname__,txt) )
            xbmc.log(msg=message, level=severity)
        except:
            message = ('%s: UnicodeEncodeError' %__addonname__)
            xbmc.log(msg=message, level=xbmc.LOGWARNING)

# Define dialogs
def _dialog(action, percentage = 0, line0 = '', line1 = '', line2 = '', line3 = '', background = False, nolabel = __localize__(32026), yeslabel = __localize__(32025) ):
    # Fix possible unicode errors 
    line0 = _normalize_string(line0)
    line1 = _normalize_string(line1)
    line2 = _normalize_string(line2)
    line3 = _normalize_string(line3)

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

# order preserving and get unique entry
def _getUniq(seq):
    seen = []
    result = []
    for item in seq:
        if item in seen: continue
        seen.append( item )
        result.append( item )
    return result

# Retrieve JSON data from site
def _get_json(url):
    _log('API: %s'% url)
    try:
        request = urllib2.Request(url)
        request.add_header("Accept", "application/json")
        req = urllib2.urlopen(request) 
        json_string = req.read()
        req.close()
    except HTTPError, e:
        if e.code == 404:
            raise HTTP404Error(url)
        elif e.code == 503:
            raise HTTP503Error(url)
        else:
            raise DownloadError(str(e))
    except:
        json_string = ''
    try:
        parsed_json = simplejson.loads(json_string)
    except:
        parsed_json = ''
    return parsed_json

# Retrieve XML data from site
def _get_xml(url):
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
def _clean_filename( filename ):
    illegal_char = '<>:"/\|?*'
    for char in illegal_char:
        filename = filename.replace( char , '' )
    return filename
    
def _save_nfo_file( data, target ):
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