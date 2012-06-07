# -*- coding: utf-8 -*-

import xbmc
import sys, os, re
from urllib import quote_plus
from traceback import print_exc

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
    
__language__      = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
BASE_RESOURCE_PATH= sys.modules[ "__main__" ].BASE_RESOURCE_PATH

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from utils import get_html_source
artist_url = '''http://musicbrainz.org/ws/2/artist/?query=artist:"%s"&limit=%d'''
release_group_url_nosingles = '''http://musicbrainz.org/ws/2/release-group/?query="%s" AND artist:"%s" NOT type:single&limit=%d'''
release_group_url_using_release_name = '''http://musicbrainz.org/ws/2/release-group/?query=release:"%s" AND artist:"%s"&limit=%d'''
release_group_url_singles = '''http://musicbrainz.org/ws/2/release-group/?query="%s" AND artist:"%s"&limit=%d'''
release_group_url_release_mbid = '''http://musicbrainz.org/ws/2/release-group/?release=%s'''
release_groups_url_artist_mbid = '''http://musicbrainz.org/ws/2/release-group/?artist="%s"'''

def split_album_info( album_result, index ):
    album = {}
    try:
        album["artist"] = album_result[ index ].releaseGroup.artist.name
        album["artist_id"] = ( album_result[ index ].releaseGroup.artist.id ).replace( "http://musicbrainz.org/artist/", "" )
        album["id"] = ( album_result[ index ].releaseGroup.id ).replace( "http://musicbrainz.org/release-group/", "" )
        album["title"] = album_result[ index ].releaseGroup.title
    except:
        album["artist"] = ""
        album["artist_id"] = ""
        album["id"] = ""
        album["title"] = ""
    return album

def get_musicbrainz_album( album_title, artist, e_count, limit=1, with_singles=False, by_release=False ):
    """ Retrieves information for Album from MusicBrainz using provided Album title and Artist name. 
        
        Use:
            album, albums = get_musicbrainz_album( album_title, artist, e_count, limit, with_singles )
        
        album_title  - the album title(must be unicode)
        artist       - the artist's name(must be unicode)
        e_count      - used internally(should be set to 0)
        limit        - limit the number of responses
        with_singles - set to True to look up single releases at the same time
    """
    album = {}
    albums = []
    count = e_count
    album["id"] = ""
    album["title"] = ""
    album["artist"] = ""
    album["artist_id"] = ""
    if not with_singles and not by_release:
        xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info - Not including Singles", xbmc.LOGDEBUG )
    elif not by_release:
        xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info - Including Singles", xbmc.LOGDEBUG )
    elif not with_singles:
        xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info - Using Release Name", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Artist: %s" % repr(artist), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album_title), xbmc.LOGDEBUG )
    artist = artist.replace('"','?')
    album_title = album_title.replace('"','?')
    if with_singles and not by_release:
        url = release_group_url_singles % ( quote_plus( album_title.encode("utf-8") ), quote_plus( artist.encode("utf-8") ), limit )
    elif not with_singles and not by_release:
        url = release_group_url_nosingles % ( quote_plus( album_title.encode("utf-8") ), quote_plus( artist.encode("utf-8") ), limit )
    elif by_release and not with_singles:
        url = release_group_url_using_release_name % ( quote_plus( album_title.encode("utf-8") ), quote_plus( artist.encode("utf-8") ), limit )
    htmlsource = get_html_source( url, "", False )
    if limit == 1:
        match = re.search( '''<release-group ext:score="(.*?)"(?:.*?)</release-group>''', htmlsource )
        if match:
            if int( match.group(1) ) > 0:
                try:
                    mbid = re.search( '''id="(.*?)"''', htmlsource)
                    mbtitle = re.search( '''<title>(.*?)</title>''', htmlsource)
                    mbartist = re.search( '''<name>(.*?)</name>''', htmlsource)
                    mbartistid = re.search( '''<artist id="(.*?)">''', htmlsource)
                    album["id"] = mbid.group(1)
                    album["title"] = mbtitle.group(1)
                    album["artist"] = mbartist.group(1)
                    album["artist_id"] = mbartistid.group(1)
                except:
                    pass            
        if not album["id"]:
            if with_singles:
                xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGDEBUG )
                album["artist"], album["artist_id"], sort_name = get_musicbrainz_artist_id( artist )
            elif by_release and not with_singles:
                xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz, checking singles", xbmc.LOGDEBUG )
                xbmc.sleep( 910 ) # sleep for allowing proper use of webserver
                album, albums = get_musicbrainz_album( album_title, artist, 0, limit, True, False ) # try again with singles
            else:
                xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz, Checking by Release name", xbmc.LOGDEBUG )
                xbmc.sleep( 910 ) # sleep for allowing proper use of webserver
                album, albums = get_musicbrainz_album( album_title, artist, 0, limit, False, True ) # try again by using release name
    else:
        # future code coming soon
        pass
    xbmc.sleep( 910 ) # sleep for allowing proper use of webserver
    return album, albums

def get_musicbrainz_artist_id( artist, limit=1 ):
    name = ""
    id = ""
    sortname = ""
    url = artist_url % ( quote_plus( artist.encode("utf-8") ), limit )
    htmlsource = get_html_source( url, "", False)
    match = re.search( '''<artist ext:score="(.*?)" type="(.*?)" id="(.*?)"><name>(.*?)</name><sort-name>(.*?)</sort-name>(?:.*?)</artist>''', htmlsource )
    if match:
        xbmc.log( "[script.cdartmanager] - Score     : %s" % match.group(1), xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - Type      : %s" % repr( match.group(2) ), xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - Id        : %s" % match.group(3), xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - Name      : %s" % repr( match.group(4) ), xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - Sort Name : %s" % repr( match.group(5) ), xbmc.LOGDEBUG )
        name = match.group(4)
        id = match.group(3)
        sortname = match.group(5)
    else:
        xbmc.log( "[script.cdartmanager] - No Artist ID found for Artist: %s" % repr( artist ), xbmc.LOGDEBUG )
    xbmc.sleep( 910 ) # sleep for allowing proper use of webserver
    return name, id, sortname

def update_musicbrainzid( type, info ):
    xbmc.log( "[script.cdartmanager] - Updating MusicBrainz ID", xbmc.LOGDEBUG )
    artist_id = ""
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
        if type == "album":
            album_id = get_musicbrainz_album( info["title"], info["artist"], 0 )["id"] 
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute("""UPDATE alblist SET musicbrainz_albumid='%s' WHERE title='%s'""" % (album_id, info["title"]) )
            conn.commit
            c.close()
    except:
        print_exc()
    return artist_id
