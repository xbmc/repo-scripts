# -*- coding: utf-8 -*-

import re
from traceback import print_exc
from urllib import quote_plus

import xbmc
import cdam
import db

from utils import get_html_source, unescape, log, get_unicode, smart_unicode

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()

artist_url = '%s/ws/2/artist/?query=artist:"%s"&limit=%d'
alias_url = '%s/ws/2/artist/?query=alias:"%s"&limit=%d'
release_group_url = '%s/ws/2/release-group/'
release_group_url_artist = release_group_url + '?query="%s"%s AND artist:"%s"'
release_group_url_alias = release_group_url + '?query="%s"%s AND alias:"%s"'
nolive_nosingles = ' NOT type:single NOT type:live'
live_nosingles = ' NOT type:single'
query_limit = '&limit=%d'

release_group_url_using_release_name = '%s/ws/2/release-group/?query=release:"%s"%s AND artist:"%s"&limit=%d'
release_group_url_using_release_name_alias = '%s/ws/2/release-group/?query=release:"%s"%s AND alias:"%s"&limit=%d'
release_group_url_release_mbid = '%s/ws/2/release-group/?release=%s'
release_groups_url_artist_mbid = '%s/ws/2/release-group/?artist="%s"'
artist_id_check = '%s/ws/2/artist/%s'
release_group_id_check = '%s/ws/2/release-group/%s'

mb_delay = 910
server = 'http://musicbrainz.org'
if not __cfg__.use_musicbrainz():
    server = __cfg__.musicbrainz_server()
    mb_delay = __cfg__.mb_delay()
    if mb_delay < 1:
        mb_delay = 1
    mb_delay *= 100


def split_album_info(album_result, index):
    album = {}
    try:
        album["artist"] = album_result[index].releaseGroup.artist.name
        album["artist_id"] = album_result[index].releaseGroup.artist.id.replace("http://musicbrainz.org/artist/", "")
        album["id"] = album_result[index].releaseGroup.id.replace("http://musicbrainz.org/release-group/", "")
        album["title"] = album_result[index].releaseGroup.title
    except Exception as e:
        log(e.message)
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
    log("Retrieving MusicBrainz Release Group MBID from Album Release MBID")
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
    album["score"] = ""
    album["id"] = ""
    album["title"] = ""
    album["artist"] = ""
    album["artist_id"] = ""
    artist = smart_unicode(get_unicode(artist))
    album_title = smart_unicode(get_unicode(album_title))
    log("Artist: %s" % artist)
    log("Album: %s" % album_title)
    artist = artist.replace('"', '?')
    artist = artist.replace('&', 'and')
    album_title = album_title.replace('"', '?')
    album_title = album_title.replace('&', 'and')
    if limit == 1:
        url = None
        if not use_alias:
            url = release_group_url_artist % (
                server, quote_plus(album_title.encode("utf-8")), match_within, quote_plus(artist.encode("utf-8")))
            if not with_singles and not by_release and not use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles or Live albums",
                    xbmc.LOGDEBUG)
                url = url + nolive_nosingles + query_limit % limit
            elif not with_singles and not by_release and use_live:
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles")
                url = url + live_nosingles + query_limit % limit
            elif not by_release:
                log("Retrieving MusicBrainz Info - Checking by Artist - Including Singles and Live albums",
                    xbmc.LOGDEBUG)
                url += query_limit % limit
            elif not with_singles:
                log("Retrieving MusicBrainz Info - Checking by Artist - Using Release Name")
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
                log("Retrieving MusicBrainz Info - Checking by Artist - Not including Singles")
                url = url + live_nosingles + query_limit % limit
            elif not by_release:
                log("Retrieving MusicBrainz Info - Checking by Artist - Including Singles and Live albums",
                    xbmc.LOGDEBUG)
                url += query_limit % limit
            elif not with_singles:
                log("Retrieving MusicBrainz Info - Checking by Artist - Using Release Name")
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
            except Exception as e:
                log(e.message)
        if not album["id"]:
            xbmc.sleep(mb_delay)  # sleep for allowing proper use of webserver
            if not with_singles and not by_release and not use_alias and not use_live:
                log("No releases found on MusicBrainz, Checking For Live Album")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, False, False,
                                                      True)  # try again by using artist alias
            elif not with_singles and not by_release and not use_alias and use_live:
                log("No releases found on MusicBrainz, Checking by Artist Alias")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, False, True,
                                                      False)  # try again by using artist alias
            elif use_alias and not with_singles and not by_release and not use_live:
                log("No releases found on MusicBrainz, Checking by Release Name")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, True, False,
                                                      False)  # try again by using release name
            elif by_release and not with_singles and not use_alias:
                log("No releases found on MusicBrainz, Checking by Release name and Artist Alias")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, False, True, True,
                                                      False)  # try again by using release name and artist alias
            elif by_release and not with_singles and use_alias:
                log("No releases found on MusicBrainz, checking singles")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, True, False, False,
                                                      False)  # try again with singles
            elif with_singles and not use_alias and not by_release:
                log("No releases found on MusicBrainz, checking singles and Artist Alias")
                album, albums = get_musicbrainz_album(album_title, artist, 0, limit, True, False, True,
                                                      False)  # try again with singles and artist alias
            else:
                log("No releases found on MusicBrainz.")
                album["artist"], album["artist_id"], _ = get_musicbrainz_artist_id(artist)
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
                    album = {"score": "", "id": "", "title": "", "artist": "", "artist_id": ""}
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
                        log("Score     : %s" % album["score"])
                        log("Title     : %s" % album["title"])
                        log("Id        : %s" % album["id"])
                        log("Artist    : %s" % album["artist"])
                        log("Artist ID : %s" % album["artist_id"])
                        albums.append(album)
                    except Exception as e:
                        log(e.message, xbmc.LOGERROR)
                        print_exc()

            else:
                pass
        else:
            pass
    xbmc.sleep(mb_delay)  # sleep for allowing proper use of webserver
    return album, albums


