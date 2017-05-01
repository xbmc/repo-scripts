# -*- coding: utf-8 -*-

import datetime
import os
import re
import time
import traceback

import sqlite3 as sql
from sqlite3 import Error as SQLError

import xbmc
import xbmcvfs

import cdam
from cdam import Def, ArtType, FileName

from mb_utils import get_musicbrainz_artist_id, get_musicbrainz_album, mbid_check, \
    get_musicbrainz_release_group
from utils import get_unicode, log, dialog_msg
from jsonrpc_calls import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()
__lng__ = __cdam__.getLocalizedString


def connect():
    return sql.connect(__cdam__.file_addon_db())


def upgrade_db(from_version):
    log("Found database version %s, upgrading to current" % from_version, xbmc.LOGNOTICE)
    # there is no upgrade path at the moment


def user_updates(details, type_):
    log("Storing User edit", xbmc.LOGNOTICE)
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        CREATE table IF NOT EXISTS artist_updates(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT)
    """)
    c.execute("""\
        CREATE table IF NOT EXISTS album_updates(album_id INTEGER, title TEXT, artist TEXT, path TEXT,
        musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)
    """)

    if type_ == "artist":
        log("Storing artist update", xbmc.LOGNOTICE)
        try:
            c.execute("""\
                SELECT DISTINCT musicbrainz_artistid FROM artist_updates WHERE local_id=?
            """, (details["local_id"],))
            db_details = c.fetchall()
            if db_details:
                log("Updating existing artist edit", xbmc.LOGNOTICE)
                c.execute("""\
                    UPDATE artist_updates SET musicbrainz_artistid=?, name=? WHERE local_id=?
                """, (details["musicbrainz_artistid"], details["name"], details["local_id"]))
            else:
                log("Storing new artist edit", xbmc.LOGNOTICE)
                c.execute("""\
                    INSERT INTO artist_updates(local_id, name, musicbrainz_artistid) values (?, ?, ?)
                """, (details["local_id"], details["name"], details["musicbrainz_artistid"]))
        except SQLError:
            log("Error updating artist_updates table", xbmc.LOGERROR)
            traceback.print_exc()
        try:
            c.execute("""\
                UPDATE lalist SET musicbrainz_artistid=?, name=? WHERE local_id=?
            """, (details["musicbrainz_artistid"], details["name"], details["local_id"]))
        except SQLError:
            log("Error updating album artist table", xbmc.LOGERROR)
            traceback.print_exc()
        try:
            c.execute("""\
                UPDATE alblist SET musicbrainz_artistid=?, artist=? WHERE artist=?
            """, (details["musicbrainz_artistid"], details["name"], details["name"]))
        except SQLError:
            log("Error updating album table", xbmc.LOGERROR)
            traceback.print_exc()
        try:
            c.execute("""\
                UPDATE local_artists SET musicbrainz_artistid=?, name=? WHERE local_id=?
            """, (details["musicbrainz_artistid"], details["name"], details["local_id"]))
        except SQLError:
            log("Error updating local artist table", xbmc.LOGERROR)
            traceback.print_exc()
    if type_ == "album":
        log("Storing album update", xbmc.LOGNOTICE)
        try:
            c.execute("""\
                SELECT DISTINCT album_id FROM album_updates WHERE album_id=? and path=?
            """, (details["local_id"], get_unicode(details["path"])))
            db_details = c.fetchall()
            print db_details
            if db_details:
                log("Updating existing album edit", xbmc.LOGNOTICE)
                c.execute("""\
                    UPDATE album_updates SET artist=?, title=?, musicbrainz_albumid=?,
                    musicbrainz_artistid=? WHERE album_id=? and path=?
                """, (get_unicode(details["artist"]), get_unicode(details["title"]), details["musicbrainz_albumid"],
                      details["musicbrainz_artistid"], details["local_id"], get_unicode(details["path"])))
            else:
                log("Storing new album edit", xbmc.LOGNOTICE)
                c.execute("""\
                    INSERT INTO album_updates(album_id, title, artist, path, musicbrainz_albumid, musicbrainz_artistid)
                    values (?, ?, ?, ?, ?, ?)
                """, (details["local_id"], get_unicode(details["title"]), get_unicode(details["artist"]),
                      get_unicode(details["path"]), details["musicbrainz_albumid"], details["musicbrainz_artistid"]))
        except SQLError:
            log("Error updating album_updates table", xbmc.LOGERROR)
            traceback.print_exc()
        try:
            c.execute("""\
                UPDATE alblist SET artist=?, title=?, musicbrainz_albumid=?, musicbrainz_artistid=?
                WHERE album_id=? and path=?
            """, (get_unicode(details["artist"]), get_unicode(details["title"]), details["musicbrainz_albumid"],
                  details["musicbrainz_artistid"], details["local_id"], get_unicode(details["path"])))
        except SQLError:
            log("Error updating album table", xbmc.LOGERROR)
            traceback.print_exc()
    conn.commit()
    c.close()


def restore_user_updates():
    try:
        conn = connect()
        c = conn.cursor()
        c.execute("""\
            UPDATE lalist SET
                musicbrainz_artistid =
                    (SELECT artist_updates.musicbrainz_artistid FROM artist_updates
                     WHERE artist_updates.local_id = lalist.local_id )
                WHERE EXISTS ( SELECT * FROM artist_updates WHERE artist_updates.name = lalist.name )
        """)
        c.execute("""\
            UPDATE local_artists SET
                musicbrainz_artistid =
                    (SELECT artist_updates.musicbrainz_artistid FROM artist_updates
                     WHERE artist_updates.local_id = local_artists.local_id )
                WHERE EXISTS ( SELECT * FROM artist_updates WHERE artist_updates.name = local_artists.name )
        """)
        c.execute("""\
            UPDATE alblist SET
                musicbrainz_artistid =
                    (SELECT album_updates.musicbrainz_artistid FROM album_updates
                     WHERE album_updates.album_id = alblist.album_id )
                WHERE EXISTS ( SELECT * FROM album_updates WHERE album_updates.album_id = alblist.album_id )
        """)
        c.execute("""\
            UPDATE alblist SET
                musicbrainz_albumid =
                    (SELECT album_updates.musicbrainz_albumid FROM album_updates
                    WHERE album_updates.album_id = alblist.album_id )
                WHERE EXISTS ( SELECT * FROM album_updates WHERE album_updates.album_id = alblist.album_id )
        """)
        conn.commit()
        c.close()
    except SQLError:
        traceback.print_exc()


def artist_list_to_string(artist):
    if not isinstance(artist, list):
        artist_string = artist
    else:
        if len(artist) > 1:
            artist_string = " / ".join(artist)
        else:
            artist_string = "".join(artist)
    return artist_string


def artwork_search(cdart_url, id_, disc, type_):
    log("Finding Artwork")
    art = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id_:
            if type_ == "cover":
                art = item
                break
            elif int(item["disc"]) == int(disc) and type_ == ArtType.CDART:
                art = item
                break
    return art


def get_xbmc_database_info(background=False):
    log("Retrieving Album Info from XBMC's Music DB")
    dialog_msg("create", heading=__lng__(32021), line1=__lng__(32105), background=background)
    album_list, total = retrieve_album_list()
    if not album_list:
        dialog_msg("close", background=background)
        return None
    album_detail_list = retrieve_album_details_full(album_list, total, background=background, simple=False,
                                                    update=False)
    dialog_msg("close", background=background)
    return album_detail_list


def retrieve_album_details_full(album_list, total, background=False, simple=False, update=False):
    log("Retrieving Album Details")
    album_detail_list = []
    album_count = 0
    try:
        for detail in album_list:
            if not detail["title"] and detail["label"]:  # check to see if title is empty and label contains something
                detail["title"] = detail["label"]
            if dialog_msg("iscanceled", background=background):
                break
            album_count += 1
            percent = int((album_count / float(total)) * 100) if float(total) > 0 else 100
            dialog_msg("update", percent=percent, line1=__lng__(20186),
                       line2="%s: %s" % (__lng__(32138), (get_unicode(detail['title']))),
                       line3="%s #:%6s      %s%6s" % (__lng__(32039), album_count, __lng__(32045), total),
                       background=background)
            try:
                album_id = detail['local_id']
            except KeyError:
                album_id = detail['albumid']
            albumdetails = retrieve_album_details(album_id)
            if not albumdetails:
                continue
            for album in albumdetails:
                if dialog_msg("iscanceled", background=background):
                    break
                previous_path = ""
                mbid_match = False
                albumrelease_mbid = ""
                albumartist_mbid = ""
                if not update:
                    paths, albumartistmbids, albumreleasembids = get_album_path(album_id)
                    if albumartistmbids:
                        albumartist_mbid = albumartistmbids[0]
                        for albumartistmbid in albumartistmbids:
                            if albumartist_mbid == albumartistmbid:
                                mbid_match = True
                                log("Found an Artist MBID in the Database: %s" % albumartist_mbid)
                                continue
                            else:
                                mbid_match = False
                        if not mbid_match:
                            albumartist_mbid = ""
                    if albumreleasembids:
                        albumrelease_mbid = albumreleasembids[0]
                        log("Found an Album Release MBID in the Database: %s" % albumrelease_mbid)
                    if not paths:
                        continue
                else:
                    paths = [detail['path']]
                for path in paths:
                    try:
                        if dialog_msg("iscanceled", background=background):
                            break
                        album_artist = {}
                        if path == previous_path:
                            continue
                        else:
                            # Helix: paths MUST end with trailing slash
                            if xbmcvfs.exists(os.path.join(path, '')):
                                log("Path Exists")
                                try:
                                    album_artist["local_id"] = detail['local_id']  # for database update
                                except KeyError:
                                    album_artist["local_id"] = detail['albumid']
                                title = detail['title']
                                album_artist["artist"] = get_unicode(
                                    artist_list_to_string(album['artist']).split(" / ")[0])
                                album_artist["path"] = get_unicode(path)
                                album_artist[ArtType.CDART] = xbmcvfs.exists(
                                    os.path.join(path, FileName.CDART).replace("\\\\", "\\"))
                                album_artist[ArtType.COVER] = xbmcvfs.exists(
                                    os.path.join(path, FileName.FOLDER).replace("\\\\", "\\"))
                                previous_path = path
                                path_match = re.search("(?:\\\\|/| - )(?:disc|cd)(?:\s|-|_|)([0-9]{0,3})",
                                                       path.replace("\\\\", "\\"), re.I)
                                title_match = re.search(
                                    "(.*?)(?:[\s]|[(]|[\s][(])(?:disc|cd)(?:[\s]|)([0-9]{0,3})(?:[)]?.*?)", title,
                                    re.I)
                                if title_match:
                                    if len(title_match.groups()) > 1:
                                        if title_match.group(2):
                                            log("Title has CD count")
                                            log("    Disc %s" % title_match.group(2))
                                            album_artist["disc"] = int(title_match.group(2))
                                            album_artist["title"] = get_unicode(
                                                (title_match.group(1).replace(" -", "")).rstrip())
                                        else:
                                            if path_match:
                                                if len(path_match.groups()) > 0:
                                                    if path_match.group(1):
                                                        log("Path has CD count")
                                                        log("    Disc %s" % repr(path_match.group(1)))
                                                        album_artist["disc"] = int(path_match.group(1))
                                                    else:
                                                        album_artist["disc"] = 1
                                                else:
                                                    album_artist["disc"] = 1
                                            else:
                                                album_artist["disc"] = 1
                                            album_artist["title"] = get_unicode((title.replace(" -", "")).rstrip())
                                    else:
                                        if path_match:
                                            if len(path_match.groups()) > 0:
                                                if path_match.group(1):
                                                    log("Path has CD count")
                                                    log("    Disc %s" % repr(path_match.group(1)))
                                                    album_artist["disc"] = int(path_match.group(1))
                                                else:
                                                    album_artist["disc"] = 1
                                            else:
                                                album_artist["disc"] = 1
                                        else:
                                            album_artist["disc"] = 1
                                        album_artist["title"] = get_unicode((title.replace(" -", "")).rstrip())
                                else:
                                    if path_match:
                                        if len(path_match.groups()) > 0:
                                            if path_match.group(1):
                                                log("Path has CD count")
                                                log("    Disc %s" % repr(path_match.group(1)))
                                                album_artist["disc"] = int(path_match.group(1))
                                            else:
                                                album_artist["disc"] = 1
                                        else:
                                            album_artist["disc"] = 1
                                    else:
                                        album_artist["disc"] = 1
                                    album_artist["title"] = get_unicode((title.replace(" -", "")).rstrip())
                                log("Album Title: %s" % album_artist["title"])
                                log("Album Artist: %s" % album_artist["artist"])
                                log("Album ID: %s" % album_artist["local_id"])
                                log("Album Path: %s" % album_artist["path"])
                                log("cdART Exists?: %s" % ("False", "True")[album_artist[ArtType.CDART]])
                                log("Cover Art Exists?: %s" % ("False", "True")[album_artist[ArtType.COVER]])
                                log("Disc #: %s" % album_artist["disc"])
                                if not simple:
                                    album_artist["musicbrainz_artistid"] = ""
                                    album_artist["musicbrainz_albumid"] = ""
                                    if albumartist_mbid:
                                        album_artist["musicbrainz_artistid"] = albumartist_mbid
                                    if albumrelease_mbid:
                                        album_artist["musicbrainz_albumid"] = get_musicbrainz_release_group(
                                            albumrelease_mbid)
                                    if not album_artist["musicbrainz_albumid"]:
                                        try:
                                            musicbrainz_albuminfo, _ = get_musicbrainz_album(
                                                album_artist["title"], album_artist["artist"], 0, 1)
                                            album_artist["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
                                            album_artist["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
                                        except Exception as e:
                                            log(e.message, xbmc.LOGERROR)
                                            traceback.print_exc()
                                    log("MusicBrainz AlbumId: %s" % album_artist["musicbrainz_albumid"])
                                    log("MusicBrainz ArtistId: %s" % album_artist["musicbrainz_artistid"],
                                        xbmc.LOGDEBUG)
                                album_detail_list.append(album_artist)

                            else:
                                log("Path does not exist: %s" % repr(path))
                                continue
                    except Exception as e:
                        log("Error Occured")
                        log("Title: %s" % detail['title'])
                        log("Path: %s" % path)
                        log(e.message, xbmc.LOGERROR)
                        traceback.print_exc()
    except Exception as e:
        log("Error Occured")
        log(e.message, xbmc.LOGERROR)
        traceback.print_exc()
        dialog_msg("close", background=background)
    return album_detail_list


def get_album_cdart(album_path):
    log("Retrieving cdART status")
    return bool(xbmcvfs.exists(os.path.join(album_path, FileName.CDART).replace("\\\\", "\\")))


def get_album_coverart(album_path):
    log("Retrieving cover art status")
    return bool(xbmcvfs.exists(os.path.join(album_path, FileName.FOLDER).replace("\\\\", "\\")))


def store_alblist(local_album_list, background=False):
    log("Storing alblist")
    album_count = 0
    cdart_existing = 0
    conn = connect()
    c = conn.cursor()
    percent = 0
    try:
        for album in local_album_list:
            dialog_msg("update", percent=percent, line1=__lng__(20186),
                       line2="%s: %s" % (__lng__(32138), get_unicode(album["title"])),
                       line3="%s%6s" % (__lng__(32100), album_count), background=background)
            log("Album Count: %s" % album_count)
            log("Album ID: %s" % album["local_id"])
            log("Album Title: %s" % album["title"])
            log("Album Artist: %s" % album["artist"])
            log("Album Path: %s" % album["path"].replace("\\\\", "\\"))
            log("cdART Exist?: %s" % ("False", "True")[album["cdart"]])
            log("Cover Art Exist?: %s" % ("False", "True")[album["cover"]])
            log("Disc #: %s" % album["disc"])
            log("MusicBrainz AlbumId: %s" % album["musicbrainz_albumid"])
            log("MusicBrainz ArtistId: %s" % album["musicbrainz_artistid"])
            try:
                if album["cdart"]:
                    cdart_existing += 1
                album_count += 1
                c.execute("""\
                    insert into
                        alblist(
                            album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (album["local_id"], get_unicode(album["title"]), get_unicode(album["artist"]),
                      get_unicode(album["path"].replace("\\\\", "\\")), ("False", "True")[album["cdart"]],
                      ("False", "True")[album["cover"]], album["disc"], album["musicbrainz_albumid"],
                      album["musicbrainz_artistid"]))
            except Exception as e:
                log("Error Saving to Database")
                log(e.message, xbmc.LOGERROR)
                traceback.print_exc()
            if dialog_msg("iscanceled", background=background):
                break
    except Exception as e:
        log("Error Saving to Database")
        log(e.message, xbmc.LOGERROR)
        traceback.print_exc()
    conn.commit()
    c.close()
    log("Finished Storing ablist")
    return album_count, cdart_existing


