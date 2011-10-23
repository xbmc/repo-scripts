import os
import socket
import urllib2
import xbmc
from resources.lib.script_exceptions import CopyError, DownloadError, CreateDirectoryError, HTTP404Error, HTTPTimeout, ItemNotFoundError
from urllib2 import HTTPError, URLError
from resources.lib import utils

xbmc_version = utils.get_xbmc_version()
import shutil
from resources.lib.smbclient import smbclient

log = utils._log

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

        self.downloadcount = 0
        addondir = xbmc.translatePath( utils.__addon__.getAddonInfo('profile') )
        self.tempdir = os.path.join(addondir, 'temp')
        if not self._exists(self.tempdir):
            if not self._exists(addondir):
                if not self._mkdir(addondir):
                    raise CreateDirectoryError(addondir)
            if not self._mkdir(self.tempdir):
                raise CreateDirectoryError(self.tempdir)


    def _exists(self, path):
        return os.path.exists(path)
    def _copy(self, source, target):
        try:
            shutil.copy(source, target)
        except:
            if os.path.exists(target):
                return True
            else:
                return False
        else:
            return True
    def _delete(self, path):
        try:
            os.remove(path)
        except:
            return False
        else:
            return True
    def _rmdir(self, path):
        try:
            os.rmdir(path)
        except:
            return False
        else:
            return True
    def _mkdir( self, path ):
        try:
           os.mkdir(path)
        except:
            if os.path.exists(path):
                return True
            else:
                orig_path = path
                log( "Building Directory", xbmc.LOGDEBUG )
                if path.startswith( "smb://" ) and not os.environ.get( "OS", "win32" ) in ("win32", "Windows_NT"):
                    self._smb_mkdir( path )
                    return True
                if ( path.startswith( "smb://" ) and os.environ.get( "OS", "win32" ) in ("win32", "Windows_NT") ):
                    log( "Building Samba Share Directory on Windows System", xbmc.LOGDEBUG )
                    if "@" in path:
                        path = "\\\\" + path.split("@")[1]
                    path = path.replace( "/", "\\" ).replace( "smb:", "" )
                # no need to create folders
                if ( os.path.isdir( path ) ): return True
                # temp path
                tmppath = path
                # loop thru and create each folder
                while ( not os.path.isdir( tmppath ) ):
                    if tmppath == "\\\\": break
                    try:
                        os.mkdir( tmppath )
                    except:
                        tmppath = os.path.dirname( tmppath )
                # call function until path exists
                if tmppath == "\\\\": return False
                if os.path.exists(orig_path):
                    log('Succesfully created folder on Samba Share Directory')
                    return True
                else:
                    if tmppath == "\\\\":
                        return False
                    else:
                        self._mkdir( orig_path )
        else:
            return True 

    def _smb_mkdir( self, path ):
        log( "Building Samba Directory on Non Windows System", xbmc.LOGDEBUG )
        if self._exists( path ):
            return
        # setup for samba communication
        samba_list = path.split( "/" )
        print samba_list
        remote_share = samba_list[ 3 ]
        if "@" in samba_list[ 2 ]:
            remote_name = samba_list[ 2 ].split( "@" )[1]
            samba_user = ( samba_list[ 2 ].split( "@" )[0] ).split( ":" )[0]
            samba_pass = ( samba_list[ 2 ].split( "@" )[0] ).split( ":" )[1]
        else:
            remote_name = samba_list[ 2 ]
            try:
                if utils.__addon__.getSetting( "protectedshare" ) == "true":
                    samba_user = utils.__addon__.getSetting( "samba_user" )
                    samba_pass = utils.__addon__.getSetting( "samba_pass" )
                else:
                    # default to guest if no user/pass is given
                    samba_user = None
                    samba_pass = None
            except:
                samba_user = None
                samba_pass = None
        log( "Samba - Remote Name: %s" % remote_name, xbmc.LOGDEBUG )
        log( "Samba - Remote Share: %s" % remote_share, xbmc.LOGDEBUG )
        log( "Samba - Username: %s" % samba_user, xbmc.LOGDEBUG )
        log( "Samba - Password: %s" % samba_pass, xbmc.LOGDEBUG )
        smb = smbclient.SambaClient( server=remote_name, share=remote_share,
                                    username=samba_user, password=samba_pass )
        path2 = "smb://" + remote_name + "/" + "/".join( samba_list[3:] )
        tmppath = "/".join( samba_list[4:] )
        while( not ( self._exists( path2 ) or path2 == "smb:" ) ):
            print path2
            try:
                log( "Attempting making direcory: %s" % tmppath, xbmc.LOGDEBUG )
                smb.mkdir( get_unicode( tmppath ) )
            except:
                tmppath = os.path.dirname( tmppath )
                # need to strip the same part from a true path for the exists option
                path2 = os.path.dirname( path2 )
        self._smb_mkdir( path )

    def _delete_file_in_dirs(self, filename, targetdirs, reason):
        """
        Delete file from all targetdirs
        """
        
        isdeleted = False
        for targetdir in targetdirs:
            path = os.path.join(targetdir, filename)
            if self._exists(path):
                self._delete(path)
                log("Deleted (%s): %s" % (reason, path), xbmc.LOGNOTICE)
                isdeleted = True
        if not isdeleted:
            log("Ignoring (%s): %s" % (reason, filename), xbmc.LOGINFO)


    def _copyfile(self, sourcepath, targetpath):

        """
        Copy sourcepath to targetpath and create directory if
        necessary
        """

        targetdir = os.path.dirname(targetpath)
        if not self._exists(targetdir):
            if not self._mkdir(targetdir):
                raise CreateDirectoryError(targetdir)
        if not self._copy(sourcepath, targetpath):
            raise CopyError(targetpath)
        else:
            log("Copied successfully: %s" % targetpath)


    def _downloadfile(self, url, filename, targetdirs):

        """
        Download url to filename and place in all targetdirs.  If file
        already exists in any of the targetdirs it is copied from there
        to the others instead of being downloaded again.
        """

        fileexists = []
        filenotexistspaths = []
        for targetdir in targetdirs:
            path = os.path.join(targetdir, filename)
            if self._exists(path):
                fileexists.append(True)
                existspath = path
            else:
                fileexists.append(False)
                filenotexistspaths.append(path)
        if not True in fileexists:
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
            except URLError, e:
                if isinstance(e.reason, socket.timeout):
                    raise HTTPTimeout(url)
                else:
                    raise DownloadError(str(e))
            else:
                log("Downloaded successfully: %s" % filename, xbmc.LOGNOTICE)
                self.downloadcount = self.downloadcount + 1
                for filenotexistspath in filenotexistspaths:
                    self._copyfile(temppath, filenotexistspath)
        elif not False in fileexists:
            log("Ignoring (Exists in all target directories): %s" % filename, xbmc.LOGINFO)
        else:
            for filenotexistspath in filenotexistspaths:
                self._copyfile(existspath, filenotexistspath)
