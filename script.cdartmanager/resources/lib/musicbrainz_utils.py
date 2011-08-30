# -*- coding: utf-8 -*-
import xbmc
import sys, os
from traceback import print_exc
_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
count=0

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError, ReleaseFilter, ReleaseGroupFilter, ReleaseGroupIncludes
from musicbrainz2.model import Release

def get_musicbrainz_with_singles( album_title, artist, e_count ):
    album = {}
    count = e_count
    xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info - Including Singles", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Artist: %s" % repr(artist), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album_title), xbmc.LOGDEBUG )
    #artist = artist.replace(" & "," ")
    #album_title = album_title.replace(" & "," ")
    try:
        q = """'"%s" AND artist:"%s"'""" % (album_title, artist)
        filter = ReleaseGroupFilter( query=q, limit=1)
        album_result = Query().getReleaseGroups( filter )
        if len( album_result ) == 0:
            xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGDEBUG )
            album["artist"] = ""
            album["artist_id"] = ""
            album["id"] = ""
            album["title"] = ""
        else:
            album["artist"] = album_result[ 0 ].releaseGroup.artist.name
            album["artist_id"] = (album_result[ 0 ].releaseGroup.artist.id).replace( "http://musicbrainz.org/artist/", "" )
            album["id"] = (album_result[ 0 ].releaseGroup.id).replace("http://musicbrainz.org/release-group/", "")
            album["title"] = album_result[ 0 ].releaseGroup.title
        # if album and artist are not matched on MusicBrainz, look up Artist for ID
        if not album["artist_id"]:
            name, id, sortname = get_musicbrainz_artist_id( album["artist"] )
            if id:
                album["artist_id"] = id
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        web_error = "%s" % e
        if int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count < 5:
            xbmc.sleep( 2000 ) # give the musicbrainz server a 2 second break hopefully it will recover
            count += 1
            album = album = get_musicbrainz_with_singles( album_title, artist, count ) # try again
        elif int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count > 5:
            xbmc.log( "[script.cdartmanager] - Script being blocked, attempted 5 tries with 2 second pauses", xbmc.LOGDEBUG )
            count = 0
        else:
            album["artist"] = ""
            album["artist_id"] = ""
            album["id"] = ""
            album["title"] = ""
    count = 0
    xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
    return album

def get_musicbrainz_album( album_title, artist, e_count ):
    album = {}
    count = e_count
    xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info - Not including Singles", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Artist: %s" % repr(artist), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album_title), xbmc.LOGDEBUG )
    #artist = artist.replace(" & "," ")
    #album_title = album_title.replace(" & "," ")
    try:
        q = """'"%s" AND artist:"%s" NOT type:"Single"'""" % (album_title, artist)
        filter = ReleaseGroupFilter( query=q, limit=1)
        #filter = ReleaseGroupFilter( artistName=artist, title=album_title, releaseTypes=Release.TYPE_ALBUM)
        album_result = Query().getReleaseGroups( filter )
        if len( album_result ) == 0:
            xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGDEBUG )
            album = get_musicbrainz_with_singles( album_title, artist, 0 )
        else:
            album["artist"] = album_result[ 0 ].releaseGroup.artist.name
            album["artist_id"] = (album_result[ 0 ].releaseGroup.artist.id).replace( "http://musicbrainz.org/artist/", "" )
            album["id"] = (album_result[ 0 ].releaseGroup.id).replace("http://musicbrainz.org/release-group/", "")
            album["title"] = album_result[ 0 ].releaseGroup.title
        # if album and artist are not matched on MusicBrainz, look up Artist for ID
        if not album["artist_id"]:
            name, id, sortname = get_musicbrainz_artist_id( album["artist"] )
            if id:
                album["artist_id"] = id
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        web_error = "%s" % e
        if int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count < 5:
            xbmc.sleep( 2000 ) # give the musicbrainz server a 2 second break hopefully it will recover
            count += 1
            album = get_musicbrainz_album( album_title, artist, count ) # try again
        elif int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count > 5:
            xbmc.log( "[script.cdartmanager] - Script being blocked, attempted 5 tries with 2 second pauses", xbmc.LOGDEBUG )
            count = 0
        else:
            xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
            album = get_musicbrainz_with_singles( album_title, artist, 0 )
    count = 0
    xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
    return album

def update_musicbrainzid( type, info ):
    xbmc.log( "[script.cdartmanager] - Updating MusicBrainz ID", xbmc.LOGDEBUG )
    try:
        if type == "artist":  # available data info["local_id"], info["name"], info["distant_id"]
            name, artist_id, sortname = get_musicbrainz_artist_id( info["name"] )
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute('UPDATE alblist SET musicbrainz_artistid="%s" WHERE artist="%s"' % (artist_id, info["name"]) )
            try:
                c.execute('UPDATE lalist SET musicbrainz_artistid="%s" WHERE name="%s"' % (artist_id, info["name"]) )
            except:
                pass
            conn.commit
            c.close()
            return artist_id
        if type == "album":
            album_id = get_musicbrainz_album( info["title"], info["artist"], 0 )["id"] 
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute("""UPDATE alblist SET musicbrainz_albumid='%s' WHERE title='%s'""" % (album_id, info["title"]) )
            conn.commit
            c.close()
            return album_id
    except:
        print_exc()
        return ""
        
def get_musicbrainz_artist_id( artist ):
    try:
        # Search for all artists matching the given name. Retrieve the Best Result
        #
        # replace spaces with plus sign
        name = ""
        id = ""
        sortname = ""
        artist=artist.replace(" ", "+").replace(" & "," ")
        f = ArtistFilter( name=artist, limit=1 )
        q_result = Query().getArtists(f)
        if not len(q_result) == 0:
            result = q_result[0]
            artist = result.artist
            xbmc.log( "[script.cdartmanager] - Score     : %s" % result.score, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Id        : %s" % artist.id, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Name      : %s" % repr( artist.name ), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Sort Name : %s" % repr( artist.sortName ), xbmc.LOGDEBUG )
            id = ( artist.id ).replace( "http://musicbrainz.org/artist/", "" )
            name = artist.name
            sortname = artist.sortName
        else: 
            xbmc.log( "[script.cdartmanager] - No Artist ID found for Artist: %s" % repr( artist ), xbmc.LOGDEBUG )
        xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
        return name, id, sortname
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        return "", "", ""