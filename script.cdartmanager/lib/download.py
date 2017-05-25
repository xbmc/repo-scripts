# -*- coding: utf-8 -*-

import os
import urllib
from traceback import print_exc

import xbmc
import xbmcvfs

import cdam
import db
import utils
import ftv_scraper

from utils import log, dialog_msg
from cdam import ArtType, FileName

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()
__lng__ = __cdam__.getLocalizedString

resizeondownload = False  # disabled because fanart.tv API V3 doesn't deliver correct sizes


def check_size(path, _type, size_w, size_h):
    # size check is disabled because currently fanart.tv always returns size=1000
    # ref: https://forum.fanart.tv/viewtopic.php?f=4&t=403
    file_name = get_filename(_type, path, "auto")
    source = os.path.join(path, file_name)
    if xbmcvfs.exists(source):
        log("size check n.a. in new fanart.tv API, returning False for %s" % source)
        return False
    else:
        log("size check n.a. in new fanart.tv API, returning True for %s" % source)
        return True


def get_filename(type_, url, mode):
    if type_ == ArtType.CDART:
        file_name = FileName.CDART
    elif type_ == ArtType.COVER:
        file_name = FileName.FOLDER
    elif type_ == ArtType.FANART:
        if mode == "auto":
            file_name = os.path.basename(url)
        else:
            file_name = FileName.FANART
    elif type_ == ArtType.CLEARLOGO:
        file_name = FileName.LOGO
    elif type_ == ArtType.THUMB:
        file_name = FileName.FOLDER
    elif type_ == ArtType.BANNER:
        file_name = FileName.BANNER
    else:
        file_name = "unknown"
    return file_name


def make_music_path(artist):
    # Helix: paths MUST end with trailing slash
    path = os.path.join(__cfg__.path_music_path(), artist).replace("\\\\", "\\")
    path2 = os.path.join(__cfg__.path_music_path(), str.lower(artist)).replace("\\\\", "\\")
    if not xbmcvfs.exists(path2):
        if not xbmcvfs.exists(path):
            if xbmcvfs.mkdirs(path):
                log("Path to music artist made")
                return True
            else:
                log("unable to make path to music artist")
                return False
    else:
        if not xbmcvfs.exists(path):
            if xbmcvfs.mkdirs(path):
                log("Path to music artist made")
                return True
            else:
                log("unable to make path to music artist")
                return False


def download_art(url_cdart, album, type_, mode, background=False):
    log("Downloading artwork... ")
    download_success = False
#    percent = 1
    is_canceled = False
    if mode == "auto":
        dialog_msg("update", percent=1, background=background)
    else:
        dialog_msg("create", heading=__lng__(32047), background=background)
        # Onscreen Dialog - "Downloading...."
    file_name = get_filename(type_, url_cdart, mode)
    # Helix: paths MUST end with trailing slash
    path = os.path.join(album["path"].replace("\\\\", "\\"), '')
    if file_name == "unknown":
        log("Unknown Type ")
        message = [__lng__(32026), __lng__(32025), "File: %s" % utils.get_unicode(path),
                   "Url: %s" % utils.get_unicode(url_cdart)]
        return message, download_success
    if not xbmcvfs.exists(path):
        try:
            xbmcvfs.mkdirs(album["path"].replace("\\\\", "\\"))
        except Exception as e:
            log(e.message)
    log("Path: %s" % path)
    log("Filename: %s" % file_name)
    log("url: %s" % url_cdart)

    # cosmetic: use subfolder for downloading instead of work folder
    if not xbmcvfs.exists(os.path.join(__cdam__.path_temp_gfx(), '').replace("\\\\", "\\")):
        xbmcvfs.mkdirs(os.path.join(__cdam__.path_temp_gfx(), '').replace("\\\\", "\\"))
    destination = os.path.join(__cdam__.path_temp_gfx(), file_name).replace("\\\\", "\\")  # download to work folder
    final_destination = os.path.join(path, file_name).replace("\\\\", "\\")
    try:
        # this give the ability to use the progress bar by retrieving the downloading information
        # and calculating the percentage
        def _report_hook(count, blocksize, totalsize):
            try:
                percent = int(float(count * blocksize * 100) / totalsize) if totalsize > 0 else 100
                if percent < 1:
                    percent = 1
                if percent > 100:
                    percent = 100
            except Exception as ex:
                log(ex.message)
                percent = 1
            if type_ in (ArtType.FANART, ArtType.CLEARLOGO, ArtType.THUMB, ArtType.BANNER):
                dialog_msg("update", percent=percent,
                           line1="%s%s" % (__lng__(32038), utils.get_unicode(album["artist"])), background=background)
            else:
                dialog_msg("update", percent=percent,
                           line1="%s%s" % (__lng__(32038), utils.get_unicode(album["artist"])),
                           line2="%s%s" % (__lng__(32039), utils.get_unicode(album["title"])), background=background)
