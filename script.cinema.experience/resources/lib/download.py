# -*- coding: utf-8 -*-
import urllib, urllib2, os, traceback, sys, socket
__useragent__ = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
try:
    import xbmcgui
except:
    pass

socket.setdefaulttimeout(30)

class _urlopener( urllib.URLopener ):
    version =  __useragent__

urllib._urlopener = _urlopener()

def download( url_path, download_path, file_tag = "", new_name= "", extension="" ):
    ''' retrieves files from url_path to download_path.
        pulls filename from url_path
        requirements:
            url_path - where to download from
            download_path - where to save file
        optional:
            file_tag - add a tag to the filename, ie "-trailer"
            new_name - rename file
            extension - change the extension to something different
    '''
    success = False
    destination = ""
    for i in range(0, 4):
        try:
            try:
                url_path = url_path.split("|")[0]
            except:
                url_path = url_path
            if file_tag:
                filename, ext = os.path.splitext( os.path.basename( url_path.replace( "?","" ) ) )
                filename = filename + file_tag + ext
            else:
                filename = os.path.basename( url_path.replace( "?","" ) )
            if new_name:
                filename = new_name
            if extension:
                filename = os.path.splitext( filename )[ 0 ]
                filename = filename + extension
            else:
                pass
            destination = os.path.join( download_path, filename ).replace( "\\\\", "\\" )
            urllib.urlretrieve( url_path, destination, _report_hook )
            success = True
            break
        except:
            traceback.print_exc()
    return success, destination

def _report_hook( count, blocksize, totalsize ):
    percent = int( float( count * blocksize * 100) / totalsize )
    try:
        xbmcgui.DialogProgress().update( percent )
    except:
        # DialogProgress must not be open
        pass
