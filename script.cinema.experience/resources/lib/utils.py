# -*- coding: utf-8 -*-

# a collection of useful utilities

import re, os, sys, traceback
import xbmc

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
        log( "Settings\n", xbmc.LOGDEBUG)
        # set base watched file path
        base_path = os.path.join( settings_path, "settings.xml" )
        # open path
        settings_file = open( base_path, "r" )
        settings_file_read = settings_file.read()
        settings_list = settings_file_read.replace("<settings>\n","").replace("</settings>\n","").split("/>\n")
        # close socket
        settings_file.close()
        for setting in settings_list:
            match = re.search('    <setting id="(.*?)" value="(.*?)"', setting)
            if not match:
                match = re.search("""    <setting id="(.*?)" value='(.*?)'""", setting)
            if match:
                log( "%30s: %s" % ( match.group(1), str( unescape( match.group(2).decode('utf-8', 'ignore') ) ) ), xbmc.LOGDEBUG )
    except:
        traceback.print_exc()

def log( text, severity=xbmc.LOGDEBUG ):
    if type( text).__name__=='unicode':
        text = text.encode('utf-8')
    message = ('[%s] - %s' % ( __scriptname__ ,text.__str__() ) )
    xbmc.log( msg=message, level=severity)