#            if mode == "auto":
#                if dialog_msg("iscanceled", background=background):
#                    is_canceled = True

        if xbmcvfs.exists(path):
            log("Fetching image: %s" % url_cdart)
            urllib.urlretrieve(url_cdart, destination, _report_hook)
            # message = ["Download Sucessful!"]
            message = [__lng__(32023), __lng__(32024), "File: %s" % utils.get_unicode(path),
                       "Url: %s" % utils.get_unicode(url_cdart)]
            xbmcvfs.copy(destination, final_destination)  # copy it to album folder
            # update database
            try:
                db.set_has_art(type_, utils.get_unicode(album["path"]))
            except Exception as e:
                log(e.message, xbmc.LOGERROR)
                log("Error updating database")
                print_exc()
            download_success = True

        else:
            log("Path error")
            log("    file path: %s" % repr(destination))
            message = [__lng__(32026), __lng__(32025), "File: %s" % utils.get_unicode(path),
                       "Url: %s" % utils.get_unicode(url_cdart)]
            # message = Download Problem, Check file paths - Artwork Not Downloaded]
        # always cleanup downloaded files
        # if type == MediaType.FANART:
        xbmcvfs.delete(destination)
    except Exception as e:
        log(e.message, xbmc.LOGWARNING)
        log("General download error")
        message = [__lng__(32026), __lng__(32025), "File: %s" % utils.get_unicode(path),
                   "Url: %s" % utils.get_unicode(url_cdart)]
        # message = [Download Problem, Check file paths - Artwork Not Downloaded]
        # print_exc()
    if mode == "auto" or mode == "single":
        # returns one of the messages built based on success or lack of
        return message, download_success, final_destination, is_canceled
    else:
        dialog_msg("close", background=background)
        return message, download_success, is_canceled


def cdart_search(cdart_url, id_, disc):
    cdart = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id_ and item["disc"] == disc:
            cdart = item
            break
    return cdart


