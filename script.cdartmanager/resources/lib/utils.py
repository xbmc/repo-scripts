# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import urllib, sys, re, os
import htmlentitydefs
from traceback import print_exc
try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
_                 = sys.modules[ "__main__" ].__language__
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
__useragent__  = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from file_item import Thumbnails
from smbclient import smbclient

from dharma_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from os import remove as delete_file
exists = os.path.exists
from shutil import copy as file_copy

pDialog = xbmcgui.DialogProgress()

def get_unicode( to_decode ):
    try:
        temp_string = to_decode.encode('utf-8')
        return to_decode
    except UnicodeDecodeError:
        return to_decode.decode('utf-8')

def smb_makedirs( path ):
    xbmc.log( "[script.cdartmanager] - Building Samba Directory on Non Windows System", xbmc.LOGDEBUG )
    if exists( path ):
        return
    # setup for samba communication
    samba_list = path.split( "/" )
    #print samba_list
    remote_share = samba_list[ 3 ]
    if "@" in samba_list[ 2 ]:
        remote_name = samba_list[ 2 ].split( "@" )[1]
        samba_user = ( samba_list[ 2 ].split( "@" )[0] ).split( ":" )[0]
        samba_pass = ( samba_list[ 2 ].split( "@" )[0] ).split( ":" )[1]
    else:
        remote_name = samba_list[ 2 ]
        try:
            if protectedshare == "true":
                samba_user = __addon__.getSetting( "samba_user" )
                samba_pass = __addon__.getSetting( "samba_pass" )
            else:
                # default to guest if no user/pass is given
                samba_user = None
                samba_pass = None
        except:
            samba_user = None
            samba_pass = None
    xbmc.log( "[script.cdartmanager] - Samba - Remote Name: %s" % remote_name, xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Samba - Remote Share: %s" % remote_share, xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Samba - Username: %s" % samba_user, xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Samba - Password: %s" % samba_pass, xbmc.LOGDEBUG )
    smb = smbclient.SambaClient( server=remote_name, share=remote_share,
                                username=samba_user, password=samba_pass )
    path2 = "smb://" + remote_name + "/" + "/".join( samba_list[3:] )
    tmppath = "/".join( samba_list[4:] )
    while( not ( exists( path2 ) or path2 == "smb:" ) ):
        #print path2
        try:
            xbmc.log( "[script.cdartmanager] - Attempting making direcory: %s" % tmppath, xbmc.LOGDEBUG )
            smb.mkdir( get_unicode( tmppath) )
        except:
            tmppath = os.path.dirname( tmppath )
            # need to strip the same part from a true path for the exists option
            path2 = os.path.dirname( path2 )
    smb_makedirs(path)

def _makedirs( _path ):
    #print os.environ.get('OS')
    xbmc.log( "[script.cdartmanager] - Building Directory", xbmc.LOGDEBUG )
    if _path.startswith( "smb://" ) and not os.environ.get( "OS", "win32" ) in ("win32", "Windows_NT"):
        smb_makedirs( _path )
        return True
    if ( _path.startswith( "smb://" ) and os.environ.get( "OS", "win32" ) in ("win32", "Windows_NT") ):
        xbmc.log( "[script.cdartmanager] - Building Samba Share Directory on Windows System", xbmc.LOGDEBUG )
        if "@" in _path:
            t_path = "\\\\" + _path.split("@")[1]
            _path = t_path
        _path = _path.replace( "/", "\\" ).replace( "smb:", "" )
    # no need to create folders
    if ( os.path.isdir( _path ) ): return True
    # temp path
    tmppath = _path
    # loop thru and create each folder
    while ( not os.path.isdir( tmppath ) ):
        try:
            os.mkdir( tmppath )
        except:
            tmppath = os.path.dirname( tmppath )
    # call function until path exists
    _makedirs( _path )
    
def clear_image_cache( url ):
    if exists( Thumbnails().get_cached_picture_thumb( url ) ):
        delete_file( Thumbnails().get_cached_picture_thumb( url ) )
        
def empty_tempxml_folder():
    if exists( tempxml_folder ):
        for file_name in os.listdir( tempxml_folder ):
            delete_file( os.path.join( tempxml_folder, file_name ) )
    else:
        pass
        
def get_html_source( url, path ):
    """ fetch the html source """
    xbmc.log( "[script.cdartmanager] - Retrieving HTML Source", xbmc.LOGDEBUG )
    error = False
    htmlsource = ""
    path = path.replace("http://fanart.tv/api/music.php?id=", "")
    path = path + ".xml"
    print path
    if not exists( tempxml_folder ):
        os.mkdir( tempxml_folder )
    file_name = os.path.join( tempxml_folder, path )
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    for i in range(0, 4):
        try:
            if exists( file_name ):
                sock = open( file_name, "r" )
            else:
                urllib.urlcleanup()
                sock = urllib.urlopen( url )
            htmlsource = sock.read()
            if not exists( file_name ):
                file( file_name , "w" ).write( htmlsource )
            sock.close()
            break
        except:
            print_exc()
            xbmc.log( "[script.cdartmanager] - # !!Unable to open page %s" % url, xbmc.LOGDEBUG )
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
    
def upload_missing_list():
    # Nothing here yet.
    # 
    # Here the script will upload the missing list stored in backup folder
    # and wait for a response from the website(a file) that will either initiate 
    # a batch download or a dialog stating that there are not any matches
    xbmc.log( "[script.cdartmanager] - #    Saving Missing cdART list to backup folder", xbmc.LOGNOTICE )
    count = 0
    percent = 0
    line = ""
    zip_filename = ""
    bkup_folder = __addon__.getSetting("backup_path")
    pDialog.create( _(32104), _(20186) )
    if bkup_folder =="":
        __addon__.openSettings()
        bkup_folder = __addon__.getSetting("backup_path")
    filename=os.path.join(addon_work_folder, "missing.txt")
    return zip_filename
        
def download_from_website( zip_filename ):
    # Nothing really here yet
    #
    # Here the script will download the zip file that the website
    # will create which stores the cdARTs matching the missing.txt file
    # The file will be stored in addon_data/script.cdartmanager/temp
    # 
    # 
    zip_file = ""
        
def extract_zip( filename ):
    # Here the script will extract the cdARTs store in the zip file downloaded from
    # the website and delete file after extraction is complete(no wasted space)
    # files will be stored in addon_data/script.cdartmanager/temp/extracted_cdarts
    xbmc.log( "[script.cdartmanager] - #  Decompressing unique cdARTs", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
    source = os.path.join(addon_work_folder, 'filename')
    destination = os.path.join(addon_work_folder, 'temp')
    xbmc.log( "[script.cdartmanager] - #    Source: %s ", source, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Destination: %s ", destination, xbmc.LOGNOTICE )
    output = tarfile.TarFile.open(destination, 'r:gz2')
    try:
        output = tarfile.TarFile.open(destination, 'r:gz2')
        try: 
            file.extractall()
        finally:
            file.close()
    except:
        xbmc.log( "[script.cdartmanager] - # Problem extracting file", xbmc.LOGNOTICE )
            
def download_missing_cdarts():
    # Nothing really here yet
    #
    # Here the script will call each of the steps for downloading the missing cdARTs
    # and extracting.  It will also recheck the local database and update counts for display
    local_album_count = 0
    local_artist_count = 0
    local_cdart_count = 0
    zip_file = ""
    zip_filename = ""
    zip_file=self.upload_missing_list()
    if zip_file == "":
        xbmc.log( "[script.cdartmanager] - # Sorry no matching cdARTs", xbmc.LOGNOTICE )
    else:
        zip_filename = os.path.join(download_temp_folder, zip_file)
        download_from_website(zip_filename)
        extract_zip(zip_filename)
        delete_file(zip_filename)
        extracted_cdarts_folder = os.path.join(download_temp_folder, "extracted_cdarts")
        self.copy_cdarts(extracted_cdarts_folder)
        # refresh local database
        delete_file(addon_db)
        local_album_count, local_artist_count, local_cdart_count = new_database_setup()
        self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            
def upload_to_website():
    # Nothing really here yet
    # 
    # open ftp and send a zip file to the website
    source = os.path.join(addon_work_folder, 'unique.tar.gz')
    cmd = "STOR unique.tar.gz"
    try:
        ftp_upload = FTP('192.168.2.9')
        ftp_upload.login('giftie61', 'gmracing')
        upload = open(source, 'rb')
        ftp_upload.storbinary(cmd, upload)
        upload.close()
        ftp_upload.close()
    except StandardError, e:
        xbmc.log( "[script.cdartmanager] - Error uploading file: %s" % e, xbmc.LOGNOTICE )

def compress_cdarts( unique_folder ):
    xbmc.log( "[script.cdartmanager] - #  Compressing unique cdARTs", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #"        , xbmc.LOGNOTICE )
    source = unique_folder
    destination = os.path.join(addon_work_folder, 'unique.tar.gz')
    xbmc.log( "[script.cdartmanager] - #    Source: %s " % source, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Destination: %s " % destination, xbmc.LOGNOTICE )
    fileList = dirEntries(source, media_type="files", recursive="TRUE", contains="")
    try:
        output = tarfile.TarFile.open(destination, 'w:gz')
        for f in fileList:
            xbmc.log( "[script.cdartmanager] - archiving file %s" % (f), xbmc.LOGNOTICE )
            output.add(f)
        output.close()
        self.upload_to_website()
    except:
        xbmc.log( "[script.cdartmanager] - # Problem Compressing Unique cdARTs", xbmc.LOGNOTICE )
    
def upload_unique_cdarts():
    # Nothing really here yet
    # 
    # Here the script will call each step for uploading unique cdARTs
    zip_file = ""
    unique, difference = self.local_vs_distant()
    if difference == 1:
        self.unique_cdart_copy( unique )
        unique_folder = __addon__.getSetting("unique_path")
        zip_file = self.compress_cdarts( unique_folder )
        self.upload_to_website()
    else:
        xbmcgui.Dialog().ok( "There are no unique local cdARTs")        


 