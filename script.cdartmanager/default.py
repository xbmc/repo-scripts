# -*- coding: utf-8 -*-

import calendar
import datetime
import os
import sys
import traceback

import xbmc
import xbmcgui
import xbmcvfs

import lib.cdam_utils as cu

from lib import cdam, cdam_db, cdam_fs, download, ftv_scraper, gui, jsonrpc_calls
from lib.cdam import Def, MediaType, ArtType, FileName
from lib.cdam_utils import log, dialog_msg
from lib.cdam_fs import sanitize

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()
__lng__ = __cdam__.getLocalizedString

script_fail = False
first_run = False
rebuild = False
soft_exit = False
background_db = False
script_mode = ""


def clear_skin_properties():
    xbmcgui.Window(10000).setProperty("cdart_manager_running", "False")
    xbmcgui.Window(10000).setProperty("cdart_manager_update", "False")
    xbmcgui.Window(10000).setProperty("cdart_manager_allartist", "False")


def artist_musicbrainz_id(artist_id, artist_mbid):
    artist_details = jsonrpc_calls.retrieve_artist_details(artist_id)
    artist_ = {}
    if not artist_details["musicbrainzartistid"] or not artist_mbid:
        artist_["name"] = cu.get_unicode(artist_details["label"])
    else:
        artist_["name"] = cu.get_unicode(artist_details["label"])
        if artist_mbid:
            artist_["musicbrainz_artistid"] = artist_mbid
        else:
            artist_["musicbrainz_artistid"] = artist_details["musicbrainzartistid"]
    return artist_


def album_musicbrainz_id(album_id):
    album_list = jsonrpc_calls.retrieve_album_details(album_id)
    if album_list:
        album_detail_list = cdam_db.retrieve_album_details_full(album_list, 1, background=True)
        return album_detail_list
    else:
        return []


def select_artwork(details, media_type_):
    artwork = None
    selection = None
    if media_type_ in (ArtType.CDART, ArtType.COVER):
        if media_type_ == ArtType.CDART:
            artwork = ftv_scraper.remote_cdart_list(details)
        else:
            artwork = ftv_scraper.remote_coverart_list(details)
        if artwork:
            for art in artwork:
                if art["musicbrainz_albumid"] == details["musicbrainz_albumid"]:
                    selection = art
            if not selection:
                dialog_msg("okdialog", heading=__lng__(32033), line1=__lng__(32030),
                           line2=__lng__(32031), background=False)
        else:
            dialog_msg("okdialog", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031),
                       background=False)
    else:
        if media_type_ == ArtType.FANART:
            artwork = ftv_scraper.remote_fanart_list(details)
        elif media_type_ == ArtType.CLEARLOGO:
            artwork = ftv_scraper.remote_clearlogo_list(details)
        elif media_type_ == ArtType.HDLOGO:
            artwork = ftv_scraper.remote_hdlogo_list(details)
        elif media_type_ == ArtType.THUMB:
            artwork = ftv_scraper.remote_artistthumb_list(details)
        elif media_type_ == ArtType.BANNER:
            artwork = ftv_scraper.remote_banner_list(details)
        if artwork:
            for art in artwork:
                print art


def thumbnail_copy(art_path, thumb_path, type_="artwork"):
    if not thumb_path.startswith("http://") or not thumb_path.startswith("image://"):
        if xbmcvfs.exists(art_path):
            if xbmcvfs.copy(art_path, thumb_path):
                log("Successfully copied %s" % type_, xbmc.LOGDEBUG)
            else:
                log("Failed to copy to %s" % type_, xbmc.LOGDEBUG)
            log("Source Path: %s" % repr(art_path), xbmc.LOGDEBUG)
            log("Destination Path: %s" % repr(thumb_path), xbmc.LOGDEBUG)
    elif thumb_path.startswith("http://") or thumb_path.startswith("image://"):
        log("Destination Path is not able to be copied to: %s" % repr(thumb_path), xbmc.LOGDEBUG)


