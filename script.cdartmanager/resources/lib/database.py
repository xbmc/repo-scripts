# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import sys, os, re
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
addon_db_backup   = sys.modules[ "__main__" ].addon_db_backup
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
notify = __addon__.getSetting("notifybackground")
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") )

safe_db_version = "1.3.2"
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
pDialog = xbmcgui.DialogProgress()
from musicbrainz_utils import get_musicbrainz_artist_id, get_musicbrainz_album, update_musicbrainzid
from fanarttv_scraper import retrieve_fanarttv_xml, remote_cdart_list
from utils import get_unicode

from dharma_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from os import remove as delete_file
exists = os.path.exists
from shutil import copy as file_copy

def artwork_search( cdart_url, id, disc, type ):
    xbmc.log( "[script.cdartmanager] - Finding Artwork", xbmc.LOGDEBUG )
    art = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id and type == "cover":
            art = item
            break
        elif item["musicbrainz_albumid"] == id and item["disc"] == disc and type == "cdart":
            art = item
            break
    return art

def get_xbmc_database_info( background ):
    xbmc.log( "[script.cdartmanager] - Retrieving Album Info from XBMC's Music DB", xbmc.LOGDEBUG )
    if not background:
        pDialog.create( _(32021), _(32105) )
    album_list, total = retrieve_album_list()
    album_detail_list = retrieve_album_details_full( album_list, total, background )
    if not background:
        pDialog.close()
    return album_detail_list 

