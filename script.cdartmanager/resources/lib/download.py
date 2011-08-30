# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import urllib, sys, re, os
from traceback import print_exc
from PIL import Image
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
__useragent__     = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"
resizeondownload  = __addon__.getSetting("resizeondownload")
music_path        = __addon__.getSetting("music_path")

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from fanarttv_scraper import get_distant_artists, get_recognized, remote_cdart_list, remote_coverart_list, remote_fanart_list, remote_clearlogo_list
from database import get_local_artists_db, get_local_albums_db, artwork_search
from utils import clear_image_cache, _makedirs
from file_item import Thumbnails

from pre_eden_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy

pDialog = xbmcgui.DialogProgress()
 
def check_size( path, type, size ):
    # first copy from source to work directory since Python does not support SMB://
    file_name = get_filename( type, path, "auto" )
    destination = os.path.join( addon_work_folder, "temp", file_name )
    source = os.path.join( path, file_name )
    xbmc.log( "[script.cdartmanager] - Checking Size", xbmc.LOGDEBUG )
    if exists( source ):
        file_copy( source, destination )
    else:
        return True
    try:
        artwork = Image.open( destination )
        if artwork.size[0] < 1000 and artwork.size[1] < 1000 and size == 1000:  # if image is smaller than 1000 x 1000 and the image on fanart.tv = 1000
            delete_file( destination )
            return True
        else:
            delete_file( destination )
            return False
    except:
        xbmc.log( "[script.cdartmanager] - artwork does not exist. Source: %s" % source, xbmc.LOGDEBUG )
        return True

def get_filename( type, url, mode ):
    if type == "cdart":
        file_name = "cdart.png"
    elif type == "cover":
        file_name = "folder.jpg"
    elif type == "fanart":
        if mode == "auto":
            file_name = os.path.basename( url )
        else:
            file_name = "fanart.jpg"
    elif type == "clearlogo":
        file_name = "logo.png"
    else:
        file_name = "unknown"
    return file_name

def make_music_path( artist ):
    path = os.path.join( music_path, artist ).replace("\\\\","\\")
    if not exists( path ):
        if _makedirs( path ):
            xbmc.log( "[script.cdartmanager] - Path to music artist made", xbmc.LOGDEBUG )
            return True
        else:
            xbmc.log( "[script.cdartmanager] - unable to make path to music artist", xbmc.LOGDEBUG )
            return False

def download_cdart( url_cdart, album, type, mode, size ):
    xbmc.log( "[script.cdartmanager] - Downloading artwork... ", xbmc.LOGDEBUG )
    download_success = False 
    file_name = get_filename( type, url_cdart, mode )
    if file_name == "unknown":
        xbmc.log( "[script.cdartmanager] - Unknown Type ", xbmc.LOGDEBUG )
        message = [ _(32026), _(32025), "File: %s" % path , "Url: %s" % url_cdart]
        return message, download_success
    path = album["path"].replace("\\\\" , "\\")
    if not exists( path ):
        try:
            pathsuccess = _makedirs( album["path"].replace("\\\\" , "\\") )
        except:
            pass
    xbmc.log( "[script.cdartmanager] - Path: %s" % repr( path ), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Filename: %s" % repr( file_name ), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - url: %s" % repr( url_cdart ), xbmc.LOGDEBUG )
    destination = os.path.join( addon_work_folder , file_name).replace("\\\\","\\") # download to work folder first
    final_destination = os.path.join( path, file_name ).replace("\\\\","\\")
    try:
        pDialog.create( _(32047) )
        #Onscreen Dialog - "Downloading...."
        #this give the ability to use the progress bar by retrieving the downloading information
        #and calculating the percentage
        def _report_hook( count, blocksize, totalsize ):
            percent = int( float( count * blocksize * 100 ) / totalsize )
            strProgressBar = str( percent )
            if type == "fanart" or type == "clearlogo":
                pDialog.update( percent, "%s%s" % ( _(32038) , repr( album["artist"] ) ) )
            else:
                pDialog.update( percent, "%s%s" % ( _(32038) , repr( album["artist"] ) ), "%s%s" % ( _(32039) , repr( album["title"] ) )  )
            #Onscreen Dialog - *DOWNLOADING CDART*
            if ( pDialog.iscanceled() ):
                pass  
        if exists( path ):
            fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
            #message = ["Download Sucessful!"]
            message = [_(32023), _(32024), "File: %s" % path , "Url: %s" % url_cdart]
            success = file_copy( destination, final_destination ) # copy it to album folder
            # update database
            if type == "cdart":
                conn = sqlite3.connect(addon_db)
                c = conn.cursor()
                c.execute('''UPDATE alblist SET cdart="True" WHERE path="%s"''' % ( album["path"] ) )
                conn.commit()
                c.close()
            elif type == "cover":
                conn = sqlite3.connect(addon_db)
                c = conn.cursor()
                c.execute('''UPDATE alblist SET cover="True" WHERE path="%s"''' % ( album["path"] ) )
                conn.commit()
                c.close()
            download_success = True
        else:
            xbmc.log( "[script.cdartmanager] - Path error", xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] -     file path: %s" % repr( destination ), xbmc.LOGDEBUG )
            message = [ _(32026),  _(32025) , "File: %s" % path , "Url: %s" % url_cdart]
            #message = Download Problem, Check file paths - Artwork Not Downloaded]           
        if type == "fanart":
            delete_file( destination )
    except:
        xbmc.log( "[script.cdartmanager] - General download error", xbmc.LOGDEBUG )
        message = [ _(32026), _(32025), "File: %s" % path , "Url: %s" % url_cdart]
        #message = [Download Problem, Check file paths - Artwork Not Downloaded]           
        print_exc()
    if mode == "auto":
        return message, download_success, final_destination  # returns one of the messages built based on success or lack of
    else:
        return message, download_success