def update_xbmc_thumbnails(background=False):
    log("Updating Thumbnails/fanart Images", xbmc.LOGNOTICE)
    xbmc.sleep(1000)
    dialog_msg("create", heading=__lng__(32042), background=background)
    # Artists
    artists = cdam_db.get_local_artists_db(mode="local_artists")
    if not artists:
        artists = cdam_db.get_local_artists_db(mode="album_artists")
    # Albums
    albums = cdam_db.get_local_albums_db("all artists", False)

    count = 0
    for artist_ in artists:
        if dialog_msg("iscanceled"):
            break

        count += 1
        dialog_msg("update", percent=cu.percent_of(count, len(artists)), line1=__lng__(32112),
                   line2=" %s %s" % (__lng__(32038), cu.get_unicode(artist_["name"])), background=background)
        # xbmc_thumbnail_path = ""
        # xbmc_fanart_path = ""
        fanart_path = cdam_fs.get_artist_path(artist_["name"], FileName.FANART)
        artistthumb_path = cdam_fs.get_artist_path(artist_["name"], FileName.FOLDER)
        if xbmcvfs.exists(fanart_path):
            thumbnail_copy(fanart_path, jsonrpc_calls.get_fanart_path(artist_["local_id"]), ArtType.FANART)
        elif xbmcvfs.exists(artistthumb_path):
            thumbnail_copy(artistthumb_path, jsonrpc_calls.get_thumbnail_path(artist_["local_id"], MediaType.ARTIST),
                           "artist thumb")
        else:
            continue

    count = 1
    for album_ in albums:
        if dialog_msg("iscanceled"):
            break
        dialog_msg("update", percent=cu.percent_of(count, len(albums)), line1=__lng__(32042), line2=__lng__(32112),
                   line3=" %s %s" % (__lng__(32039), cu.get_unicode(album_["title"])), background=background)
        xbmc_thumbnail_path = ""
        coverart_path = sanitize(os.path.join(album_["path"], FileName.FOLDER))
        if xbmcvfs.exists(coverart_path):
            xbmc_thumbnail_path = jsonrpc_calls.get_thumbnail_path(album_["local_id"], "album")
        if xbmc_thumbnail_path:
            thumbnail_copy(coverart_path, xbmc_thumbnail_path, "album cover")
        count += 1
    log("Finished Updating Thumbnails/fanart Images", xbmc.LOGNOTICE)


def get_script_mode():
    script_mode_ = ""
    start_mbid = ""
    start_dbid = 0
    start_media_type = ()
    if len(sys.argv) < 2:
        script_mode_ = "normal"

    try:
        log("sys.argv[0]: %s" % sys.argv[0])
        log("sys.argv[1]: %s" % sys.argv[1])
        log("sys.argv[2]: %s" % sys.argv[2])
        log("sys.argv[3]: %s" % sys.argv[3])
    except IndexError:
        pass

    for arg in sys.argv:
        if arg in (
                "autocdart", "autocover", "autofanart", "autologo", "autothumb", "autobanner", "autoall", "database",
                "update", "oneshot", "artist"):
            script_mode_ = arg
        if len(arg) == 36 and arg[8] == "-":  # MBID
            start_mbid = arg
        try:
            start_dbid = int(arg)
        except ValueError:
            pass
        if arg.startswith("mediatype="):
            start_media_type = arg.replace("mediatype=", "").split("/")
    return script_mode_, start_mbid, start_dbid, start_media_type


