# -*- coding: utf-8 -*-

import sys
import os
import re
from urllib import quote_plus, quote
from traceback import print_exc

import xbmc

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

__language__ = sys.modules["__main__"].__language__
__scriptname__ = sys.modules["__main__"].__scriptname__
__scriptID__ = sys.modules["__main__"].__scriptID__
__version__ = sys.modules["__main__"].__version__
__addon__ = sys.modules["__main__"].__addon__
use_musicbrainz = sys.modules["__main__"].use_musicbrainz
musicbrainz_server = sys.modules["__main__"].musicbrainz_server
addon_db = sys.modules["__main__"].addon_db
addon_work_folder = sys.modules["__main__"].addon_work_folder
BASE_RESOURCE_PATH = sys.modules["__main__"].BASE_RESOURCE_PATH
mb_delay = sys.modules["__main__"].mb_delay

# sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from utils import get_html_source, unescape, log, get_unicode, smart_unicode

artist_url = '''%s/ws/2/artist/?query=artist:"%s"&limit=%d'''
alias_url = '''%s/ws/2/artist/?query=alias:"%s"&limit=%d'''
release_group_url = '''%s/ws/2/release-group/'''
release_group_url_artist = release_group_url + '''?query="%s"%s AND artist:"%s"'''
release_group_url_alias = release_group_url + '''?query="%s"%s AND alias:"%s"'''
nolive_nosingles = ''' NOT type:single NOT type:live'''
live_nosingles = ''' NOT type:single'''
query_limit = '''&limit=%d'''

release_group_url_using_release_name = '''%s/ws/2/release-group/?query=release:"%s"%s AND artist:"%s"&limit=%d'''
release_group_url_using_release_name_alias = '''%s/ws/2/release-group/?query=release:"%s"%s AND alias:"%s"&limit=%d'''
release_group_url_release_mbid = '''%s/ws/2/release-group/?release=%s'''
release_groups_url_artist_mbid = '''%s/ws/2/release-group/?artist="%s"'''
artist_id_check = '''%s/ws/2/artist/%s'''
release_group_id_check = '''%s/ws/2/release-group/%s'''
server = musicbrainz_server


def split_album_info(album_result, index):
    album = {}
    try:
        album["artist"] = album_result[index].releaseGroup.artist.name
        album["artist_id"] = (album_result[index].releaseGroup.artist.id).replace("http://musicbrainz.org/artist/", "")
        album["id"] = (album_result[index].releaseGroup.id).replace("http://musicbrainz.org/release-group/", "")
        album["title"] = album_result[index].releaseGroup.title
    except:
        album["artist"] = ""
        album["artist_id"] = ""
        album["id"] = ""
        album["title"] = ""
    return album


def get_musicbrainz_release_group(release_mbid):
    """ Retrieves the MusicBrainz Release Group MBID from a given release MBID
        
        Use:
            release_groupmbid = get_musicbrainz_release_group( release_mbid )
        
        release_mbid - valid release mbid
    """
    log("Retrieving MusicBrainz Release Group MBID from Album Release MBID", xbmc.LOGDEBUG)
    url = release_group_url_release_mbid % (server, quote_plus(release_mbid))
    mbid = ""
    htmlsource = get_html_source(url, release_mbid, save_file=False, overwrite=False)
    match = re.search('''<release-group-list count="(?:.*?)">(.*?)</release-group-list>''', htmlsource)
    if match:
        mbid_match = re.search('''<release-group id="(.*?)"(?:.*?)">''', match.group(1))
        if not mbid_match:
            mbid_match = re.search('''<release-group (?:.*?)id="(.*?)">''', match.group(1))
        if mbid_match:
            mbid = mbid_match.group(1)
    xbmc.sleep(mb_delay)
    return mbid