def recount_cdarts():
    log("Recounting cdARTS")
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        SELECT count(*) FROM alblist where cdart='True'
    """)
    db = c.fetchone()
    cdart_existing = db[0]
    c.close()
    return cdart_existing


def store_lalist(local_artist_list):
    log("Storing lalist")
    conn = connect()
    c = conn.cursor()
    artist_count = 0
    c.execute("""\
        DROP table IF EXISTS lalist
    """)
    # create local artists database
    c.execute("""\
        CREATE TABLE lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    for artist in local_artist_list:
        try:
            try:
                c.execute("""\
                    insert into lalist(local_id, name, musicbrainz_artistid, fanarttv_has_art) values (?, ?, ?, ?)
                """, (artist["local_id"], unicode(artist["name"], 'utf-8'), artist["musicbrainz_artistid"],
                      artist["has_art"]))
            except TypeError:
                c.execute("""\
                    insert into lalist(local_id, name, musicbrainz_artistid, fanarttv_has_art) values (?, ?, ?, ?)
                """, (artist["local_id"], get_unicode(artist["name"]), artist["musicbrainz_artistid"],
                      artist["has_art"]))
            except Exception as e:
                log(e.message, xbmc.LOGERROR)
                traceback.print_exc()
            artist_count += 1
        except Exception as e:
            log(e.message, xbmc.LOGERROR)
            traceback.print_exc()
    conn.commit()
    c.close()
    log("Finished Storing lalist")
    return artist_count


