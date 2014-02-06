# -*- coding: utf-8 -*-

# a collection of useful utilities

import re, os, sys, traceback, htmlentitydefs, socket
import xbmc, xbmcvfs

__scriptname__         = sys.modules[ "__main__" ].__addonname__
__scriptID__           = sys.modules[ "__main__" ].__scriptID__

def list_to_string( item ):
    list_to_string = ""
    if not ( type( item ) is list ):
        list_to_string = item
    else:
        if len( item ) > 1:
            list_to_string = " / ".join( item )
        else:
            list_to_string = "".join( item )
    return list_to_string

def smart_unicode(s):
    """credit : sfaxman"""
    if not s:
        return ''
    try:
        if not isinstance(s, basestring):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                s = unicode(str(s), 'UTF-8')
        elif not isinstance(s, unicode):
            s = unicode(s, 'UTF-8')
    except:
        if not isinstance(s, basestring):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                s = unicode(str(s), 'ISO-8859-1')
        elif not isinstance(s, unicode):
            s = unicode(s, 'ISO-8859-1')
    return s

def smart_utf8(s):
    return smart_unicode(s).encode('utf-8')
    
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def settings_to_log( settings_path, script_heading="[utils.py]" ):
    try:
        log( "Settings" )
        base_path = os.path.join( settings_path, "settings.xml" )
        settings_file = xbmcvfs.File( base_path ).read()
        settings_list = settings_file.replace("<settings>\n","").replace("</settings>\n","").split("/>\n")
        for setting in settings_list:
            match = re.search('    <setting id="(.*?)" value="(.*?)"', setting)
            if not match:
                match = re.search("""    <setting id="(.*?)" value='(.*?)'""", setting)
            if match:
                log( "%30s: %s" % ( match.group(1), str( unescape( match.group(2).decode('utf-8', 'ignore') ) ) ) )
    except:
        traceback.print_exc()

def log( text, severity=xbmc.LOGDEBUG ):
    if type( text).__name__=='unicode':
        text = text.encode('utf-8')
    message = ('[%s] - %s' % ( __scriptname__ ,text.__str__() ) )
    xbmc.log( msg=message, level=severity )

def load_saved_list( f_name, type ):
    saved_list = []
    if xbmcvfs.exists( f_name ):
        log( "Loading Saved List, %s" % type, xbmc.LOGNOTICE )
        try:
            f_object = xbmcvfs.File( f_name )
            saved_list = eval( f_object.read() )
            f_object.close()
            assert isinstance( saved_list, ( list, tuple ) ) and not isinstance( saved_list, basestring )
        except:
            log( "Error Loading Saved List, %s" % type, xbmc.LOGNOTICE )
            traceback.print_exc()
            saved_list = []
    else:
        log( "List does not exist, %s" % type, xbmc.LOGNOTICE )
    return saved_list

def save_list( f_name, f_list, type ):
    log( "Saving List, %s" % type, xbmc.LOGNOTICE )
    try:
        if not xbmcvfs.exists( os.path.dirname( f_name ) ):
            xbmcvfs.mkdirs( os.path.dirname( f_name ) )
        # open source path for writing
        file_object = xbmcvfs.File( f_name, "w" )
        # write xmlSource
        file_object.write( repr( f_list ) )
        # close file object
        file_object.close()
    except:
        log( "Error Loading Saved List, %s" % type, xbmc.LOGNOTICE )
        traceback.print_exc()
        
def broadcastUDP( data, port = 8278, ipaddress = '255.255.255.255' ): # XBMC's former HTTP API output port is 8278
    IPADDR = ipaddress
    PORTNUM = port
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    if hasattr(socket,'SO_BROADCAST'):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect((IPADDR, PORTNUM))
    s.send(data)
    s.close()