def get_musicbrainz_album(album_title, artist, e_count, limit=1, with_singles=False, by_release=False, use_alias=False,
                          use_live=False):
    """ Retrieves information for Album from MusicBrainz using provided Album title and Artist name. 
        
        Use:
            album, albums = get_musicbrainz_album( album_title, artist, e_count, limit, with_singles, by_release )
        
        album_title  - the album title(must be unicode)
        artist       - the artist's name(must be unicode)
        e_count      - used internally(should be set to 0)
        limit        - limit the number of responses
        with_singles - set to True to look up single releases at the same time
        by_release   - use release name for search
    """
    match_within = "~2"
    album = {}
    albums = []
    count = e_count
    album["score"] = ""
    album["id"] = ""
    album["title"] = ""
    album["artist"] = ""
    album["artist_id"] = ""
    album_temp = smart_unicode(album_title)
    artist = smart_unicode(get_unicode(artist))
    album_title = smart_unicode(get_unicode(album_title))
    log("Artist: %s" % artist, xbmc.LOGDEBUG)
    log("Album: %s" % album_title, xbmc.LOGDEBUG)
    artist = artist.replace('"', '?')
    artist = artist.replace('&', 'and')
    album_title = album_title.replace('"', '?')
    album_title = album_title.replace('&', 'and')
    if limit == 1:
        if not use_alias:
            url = release_group_url_artist % (
            server, quote_plus(album_title.encode("utf-8")), match_within, quote_plus(artist.encode("utf-8")))
            if not with_singles and not by_release and not use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles or Live albums",
                    xbmc.LOGDEBUG)
                url = url + nolive_nosingles + query_limit % limit
            elif not with_singles and not by_release and use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles", xbmc.LOGDEBUG)
                url = url + live_nosingles + query_limit % limit
            elif not by_release:
                log("Retrieving MusicBrainz Info - Checking by Artist - Including Singles and Live albums",
                    xbmc.LOGDEBUG)
                url = url + query_limit % limit
            elif not with_singles:
                log("Retrieving MusicBrainz Info - Checking by Artist - Using Release Name", xbmc.LOGDEBUG)
                url = release_group_url_artist % (server, quote_plus(album_title.encode("utf-8")), match_within,
                                                  quote_plus(artist.encode("utf-8"))) + query_limit % limit
        elif use_alias:
            url = release_group_url_alias % (
            server, quote_plus(album_title.encode("utf-8")), match_within, quote_plus(artist.encode("utf-8")))
            if not with_singles and not by_release and not use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles or Live albums",
                    xbmc.LOGDEBUG)
                url = url + nolive_nosingles + query_limit % limit
            elif not with_singles and not by_release and use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles", xbmc.LOGDEBUG)
                url = url + live_nosingles + query_limit % limit
            elif not by_release:
                log("Retrieving MusicBrainz Info - Checking by Artist - Including Singles and Live albums",
                    xbmc.LOGDEBUG)
                url = url + query_limit % limit
            elif not with_singles:
                log("Retrieving MusicBrainz Info - Checking by Artist - Using Release Name", xbmc.LOGDEBUG)
                url = release_group_url_alias % (server, quote_plus(album_title.encode("utf-8")), match_within,
                                                 quote_plus(artist.encode("utf-8"))) + query_limit % limit
        htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
        match = re.search('''<release-group-list count="(?:.*?)" offset="(?:.*?)">(.*?)</release-group-list>''',
                          htmlsource)
        if match:
            try:
                mbid = re.search('''<release-group id="(.*?)"(?:.*?)">''', htmlsource)
                if not mbid:
                    mbid = re.search('''<release-group (?:.*?)id="(.*?)">''', htmlsource)
                mbtitle = re.search('''<title>(.*?)</title>''', htmlsource)
                mbartist = re.search('''<name>(.*?)</name>''', htmlsource)
                mbartistid = re.search('''<artist id="(.*?)">''', htmlsource)
                album["id"] = mbid.group(1)
                album["title"] = unescape(smart_unicode(mbtitle.group(1)))
                album["artist"] = unescape(smart_unicode(mbartist.group(1)))
                album["artist_id"] = mbartistid.group(1)
            except:
                pass
        if not album["id"]:
            xbmc.sleep(mb_delay)  # sleep for allowing proper use of webserver
            if not with_singles and not by_release and not use_alias and not use_live:
                log("No releases found on MusicBrainz, Checking For Live Album", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, False, False,
                                                      True)  # try again by using artist alias
            elif not with_singles and not by_release and not use_alias and use_live:
                log("No releases found on MusicBrainz, Checking by Artist Alias", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, False, True,
                                                      False)  # try again by using artist alias
            elif use_alias and not with_singles and not by_release and not use_live:
                log("No releases found on MusicBrainz, Checking by Release Name", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, True, False,
                                                      False)  # try again by using release name
            elif by_release and not with_singles and not use_alias:
                log("No releases found on MusicBrainz, Checking by Release name and Artist Alias", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, True, True,
                                                      False)  # try again by using release name and artist alias
            elif by_release and not with_singles and use_alias:
                log("No releases found on MusicBrainz, checking singles", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, True, False, False,
                                                      False)  # try again with singles
            elif with_singles and not use_alias and not by_release:
                log("No releases found on MusicBrainz, checking singles and Artist Alias", xbmc.LOGDEBUG)
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, True, False, True,
                                                      False)  # try again with singles and artist alias
            else:
                log("No releases found on MusicBrainz.", xbmc.LOGDEBUG)
                album["artist"], album["artist_id"], sort_name = get_musicbrainz_artist_id(artist)
    else:
        match_within = "~4"
        url = release_group_url_artist % (
        server, (album_title.encode("utf-8")), match_within, (artist.encode("utf-8"))) + query_limit % limit
        htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
        match = re.search('''<release-group-list count="(?:.*?)" offset="(?:.*?)">(.*?)</release-group-list>''',
                          htmlsource)
        if match:
            match_release_group = re.findall('''<release-group(.*?)</release-group>''', match.group(1))
            if match_release_group:
                for item in match_release_group:
                    album = {}
                    album["score"] = ""
                    album["id"] = ""
                    album["title"] = ""
                    album["artist"] = ""
                    album["artist_id"] = ""
                    try:
                        mbscore = re.search('''score="(.*?)"''', item)
                        mbid = re.search('''<release-group id="(.*?)"(?:.*?)">''', item)
                        if not mbid:
                            mbid = re.search('''id="(.*?)"(?:.*?)">''', item)
                            if not mbid:
                                mbid = re.search('''<release-group (?:.*?)id="(.*?)">''', htmlsource)
                        mbtitle = re.search('''<title>(.*?)</title>''', item)
                        mbartist = re.search('''<name>(.*?)</name>''', item)
                        mbartistid = re.search('''<artist id="(.*?)">''', item)
                        album["score"] = mbscore.group(1)
                        album["id"] = mbid.group(1)
                        album["title"] = unescape(smart_unicode(mbtitle.group(1)))
                        album["artist"] = unescape(smart_unicode(mbartist.group(1)))
                        album["artist_id"] = mbartistid.group(1)
                        log("Score     : %s" % album["score"], xbmc.LOGDEBUG)
                        log("Title     : %s" % album["title"], xbmc.LOGDEBUG)
                        log("Id        : %s" % album["id"], xbmc.LOGDEBUG)
                        log("Artist    : %s" % album["artist"], xbmc.LOGDEBUG)
                        log("Artist ID : %s" % album["artist_id"], xbmc.LOGDEBUG)
                        albums.append(album)
                    except:
                        print_exc()

            else:
                pass
        else:
            pass
    xbmc.sleep(mb_delay)  # sleep for allowing proper use of webserver
    return album, albums