def get_musicbrainz_artists(artist_search, limit=1):
    log("Artist: %s" % artist_search)
    artists = []
    artist_name = smart_unicode((artist_search.replace('"', '?').replace('&', 'and')))
    url = artist_url % (server, quote_plus(artist_name.encode("utf-8")), limit)
    htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
    match = re.findall('''<artist(.*?)</artist>''', htmlsource)
    if match:
        for item in match:
            artist = {"score": "", "name": "", "id": "", "sortname": ""}
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
            log("Score     : %s" % artist["score"])
            log("Id        : %s" % artist["id"])
            log("Name      : %s" % artist["name"])
            log("Sort Name : %s" % artist["sortname"])
            artists.append(artist)
    else:
        log("No Artist ID found for Artist: %s" % repr(artist_search))
    xbmc.sleep(mb_delay)
    return artists


def get_musicbrainz_artist_id(artist_search, limit=1, alias=False):
    name = ""
    id_ = ""
    score = ""
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
            id_ = id_match.group(1)
        if sort_name_match:
            sortname = unescape(smart_unicode(sort_name_match.group(1)))
        log("Score     : %s" % score)
        log("Id        : %s" % id_)
        log("Name      : %s" % name)
        log("Sort Name : %s" % sortname)
    else:
        if not alias:
            log("No Artist ID found trying aliases: %s" % artist_search)
            name, id_, sortname = get_musicbrainz_artist_id(artist_search, limit, True)
        else:
            log("No Artist ID found for Artist: %s" % artist_search)
    xbmc.sleep(mb_delay)
    return name, id_, sortname


def update_musicbrainz_id(type_, info):
    log("Updating MusicBrainz ID")
    artist_id = ""
    try:
        if type_ == "artist":  # available data info["local_id"], info["name"], info["distant_id"]
            _, artist_id, _ = get_musicbrainz_artist_id(info["name"])
            db.set_artist_mbid(artist_id, info["name"])
        if type_ == "album":
            album, _ = get_musicbrainz_album(info["title"], info["artist"], 0)
            db.set_album_mbid(album["id"], info["title"])
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return artist_id


def mbid_check(database_mbid, type_):
    log("Looking up %s MBID. Current MBID: %s" % (type_, database_mbid), xbmc.LOGNOTICE)
    new_mbid = ""
    mbid_match = False
    url = None
    if type_ == "release-group":
        url = release_group_id_check % (server, database_mbid)
    elif type_ == "artist":
        url = artist_id_check % (server, database_mbid)
    htmlsource = get_html_source(url, "", save_file=False, overwrite=False)
    if type_ == "release-group":
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
        mbid_match = bool(new_mbid == database_mbid)
    elif type_ == "artist":
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
    log("Current MBID: %s    New MBID: %s" % (database_mbid, new_mbid))
    if mbid_match:
        log("MBID is current. No Need to change")
    else:
        log("MBID is not current. Need to change")
    xbmc.sleep(mb_delay)
    return mbid_match, new_mbid