def cdart_search( cdart_url, id, disc ):
    cdart = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id and item["disc"] == disc:
            cdart = item
            break
    return cdart
    
#Automatic download of non existing cdarts and refreshes addon's db
def auto_download( type ):
    xbmc.log( "[script.cdartmanager] - Autodownload", xbmc.LOGDEBUG )
    try:
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        d_error=False
        percent = 0
        successfully_downloaded = []
        local_artist = get_local_artists_db()
        distant_artist = get_distant_artists()
        recognized_artists, artists_list = get_recognized( distant_artist, local_artist )
        count_artist_local = len(recognized_artists)
        percent = 0
        pDialog.create( _(32046) )
        #Onscreen Dialog - Automatic Downloading of cdART
        for artist in recognized_artists:
            if ( pDialog.iscanceled() ):
                break
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            xbmc.log( "[script.cdartmanager] - Artist: %-40s Local ID: %-10s   Distant ID: %s" % (repr(artist["name"]), artist["local_id"], artist["distant_id"]), xbmc.LOGNOTICE )
            if type == "fanart" or type == "clearlogo":
                pDialog.update( percent , "%s%s" % (_(32038) , repr(artist["name"]) ) )
                auto_art = {}
                auto_art["musicbrainz_artistid"] = artist["distant_id"]
                if not auto_art["musicbrainz_artistid"]:
                    continue
                auto_art["artist"] = artist["name"]
                path = os.path.join( music_path, artist["name"] )
                if type == "fanart":
                    art = remote_fanart_list( auto_art )
                else:
                    art = remote_clearlogo_list( auto_art )
                if art:
                    if type == "fanart":
                        auto_art["path"] = os.path.join( path, "extrafanart" ).replace("\\\\" , "\\")
                        if not exists( auto_art["path"] ):
                            try:
                                if _makedirs( auto_art["path"] ):
                                    xbmc.log( "[script.cdartmanager] - extrafanart directory made", xbmc.LOGDEBUG )
                            except:
                                print_exc()
                                xbmc.log( "[script.cdartmanager] - unable to make extrafanart directory", xbmc.LOGDEBUG )
                                continue
                        else:
                            xbmc.log( "[script.cdartmanager] - extrafanart directory already exists", xbmc.LOGDEBUG )
                    else:
                        auto_art["path"] = path
                    if type == "fanart":
                        for artwork in art:
                            fanart = {}
                            if exists( os.path.join( auto_art["path"], os.path.basename( artwork ) ) ):
                                xbmc.log( "[script.cdartmanager] - Fanart already exists, skipping", xbmc.LOGDEBUG )
                                continue
                            else:
                                message, d_success, final_destination = download_cdart( artwork , auto_art, "fanart", "auto", 0 )
                            if d_success == 1:
                                download_count += 1
                                fanart["artist"] = auto_art["artist"]
                                fanart["fanart"] = final_destination
                                successfully_downloaded.append( fanart )
                            else:
                                xbmc.log( "[script.cdartmanager] - Download Error...  Check Path.", xbmc.LOGDEBUG )
                                xbmc.log( "[script.cdartmanager] -     Path: %s" % repr( auto_art["path"]), xbmc.LOGDEBUG )
                                d_error = True
                    else:
                        artwork = art[0]
                        if exists( os.path.join( auto_art["path"], "logo.png" ) ):
                            xbmc.log( "[script.cdartmanager] - ClearLOGO already exists, skipping", xbmc.LOGDEBUG )
                            continue
                        else:
                            message, d_success, final_destination = download_cdart( artwork , auto_art, "clearlogo", "auto", 0 )
                        if d_success == 1:
                            download_count += 1
                            auto_art["path"] = final_destination
                            successfully_downloaded.append( auto_art )
                        else:
                            xbmc.log( "[script.cdartmanager] - Download Error...  Check Path.", xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] -     Path: %s" % repr( auto_art["path"]), xbmc.LOGDEBUG )
                            d_error = True
                else :
                        xbmc.log( "[script.cdartmanager] - Artist Match not found", xbmc.LOGDEBUG )
            else:
                local_album_list = get_local_albums_db( artist["name"], False )
                remote_cdart_url = remote_cdart_list( artist )
                remote_coverart_url = remote_coverart_list( artist )
                for album in local_album_list:
                    low_res = True
                    if ( pDialog.iscanceled() ):
                        break
                    if not remote_cdart_url:
                        xbmc.log( "[script.cdartmanager] - No artwork found", xbmc.LOGDEBUG )
                        break
                    album_count += 1
                    pDialog.update( percent , "%s%s" % (_(32038) , repr(artist["name"]) )  , "%s%s" % (_(32039) , repr(album["title"] )) )
                    name = artist["name"]
                    title = album["title"]
                    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album["title"]), xbmc.LOGDEBUG )
                    if type == "cdart":
                        if not album["cdart"] or resizeondownload == "true":
                            musicbrainz_albumid = album["musicbrainz_albumid"]
                            if not musicbrainz_albumid:
                                continue
                            cdart = artwork_search( remote_cdart_url, musicbrainz_albumid, album["disc"], "cdart" )
                            if cdart:
                                if resizeondownload == "true":
                                    low_res = check_size( album["path"].replace( "\\\\", "\\" ), "cdart", cdart["size"] )
                                if cdart["picture"]: 
                                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH FOUND", xbmc.LOGDEBUG )
                                    #xbmc.log( "[script.cdartmanager] - test_album[0]: %s" % test_album[0], xbmc.LOGDEBUG )
                                    if low_res:
                                        message, d_success, final_destination = download_cdart( cdart["picture"] , album, "cdart", "auto", 0 )
                                        if d_success == 1:
                                            download_count += 1
                                            album["cdart"] = True
                                            album["path"] = final_destination
                                            successfully_downloaded.append( album )
                                        else:
                                            xbmc.log( "[script.cdartmanager] - Download Error...  Check Path.", xbmc.LOGDEBUG )
                                            xbmc.log( "[script.cdartmanager] -     Path: %s" % repr(album["path"]), xbmc.LOGDEBUG )
                                            d_error = True
                                    else:
                                        pass
                                else:
                                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH NOT FOUND", xbmc.LOGDEBUG )
                            else :
                                xbmc.log( "[script.cdartmanager] - ALBUM MATCH NOT FOUND", xbmc.LOGDEBUG )
                        else:
                            cdart_existing += 1
                            xbmc.log( "[script.cdartmanager] - cdART file already exists, skipped..."    , xbmc.LOGDEBUG )
                    elif type == "cover":
                        if not album["cover"]:
                            musicbrainz_albumid = album["musicbrainz_albumid"]
                            if not musicbrainz_albumid:
                                continue
                            art = artwork_search( remote_coverart_url, musicbrainz_albumid, album["disc"], "cover" )
                            if art:
                                if resizeondownload == "true":
                                    low_res = check_size( album["path"].replace( "\\\\", "\\" ), "cover", 1000 )
                                if art["cover"]: 
                                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH FOUND", xbmc.LOGDEBUG )
                                    if low_res:
                                        message, d_success, final_destination = download_cdart( art["cover"] , album, "cover", "auto", 0 )
                                        if d_success == 1:
                                            download_count += 1
                                            album["cover"] = True
                                            album["path"] = final_destination
                                            successfully_downloaded.append( album )
                                        else:
                                            xbmc.log( "[script.cdartmanager] - Download Error...  Check Path.", xbmc.LOGDEBUG )
                                            xbmc.log( "[script.cdartmanager] -     Path: %s" % repr(album["path"]), xbmc.LOGDEBUG )
                                            d_error = True
                                    else:
                                        pass
                                else :
                                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH NOT FOUND", xbmc.LOGDEBUG )
                            else :
                                xbmc.log( "[script.cdartmanager] - ALBUM MATCH NOT FOUND", xbmc.LOGDEBUG )
                        else:
                            cdart_existing += 1
                            xbmc.log( "[script.cdartmanager] - cover file already exists, skipped..."    , xbmc.LOGDEBUG )
        pDialog.close()
        if d_error:
            xbmcgui.Dialog().ok( _(32026), "%s: %s" % ( _(32041), download_count ) )
        else:
            xbmcgui.Dialog().ok( _(32040), "%s: %s" % ( _(32041), download_count ) )
        
        return download_count, successfully_downloaded
    except:
        print_exc()
        pDialog.close()