if __name__ == "__main__":

    log("#############################################################", xbmc.LOGNOTICE)
    for credit in __cdam__.credits():
        log("#  %-55s  #" % credit, xbmc.LOGNOTICE)
    log("#############################################################", xbmc.LOGNOTICE)

    log("Looking for settings.xml", xbmc.LOGNOTICE)
    if not xbmcvfs.exists(__cdam__.file_settings_xml()):  # Open Settings if settings.xml does not exists
        log("settings.xml File not found, creating path and opening settings", xbmc.LOGNOTICE)
        xbmcvfs.mkdirs(__cdam__.path_profile())
        __cfg__.open()
        soft_exit = True

    cu.settings_to_log(__cdam__.file_settings_xml())
    script_mode, provided_mbid, provided_dbid, media_type = get_script_mode()

    if xbmcgui.Window(10000).getProperty("cdart_manager_running") == "True":
        log("cdART Manager Already running, exiting...", xbmc.LOGNOTICE)
        soft_exit = True
    else:
        xbmcgui.Window(10000).setProperty("cdart_manager_running", "True")

    if not soft_exit:
        try:
            if __cfg__.enable_all_artists():
                xbmcgui.Window(10000).setProperty("cdart_manager_allartist", "True")
            else:
                xbmcgui.Window(10000).setProperty("cdart_manager_allartist", "False")

            all_artists = []
            local_artists = []

            if script_mode == "database":
                log("Start method - Build Database in background", xbmc.LOGNOTICE)
                xbmcgui.Window(10000).setProperty("cdartmanager_update", "True")
                local_album_count, local_artist_count, local_cdart_count = cdam_db.refresh_db(background=True)
                local_artists = cdam_db.get_local_artists_db(mode="album_artists")
                if __cfg__.enable_all_artists():
                    all_artists = cdam_db.get_local_artists_db(mode="all_artists")
                else:
                    all_artists = []
                ftv_scraper.first_check(all_artists, local_artists, background=True)
                xbmcgui.Window(10000).setProperty("cdartmanager_update", "False")
            elif script_mode in ("autocdart", "autocover", "autofanart", "autologo",
                                 "autothumb", "autobanner", "autoall", "update"):
                local_artists = cdam_db.get_local_artists_db(mode="album_artists")
                if __cfg__.enable_all_artists():
                    all_artists = cdam_db.get_local_artists_db(mode="all_artists")
                else:
                    all_artists = []
            if script_mode in ("autocdart", "autocover", "autofanart", "autologo", "autothumb", "autobanner"):
                xbmcgui.Window(10000).setProperty("cdart_manager_running", "True")
                artwork_type = None
                if script_mode == "autocdart":
                    log("Start method - Autodownload Album cdARTs in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.CDART
                elif script_mode == "autocover":
                    log("Start method - Autodownload Album Cover art in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.COVER
                elif script_mode == "autofanart":
                    log("Start method - Autodownload Artist Fanarts in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.FANART
                elif script_mode == "autologo":
                    log("Start method - Autodownload Artist Logos in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.CLEARLOGO
                elif script_mode == "autothumb":
                    log("Start method - Autodownload Artist Thumbnails in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.THUMB
                elif script_mode == "autobanner":
                    log("Start method - Autodownload Artist Music Banners in background", xbmc.LOGNOTICE)
                    artwork_type = ArtType.BANNER
                if artwork_type in (ArtType.FANART, ArtType.CLEARLOGO, ArtType.THUMB, ArtType.BANNER) \
                        and __cfg__.enable_all_artists():
                    download_count, successfully_downloaded = download.auto_download(artwork_type, all_artists,
                                                                                     background=True)
                else:
                    download_count, successfully_downloaded = download.auto_download(artwork_type, local_artists,
                                                                                     background=True)
                log("Autodownload of %s artwork completed\nTotal artwork downloaded: %d" % (
                    artwork_type, download_count), xbmc.LOGNOTICE)
            elif script_mode == "update":
                log("Start method - Update Database in background", xbmc.LOGNOTICE)
                xbmcgui.Window(10000).setProperty("cdart_manager_update", "True")
                cdam_db.update_database(background=True)
                local_artists = cdam_db.get_local_artists_db(mode="album_artists")
                if __cfg__.enable_all_artists():
                    all_artists = cdam_db.get_local_artists_db(mode="all_artists")
                else:
                    all_artists = []
                d = datetime.datetime.utcnow()
                present_datecode = calendar.timegm(d.utctimetuple())
                ftv_scraper.first_check(all_artists, local_artists, background=True, update_db=True)
            elif script_mode == "autoall":
                xbmcgui.Window(10000).setProperty("cdart_manager_running", "True")
                log("Start method - Autodownload all artwork in background", xbmc.LOGNOTICE)
                total_artwork = 0
                for artwork_type in (ArtType.CDART, ArtType.COVER, ArtType.FANART,
                                     ArtType.CLEARLOGO, ArtType.THUMB, ArtType.BANNER):
                    log("Start method - Autodownload %s in background" % artwork_type, xbmc.LOGNOTICE)
                    download_count = 0
                    if artwork_type in (ArtType.FANART, ArtType.CLEARLOGO, ArtType.THUMB, ArtType.BANNER) \
                            and __cfg__.enable_all_artists():
                        download_count, successfully_downloaded = download.auto_download(artwork_type, all_artists,
                                                                                         background=True)
                    elif artwork_type:
                        download_count, successfully_downloaded = download.auto_download(artwork_type, local_artists,
                                                                                         background=True)
                    total_artwork += download_count
                log("Autodownload all artwork completed\nTotal artwork downloaded: %d" % total_artwork, xbmc.LOGNOTICE)
            elif script_mode == "update_thumbs":
                log("Start method - Update Thumbnails in background", xbmc.LOGNOTICE)
                update_xbmc_thumbnails()
            elif script_mode == "oneshot":
                log("Start method - One Shot Download method", xbmc.LOGNOTICE)
                if provided_dbid or provided_mbid:
                    if media_type[0] in (ArtType.CLEARLOGO, ArtType.FANART, ArtType.THUMB, ArtType.BANNER):
                        artist = artist_musicbrainz_id(provided_dbid, provided_mbid)
                        if not artist:
                            log("No MBID found", xbmc.LOGNOTICE)
                        else:
                            print artist
                            log("Artist: %s" % artist["artist"], xbmc.LOGDEBUG)
                            log("MBID: %s" % artist["musicbrainz_artistid"], xbmc.LOGDEBUG)
                            select_artwork(artist, media_type[0])
                    elif media_type[0] in (ArtType.CDART, ArtType.COVER):
                        if provided_dbid:
                            album_details = album_musicbrainz_id(provided_dbid)
                            if not album_details:
                                log("No MBID found", xbmc.LOGNOTICE)
                            else:
                                for album in album_details:
                                    log("Album: %s" % album["title"])
                                    log("MBID: %s" % album["musicbrainz_albumid"])
                                    log("Artist: %s" % album["artist"])
                                    log("MBID: %s" % album["musicbrainz_artistid"])
                                    select_artwork(album, media_type[0])
                        else:
                            log("No Database ID provided")
                else:
                    log("A Database ID or MusicBrainz ID needed")
            elif script_mode == "normal":
                log("Addon Work Folder: %s" % __cdam__.path_profile(), xbmc.LOGNOTICE)
                log("Addon Database: %s" % __cdam__.file_addon_db(), xbmc.LOGNOTICE)
                log("Addon settings: %s" % __cdam__.file_settings_xml(), xbmc.LOGNOTICE)
                if xbmcgui.Window(10000).getProperty(
                        "cdart_manager_update") == "True":
                    # Check to see if skin property is set, if it is, gracefully exit the script
                    if not os.environ.get("OS", "win32") in ("win32", "Windows_NT"):
                        background_db = False
                        # message "cdART Manager, Stopping Background Database Building"
                        dialog_msg("okdialog", heading=__lng__(32042), line1=__lng__(32119))
                        log("BackgroundDB was in Progress, Stopping, allowing script to continue", xbmc.LOGNOTICE)
                        xbmcgui.Window(10000).setProperty("cdartmanager_update", "False")
                    else:
                        background_db = True
                        # message "cdART Manager, Background Database building in progress...  Exiting Script..."
                        dialog_msg("okdialog", heading=__lng__(32042), line1=__lng__(32118))
                        log("Background Database Building in Progress, exiting", xbmc.LOGNOTICE)
                        xbmcgui.Window(10000).setProperty("cdartmanager_update", "False")
                if not background_db and not soft_exit:  # If Settings exists and not in background_db mode, continue on
                    log("Addon Work Folder Found, Checking For Database", xbmc.LOGNOTICE)
                # if l_cdart.db missing, must be first run
                if not xbmcvfs.exists(__cdam__.file_addon_db()) and not background_db:
                    log("Addon Db not found, Must Be First Run", xbmc.LOGNOTICE)
                    first_run = True
                elif not background_db and not soft_exit:
                    log("Addon Db Found, Checking Database Version", xbmc.LOGNOTICE)
                # if l_cdart.db.journal exists, creating database must have crashed at some point, delete and start over
                if xbmcvfs.exists(__cdam__.file_addon_db_crash()) \
                        and not first_run and not background_db and not soft_exit:
                    log("Detected Database Crash, Trying to delete", xbmc.LOGNOTICE)
                    try:
                        xbmcvfs.delete(__cdam__.file_addon_db())
                        xbmcvfs.delete(__cdam__.file_addon_db_crash())
                    except StandardError, e:
                        log("Error Occurred: %s " % e.__class__.__name__, xbmc.LOGNOTICE)
                        traceback.print_exc()
                        script_fail = True
                elif not first_run and not background_db and not soft_exit and not script_fail:  # Test database version
                    log("Looking for database version: %s" % Def.DB_VERSION, xbmc.LOGNOTICE)
                    try:
                        version = cdam_db.get_db_version()
                        if version == Def.DB_VERSION:
                            log("Database matched", xbmc.LOGNOTICE)
                        else:
                            log("Old version found, upgrading database", xbmc.LOGNOTICE)
                            cdam_db.upgrade_db(version)
                    except StandardError, e:
                        traceback.print_exc()
                        log("# Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE)
                        try:
                            log("Trying To Delete Database", xbmc.LOGNOTICE)
                            xbmcvfs.delete(__cdam__.file_addon_db())
                        except StandardError, e:
                            traceback.print_exc()
                            log("# unable to remove folder", xbmc.LOGNOTICE)
                            log("# Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE)
                            script_fail = True
                if not script_fail and not background_db:
                    if rebuild:
                        local_album_count, local_artist_count, local_cdart_count = cdam_db.refresh_db(True)
                    elif not rebuild and not soft_exit:
                        try:
                            ui = gui.GUI("script-cdartmanager.xml", __cdam__.path())
                            xbmc.sleep(2000)
                            ui.doModal()
                            del ui
                            clear_skin_properties()
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            log("Error in script occured", xbmc.LOGNOTICE)
                            log(e.message, xbmc.LOGWARNING)
                            traceback.print_exc()
                            dialog_msg("close")
                            clear_skin_properties()
                elif not background_db and not soft_exit:
                    log("Problem accessing folder, exiting script", xbmc.LOGNOTICE)
                    xbmc.executebuiltin(
                        "Notification( %s, %s, %d, %s)" % (
                            __lng__(32042), __lng__(32110), 500, __cdam__.file_icon()))
            clear_skin_properties()
        except Exception as e:
            print "Unexpected error:", sys.exc_info()[0]
            log(e.message, xbmc.LOGWARNING)
            clear_skin_properties()
            raise
    else:
        clear_skin_properties()
