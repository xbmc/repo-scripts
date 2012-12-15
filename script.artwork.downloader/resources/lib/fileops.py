#import modules
import os
import socket
import urllib2
import urllib
import xbmc
import xbmcvfs

### import libraries
from traceback import print_exc
from urllib2 import HTTPError, URLError
from resources.lib.script_exceptions import *
from resources.lib import utils
from resources.lib.settings import settings
from resources.lib.utils import log
THUMBS_CACHE_PATH = xbmc.translatePath( "special://profile/Thumbnails/Video" )


### adjust default timeout to stop script hanging
timeout = 10
socket.setdefaulttimeout(timeout)

class fileops:
    """
    This class handles all types of file operations needed by
    script.extrafanartdownloader (creating directories, downloading
    files, copying files etc.)
    """

    def __init__(self):
        log("Setting up fileops")
        self.settings = settings()
        self.settings._get_general()
        self._exists = lambda path: xbmcvfs.exists(path)
        self._rmdir = lambda path: xbmcvfs.rmdir(path)
        self._mkdir = lambda path: xbmcvfs.mkdir(path)
        self._delete = lambda path: xbmcvfs.delete(path)

        self.downloadcount = 0
        self.tempdir = os.path.join(utils.__addonprofile__, 'temp')
        if not self._exists(self.tempdir):
            if not self._exists(utils.__addonprofile__):
                if not self._mkdir(utils.__addonprofile__):
                    raise CreateDirectoryError(utils.__addonprofile__)
            if not self._mkdir(self.tempdir):
                raise CreateDirectoryError(self.tempdir)
        
    def _copy(self, source, target):
        return xbmcvfs.copy(source.encode("utf-8"), target.encode("utf-8"))

    ### Delete file from all targetdirs
    def _delete_file_in_dirs(self, filename, targetdirs, reason, media_name = '' ):
        isdeleted = False
        for targetdir in targetdirs:
            path = os.path.join(targetdir, filename)
            if self._exists(path):
                self._delete(path)
                log("[%s] Deleted (%s): %s" % (media_name, reason, path))
                isdeleted = True
        if not isdeleted:
            log("[%s] Ignoring (%s): %s" % (media_name, reason, filename))

    ### erase old cache file and copy new one
    def erase_current_cache(self,filename):
        try: 
            cached_thumb = self.get_cached_thumb(filename)
            log( "Cache file %s" % cached_thumb )
            if xbmcvfs.exists( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") ):
                xbmcvfs.delete( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") )
            copy = xbmcvfs.copy( filename , cached_thumb )
            if copy:
                log("Cache succesful")
            else:
                log("Failed to copy to cached thumb")
        except :
            print_exc()
            log("Cache erasing error")

    # retrieve cache filename
    def get_cached_thumb(self, filename):
        if filename.startswith("stack://"):
            filename = strPath[ 8 : ].split(" , ")[ 0 ]
        if filename.endswith("folder.jpg"):
            cachedthumb = xbmc.getCacheThumbName(filename)
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb ).replace( "/Video" , "")
        else:
            cachedthumb = xbmc.getCacheThumbName(filename)
            if ".jpg" in filename:
                cachedthumb = cachedthumb.replace("tbn" ,"jpg")
            elif ".png" in filename:
                cachedthumb = cachedthumb.replace("tbn" ,"png")      
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb ).replace( "/Video" , "")    
        return thumbpath         

    # copy file from temp to final location
    def _copyfile(self, sourcepath, targetpath, media_name = ''):
        targetdir = os.path.dirname(targetpath).encode("utf-8")
        if not self._exists(targetdir):
            if not self._mkdir(targetdir):
                raise CreateDirectoryError(targetdir)
        if not self._copy(sourcepath, targetpath):
            raise CopyError(targetpath)
        else:
            log("[%s] Copied successfully: %s" % (media_name, targetpath) )

    # download file
    def _downloadfile(self, url, filename, targetdirs, media_name, mode = ""):
        try:
            temppath = os.path.join(self.tempdir, filename)
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
        except Exception, e:
            log(str(e), xbmc.LOGNOTICE)
        else:
            log("[%s] Downloaded: %s" % (media_name, filename))
            self.downloadcount += 1
            for targetdir in targetdirs:
                #targetpath = os.path.join(urllib.url2pathname(targetdir).replace('|',':'), filename)
                targetpath = os.path.join(targetdir, filename)
                self._copyfile(temppath, targetpath, media_name)
                #if self.settings.xbmc_caching_enabled or mode in ['gui','customgui']:
                #    self.erase_current_cache(targetpath)