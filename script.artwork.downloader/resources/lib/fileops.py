import os
import socket
import urllib2
import xbmc
import xbmcvfs
from traceback import print_exc
from resources.lib.script_exceptions import CopyError, DownloadError, CreateDirectoryError, HTTP404Error, HTTPTimeout, ItemNotFoundError
from urllib2 import HTTPError, URLError
from resources.lib import utils
from resources.lib.settings import _settings
from resources.lib.utils import _log as log
THUMBS_CACHE_PATH = xbmc.translatePath( "special://profile/Thumbnails/Video" )


### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)

class fileops:
    """
    This class handles all types of file operations needed by
    script.extrafanartdownloader (creating directories, downloading
    files, copying files etc.)
    """

    def __init__(self):

        """Initialise needed directories/vars for fileops"""

        log("Setting up fileops")
        self.settings = _settings()
        self.settings._get()
        self._exists = lambda path: xbmcvfs.exists(path)
        self._rmdir = lambda path: xbmcvfs.rmdir(path)
        self._mkdir = lambda path: xbmcvfs.mkdir(path)
        self._delete = lambda path: xbmcvfs.delete(path)

        self.downloadcount = 0
        addondir = xbmc.translatePath( utils.__addon__.getAddonInfo('profile') )
        self.tempdir = os.path.join(addondir, 'temp')
        if not self._exists(self.tempdir):
            if not self._exists(addondir):
                if not self._mkdir(addondir):
                    raise CreateDirectoryError(addondir)
            if not self._mkdir(self.tempdir):
                raise CreateDirectoryError(self.tempdir)
        
    def _copy(self, source, target):
        return xbmcvfs.copy(source, target)

    ### Delete file from all targetdirs
    def _delete_file_in_dirs(self, filename, targetdirs, reason):
        isdeleted = False
        for targetdir in targetdirs:
            path = os.path.join(targetdir, filename)
            if self._exists(path):
                self._delete(path)
                log("Deleted (%s): %s" % (reason, path), xbmc.LOGNOTICE)
                isdeleted = True
        if not isdeleted:
            log("Ignoring (%s): %s" % (reason, filename))

    ### erase old cache file and copy new one
    def erase_current_cache(self,filename):
        try: 
            cached_thumb = self.get_cached_thumb(filename)
            log( "Cache file %s" % cached_thumb )
            if xbmcvfs.exists( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") ):
                xbmcvfs.delete( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") )
            copy = xbmcvfs.copy( filename , cached_thumb )
            if copy:
                log( "Cache succesful" )
            else:
                log( "Failed to copy to cached thumb" )
        except :
            print_exc()
            log( "Cache erasing error" )

    # retrieve cache filename
    def get_cached_thumb( self, filename ):
        if filename.startswith( "stack://" ):
            filename = strPath[ 8 : ].split( " , " )[ 0 ]
        if filename.endswith( "folder.jpg" ):
            cachedthumb = xbmc.getCacheThumbName( filename )
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb )
        else:
            cachedthumb = xbmc.getCacheThumbName( filename )
            if ".jpg" in filename:
                cachedthumb = cachedthumb.replace("tbn" , "jpg")
            elif ".png" in filename:
                cachedthumb = cachedthumb.replace("tbn" , "png")      
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb ).replace( "/Video" , "")    
        return thumbpath         

    # copy filen from temp to final location
    def _copyfile(self, sourcepath, targetpath):
        targetdir = os.path.dirname(targetpath)
        if not self._exists(targetdir):
            if not self._mkdir(targetdir):
                raise CreateDirectoryError(targetdir)
        if not self._copy(sourcepath, targetpath):
            raise CopyError(targetpath)
        else:
            log("Copied successfully: %s" % targetpath)

    # download file
    def _downloadfile(self, url, filename, targetdirs, media_name):

        """
        Download url to filename and place in all targetdirs.
        """

        try:
            temppath = os.path.join(self.tempdir, filename)
            url = url.replace(" ", "%20")
            tempfile = open(temppath, "wb")
            response = urllib2.urlopen(url)
            tempfile.write(response.read())
            tempfile.close()
            response.close()
        except HTTPError, e:
            if e.code == 404:
                raise HTTP404Error(url)
            else:
                raise DownloadError(str(e))
        except URLError:
            raise HTTPTimeout(url)
        except socket.timeout, e:
            raise HTTPTimeout(url)
        else:
            log("Downloaded (%s): %s" % (media_name, filename), xbmc.LOGNOTICE)
            self.downloadcount = self.downloadcount + 1
            for targetdir in targetdirs:
                targetpath = os.path.join(targetdir, filename)
                self._copyfile(temppath, targetpath)
                if self.settings.xbmc_caching_enabled:
                    self.erase_current_cache(targetpath)