def retrieve_fanarttv_datecode():
    conn_l = connect()
    c = conn_l.cursor()
    c.execute("""\
        SELECT datecode FROM counts
    """)
    result = c.fetchall()
    c.close()
    datecode = result[0][0]
    return datecode


def store_fanarttv_datecode(datecode):
    local_artist_count, album_count, artist_count, cdart_existing = new_local_count()
    store_counts(local_artist_count, artist_count, album_count, cdart_existing, datecode=datecode)


def retrieve_distinct_album_artists():
    log("Retrieving Distinct Album Artist")
    album_artists = []
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        SELECT DISTINCT artist, musicbrainz_artistid FROM alblist
    """)
    db = c.fetchall()
    for item in db:
        artist = {"name": get_unicode(item[0]), "musicbrainz_artistid": get_unicode(item[1])}
        album_artists.append(artist)
    c.close()
    log("Finished Retrieving Distinct Album Artists")
    return album_artists


def store_counts(local_artists_count, artist_count, album_count, cdart_existing, datecode=0):
    log("Storing Counts", xbmc.LOGNOTICE)
    log("    Album Count: %s" % album_count, xbmc.LOGNOTICE)
    log("    Album Artist Count: %s" % artist_count, xbmc.LOGNOTICE)
    log("    Local Artist Count: %s" % local_artists_count, xbmc.LOGNOTICE)
    log("    cdARTs Existing Count: %s" % cdart_existing, xbmc.LOGNOTICE)
    log("    Unix Date Code: %s" % datecode, xbmc.LOGNOTICE)
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("""\
            DROP table IF EXISTS counts
        """)
    except sql.Error:
        # table missing
        traceback.print_exc()
    try:
        c.execute("""\
            CREATE TABLE counts(local_artists INTEGER, artists INTEGER,
                                albums INTEGER, cdarts INTEGER, version TEXT, datecode INTEGER)
        """)
    except SQLError:
        traceback.print_exc()
    if datecode == 0:
        c.execute("""\
            insert into counts(local_artists, artists, albums, cdarts, version) values (?, ?, ?, ?, ?)
        """, (local_artists_count, artist_count, album_count, cdart_existing, Def.DB_VERSION))
    else:
        c.execute("""\
            insert into counts(local_artists, artists, albums, cdarts, version, datecode) values (?, ?, ?, ?, ?, ?)
        """, (local_artists_count, artist_count, album_count, cdart_existing, Def.DB_VERSION, datecode))
    conn.commit()
    c.close()
    log("Finished Storing Counts")


def check_local_albumartist(album_artist, local_artist_list, background=False):
    log("Checking Local Artists", xbmc.LOGNOTICE)
    artist_count = 0
    percent = 0
    local_album_artist_list = []
    for artist in album_artist:  # match album artist to local artist id
        album_artist_1 = {}
        name = get_unicode(artist_list_to_string(artist["name"]))
        artist_count += 1
        id_ = None
        for local in local_artist_list:
            dialog_msg("update", percent=percent, line1=__lng__(20186), line2="%s" % __lng__(32101),
                       line3="%s:%s" % (__lng__(32038), (get_unicode(artist_list_to_string(local["artist"])))),
                       background=background)
            if dialog_msg("iscanceled", background=background):
                break
            if name == get_unicode(artist_list_to_string(local["artist"])):
                id_ = local["artistid"]
                break
        if id_ is not None:
            album_artist_1["name"] = name  # store name and
            album_artist_1["local_id"] = id_  # local id
            album_artist_1["musicbrainz_artistid"] = artist["musicbrainz_artistid"]
            album_artist_1["has_art"] = "False"
            local_album_artist_list.append(album_artist_1)
        else:
            log("Artist Not Found:")
            try:
                log(repr(artist_list_to_string(artist["name"])))
            except Exception as e:
                log(e.message, xbmc.LOGERROR)
                traceback.print_exc()
    return local_album_artist_list, artist_count


def database_setup(background=False):
    cdart_existing = 0
    album_count = 0
    artist_count = 0
    local_artist_count = 0
    log("Setting Up Database")
    log("    addon_work_path: %s" % __cdam__.path_profile())
    if not xbmcvfs.exists(os.path.join(__cdam__.path_profile(), "settings.xml")):
        dialog_msg("ok", heading=__lng__(32071), line1=__lng__(32072), line2=__lng__(32073),
                   background=background)
        log("Settings not set, aborting database creation")
        return album_count, artist_count, cdart_existing
    local_album_list = get_xbmc_database_info(background=background)
    if not local_album_list:
        dialog_msg("ok", heading=__lng__(32130), line1=__lng__(32131), background=background)
        log("XBMC Music Library does not exist, aborting database creation")
        return album_count, artist_count, cdart_existing
    dialog_msg("create", heading=__lng__(32021), line1=__lng__(20186), background=background)
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        CREATE TABLE counts(local_artists INTEGER, artists INTEGER, albums INTEGER,
                            cdarts INTEGER, version TEXT, datecode INTEGER)
    """)
    # create local album artists database
    c.execute("""\
        CREATE TABLE lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    # create local album database
    c.execute("""\
        CREATE TABLE alblist(album_id INTEGER, title TEXT, artist TEXT, path TEXT, cdart TEXT,
                             cover TEXT, disc INTEGER, musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)
    """)
    # create unique database
    c.execute("""\
        CREATE TABLE unqlist(title TEXT, disc INTEGER, artist TEXT, path TEXT, cdart TEXT)
    """)
    c.execute("""\
        CREATE TABLE local_artists(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    conn.commit()
    c.close()
    store_counts(0, 0, 0, 0)
    album_count, cdart_existing = store_alblist(local_album_list, background=background)  # store album details first
    album_artist = retrieve_distinct_album_artists()  # then retrieve distinct album artists
    local_artist_list = get_all_local_artists()  # retrieve local artists(to get idArtist)
    local_album_artist_list, artist_count = check_local_albumartist(album_artist, local_artist_list,
                                                                    background=background)
    store_lalist(local_album_artist_list)  # then store in database
    if __cfg__.enable_all_artists():
        local_artist_count = build_local_artist_table(background=background)
    store_counts(local_artist_count, artist_count, album_count, cdart_existing)
    if dialog_msg("iscanceled", background=background):
        dialog_msg("close", background=background)
        dialog_msg("ok", heading=__lng__(32050), line1=__lng__(32051), line2=__lng__(32052),
                   line3=__lng__(32053), background=background)
    log("Finished Storing Database")
    dialog_msg("close", background=background)
    return album_count, artist_count, cdart_existing


# retrieve the addon's database - saves time by no needing to search system for infomation on every addon access
def get_local_albums_db(artist_name, background=False):
    log("Retrieving Local Albums Database")
    local_album_list = []
    conn_l = connect()
    c = conn_l.cursor()
    try:
        if artist_name == "all artists":
            dialog_msg("create", heading=__lng__(32102), line1=__lng__(20186), background=background)
            c.execute("""\
                SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid,
                musicbrainz_artistid FROM alblist ORDER BY artist, title ASC
            """)
        else:
            try:
                c.execute("""\
                    SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid,
                    musicbrainz_artistid FROM alblist WHERE artist=? ORDER BY title ASC
                """, (artist_name,))
            except SQLError:
                try:
                    c.execute("""\
                        SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid,
                        musicbrainz_artistid FROM alblist WHERE artist=? ORDER BY title ASC
                    """, (artist_name,))
                except SQLError:
                    c.execute("""\
                        SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid,
                        musicbrainz_artistid FROM alblist WHERE artist=? ORDER BY title ASC
                    """, (artist_name,))
            except Exception as e:
                log(e.message, xbmc.LOGERROR)
                traceback.print_exc()
        db = c.fetchall()
        c.close()
        for item in db:
            album = {"local_id": (item[0]), "title": get_unicode(item[1]), "artist": get_unicode(item[2]),
                     "path": get_unicode(item[3]).replace('"', ''), "cdart": eval(get_unicode(item[4])),
                     "cover": eval(get_unicode(item[5])), "disc": (item[6]),
                     "musicbrainz_albumid": get_unicode(item[7]), "musicbrainz_artistid": get_unicode(item[8])}
            # print album
            local_album_list.append(album)
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        traceback.print_exc()
        dialog_msg("close", background=background)
    # log( local_album_list )
    if artist_name == "all artists":
        dialog_msg("close", background=background)
    log("Finished Retrieving Local Albums from Database")
    return local_album_list


def get_local_artists_db(mode="album_artists"):
    local_artist_list = []
    if mode == "album_artists":
        log("Retrieving Local Album Artists from Database")
        query = """\
            SELECT DISTINCT local_id, name, musicbrainz_artistid, fanarttv_has_art FROM lalist ORDER BY name ASC
        """
    else:
        log("Retrieving All Local Artists from Database")
        query = """\
            SELECT DISTINCT local_id, name, musicbrainz_artistid, fanarttv_has_art FROM local_artists ORDER BY name ASC
        """
    conn_l = connect()
    c = conn_l.cursor()
    try:
        c.execute(query)
        db = c.fetchall()
        c.close()
        for item in db:
            artists = {"local_id": (item[0]), "name": get_unicode(item[1]),
                       "musicbrainz_artistid": get_unicode(item[2])}
            if not item[3]:
                artists["has_art"] = "False"
            else:
                artists["has_art"] = (item[3])
            local_artist_list.append(artists)
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        traceback.print_exc()
    return local_artist_list


def store_local_artist_table(artist_list, background=False):
    count = 0
    conn = connect()
    c = conn.cursor()
    dialog_msg("create", heading=__lng__(32124), line1=__lng__(20186), background=background)
    c.execute("""\
        DROP table IF EXISTS local_artists
    """)
    # create local artists database
    c.execute("""\
        CREATE TABLE local_artists(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    for artist in artist_list:
        percent = int((count / float(len(artist_list))) * 100) if len(artist_list) > 0 else 100
        dialog_msg("update", percent=percent, line1=__lng__(32124),
                   line2="%s%s" % (__lng__(32125), artist["local_id"]),
                   line3="%s%s" % (__lng__(32028), get_unicode(artist["name"])), background=background)
        try:
            c.execute("""\
                insert into local_artists(local_id, name, musicbrainz_artistid, fanarttv_has_art) values (?, ?, ?, ?)
            """, (artist["local_id"], get_unicode(artist["name"]), artist["musicbrainz_artistid"], artist["has_art"]))
            count += 1
        except KeyError:
            c.execute("""\
                insert into local_artists(local_id, name, musicbrainz_artistid, fanarttv_has_art) values (?, ?, ?, ?)
            """, (artist["local_id"], get_unicode(artist["name"]), artist["musicbrainz_artistid"], "False"))
            count += 1
        except Exception as e:
            log(e.message, xbmc.LOGERROR)
            traceback.print_exc()
    conn.commit()
    dialog_msg("close", background=background)
    c.close()
    return count


def build_local_artist_table(background=False):
    log("Retrieving All Local Artists From XBMC")
    new_local_artist_list = []
    local_artist_list = get_all_local_artists()
    local_album_artist_list = get_local_artists_db()
    count = 1
    total = len(local_artist_list)
    conn = connect()
    c = conn.cursor()
    dialog_msg("create", heading=__lng__(32124), line1=__lng__(20186), background=background)
    try:
        for local_artist in local_artist_list:
            if dialog_msg("iscanceled", background=background):
                break
            artist = {}
            percent = int((count / float(total)) * 100) if float(total) > 0 else 100
            dialog_msg("update", percent=percent, line1=__lng__(20186),
                       line2="%s: %s" % (__lng__(32125), local_artist["artistid"]), line3="%s: %s" % (
                    __lng__(32137), get_unicode(artist_list_to_string(local_artist["artist"]))),
                       background=background)
            count += 1
            for album_artist in local_album_artist_list:
                if dialog_msg("iscanceled", background=background):
                    break
                if local_artist["artistid"] == album_artist["local_id"]:
                    artist["name"] = get_unicode(artist_list_to_string(local_artist["artist"]))
                    artist["local_id"] = local_artist["artistid"]
                    artist["musicbrainz_artistid"] = album_artist["musicbrainz_artistid"]
                    artist["has_art"] = album_artist["has_art"]
                    break
            if not artist:
                try:
                    artist["name"] = get_unicode(artist_list_to_string(local_artist["artist"]))
                    _, artist["musicbrainz_artistid"], _ = get_musicbrainz_artist_id(
                        get_unicode(artist_list_to_string(local_artist["artist"])))
                except Exception as e:
                    log(e.message)
                    artist["name"] = get_unicode(artist_list_to_string(local_artist["artist"]))
                    _, artist["musicbrainz_artistid"], _ = get_musicbrainz_artist_id(
                        artist_list_to_string(local_artist["artist"]))
                artist["local_id"] = artist_list_to_string(local_artist["artistid"])
                artist["has_art"] = "False"
            new_local_artist_list.append(artist)
        store_local_artist_table(new_local_artist_list, background=background)
        dialog_msg("close", background=background)
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        log("Problem with making all artists table")
        traceback.print_exc()
        dialog_msg("close", background=background)
    c.close()
    return count


# retrieves counts for local album, artist and cdarts
def new_local_count():
    log("Counting Local Artists, Albums and cdARTs")
    conn_l = connect()
    c = conn_l.cursor()
    try:
        local_artist_count = 0
        album_artist = 0
        album_count = 0
        cdart_existing = recount_cdarts()

        c.execute("""\
            SELECT local_artists, artists, albums, cdarts FROM counts
        """)
        counts = c.fetchall()
        c.close()
        for item in counts:
            local_artist_count = item[0]
            album_artist = item[1]
            album_count = item[2]
        return local_artist_count, album_count, album_artist, cdart_existing
    except UnboundLocalError:
        log("Counts Not Available in Local DB, Rebuilding DB")
        c.close()
        return 0, 0, 0, 0


# user call from Advanced menu to refresh the addon's database
def refresh_db(background=False):
    log("Refreshing Local Database")
    local_album_count = 0
    local_artist_count = 0
    local_cdart_count = 0
    if xbmcvfs.exists(__cdam__.file_addon_db()):
        # File exists needs to be deleted
        if not background:
            db_delete = dialog_msg("yesno", line1=__lng__(32042), line2=__lng__(32015), background=background)
        else:
            db_delete = True
        if db_delete:
            if xbmcvfs.exists(__cdam__.file_addon_db()):
                # backup database
                backup_database()
                try:
                    # try to delete exsisting database
                    xbmcvfs.delete(__cdam__.file_addon_db())
                except Exception as e:
                    log(e.message, xbmc.LOGERROR)
                    log("Unable to delete Database")
            if xbmcvfs.exists(__cdam__.file_addon_db()):
                # if database file still exists even after trying to delete it. Wipe out its contents
                conn = connect()
                c = conn.cursor()
                c.execute("""\
                    DROP table IF EXISTS counts
                """)
                c.execute("""\
                    DROP table IF EXISTS lalist
                """)  # drop local album artists database
                c.execute("""\
                    DROP table IF EXISTS alblist
                """)  # drop local album database
                c.execute("""\
                    DROP table IF EXISTS unqlist
                """)  # drop unique database
                c.execute("""\
                    DROP table IF EXISTS local_artists
                """)
                conn.commit()
                c.close()
            local_album_count, local_artist_count, local_cdart_count = database_setup(background=background)
        else:
            pass
    else:
        # If file does not exist and some how the program got here, create new database
        local_album_count, local_artist_count, local_cdart_count = database_setup(background=background)
    # update counts
    log("Finished Refeshing Database")
    return local_album_count, local_artist_count, local_cdart_count


def check_album_mbid(albums, background=False):
    updated_albums = []
    canceled = False
    count = 0
    if not background:
        dialog_msg("create", heading=__lng__(32150))
        xbmc.sleep(500)
    if not albums:
        albums = get_local_albums_db("all artists", background)
    for album in albums:
        update_album = album
        percent = int((count / float(len(albums))) * 100) if len(albums) > 0 else 100
        if percent < 1:
            percent = 1
        if percent > 100:
            percent = 100
        count += 1
        if dialog_msg("iscanceled", background=background):
            canceled = True
            break
        dialog_msg("update", percent=percent, line1=__lng__(32150),
                   line2="%s: %s" % (__lng__(32138), get_unicode(album["title"])),
                   line3="%s: %s" % (__lng__(32137), get_unicode(album["artist"])), background=background)
        if album["musicbrainz_albumid"]:
            mbid_match, current_mbid = mbid_check(album["musicbrainz_albumid"], "release-group")
            if not mbid_match:
                update_album["musicbrainz_albumid"] = current_mbid
        updated_albums.append(update_album)
    dialog_msg("close", background=background)
    return updated_albums, canceled


def check_artist_mbid(artists, background=False, mode="all_artists"):
    updated_artists = []
    canceled = False
    count = 0
    dialog_msg("create", heading=__lng__(32149), background=background)
    if not background:
        xbmc.sleep(500)
    if not artists:
        if mode != "all_artists":
            artists = get_local_artists_db("album_artists")
        else:
            artists = get_local_artists_db("all_artists")
    for artist in artists:
        update_artist = artist
        percent = int((count / float(len(artists))) * 100) if len(artists) > 0 else 100
        if percent < 1:
            percent = 1
        if percent > 100:
            percent = 100
        count += 1
        if dialog_msg("iscanceled", background=background):
            canceled = True
            break
        if update_artist["musicbrainz_artistid"]:
            dialog_msg("update", percent=percent, line1=__lng__(32149),
                       line2="%s%s" % (__lng__(32125), update_artist["local_id"]),
                       line3="%s: %s" % (__lng__(32137), get_unicode(update_artist["name"])),
                       background=background)
            mbid_match, current_mbid = mbid_check(update_artist["musicbrainz_artistid"], "artist")
            if not mbid_match:
                update_artist["musicbrainz_artistid"] = current_mbid
        updated_artists.append(update_artist)
    dialog_msg("close", background=background)
    return updated_artists, canceled


def update_missing_artist_mbid(artists, background=False, mode="all_artists", repair=False):
    if repair:
        log("Updating Removed MBID", xbmc.LOGNOTICE)
    else:
        log("Updating Missing MBID", xbmc.LOGNOTICE)
    updated_artists = []
    canceled = False
    count = 0
    if not background:
        dialog_msg("create", heading=__lng__(32132), background=background)
        xbmc.sleep(500)
    if not artists:
        if mode != "all_artists":
            artists = get_local_artists_db("album_artists")
        else:
            artists = get_local_artists_db("all_artists")
    for artist in artists:
        update_artist = artist
        percent = int((count / float(len(artists))) * 100) if len(artists) > 0 else 100
        if percent < 1:
            percent = 1
        if percent > 100:
            percent = 100
        count += 1
        if (len(update_artist["musicbrainz_artistid"]) != 36 and not repair) or (
                        update_artist["musicbrainz_artistid"] == "removed" and repair):
            if dialog_msg("iscanceled", background=background):
                canceled = True
                break
            dialog_msg("update", percent=percent, line1=__lng__(32132),
                       line2="%s%s" % (__lng__(32125), update_artist["local_id"]),
                       line3="%s: %s" % (__lng__(32137), get_unicode(update_artist["name"])),
                       background=background)
            try:
                _, update_artist["musicbrainz_artistid"], _ = get_musicbrainz_artist_id(
                    get_unicode(update_artist["name"]))
            except Exception as e:
                log(e.message)
                _, update_artist["musicbrainz_artistid"], _ = get_musicbrainz_artist_id(update_artist["name"])
        updated_artists.append(update_artist)
    dialog_msg("close", background=background)
    return updated_artists, canceled


def update_missing_album_mbid(albums, background=False, repair=False):
    if repair:
        log("Updating Removed MBID", xbmc.LOGNOTICE)
    else:
        log("Updating Missing MBID", xbmc.LOGNOTICE)
    updated_albums = []
    canceled = False
    count = 0
    if not background:
        dialog_msg("create", heading=__lng__(32133))
        xbmc.sleep(500)
    if not albums:
        albums = get_local_albums_db("all artists", background)
    for album in albums:
        update_album = album
        percent = int((count / float(len(albums))) * 100) if len(albums) > 0 else 100
        if percent < 1:
            percent = 1
        if percent > 100:
            percent = 100
        count += 1
        if (len(album["musicbrainz_albumid"]) != 36 and not repair) or (
                        album["musicbrainz_albumid"] == "removed" and repair):
            if dialog_msg("iscanceled", background=background):
                canceled = True
                break
            dialog_msg("update", percent=percent, line1=__lng__(32133),
                       line2="%s: %s" % (__lng__(32138), get_unicode(album["title"])),
                       line3="%s: %s" % (__lng__(32137), get_unicode(album["artist"])), background=background)
            musicbrainz_albuminfo, _ = get_musicbrainz_album(get_unicode(album["title"]),
                                                             get_unicode(album["artist"]), 0, 1)
            update_album["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
            update_album["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
        updated_albums.append(update_album)
    dialog_msg("close", background=background)
    return updated_albums, canceled


def update_database(background=False):
    log("Updating Addon's DB", xbmc.LOGNOTICE)
    log("Checking to see if DB already exists")
    if not xbmcvfs.exists(__cdam__.file_addon_db()):
        refresh_db(background)
        return
    if __cfg__.backup_during_update():
        backup_database()
    matched = []
    unmatched = []
    matched_indexed = {}
    album_detail_list_indexed = {}
    local_artists_matched = []
    local_artists_unmatched = []
    local_artists_indexed = {}
    local_artists_matched_indexed = {}
    temp_local_artists = []
    updated_albums = []
    canceled = False
    local_artist_count = 0
    get_local_artists_db(mode="album_artists")
    log("Updating Addon's DB - Checking Albums", xbmc.LOGNOTICE)
    dialog_msg("create", heading=__lng__(32134), line1=__lng__(32105),
               background=background)  # retrieving all artist from xbmc
    local_album_list = get_local_albums_db("all artists", background)
    dialog_msg("create", heading=__lng__(32134), line1=__lng__(32105),
               background=background)  # retrieving album list
    album_list, total = retrieve_album_list()
    dialog_msg("create", heading=__lng__(32134), line1=__lng__(32105),
               background=background)  # retrieving album details
    album_detail_list = retrieve_album_details_full(album_list, total, background=background, simple=True, update=False)
    dialog_msg("create", heading=__lng__(32134), line1=__lng__(32105),
               background=background)  # retrieving local artist details
    # album matching
    for item in album_detail_list:
        album_detail_list_indexed[(
            item["disc"], get_unicode(item["artist"]), get_unicode(item["title"]), item["cover"], item["cdart"],
            item["local_id"], get_unicode(item["path"]))] = item
    for item in local_album_list:
        if (item["disc"], get_unicode(item["artist"]), get_unicode(item["title"]), item["cover"], item["cdart"],
                item["local_id"], get_unicode(item["path"])) in album_detail_list_indexed:
            matched.append(item)
    for item in matched:
        matched_indexed[(
            item["disc"], get_unicode(item["artist"]), get_unicode(item["title"]), item["cover"], item["cdart"],
            item["local_id"], get_unicode(item["path"]))] = item
    for item in album_detail_list:
        if not (item["disc"], get_unicode(item["artist"]), get_unicode(item["title"]), item["cover"], item["cdart"],
                item["local_id"], get_unicode(item["path"])) in matched_indexed:
            unmatched.append(item)
    unmatched_details = retrieve_album_details_full(unmatched, len(unmatched), background=background, simple=False,
                                                    update=True)
    combined = matched
    combined.extend(unmatched_details)
    combined_artists = []
    # artist matching
    if __cfg__.enable_all_artists():
        local_artists = get_all_local_artists(True)
        log("Updating Addon's DB - Checking Artists", xbmc.LOGNOTICE)
        for artist in local_artists:
            new_artist = {"name": get_unicode(artist_list_to_string(artist["artist"])), "local_id": artist["artistid"],
                          "musicbrainz_artistid": ""}
            temp_local_artists.append(new_artist)
        local_artists = temp_local_artists
        local_artists_db = get_local_artists_db("all_artists")
        for item in local_artists:
            local_artists_indexed[(item["local_id"], get_unicode(item["name"]))] = item
        for item in local_artists_db:
            if (item["local_id"], get_unicode(item["name"])) in local_artists_indexed:
                local_artists_matched.append(item)
        for item in local_artists_matched:
            local_artists_matched_indexed[(item["local_id"], get_unicode(item["name"]))] = item
        for item in local_artists:
            if not (item["local_id"], get_unicode(item["name"])) in local_artists_matched_indexed:
                local_artists_unmatched.append(item)
        if __cfg__.update_musicbrainz() and not canceled:  # update missing MusicBrainz ID's
            combined_artists, canceled = update_missing_artist_mbid(local_artists_matched, background=background,
                                                                    mode="all_artists")
        else:
            combined_artists = local_artists_matched
        if __cfg__.check_mbid() and not canceled:
            temp_local_artists, canceled = check_artist_mbid(combined_artists, background=background,
                                                             mode="all_artists")
            combined_artists = temp_local_artists
        if local_artists_unmatched:
            updated_artists, canceled = update_missing_artist_mbid(local_artists_unmatched, background=background,
                                                                   mode="all_artists")
            combined_artists.extend(updated_artists)

    log("Updating Addon's DB - Getting MusicBrainz ID's for Artist and Albums", xbmc.LOGNOTICE)
    if __cfg__.update_musicbrainz() and not canceled:  # update missing MusicBrainz ID's
        if not canceled:
            updated_albums, canceled = update_missing_album_mbid(combined, background=background)
        combined = updated_albums
    if __cfg__.check_mbid() and not canceled:
        updated_albums, canceled = check_album_mbid(combined, background=background)
        combined = updated_albums
        if __cfg__.enable_all_artists() and not canceled:
            updated_artists, canceled = check_artist_mbid(combined_artists, background=background, mode="all_artists")
    if canceled:
        dialog_msg("close", background=background)
        return
    conn = connect()
    c = conn.cursor()
    # if database file still exists even after trying to delete it. Wipe out its contents
    if xbmcvfs.exists(__cdam__.file_addon_db()):
        c.execute("""\
            DROP table IF EXISTS lalist_bk
        """)  # drop the local artists list backup table
        c.execute("""\
            DROP table IF EXISTS local_artists_bk
        """)  # drop local artists backup table
        c.execute("""\
            CREATE TABLE lalist_bk AS SELECT * FROM lalist
        """)  # create a backup of the Album artist table
        c.execute("""\
            CREATE TABLE local_artists_bk AS SELECT * FROM local_artists
        """)  # create backup of the Local Artists
        c.execute("""\
            DROP table IF EXISTS counts
        """)  # drop the count table
        c.execute("""\
            DROP table IF EXISTS lalist
        """)  # drop local album artists table
        c.execute("""\
            DROP table IF EXISTS alblist
        """)  # drop local album table
        c.execute("""\
            DROP table IF EXISTS unqlist
        """)  # drop unique table
        c.execute("""\
            DROP table IF EXISTS local_artists
        """)
    c.execute("""\
        CREATE TABLE counts(local_artists INTEGER, artists INTEGER, albums INTEGER, cdarts INTEGER, version TEXT)
    """)
    # create local album artists database
    c.execute("""\
        CREATE TABLE lalist(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    # create local album database
    c.execute("""\
        CREATE TABLE alblist(album_id INTEGER, title TEXT, artist TEXT, path TEXT, cdart TEXT, cover TEXT,
        disc INTEGER, musicbrainz_albumid TEXT, musicbrainz_artistid TEXT)
    """)
    # create unique database
    c.execute("""\
        CREATE TABLE unqlist(title TEXT, disc INTEGER, artist TEXT, path TEXT, cdart TEXT)
    """)
    # create local artists database
    c.execute("""\
        CREATE TABLE local_artists(local_id INTEGER, name TEXT, musicbrainz_artistid TEXT, fanarttv_has_art TEXT)
    """)
    conn.commit()
    c.close()
    store_counts(0, 0, 0, 0)
    album_count, cdart_existing = store_alblist(combined, background=background)
    album_artist = retrieve_distinct_album_artists()  # then retrieve distinct album artists
    local_artist_list = get_all_local_artists(all_artists=False)  # retrieve local artists(to get idArtist)
    local_album_artist_list, artist_count = check_local_albumartist(album_artist, local_artist_list,
                                                                    background=background)
    store_lalist(local_album_artist_list)  # then store in database
    if __cfg__.enable_all_artists():
        local_artist_count = len(combined_artists)
    store_counts(local_artist_count, artist_count, album_count, cdart_existing)
    if not background:
        dialog_msg("close", background=background)
        xbmc.sleep(5000)
    if __cfg__.enable_all_artists():
        if len(combined_artists) > 0:
            log("Updating Addon's DB - Adding All Artists to Database", xbmc.LOGNOTICE)
            dialog_msg("create", heading=__lng__(32135), background=background)
            store_local_artist_table(combined_artists, background=background)
    conn = connect()
    c = conn.cursor()
    # copy fanarttv_has_art values from backup tables if MBIDs match
    c.execute("""\
        UPDATE lalist SET fanarttv_has_art =
            (SELECT lalist_bk.fanarttv_has_art FROM lalist_bk
                WHERE lalist_bk.musicbrainz_artistid = lalist.musicbrainz_artistid )
            WHERE EXISTS ( SELECT * FROM lalist_bk WHERE lalist_bk.musicbrainz_artistid = lalist.musicbrainz_artistid )
    """)
    c.execute("""\
        UPDATE local_artists SET fanarttv_has_art =
            (SELECT local_artists_bk.fanarttv_has_art FROM local_artists_bk
                WHERE local_artists_bk.musicbrainz_artistid = local_artists.musicbrainz_artistid )
            WHERE EXISTS ( SELECT * FROM local_artists_bk
                WHERE local_artists_bk.musicbrainz_artistid = local_artists.musicbrainz_artistid )
    """)
    c.execute("""\
        DROP table IF EXISTS lalist_bk
    """)  # drop local album artists backup table
    c.execute("""\
        DROP table IF EXISTS local_artists_bk
    """)
    conn.commit()
    c.close()
    restore_user_updates()


def backup_database():
    todays_date = datetime.datetime.today().strftime("%m-%d-%Y")
    current_time = time.strftime('%H%M')
    db_backup_file = "l_cdart-%s-%s.bak" % (todays_date, current_time)
    addon_backup_path = os.path.join(__cdam__.path_profile(), db_backup_file).replace("\\\\", "\\")
    xbmcvfs.copy(__cdam__.file_addon_db(), addon_backup_path)
    if xbmcvfs.exists(addon_backup_path):
        try:
            xbmcvfs.delete(addon_backup_path)
        except Exception as e:
            log(e.message, xbmc.LOGERROR)
            log("Unable to delete Database Backup")
    try:
        xbmcvfs.copy(__cdam__.file_addon_db(), addon_backup_path)
        log("Backing up old Local Database")
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        log("Unable to make Database Backup")


def unset_cdart(album):
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        UPDATE alblist SET cdart=? WHERE title=?
    """, (False, album))
    conn.commit()
    c.close()


def get_db_version():
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        SELECT version FROM counts
    """)
    version = c.fetchall()
    c.close()
    return version[0][0]


def set_artist_mbid(artist_id, artist_name):
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        UPDATE alblist SET musicbrainz_artistid=? WHERE artist=?
    """, (artist_id, artist_name))
    try:
        c.execute("""\
            UPDATE lalist SET musicbrainz_artistid=? WHERE name=?
        """, (artist_id, artist_name))
    except SQLError:
        pass
    conn.commit()
    c.close()


def update_artist_mbid(new_mbid, local_id, old_mbid=None, artist_name=None):
    conn = connect()
    c = conn.cursor()

    # update artist by id
    try:
        c.execute("""\
            UPDATE lalist SET musicbrainz_artistid=? WHERE local_id=?
        """, (new_mbid, local_id))
    except Exception as ex:
        log(ex.message)
        log("Error updating database(lalist)", xbmc.LOGERROR)
        traceback.print_exc()

    # update local artist by id
    try:
        c.execute("""\
            UPDATE local_artists SET musicbrainz_artistid=? WHERE local_id=?
        """, (new_mbid, local_id))
    except Exception as ex:
        log(ex.message)
        log("Error updating database(local_artists)", xbmc.LOGERROR)
        traceback.print_exc()

    # update albums by mbid
    if old_mbid is not None:
        try:
            c.execute("""\
                UPDATE alblist SET musicbrainz_artistid=? WHERE musicbrainz_artistid=?
            """, (new_mbid, old_mbid))
        except Exception as ex:
            log(ex.message)
            log("Error updating database(lalist)", xbmc.LOGERROR)
            traceback.print_exc()

    # update albums by artist_name
    if artist_name is not None:
        try:
            c.execute("""\
                UPDATE alblist SET musicbrainz_artistid=? WHERE artist=?
            """, (new_mbid, artist_name))
        except Exception as ex:
            log(ex.message)
            log("Error updating database", xbmc.LOGERROR)
            traceback.print_exc()

    conn.commit()
    c.close()


def set_album_mbid(album_mbid, album_title):
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        UPDATE alblist SET musicbrainz_albumid=? WHERE title=?
    """, (album_mbid, album_title))
    conn.commit()
    c.close()


def set_album_mbids(local_id, album_mbid, artist_mbid):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("""\
            UPDATE alblist SET musicbrainz_albumid=?, musicbrainz_artistid=? WHERE album_id=?
        """, (album_mbid, artist_mbid, local_id))
    except Exception as ex:
        log(ex.message)
        log("Error updating database", xbmc.LOGERROR)
        traceback.print_exc()
    conn.commit()
    c.close()


def set_has_art(type_, album_path):
    conn = connect()
    c = conn.cursor()
    if type_ == ArtType.CDART:
        c.execute("""\
            UPDATE alblist SET cdart="True" WHERE path=?
        """, (album_path,))
    elif type_ == ArtType.COVER:
        c.execute("""\
            UPDATE alblist SET cover="True" WHERE path=?
        """, (album_path,))
    conn.commit()
    c.close()


def insert_unique(title, artist, path, cdart):
    conn = connect()
    c = conn.cursor()
    c.execute("""\
        insert into unqlist(title, artist, path, cdart) values (?, ?, ?, ?)
    """, (title, artist, path, cdart))
    conn.commit()
    c.close()


def manual_update_album(album_mbid, artist_mbid, local_id, path):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("""\
            UPDATE alblist SET musicbrainz_albumid=?, musicbrainz_artistid=?
            WHERE album_id=? and path=?
        """, (album_mbid, artist_mbid, local_id, path))
    except Exception as ex:
        log(ex.message)
        log("Error updating database(alblist)", xbmc.LOGERROR)
        traceback.print_exc()
    try:
        c.execute("""\
            UPDATE lalist SET musicbrainz_artistid=? WHERE local_id=?
        """, (artist_mbid, local_id))
    except Exception as ex:
        log(ex.message)
        log("Error updating database(lalist)", xbmc.LOGERROR)
        traceback.print_exc()
    try:
        c.execute("""\
            UPDATE local_artists SET musicbrainz_artistid=? WHERE local_id=?
        """, (artist_mbid, local_id))
    except Exception as ex:
        log(ex.message)
        log("Error updating database(local_artists)", xbmc.LOGERROR)
        traceback.print_exc()
    conn.commit()
    c.close()