def get_musicbrainz_artists(artist_search, limit=1):
    log("Artist: %s" % artist_search, xbmc.LOGDEBUG)
    score = ""
    name = ""
    id = ""
    sortname = ""
    artists = []
    artist_name = smart_unicode((artist_search.replace('"', '?').replace('&', 'and')))
    url = artist_url % (server, quote_plus(artist_name.encode("utf-8")), limit)
    htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
    match = re.findall('''<artist(.*?)</artist>''', htmlsource)
    if match:
        for item in match:
            artist = {}
            artist["score"] = ""
            artist["name"] = ""
            artist["id"] = ""
            artist["sortname"] = ""
            score_match = re.search('''score="(.*?)"''', item)
            name_match = re.search('''<name>(.*?)</name>''', item)
            id_match = re.search('''id="(.*?)"(?:.*?)>''', item)
            if not id_match:
                id_match = re.search('''id="(.*?)">''', item)
            sort_name_match = re.search('''<sort-name>(.*?)</sort-name>''', item)
            if score_match:
                artist["score"] = score_match.group(1)
            if name_match:
                artist["name"] = unescape(smart_unicode(name_match.group(1)))
            if id_match:
                artist["id"] = id_match.group(1)
            if sort_name_match:
                artist["sortname"] = unescape(smart_unicode(sort_name_match.group(1)))
            log("Score     : %s" % artist["score"], xbmc.LOGDEBUG)
            log("Id        : %s" % artist["id"], xbmc.LOGDEBUG)
            log("Name      : %s" % artist["name"], xbmc.LOGDEBUG)
            log("Sort Name : %s" % artist["sortname"], xbmc.LOGDEBUG)
            artists.append(artist)
    else:
        log("No Artist ID found for Artist: %s" % repr(artist_search), xbmc.LOGDEBUG)
    xbmc.sleep(mb_delay)
    return artists