def retrieve_album_details_full( album_list, total, background ):
    xbmc.log( "[script.cdartmanager] - Retrieving Album Details", xbmc.LOGDEBUG )
    album_detail_list = []
    album_count = 0
    percent = 0
    try:
        for detail in album_list:
            if notify == "true" and background:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( _(32042), repr(detail['label']), 500, image) )
            if not background:
                if (pDialog.iscanceled()):
                    break
            album_count += 1
            percent = int((album_count/float(total)) * 100)
            if not background:
                pDialog.update( percent, _(20186), "Album: %s" % detail['label'] , "%s #:%6s      %s:%6s" % ( _(32039), album_count, _(32045), total ) )
            album_id = detail['albumid']
            albumdetails = retrieve_album_details( album_id )
            for albums in albumdetails:
                if not background:
                    if (pDialog.iscanceled()):
                        break
                album_artist = {}
                previous_path = ""
                paths = get_album_path( album_id )
                for path in paths:
                    if not background:
                        if (pDialog.iscanceled()):
                            break
                    album_artist = {}
                    if path == previous_path:
                        continue
                    else:
                        if exists(path):
                            xbmc.log( "[script.cdartmanager] - Path Exists", xbmc.LOGDEBUG )
                            album_artist["local_id"] = detail['albumid']
                            title = detail['label']
                            album_artist["artist"] = get_unicode( albums['artist'] )
                            album_artist["path"] = path
                            album_artist["cdart"] = exists( os.path.join( path , "cdart.png").replace("\\\\" , "\\") )
                            album_artist["cover"] = exists( os.path.join( path , "folder.jpg").replace("\\\\" , "\\") )
                            previous_path = path
                            path_match = re.search( "(?:disc|part|cd|pt)([0-9]{0,3})" , path.replace("\\\\","\\"), re.I)
                            if path_match:
                                if not path_match.group(1):
                                    path_match = re.search( "(?:disc|part|cd|pt)(?: |_|-)([0-9]{0,3})" , path.replace("\\\\","\\"), re.I)
                            title_match = re.search( "(.*?)(?:[\s]|[\(]|[\s][\(])(?:disc|part|cd)(?:[\s]|)([0-9]{0,3})(?:[\)]?.*?)" , title, re.I)
                            if title_match:
                                if title_match.group(2):
                                    xbmc.log( "[script.cdartmanager] - Title has CD count", xbmc.LOGDEBUG )
                                    xbmc.log( "[script.cdartmanager] -     Disc %s" % title_match.group( 2 ), xbmc.LOGDEBUG )
                                    album_artist["disc"] = int( title_match.group(2) )
                                    album_artist["title"] = ( title_match.group( 1 ).replace(" -", "") ).rstrip()
                                else:
                                    if path_match:
                                        if path_match.group(1):
                                            xbmc.log( "[script.cdartmanager] - Path has CD count", xbmc.LOGDEBUG )
                                            xbmc.log( "[script.cdartmanager] -     Disc %s" % path_match.group( 1 ), xbmc.LOGDEBUG )
                                            album_artist["disc"] = int( path_match.group(1) )
                                        else:
                                            album_artist["disc"] = 1
                                    else:
                                        album_artist["disc"] = 1
                                    album_artist["title"] = ( title.replace(" -", "") ).rstrip()
                            else:
                                if path_match:
                                    if path_match.group(1):
                                        xbmc.log( "[script.cdartmanager] - Path has CD count", xbmc.LOGDEBUG )
                                        xbmc.log( "[script.cdartmanager] -     Disc %s" % path_match.group( 1 ), xbmc.LOGDEBUG )
                                        album_artist["disc"] = int( path_match.group(1) )
                                    else:
                                        album_artist["disc"] = 1
                                else:
                                    album_artist["disc"] = 1
                                album_artist["title"] = ( title.replace(" -", "") ).rstrip()
                            try:
                                album_artist["title"] = get_unicode( album_artist["title"] )
                                musicbrainz_albuminfo = get_musicbrainz_album( album_artist["title"], album_artist["artist"], 0 )
                            except:
                                print_exc()
                            album_artist["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
                            album_artist["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
                            xbmc.log( "[script.cdartmanager] - Album Title: %s" % repr(album_artist["title"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Artist: %s" % repr(album_artist["artist"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album ID: %s" % album_artist["local_id"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr(album_artist["path"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - cdART Exists?: %s" % album_artist["cdart"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Cover Art Exists?: %s" % album_artist["cover"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Disc #: %s" % album_artist["disc"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - MusicBrainz AlbumId: %s" % album_artist["musicbrainz_albumid"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - MusicBrainz ArtistId: %s" % album_artist["musicbrainz_artistid"], xbmc.LOGDEBUG )
                            album_detail_list.append(album_artist)
                        else:
                            xbmc.log( "[script.cdartmanager] - Path does not exist: %s" % repr( path ), xbmc.LOGDEBUG )
                            break
    except:
        xbmc.log( "[script.cdartmanager] - Error Occured", xbmc.LOGDEBUG )
        print_exc()
        if not background:
            pDialog.close()
    return album_detail_list
    
def get_album_cdart( album_path ):
    xbmc.log( "[script.cdartmanager] - Retrieving cdART status", xbmc.LOGDEBUG )
    if exists( os.path.join( album_path , "cdart.png").replace("\\\\" , "\\") ):
        return True
    else:
        return False
        
def get_album_coverart( album_path ):
    xbmc.log( "[script.cdartmanager] - Retrieving cover art status", xbmc.LOGDEBUG )
    if exists( os.path.join( album_path , "folder.jpg").replace("\\\\" , "\\") ):
        return True
    else:
        return False
    
def store_alblist( local_album_list, background ):
    xbmc.log( "[script.cdartmanager] - Storing alblist", xbmc.LOGDEBUG )
    album_count = 0
    cdart_existing = 0
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    percent = 0 
    try:
        for album in local_album_list:
            if not background:
                pDialog.update( percent, _(20186), "" , "%s:%6s" % ( _(32100), album_count ) )
            if not album["musicbrainz_artistid"]:
                album["artist"] = get_unicode( album["artist"] )
                name, album["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( album["artist"] )
            xbmc.log( "[script.cdartmanager] - Album Count: %s" % album_count, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album ID: %s" % album["local_id"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Title: %s" % repr(album["title"]), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Artist: %s" % repr(album["artist"]), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr(album["path"]).replace("\\\\" , "\\"), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - cdART Exist?: %s" % album["cdart"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Cover Art Exist?: %s" % album["cover"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Disc #: %s" % album["disc"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - MusicBrainz AlbumId: %s" % album["musicbrainz_albumid"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - MusicBrainz ArtistId: %s" % album["musicbrainz_artistid"], xbmc.LOGDEBUG )
            try:
                if album["cdart"]:
                    cdart_existing += 1
                album_count += 1
                c.execute("insert into alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ( album["local_id"], get_unicode( album["title"] ), get_unicode( album["artist"] ), get_unicode( album["path"].replace("\\\\" , "\\") ), ("False","True")[album["cdart"]], ("False","True")[album["cover"]], album["disc"], album["musicbrainz_albumid"], album["musicbrainz_artistid"] ) )
            except:
                xbmc.log( "[script.cdartmanager] - Error Saving to Database", xbmc.LOGDEBUG )
                print_exc()
            if not background:
                if (pDialog.iscanceled()):
                    break
    except:
        xbmc.log( "[script.cdartmanager] - Error Saving to Database", xbmc.LOGDEBUG )
        print_exc()
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Storing ablist", xbmc.LOGDEBUG )
    return album_count, cdart_existing
    
def recount_cdarts():
    xbmc.log( "[script.cdartmanager] - Recounting cdARTS", xbmc.LOGDEBUG )
    cdart_existing = 0
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("""SELECT title, cdart FROM alblist""")
    db=c.fetchall()
    for item in db:
        if eval( item[1] ):
            cdart_existing += 1
    c.close()
    return cdart_existing
        
def store_lalist( local_artist_list, count_artist_local, background ):
    xbmc.log( "[script.cdartmanager] - Storing lalist", xbmc.LOGDEBUG )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    artist_count = 0
    for artist in local_artist_list:
        try:
            c.execute("insert into lalist(local_id, name, musicbrainz_artistid) values (?, ?, ?)", (artist["local_id"], unicode(artist["name"], 'utf-8', ), artist["musicbrainz_artistid"]))
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            if not background:
                if (pDialog.iscanceled()):
                    break
        except:
            print_exe()
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Storing lalist", xbmc.LOGDEBUG )
    return artist_count
        
def retrieve_distinct_album_artists():
    xbmc.log( "[script.cdartmanager] - Retrieving Distinct Album Artist", xbmc.LOGDEBUG )
    album_artists = []
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("""SELECT DISTINCT artist, musicbrainz_artistid FROM alblist""")
    db=c.fetchall()
    for item in db:
        artist = {}
        artist["name"] = ( item[0].encode('utf-8') ).lstrip("'u").rstrip("'")
        artist["musicbrainz_artistid"] = item[1]
        #xbmc.log( repr(artist["name"]), xbmc.LOGDEBUG )
        album_artists.append(artist)
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Retrieving Distinct Album Artists", xbmc.LOGDEBUG )
    return album_artists
        
def store_counts( artist_count, album_count, cdart_existing ):
    xbmc.log( "[script.cdartmanager] - Storing Counts", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     Album Count: %s" % album_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     Artist Count: %s" % artist_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     cdARTs Existing Count: %s" % cdart_existing, xbmc.LOGNOTICE )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("insert into counts(artists, albums, cdarts, version) values (?, ?, ?, ?)", (artist_count, album_count, cdart_existing, safe_db_version))
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Storing Counts", xbmc.LOGDEBUG )
    
def check_local_albumartist( album_artist, local_artist_list, background ):
    artist_count = 0
    percent = 0
    found = False
    local_album_artist_list = []
    for artist in album_artist:        # match album artist to local artist id
        if not background:
            pDialog.update( percent, _(20186), "%s"  % _(32101) , "%s:%s" % ( _(32038), repr(artist["name"]) ) )
            if (pDialog.iscanceled()):
                break
        #xbmc.log( artist, xbmc.LOGDEBUG )
        album_artist_1 = {}
        name = ""
        name = artist["name"]
        artist_count += 1
        for local in local_artist_list:
            if name == local["artist"]:
                id = local["artistid"]
                found = True
                break
        if found:
            album_artist_1["name"] = name                                   # store name and
            album_artist_1["local_id"] = id                                 # local id
            album_artist_1["musicbrainz_artistid"] = artist["musicbrainz_artistid"]
            local_album_artist_list.append(album_artist_1)
        else:
            try:
                print artist["name"]
            except:
                print_exc()
    return local_album_artist_list, artist_count
    
def new_database_setup( background ):
    global local_artist
    artist_count = 0
    download_count = 0
    cdart_existing = 0
    album_count = 0
    percent=0
    local_artist_list = []
    local_album_artist_list = []
    count_artist_local = 0
    album_artist = []
    xbmc.log( "[script.cdartmanager] - Setting Up Database", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] -     addon_work_path: %s" % addon_work_folder, xbmc.LOGDEBUG )
    if not background:
        if not exists( os.path.join( addon_work_folder, "settings.xml") ):
            xbmcgui.Dialog().ok( _(32071), _(32072), _(32073) )
            xbmc.log( "[script.cdartmanager] - Settings not set, aborting database creation", xbmc.LOGDEBUG )
            return album_count, artist_count, cdart_existing
    local_album_list = get_xbmc_database_info( background )
    if not background:
        pDialog.create( _(32021), _(20186) )
    #Onscreen Dialog - Creating Addon Database
    #                      Please Wait....
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute('''create table counts(artists INTEGER, albums INTEGER, cdarts INTEGER, version TEXT)''') 
    c.execute('''create table lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)''')   # create local album artists database
    c.execute('''create table alblist(album_id INTEGER, title TEXT, artist TEXT, path TEXT, cdart TEXT, cover TEXT, disc INTEGER, musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)''')  # create local album database
    c.execute('''create table unqlist(title TEXT, disc INTEGER, artist TEXT, path TEXT, cdart TEXT)''')  # create unique database
    conn.commit()
    c.close()
    album_count, cdart_existing = store_alblist( local_album_list, background ) # store album details first
    album_artist = retrieve_distinct_album_artists()               # then retrieve distinct album artists
    local_artist_list = get_all_local_artists()         # retrieve local artists(to get idArtist)
    local_album_artist_list, artist_count = check_local_albumartist( album_artist, local_artist_list, background )
    count = store_lalist( local_album_artist_list, artist_count, background )         # then store in database
    if not background:
        if (pDialog.iscanceled()):
            pDialog.close()
            ok=xbmcgui.Dialog().ok(_(32050), _(32051), _(32052), _(32053))
    store_counts( artist_count, album_count, cdart_existing )
    xbmc.log( "[script.cdartmanager] - Finished Storing Database", xbmc.LOGDEBUG )
    if not background:
        pDialog.close()
    return album_count, artist_count, cdart_existing
    
#retrieve the addon's database - saves time by no needing to search system for infomation on every addon access
def get_local_albums_db( artist_name, background ):
    xbmc.log( "[script.cdartmanager] - Retrieving Local Albums Database", xbmc.LOGDEBUG )
    local_album_list = []
    query = ""
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        if artist_name == "all artists":
            if not background:
                pDialog.create( _(32102), _(20186) )
            query="SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid FROM alblist ORDER BY artist"
            c.execute(query)
        else:
            query='SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid FROM alblist WHERE artist="%s"' % artist_name
            try:
                c.execute(query)
            except sqlite3.OperationalError:
                query="SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid FROM alblist WHERE artist='%s'" % artist_name
                c.execute(query)
            except:
                print_exc()
        db=c.fetchall()
        c.close
        for item in db:
            album = {}
            album["local_id"] = ( item[0] )
            album["title"] = ( item[1].encode("utf-8") ).lstrip("'u")
            album["artist"] = ( item[2].encode("utf-8") ).lstrip("'u")
            album["path"] = ( (item[3]).encode("utf-8") ).replace('"','').lstrip("'u").rstrip("'")
            album["cdart"] = eval( ( item[4].encode("utf-8") ).lstrip("'u") )
            album["cover"] = eval( ( item[5].encode("utf-8") ).lstrip("'u") )
            album["disc"] = ( item[6] )
            album["musicbrainz_albumid"] = item[7]
            album["musicbrainz_artistid"] = item[8]
            local_album_list.append(album)
    except:
        print_exc()
        c.close
    #xbmc.log( local_album_list, xbmc.LOGDEBUG )
    if artist_name == "all artists":
        if not background:
            pDialog.close()
    xbmc.log( "[script.cdartmanager] - Finished Retrieving Local Albums Database", xbmc.LOGDEBUG )
    return local_album_list
        
def get_local_artists_db():
    xbmc.log( "[script.cdartmanager] - Retrieving Local Artists Database", xbmc.LOGDEBUG )
    local_artist_list = []    
    query = "SELECT DISTINCT local_id, name, musicbrainz_artistid FROM lalist ORDER BY name"
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        c.execute(query)
        db=c.fetchall()
        c.close
        count = 0
        for item in db:
            count += 1
            artists = {}
            artists["local_id"] = ( item[0] )
            artists["name"] = ( item[1].encode("utf-8")).lstrip("'u")
            artists["musicbrainz_artistid"] = item[2]
            #xbmc.log( repr(artists), xbmc.LOGDEBUG )
            local_artist_list.append(artists)
    except:
        print_exc()
    #xbmc.log( local_artist_list, xbmc.LOGDEBUG )
    return local_artist_list
    
#retrieves counts for local album, artist and cdarts
def new_local_count():
    xbmc.log( "[script.cdartmanager] - Counting Local Artists, Albums and cdARTs", xbmc.LOGDEBUG )
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        query = "SELECT artists, albums, cdarts FROM counts"
        pDialog.create( _(32020), _(20186) )
        #Onscreen Dialog - Retrieving Local Music Database, Please Wait....
        c.execute(query)
        counts=c.fetchall()
        c.close
        for item in counts:
            local_artist = item[0]
            album_count = item[1]
            cdart_existing = item[2]
        cdart_existing = recount_cdarts()
        pDialog.close()
        return album_count, local_artist, cdart_existing
    except UnboundLocalError:
        xbmc.log( "[script.cdartmanager] - Counts Not Available in Local DB, Rebuilding DB", xbmc.LOGDEBUG )
        c.close
        refresh_db( False )
    
#user call from Advanced menu to refresh the addon's database
def refresh_db( background ):
    xbmc.log( "[script.cdartmanager] - Refreshing Local Database", xbmc.LOGDEBUG )
    local_album_count = 0
    local_artist_count = 0
    local_cdart_count = 0
    if exists( addon_db ):
        #File exists needs to be deleted
        if not background:
            db_delete = xbmcgui.Dialog().yesno( _(32042) , _(32015) )
        else:
            db_delete = True
        if db_delete:
            xbmc.log( "[script.cdartmanager] - Deleting Local Database", xbmc.LOGDEBUG )
            if exists(addon_db_backup):
                try:
                    delete_file(addon_db_backup)
                except:
                    xbmc.log( "[script.cdartmanager] - Unable to delete Database Backup", xbmc.LOGDEBUG )
            if exists( addon_db ):
                try:
                    file_copy(addon_db,addon_db_backup)
                    xbmc.log( "[script.cdartmanager] - Backing up old Local Database", xbmc.LOGDEBUG )
                except:
                    xbmc.log( "[script.cdartmanager] - Unable to make Database Backup", xbmc.LOGDEBUG )
                try:
                    delete_file( addon_db )
                except:
                    xbmc.log( "[script.cdartmanager] - Unable to delete Database", xbmc.LOGDEBUG )
            if exists( addon_db ): # if database file still exists even after trying to delete it. Wipe out its contents
                conn = sqlite3.connect( addon_db )
                c = conn.cursor()
                c.execute('''DROP table counts''') 
                c.execute('''DROP table lalist''')   # create local album artists database
                c.execute('''DROP table alblist''')  # create local album database
                c.execute('''DROP table unqlist''')  # create unique database
                conn.commit()
                c.close()
            local_album_count, local_artist_count, local_cdart_count = new_database_setup( background )
        else:
            pass
    else :
        #If file does not exist and some how the program got here, create new database
        local_album_count, local_artist_count, local_cdart_count = new_database_setup( background )
    #update counts
    xbmc.log( "[script.cdartmanager] - Finished Refeshing Database", xbmc.LOGDEBUG )
    return local_album_count, local_artist_count, local_cdart_count