# -*- coding: utf-8 -*-

import xbmc, xbmcgui
import sys, os, re, datetime
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
addon_db_backup   = sys.modules[ "__main__" ].addon_db_backup
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
BASE_RESOURCE_PATH= sys.modules[ "__main__" ].BASE_RESOURCE_PATH
notify = __addon__.getSetting("notifybackground")
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") )

safe_db_version = "1.5.3"
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
pDialog = xbmcgui.DialogProgress()
from musicbrainz_utils import get_musicbrainz_artist_id, get_musicbrainz_album, update_musicbrainzid
from fanarttv_scraper import retrieve_fanarttv_xml, remote_cdart_list
from utils import get_unicode

from jsonrpc_calls import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy
try:
    from xbmcvfs import mkdirs as _makedirs
except:
    from utils import _makedirs

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
        pDialog.create( __language__(32021), __language__(32105) )
    album_list, total = retrieve_album_list()
    if not album_list:
        if not background:
            pDialog.close()
        return None
    album_detail_list = retrieve_album_details_full( album_list, total, background, False, False )
    if not background:
        pDialog.close()
    return album_detail_list 

def retrieve_album_details_full( album_list, total, background, simple, update ):
    xbmc.log( "[script.cdartmanager] - Retrieving Album Details", xbmc.LOGDEBUG )
    album_detail_list = []
    album_count = 0
    percent = 0
    try:
        for detail in album_list:
            if notify == "true" and background:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( __language__(32042), ( repr( detail['title'] ) ), 500, image) )
            if not background:
                if (pDialog.iscanceled()):
                    break
            album_count += 1
            percent = int((album_count/float(total)) * 100)
            if not background:
                pDialog.update( percent, __language__(20186), "%s%s" % ( __language__(32138), ( repr( detail['title'] ) ) ), "%s #:%6s      %s%6s" % ( __language__(32039), album_count, __language__(32045), total ) )
            try:
                album_id = detail['local_id']
            except:
                album_id = detail['albumid']
            albumdetails = retrieve_album_details( album_id )
            if not albumdetails:
                continue
            for albums in albumdetails:
                if not background:
                    if (pDialog.iscanceled()):
                        break
                album_artist = {}
                previous_path = ""
                if not update:
                    paths = get_album_path( album_id )
                    if not paths:
                        continue
                else:
                    paths = []
                    paths.append( detail['path'] )                    
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
                            try:
                                album_artist["local_id"] = detail['local_id']  # for database update
                            except:
                                album_artist["local_id"] = detail['albumid']
                            title = detail['title']
                            album_artist["artist"] = get_unicode( albums['artist'].split(" / ")[0] )
                            album_artist["path"] = path
                            album_artist["cdart"] = exists( os.path.join( path , "cdart.png").replace("\\\\" , "\\") )
                            album_artist["cover"] = exists( os.path.join( path , "folder.jpg").replace("\\\\" , "\\") )
                            previous_path = path
                            path_match = re.search( "(?:disc|cd)([0-9]{0,3})" , path.replace("\\\\","\\"), re.I)
                            if path_match:
                                if not path_match.group(1):
                                    path_match = re.search( "(?:disc|cd)(?: |_|-)([0-9]{0,3})" , path.replace("\\\\","\\"), re.I)
                            title_match = re.search( "(.*?)(?:[\s]|[\(]|[\s][\(])(?:disc|cd)(?:[\s]|)([0-9]{0,3})(?:[\)]?.*?)" , title, re.I)
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
                                            xbmc.log( "[script.cdartmanager] -     Disc %s" % repr( path_match.group( 1 ) ), xbmc.LOGDEBUG )
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
                                        xbmc.log( "[script.cdartmanager] -     Disc %s" % repr( path_match.group( 1 ) ), xbmc.LOGDEBUG )
                                        album_artist["disc"] = int( path_match.group(1) )
                                    else:
                                        album_artist["disc"] = 1
                                else:
                                    album_artist["disc"] = 1
                                album_artist["title"] = ( title.replace(" -", "") ).rstrip()
                            xbmc.log( "[script.cdartmanager] - Album Title: %s" % repr( album_artist["title"] ), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Artist: %s" % repr( album_artist["artist"] ), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album ID: %s" % album_artist["local_id"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr( album_artist["path"] ), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - cdART Exists?: %s" % album_artist["cdart"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Cover Art Exists?: %s" % album_artist["cover"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Disc #: %s" % album_artist["disc"], xbmc.LOGDEBUG )
                            album_detail_list.append(album_artist)
                            if not simple:
                                try:
                                    album_artist["title"] = get_unicode( album_artist["title"] )
                                    musicbrainz_albuminfo, discard = get_musicbrainz_album( album_artist["title"], album_artist["artist"], 0, 1 )
                                except:
                                    print_exc()
                                album_artist["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
                                album_artist["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
                                xbmc.log( "[script.cdartmanager] - MusicBrainz AlbumId: %s" % album_artist["musicbrainz_albumid"], xbmc.LOGDEBUG )
                                xbmc.log( "[script.cdartmanager] - MusicBrainz ArtistId: %s" % album_artist["musicbrainz_artistid"], xbmc.LOGDEBUG )
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
                pDialog.update( percent, __language__(20186), "%s%s" % ( __language__(32138), repr( album["title"] ) ), "%s%6s" % ( __language__(32100), album_count ) )
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
                c.execute("insert into alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ( album["local_id"], get_unicode( album["title"] ), get_unicode( album["artist"] ), get_unicode( album["path"].replace("\\\\" , "\\") ), ("False","True")[album["cdart"]], ("False","True")[album["cover"]], album["disc"], album["musicbrainz_albumid"], album["musicbrainz_artistid"] ))
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
            try:
                c.execute("insert into lalist(local_id, name, musicbrainz_artistid) values (?, ?, ?)", (artist["local_id"], unicode(artist["name"], 'utf-8', ), artist["musicbrainz_artistid"]))
            except TypeError:
                c.execute("insert into lalist(local_id, name, musicbrainz_artistid) values (?, ?, ?)", (artist["local_id"], get_unicode( artist["name"] ), artist["musicbrainz_artistid"]))
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            if not background:
                if (pDialog.iscanceled()):
                    break
        except:
            print_exc()
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
        artist["name"] = get_unicode( item[0] )
        artist["musicbrainz_artistid"] = get_unicode( item[1] )
        #xbmc.log( (artist["name"]), xbmc.LOGDEBUG )
        album_artists.append(artist)
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Retrieving Distinct Album Artists", xbmc.LOGDEBUG )
    return album_artists
        
def store_counts( local_artists_count, artist_count, album_count, cdart_existing ):
    xbmc.log( "[script.cdartmanager] - Storing Counts", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     Album Count: %s" % album_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     Album Artist Count: %s" % artist_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     Local Artist Count: %s" % local_artists_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] -     cdARTs Existing Count: %s" % cdart_existing, xbmc.LOGNOTICE )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    try:
        c.execute('''DROP table IF EXISTS counts''')
    except:
        # table missing
        print_exc()
    try:
        c.execute('''create table counts(local_artists INTEGER, artists INTEGER, albums INTEGER, cdarts INTEGER, version TEXT)''')
    except:
        print_exc()
    c.execute("insert into counts(local_artists, artists, albums, cdarts, version) values (?, ?, ?, ?, ?)", (local_artists_count, artist_count, album_count, cdart_existing, safe_db_version))
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - Finished Storing Counts", xbmc.LOGDEBUG )
    
def check_local_albumartist( album_artist, local_artist_list, background ):
    artist_count = 0
    percent = 0
    found = False
    local_album_artist_list = []
    for artist in album_artist:        # match album artist to local artist id
        #xbmc.log( artist, xbmc.LOGDEBUG )
        album_artist_1 = {}
        name = ""
        name = get_unicode( artist["name"] )
        artist_count += 1
        for local in local_artist_list:
            if not background:
                pDialog.update( percent, __language__(20186), "%s"  % __language__(32101) , "%s:%s" % ( __language__(32038), ( get_unicode( local["artist"] ) ) ) )
                if (pDialog.iscanceled()):
                    break
            if name == get_unicode( local["artist"] ):
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
    download_count = 0
    cdart_existing = 0
    album_count = 0
    local_artist_count = 0
    percent=0
    local_artist_list = []
    local_album_artist_list = []
    count_artist_local = 0
    album_artist = []
    xbmc.log( "[script.cdartmanager] - Setting Up Database", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] -     addon_work_path: %s" % addon_work_folder, xbmc.LOGDEBUG )
    if not background:
        if not exists( os.path.join( addon_work_folder, "settings.xml") ):
            xbmcgui.Dialog().ok( __language__(32071), __language__(32072), __language__(32073) )
            xbmc.log( "[script.cdartmanager] - Settings not set, aborting database creation", xbmc.LOGDEBUG )
            return album_count, artist_count, cdart_existing
    local_album_list = get_xbmc_database_info( background )
    if not local_album_list:
        xbmcgui.Dialog().ok( __language__(32130), __language__(32131), "" )
        xbmc.log( "[script.cdartmanager] - XBMC Music Library does not exist, aborting database creation", xbmc.LOGDEBUG )
        return album_count, artist_count, cdart_existing
    if not background:
        pDialog.create( __language__(32021), __language__(20186) )
    #Onscreen Dialog - Creating Addon Database
    #                      Please Wait....
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute('''create table counts(local_artists INTEGER, artists INTEGER, albums INTEGER, cdarts INTEGER, version TEXT)''') 
    c.execute('''create table lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)''')   # create local album artists database
    c.execute('''create table alblist(album_id INTEGER, title TEXT, artist TEXT, path TEXT, cdart TEXT, cover TEXT, disc INTEGER, musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)''')  # create local album database
    c.execute('''create table unqlist(title TEXT, disc INTEGER, artist TEXT, path TEXT, cdart TEXT)''')  # create unique database
    c.execute('''create table local_artists(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)''')
    conn.commit()
    c.close()
    album_count, cdart_existing = store_alblist( local_album_list, background ) # store album details first
    album_artist = retrieve_distinct_album_artists()               # then retrieve distinct album artists
    local_artist_list = get_all_local_artists()         # retrieve local artists(to get idArtist)
    local_album_artist_list, artist_count = check_local_albumartist( album_artist, local_artist_list, background )
    count = store_lalist( local_album_artist_list, artist_count, background )         # then store in database
    if __addon__.getSetting("enable_all_artists") == "true":
        local_artist_count = build_local_artist_table( background )
    store_counts( local_artist_count, artist_count, album_count, cdart_existing )
    if not background:
        if (pDialog.iscanceled()):
            pDialog.close()
            ok=xbmcgui.Dialog().ok( __language__(32050), __language__(32051), __language__(32052), __language__(32053))
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
            #if not background:
            #    pDialog.create( __language__(32102), __language__(20186) )
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
            album["title"] = get_unicode( item[1] )
            album["artist"] = get_unicode( item[2] )
            album["path"] = get_unicode( item[3] ).replace('"','')
            album["cdart"] = eval( get_unicode( item[4] ) )
            album["cover"] = eval( get_unicode( item[5] ) )
            album["disc"] = ( item[6] )
            album["musicbrainz_albumid"] = get_unicode( item[7] )
            album["musicbrainz_artistid"] = get_unicode( item[8] )
            #print album
            local_album_list.append(album)
    except:
        print_exc()
        #if not background:
        #    pDialog.close()
    #xbmc.log( local_album_list, xbmc.LOGDEBUG )
    #if artist_name == "all artists":
    #    if not background:
    #        pDialog.close()
    xbmc.log( "[script.cdartmanager] - Finished Retrieving Local Albums from Database", xbmc.LOGDEBUG )
    return local_album_list
        
def get_local_artists_db( mode="album_artists" ):
    local_artist_list = []    
    if mode == "album_artists":
        xbmc.log( "[script.cdartmanager] - Retrieving Local Album Artists from Database", xbmc.LOGDEBUG )
        query = "SELECT DISTINCT local_id, name, musicbrainz_artistid FROM lalist ORDER BY name"
    else:
        xbmc.log( "[script.cdartmanager] - Retrieving All Local Artists from Database", xbmc.LOGDEBUG )
        query = "SELECT DISTINCT local_id, name, musicbrainz_artistid FROM local_artists ORDER BY name"
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
            artists["name"] = get_unicode( item[1] )
            artists["musicbrainz_artistid"] = get_unicode( item[2] )
            #xbmc.log( (artists), xbmc.LOGDEBUG )
            local_artist_list.append(artists)
    except:
        print_exc()
    #xbmc.log( local_artist_list, xbmc.LOGDEBUG )
    return local_artist_list
    
def build_local_artist_table( background ):
    xbmc.log( "[script.cdartmanager] - Retrieving All Local Artists From XBMC", xbmc.LOGDEBUG )
    new_local_artist_list = []
    local_artist_list = get_all_local_artists()
    local_album_artist_list = get_local_artists_db()
    percent = 0
    count = 1
    total = len( local_artist_list ) 
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    if not background:
        pDialog.create( __language__(32124), __language__(20186) )
    try:
        for local_artist in local_artist_list:
            if not background:
                if (pDialog.iscanceled()):
                    break
            artist = {}
            percent = int( ( count/float( total ) ) * 100 )
            if not background:
                pDialog.update( percent, __language__(20186), "%s%s" % ( __language__(32125), local_artist["artistid"] ), "%s%s" % ( __language__(32137), get_unicode( local_artist["artist"] ) ) )
            count += 1
            for album_artist in local_album_artist_list:
                if not background:
                    if (pDialog.iscanceled()):
                        break
                if local_artist["artistid"] == album_artist["local_id"]:
                    artist["name"] = get_unicode( local_artist["artist"] )
                    artist["local_id"] = local_artist["artistid"]
                    artist["musicbrainz_artistid"] = album_artist["musicbrainz_artistid"]
                    break
                else:
                    continue
            if not artist:
                try:
                    artist["name"] = get_unicode( local_artist["artist"] )
                    name, artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( get_unicode( local_artist["artist"] ) )
                except:
                    artist["name"] = get_unicode( local_artist["artist"] )
                    name, artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( local_artist["artist"] )
                artist["local_id"] = local_artist["artistid"]
            new_local_artist_list.append( artist )
        count = 0
        percent = 0
        for artist in new_local_artist_list:
            percent = int( ( count/float( len(new_local_artist_list ) ) ) * 100 )
            if not background:
                pDialog.update( percent, __language__(32124), "%s%s" % ( __language__(32125), artist["local_id"] ), "%s%s" % ( __language__(32028), get_unicode( artist["name"] ) ) )
            try:
                c.execute("insert into local_artists(local_id, name, musicbrainz_artistid) values (?, ?, ?)", ( artist["local_id"], get_unicode( artist["name"] ), artist["musicbrainz_artistid"] ) )
                count += 1
            except:
                print_exc()
        conn.commit()
        if not background:
            pDialog.close()
    except:
        xbmc.log( "[script.cdartmanager] - Problem with making all artists table", xbmc.LOGDEBUG )
        print_exc()
        if not background:
            pDialog.close()
    c.close
    return count
    
#retrieves counts for local album, artist and cdarts
def new_local_count():
    xbmc.log( "[script.cdartmanager] - Counting Local Artists, Albums and cdARTs", xbmc.LOGDEBUG )
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        pDialog.create( __language__(32020), __language__(20186) )
        #Onscreen Dialog - Retrieving Local Music Database, Please Wait....
        query = "SELECT artists, albums, cdarts FROM counts"
        c.execute(query)
        counts=c.fetchall()
        c.close
        for item in counts:
            album_artist = item[0]
            album_count = item[1]
            cdart_existing = item[2]
        cdart_existing = recount_cdarts()
        pDialog.close()
        return album_count, album_artist, cdart_existing
    except UnboundLocalError:
        xbmc.log( "[script.cdartmanager] - Counts Not Available in Local DB, Rebuilding DB", xbmc.LOGDEBUG )
        c.close
        return 0,0,0
    
#user call from Advanced menu to refresh the addon's database

def refresh_db( background ):
    xbmc.log( "[script.cdartmanager] - Refreshing Local Database", xbmc.LOGDEBUG )
    local_album_count = 0
    local_artist_count = 0
    local_cdart_count = 0
    if exists( addon_db ):
        #File exists needs to be deleted
        if not background:
            db_delete = xbmcgui.Dialog().yesno( __language__(32042) , __language__(32015) )
        else:
            db_delete = True
        if db_delete:
            if exists( addon_db ):
                # backup database
                backup_database()
                try:
                    # try to delete exsisting database
                    delete_file( addon_db )
                except:
                    xbmc.log( "[script.cdartmanager] - Unable to delete Database", xbmc.LOGDEBUG )
            if exists( addon_db ):
                # if database file still exists even after trying to delete it. Wipe out its contents
                conn = sqlite3.connect(addon_db)
                c = conn.cursor()
                c.execute('''DROP table IF EXISTS counts''') 
                c.execute('''DROP table IF EXISTS lalist''')   # drop local album artists database
                c.execute('''DROP table IF EXISTS alblist''')  # drop local album database
                c.execute('''DROP table IF EXISTS unqlist''')  # drop unique database
                c.execute('''DROP table IF EXISTS local_artists''')
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

def update_database( background ):
    xbmc.log( "[script.cdartmanager] - Updating Addon's DB", xbmc.LOGDEBUG )
    update_list = []
    new_list = []
    matched = []
    unmatched = []
    matched_indexed = {}
    album_detail_list_indexed = {}
    local_artists_matched = []
    local_artists_unmatched = []
    local_artists_indexed = {}
    local_artists_matched_indexed = {}
    local_artists_unmatched_detail = []
    temp_local_artists = []
    artist = {}
    updated_artists = []
    updated_albums = []
    if not background:
        pDialog.create( __language__(32134), __language__(32105) ) # retrieving all artist from xbmc
    local_album_list = get_local_albums_db( "all artists", False )
    if not background:
        pDialog.create( __language__(32134), __language__(32105) ) # retrieving album list
    album_list, total = retrieve_album_list()
    if not background:
        pDialog.create( __language__(32134), __language__(32105) ) #  retrieving album details
    album_detail_list = retrieve_album_details_full( album_list, total, background, True, False )
    if not background:
        pDialog.create( __language__(32134), __language__(32105) ) #  retrieving local artist details
    for item in album_detail_list:
        album_detail_list_indexed[( item["disc"], item["artist"], item["title"], item["cover"], item["cdart"], item["local_id"], item["path"] )] = item
    for item in local_album_list:
        if ( item["disc"], item["artist"], item["title"], item["cover"], item["cdart"], item["local_id"], item["path"] ) in album_detail_list_indexed:
            matched.append(item)
    for item in matched:
        matched_indexed[( item["disc"], item["artist"], item["title"], item["cover"], item["cdart"], item["local_id"], item["path"] )] = item
    for item in album_detail_list:
        if not ( item["disc"], item["artist"], item["title"], item["cover"], item["cdart"], item["local_id"], item["path"] ) in matched_indexed:
            unmatched.append(item)
    unmatched_details = retrieve_album_details_full( unmatched, len( unmatched ), background, False, True )
    combined = matched
    combined.extend( unmatched_details )
    local_artists = get_all_local_artists()
    for artist in local_artists:
        new_artist = {}
        new_artist["name"] = get_unicode( artist["artist"] )
        new_artist["local_id"] = artist["artistid"]
        temp_local_artists.append( new_artist )
    local_artists = temp_local_artists
    local_artists_db = get_local_artists_db( "all artists" )
    for item in local_artists:
        local_artists_indexed[( item["local_id"],  item["name"] )] = item
    for item in local_artists_db:
        if ( item["local_id"], item["name"] ) in local_artists_indexed:
            local_artists_matched.append( item )
    for item in local_artists_matched:
        local_artists_matched_indexed[( item["local_id"], item["name"] )] = item
    for item in local_artists:
        if not ( item["local_id"], item["name"] ) in local_artists_matched_indexed:
            local_artists_unmatched.append( item )
    combined_artists = local_artists_matched
    percent = 0
    count = 0
    if __addon__.getSetting("enable_all_artists") == "true":
        for local_artist in local_artists_unmatched:
            artist = {}
            percent = int( ( count/float( len( local_artists_unmatched ) ) ) * 100 )
            if not background:
                pDialog.update( percent, __language__(32135), "%s%s" % ( __language__(32125), local_artist["local_id"] ), "%s%s" % ( __language__(32137), repr( local_artist["name"] ) ) )
            count += 1
            artist["name"] = get_unicode( local_artist["name"] )
            artist["local_id"] = local_artist["local_id"]
            try:
                name, artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( get_unicode( local_artist["name"] ) )
            except:
                name, artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( local_artist["name"] )
            local_artists_unmatched_detail.append( artist )
    if __addon__.getSetting("update_musicbrainz") == "true":  # update missing MusicBrainz ID's
        count = 1
        if __addon__.getSetting("enable_all_artists") == "true":
            for artist in combined_artists:
                update_artist = artist
                percent = int( ( count/float( len( combined_artists ) ) ) * 100 )
                count += 1
                if not background:
                    pDialog.update( percent, __language__(32132), "%s%s" % ( __language__(32125), update_artist["local_id"] ), "%s%s" % ( __language__(32137), repr( update_artist["name"] ) ) )
                    if (pDialog.iscanceled()):
                        break
                if not update_artist["musicbrainz_artistid"]:
                    try:
                        name, update_artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( get_unicode( update_artist["name"] ) )
                    except:
                        name, update_artist["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( update_artist["name"] )
                updated_artists.append( update_artist )
            count = 1
        else:
            updated_artists = combined_artists
        for album in combined:
            update_album = album
            percent = int( ( count/float( len( combined ) ) ) * 100 )
            count += 1
            if not background:
                pDialog.update( percent, __language__(32133), "%s%s" % ( __language__(32138), repr( album["title"] ) ), "%s%s" % ( __language__(32137), repr( album["artist"] ) ) )
                if (pDialog.iscanceled()):
                    break
            if not album["musicbrainz_albumid"]:
                musicbrainz_albuminfo, discard = get_musicbrainz_album( get_unicode( album["title"] ), get_unicode( album["artist"] ), 0, 1 )
                print musicbrainz_albuminfo
                update_album["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
                update_album["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
            updated_albums.append( update_album )
    combined_artists = updated_artists
    combined = updated_albums
    combined_artists.extend( local_artists_unmatched_detail )
    conn = sqlite3.connect( addon_db )
    c = conn.cursor()
    if exists( addon_db ): # if database file still exists even after trying to delete it. Wipe out its contents
        c.execute('''DROP table IF EXISTS counts''') 
        c.execute('''DROP table IF EXISTS lalist''')   # drop local album artists database
        c.execute('''DROP table IF EXISTS alblist''')  # drop local album database
        c.execute('''DROP table IF EXISTS unqlist''')  # drop unique database
        c.execute('''DROP table IF EXISTS local_artists''')
    c.execute('''create table counts(local_artists INTEGER, artists INTEGER, albums INTEGER, cdarts INTEGER, version TEXT)''') 
    c.execute('''create table lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)''')   # create local album artists database
    c.execute('''create table alblist(album_id INTEGER, title TEXT, artist TEXT, path TEXT, cdart TEXT, cover TEXT, disc INTEGER, musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)''')  # create local album database
    c.execute('''create table unqlist(title TEXT, disc INTEGER, artist TEXT, path TEXT, cdart TEXT)''')  # create unique database
    c.execute('''create table local_artists(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)''')  # create local artists database
    album_count, cdart_existing = store_alblist( combined, background )
    conn.commit()
    c.close()
    album_artist = retrieve_distinct_album_artists()               # then retrieve distinct album artists
    local_artist_list = get_all_local_artists()                    # retrieve local artists(to get idArtist)
    local_album_artist_list, artist_count = check_local_albumartist( album_artist, local_artist_list, background )
    count = store_lalist( local_album_artist_list, artist_count, background )         # then store in database
    conn = sqlite3.connect( addon_db )
    c = conn.cursor()
    if len( combined_artists ) > 0:
        for artist in combined_artists:
            percent = int( ( count/float( len( combined_artists ) ) ) * 100 )
            if not background:
                pDialog.update( percent, __language__(32124), "%s%s" % ( __language__(32125), artist["local_id"] ), "%s%s" % ( __language__(32028), ( repr( artist["name"] ) ) ) )
            try:
                c.execute("insert into local_artists(local_id, name, musicbrainz_artistid) values (?, ?, ?)", ( artist["local_id"], get_unicode( artist["name"] ), artist["musicbrainz_artistid"] ) )
                count += 1
            except:
                print_exc()
                continue            
    conn.commit()
    if not background:
        pDialog.close()
    c.close()
    local_artist_count = len( combined_artists )
    store_counts( local_artist_count, artist_count, album_count, cdart_existing )
    if not background:
        pDialog.close()

def backup_database():
    todays_date = today = datetime.datetime.today().strftime("%m-%d-%Y")
    db_backup_file = "l_cdart-%s.bak" % todays_date
    addon_backup_path = os.path.join( addon_work_folder, db_backup_file ).replace("\\\\","\\")
    file_copy( addon_db, addon_backup_path )
    if exists( addon_backup_path ):
        try:
            delete_file( addon_backup_path )
        except:
            xbmc.log( "[script.cdartmanager] - Unable to delete Database Backup", xbmc.LOGDEBUG )
    try:
        file_copy( addon_db, addon_backup_path )
        xbmc.log( "[script.cdartmanager] - Backing up old Local Database", xbmc.LOGDEBUG )
    except:
        xbmc.log( "[script.cdartmanager] - Unable to make Database Backup", xbmc.LOGDEBUG )