def get_musicbrainz_artist_id(artist_search, limit=1, alias=False):
    name = ""
    id = ""
    sortname = ""
    artist_name = smart_unicode((artist_search.replace('"', '?').replace('&', 'and')))
    if not alias:
        url = artist_url % (server, quote_plus(artist_name.encode("utf-8")), limit)
    else:
        url = alias_url % (server, quote_plus(artist_name.encode("utf-8")), limit)
    htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
    match = re.search('''<artist(.*?)</artist>''', htmlsource)
    if match:
        score_match = re.search('''score="(.*?)"''', htmlsource)
        name_match = re.search('''<name>(.*?)</name>''', htmlsource)
        id_match = re.search('''<artist id="(.*?)"(?:.*?)>''', htmlsource)
        if not id_match:
            id_match = re.search('''<artist (?:.*?)id="(.*?)">''', htmlsource)
        sort_name_match = re.search('''<sort-name>(.*?)</sort-name>''', htmlsource)

        if score_match:
            score = score_match.group(1)
        if name_match:
            name = unescape(smart_unicode(name_match.group(1)))
        if id_match:
            id = id_match.group(1)
        if sort_name_match:
            sortname = unescape(smart_unicode(sort_name_match.group(1)))
        log("Score     : %s" % score, xbmc.LOGDEBUG)
        log("Id        : %s" % id, xbmc.LOGDEBUG)
        log("Name      : %s" % name, xbmc.LOGDEBUG)
        log("Sort Name : %s" % sortname, xbmc.LOGDEBUG)
    else:
        if not alias:
            log("No Artist ID found trying aliases: %s" % artist_search, xbmc.LOGDEBUG)
            name, id, sortname = get_musicbrainz_artist_id(artist_search, limit, True)
        else:
            log("No Artist ID found for Artist: %s" % artist_search, xbmc.LOGDEBUG)
    xbmc.sleep(mb_delay)
    return name, id, sortname


def update_musicbrainzid(type, info):
    log("Updating MusicBrainz ID", xbmc.LOGDEBUG)
    artist_id = ""
    try:
        if type == "artist":  # available data info["local_id"], info["name"], info["distant_id"]
            name, artist_id, sortname = get_musicbrainz_artist_id(info["name"])
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute('UPDATE alblist SET musicbrainz_artistid="%s" WHERE artist="%s"' % (artist_id, info["name"]))
            try:
                c.execute('UPDATE lalist SET musicbrainz_artistid="%s" WHERE name="%s"' % (artist_id, info["name"]))
            except:
                pass
            conn.commit
            c.close()
        if type == "album":
            album_id = get_musicbrainz_album(info["title"], info["artist"], 0)["id"]
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute("""UPDATE alblist SET musicbrainz_albumid='%s' WHERE title='%s'""" % (album_id, info["title"]))
            conn.commit
            c.close()
    except:
        print_exc()
    return artist_id


def mbid_check(database_mbid, type):
    log("Looking up %s MBID. Current MBID: %s" % (type, database_mbid), xbmc.LOGNOTICE)
    new_mbid = ""
    mbid_match = False
    if type == "release-group":
        url = release_group_id_check % (server, database_mbid)
    elif type == "artist":
        url = artist_id_check % (server, database_mbid)
    htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
    if type == "release-group":
        match = re.search('''<release-group id="(.*?)"(?:.*?)>''', htmlsource)
        if match:
            new_mbid = match.group(1)
        else:
            match = re.search('''<release-group (?:.*?)id="(.*?)">''', htmlsource)
            if match:
                new_mbid = match.group(1)
            else:
                match = re.search('''<release-group ext:score=(?:.*?)id="(.*?)">''', htmlsource)
                if match:
                    new_mbid = match.group(1)
        if new_mbid == database_mbid:
            mbid_match = True
        else:
            mbid_match = False
    elif type == "artist":
        match = re.search('''<artist id="(.*?)"(?:.*?)>''', htmlsource)
        if match:
            new_mbid = match.group(1)
        else:
            match = re.search('''<artist(?:.*?)id="(.*?)">''', htmlsource)
            if match:
                new_mbid = match.group(1)
        if new_mbid == database_mbid:
            mbid_match = True
        else:
            mbid_match = False
    else:
        pass
    log("Current MBID: %s    New MBID: %s" % (database_mbid, new_mbid), xbmc.LOGDEBUG)
    if mbid_match:
        log("MBID is current. No Need to change", xbmc.LOGDEBUG)
    else:
        log("MBID is not current. Need to change", xbmc.LOGDEBUG)
    xbmc.sleep(mb_delay)
    return mbid_match, new_mbid