# Automatic download of non existing cdarts and refreshes addon's db
def auto_download(type_, artist_list, background=False):
    is_canceled = False
    log("Autodownload")
    try:
        artist_count = 0
        download_count = 0
        album_count = 0
        d_error = False
        successfully_downloaded = []
        if type_ in ("clearlogo_allartists", "artistthumb_allartists", "fanart_allartists", "musicbanner_allartists"):
            if type_ == "clearlogo_allartists":
                type_ = ArtType.CLEARLOGO
            elif type_ == "artistthumb_allartists":
                type_ = ArtType.THUMB
            elif type_ == "musicbanner_allartists":
                type_ = ArtType.BANNER
            else:
                type_ = ArtType.FANART
        count_artist_local = len(artist_list)
        dialog_msg("create", heading=__lng__(32046), background=background)
        # Onscreen Dialog - Automatic Downloading of Artwork
        key_label = type_
        for artist in artist_list:
            if dialog_msg("iscanceled", background=background) or is_canceled:
                break
            artist_count += 1
            if not artist["has_art"] == "True":
                # If fanart.tv does not report that it has an artist match skip it.
                continue
            percent = int((artist_count / float(count_artist_local)) * 100)
            if percent < 1:
                percent = 1
            if percent > 100:
                percent = 100
            log("Artist: %-40s Local ID: %-10s   Distant MBID: %s" % (
                artist["name"], artist["local_id"], artist["musicbrainz_artistid"]), xbmc.LOGNOTICE)
            if type_ in (ArtType.FANART, ArtType.CLEARLOGO, ArtType.THUMB, ArtType.BANNER) \
                    and artist["has_art"]:
                dialog_msg("update",
                           percent=percent,
                           line1="%s%s" % (__lng__(32038), utils.get_unicode(artist["name"])),
                           background=background)

                temp_art = {"musicbrainz_artistid": artist["musicbrainz_artistid"], "artist": artist["name"]}
                auto_art = {"musicbrainz_artistid": artist["musicbrainz_artistid"], "artist": artist["name"]}

                path = os.path.join(__cfg__.path_music_path(),
                                    utils.change_characters(utils.smart_unicode(artist["name"])))
                if type_ == ArtType.FANART:
                    art = ftv_scraper.remote_fanart_list(auto_art)
                elif type_ == ArtType.CLEARLOGO:
                    art = ftv_scraper.remote_hdlogo_list(auto_art)
                    if not art:
                        art = ftv_scraper.remote_clearlogo_list(auto_art)
                elif type_ == ArtType.BANNER:
                    art = ftv_scraper.remote_banner_list(auto_art)
                else:
                    art = ftv_scraper.remote_artistthumb_list(auto_art)
                if art:
                    if type_ == ArtType.FANART:
                        temp_art["path"] = path
                        auto_art["path"] = os.path.join(path, "extrafanart").replace("\\\\", "\\")
                        if not xbmcvfs.exists(auto_art["path"]):
                            try:
                                if xbmcvfs.mkdirs(auto_art["path"]):
                                    log("extrafanart directory made")
                            except Exception as e:
                                log(e.message, xbmc.LOGWARNING)
                                print_exc()
                                log("unable to make extrafanart directory")
                                continue
                        else:
                            log("extrafanart directory already exists")
                    else:
                        auto_art["path"] = path
                    if type_ == ArtType.FANART:
                        if __cfg__.enable_fanart_limit():
                            _, fanart_files = xbmcvfs.listdir(auto_art["path"])
                            fanart_number = len(fanart_files)
                            if fanart_number == __cfg__.fanart_limit():
                                continue
                        if not xbmcvfs.exists(os.path.join(path, FileName.FANART).replace("\\\\", "\\")):
                            message, d_success, final_destination, is_canceled = download_art(art[0], temp_art,
                                                                                              ArtType.FANART,
                                                                                              "single", background)
                        for artwork in art:
                            fanart = {}
                            fanart_number = 0
                            if __cfg__.enable_fanart_limit() and fanart_number == __cfg__.fanart_limit():
                                log("Fanart Limit Reached", xbmc.LOGNOTICE)
                                continue
                            if xbmcvfs.exists(os.path.join(auto_art["path"], os.path.basename(artwork))):
                                log("Fanart already exists, skipping")
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  ArtType.FANART,
                                                                                                  "auto", background)
                            if d_success == 1:
                                if __cfg__.enable_fanart_limit():
                                    fanart_number += 1
                                download_count += 1
                                fanart["artist"] = auto_art["artist"]
                                fanart["path"] = final_destination
                                successfully_downloaded.append(fanart)
                            else:
                                log("Download Error...  Check Path.")
                                log("    Path: %s" % auto_art["path"])
                                d_error = True
                    else:
                        artwork = art[0]
                        d_success = 0
                        final_destination = None
                        if type_ == ArtType.THUMB:
                            if xbmcvfs.exists(os.path.join(auto_art["path"], FileName.FOLDER)):
                                log("Artist Thumb already exists, skipping")
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  ArtType.THUMB,
                                                                                                  "auto", background)
                        elif type_ == ArtType.CLEARLOGO:
                            if xbmcvfs.exists(os.path.join(auto_art["path"], FileName.LOGO)):
                                log("ClearLOGO already exists, skipping")
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  ArtType.CLEARLOGO,
                                                                                                  "auto", background)
                        elif type_ == ArtType.BANNER:
                            if xbmcvfs.exists(os.path.join(auto_art["path"], FileName.BANNER)):
                                log("Music Banner already exists, skipping")
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  ArtType.BANNER,
                                                                                                  "auto", background)
                        if d_success == 1:
                            download_count += 1
                            auto_art["path"] = final_destination
                            successfully_downloaded.append(auto_art)
                        else:
                            log("Download Error...  Check Path.")
                            log("    Path: %s" % auto_art["path"])
                            d_error = True
                else:
                    log("Artist Match not found")
            elif type_ in (ArtType.CDART, ArtType.COVER) and artist["has_art"]:
                local_album_list = db.get_local_albums_db(artist["name"], background)
                if type_ == ArtType.CDART:
                    remote_art_url = ftv_scraper.remote_cdart_list(artist)
                else:
                    remote_art_url = ftv_scraper.remote_coverart_list(artist)
                for album in local_album_list:
                    low_res = True
                    if dialog_msg("iscanceled", background=background):
                        break
                    if not remote_art_url:
                        log("No artwork found")
                        break
                    album_count += 1
                    if not album["musicbrainz_albumid"]:
                        continue
                    dialog_msg("update", percent=percent,
                               line1="%s%s" % (__lng__(32038), utils.get_unicode(artist["name"])),
                               line2="%s%s" % (__lng__(32039), utils.get_unicode(album["title"])),
                               background=background)
                    log("Album: %s" % album["title"])
                    if not album[key_label] or resizeondownload:
                        musicbrainz_albumid = album["musicbrainz_albumid"]
                        art = db.artwork_search(remote_art_url, musicbrainz_albumid, album["disc"], key_label)
                        if art:
                            if resizeondownload:
                                low_res = check_size(album["path"].replace("\\\\", "\\"), key_label, art["size"],
                                                     art["size"])
                            if art["picture"]:
                                log("ALBUM MATCH ON FANART.TV FOUND")
                                # log( "test_album[0]: %s" % test_album[0] )
                                if low_res:
                                    message, d_success, final_destination, is_canceled = download_art(art["picture"],
                                                                                                      album,
                                                                                                      key_label, "auto",
                                                                                                      background)
                                    if d_success == 1:
                                        download_count += 1
                                        album[key_label] = True
                                        album["path"] = final_destination
                                        successfully_downloaded.append(album)
                                    else:
                                        log("Download Error...  Check Path.")
                                        log("    Path: %s" % repr(album["path"]))
                                        d_error = True
                                else:
                                    pass
                            else:
                                log("ALBUM NOT MATCHED ON FANART.TV INTERNAL")
                        else:
                            log("ALBUM NOT MATCHED ON FANART.TV EXTERNAL")
                    else:
                        log("%s artwork file already exists, skipping..." % key_label)
        dialog_msg("close", background=background)
        if d_error:
            dialog_msg("ok", line1=__lng__(32026), line2="%s: %s" % (__lng__(32041), download_count),
                       background=background)
        else:
            dialog_msg("ok", line1=__lng__(32040), line2="%s: %s" % (__lng__(32041), download_count),
                       background=background)
        return download_count, successfully_downloaded
    except Exception as e:
        xbmc.log(e.message, xbmc.LOGERROR)
        print_exc()
        dialog_msg("close", background=background)
