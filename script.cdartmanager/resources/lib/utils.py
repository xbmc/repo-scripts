# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import urllib, sys, re, os
import htmlentitydefs
from traceback import print_exc

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
__language__      = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__author__        = sys.modules[ "__main__" ].__author__
__credits__       = sys.modules[ "__main__" ].__credits__
__credits2__      = sys.modules[ "__main__" ].__credits2__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
tempxml_folder    = os.path.join( addon_work_folder, "tempxml" )
__useragent__  = "%s\\%s (giftie61@hotmail.com)" % ( __scriptname__, __version__ )
BASE_RESOURCE_PATH= sys.modules[ "__main__" ].BASE_RESOURCE_PATH

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from file_item import Thumbnails
from jsonrpc_calls import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy
from xbmcvfs import mkdir

pDialog = xbmcgui.DialogProgress()

def get_unicode( to_decode ):
    final = []
    try:
        temp_string = to_decode.encode('utf8')
        return to_decode
    except:
        while True:
            try:
                final.append(to_decode.decode('utf8'))
                break
            except UnicodeDecodeError, exc:
                # everything up to crazy character should be good
                final.append(to_decode[:exc.start].decode('utf8'))
                # crazy character is probably latin1
                final.append(to_decode[exc.start].decode('latin1'))
                # remove already encoded stuff
                to_decode = to_decode[exc.start+1:]
        return "".join(final)
            
def settings_to_log( settings_path, script_heading="[utils.py]" ):
    try:
        xbmc.log( "%s - Settings\n" % script_heading, level=xbmc.LOGDEBUG)
        # set base watched file path
        base_path = os.path.join( settings_path, "settings.xml" )
        # open path
        usock = open( base_path, "r" )
        u_read = usock.read()
        settings_list = u_read.replace("<settings>\n","").replace("</settings>\n","").split("/>\n")
        # close socket
        usock.close()
        for set in settings_list:
            match = re.search('    <setting id="(.*?)" value="(.*?)"', set)
            if match:
                xbmc.log( "%s - %30s: %s" % ( script_heading, match.group(1), match.group(2) ), level=xbmc.LOGDEBUG)
    except:
        traceback.print_exc()
                
def _makedirs( _path ):
    xbmc.log( "[script.cdartmanager] - Building Directory", xbmc.LOGDEBUG )
    success = False
    canceled = False
    if ( exists( _path ) ): return True
    # temp path
    tmppath = _path
    # loop thru and create each folder
    while ( not exists( tmppath ) ):
        try:
            if (pDialog.iscanceled()):
                canceled = True
                break 
        except:
            pass
        success = mkdir( tmppath )
        if not success:
            tmppath = os.path.dirname( tmppath )
    # call function until path exists
    if not canceled:
        _makedirs( _path )
    else:
        return canceled

def clear_image_cache( url ):
    thumb = Thumbnails().get_cached_picture_thumb( url )
    png = os.path.splitext( thumb )[0] + ".png"
    dds = os.path.splitext( thumb )[0] + ".dds"
    jpg = os.path.splitext( thumb )[0] + ".jpg"
    if exists( thumb ):
        delete_file( thumb )
    if exists( png ):
        delete_file( png )
    if exists( jpg ):
        delete_file( jpg )
    if exists( dds ):
        delete_file( dds )

def empty_tempxml_folder():
    if exists( tempxml_folder ):
        for file_name in os.listdir( tempxml_folder ):
            delete_file( os.path.join( tempxml_folder, file_name ) )
    else:
        pass
        
def get_html_source( url, path, save_file = True ):
    """ fetch the html source """
    xbmc.log( "[script.cdartmanager] - Retrieving HTML Source", xbmc.LOGDEBUG )
    error = False
    htmlsource = ""
    file_name = ""
    if save_file:
        path = path.replace("http://fanart.tv/api/music.php?id=", "")
        path = path + ".xml"
        if not exists( tempxml_folder ):
            os.mkdir( tempxml_folder )
        file_name = os.path.join( tempxml_folder, path )
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    for i in range(0, 4):
        try:
            if save_file:
                if exists( file_name ):
                    sock = open( file_name, "r" )
                else:
                    urllib.urlcleanup()
                    sock = urllib.urlopen( url )
            else:
                urllib.urlcleanup()
                sock = urllib.urlopen( url )
            htmlsource = sock.read()
            if save_file:
                if not exists( file_name ):
                    file( file_name , "w" ).write( htmlsource )
            sock.close()
            break
        except:
            print_exc()
            xbmc.log( "[script.cdartmanager] - !!Unable to open page %s" % url, xbmc.LOGDEBUG )
            error = True
    if error:
        return htmlsource
    else:
        xbmc.log( "[script.cdartmanager] - HTML Source:\n%s" % htmlsource, xbmc.LOGDEBUG )
        return htmlsource

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
 