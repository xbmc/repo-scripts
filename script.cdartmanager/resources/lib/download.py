# -*- coding: utf-8 -*-

import os
import sys
import urllib
from traceback import print_exc

import xbmc

# Helix: PIL is not available in Helix 14.1 on Android
try:
    from PIL import Image

    pil_is_available = True
except:
    pil_is_available = False

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

true = True
false = False
null = None

__language__ = sys.modules["__main__"].__language__
__scriptname__ = sys.modules["__main__"].__scriptname__
__scriptID__ = sys.modules["__main__"].__scriptID__
__author__ = sys.modules["__main__"].__author__
__credits__ = sys.modules["__main__"].__credits__
__credits2__ = sys.modules["__main__"].__credits2__
__version__ = sys.modules["__main__"].__version__
__addon__ = sys.modules["__main__"].__addon__
addon_db = sys.modules["__main__"].addon_db
addon_work_folder = sys.modules["__main__"].addon_work_folder
BASE_RESOURCE_PATH = sys.modules["__main__"].BASE_RESOURCE_PATH
__useragent__ = sys.modules["__main__"].__useragent__
# resizeondownload = eval(__addon__.getSetting("resizeondownload"))
resizeondownload = False  # disabled because fanart.tv API V3 doesn't deliver correct sizes
music_path = sys.modules["__main__"].music_path
enable_hdlogos = sys.modules["__main__"].enable_hdlogos
fanart_limit = sys.modules["__main__"].fanart_limit
enable_fanart_limit = sys.modules["__main__"].enable_fanart_limit
# use temp folder for downloading
tempgfx_folder = sys.modules["__main__"].tempgfx_folder

from fanarttv_scraper import remote_banner_list, remote_hdlogo_list, remote_cdart_list, \
    remote_coverart_list, remote_fanart_list, remote_clearlogo_list, remote_artistthumb_list
from database import get_local_albums_db, artwork_search
from utils import get_unicode, change_characters, log, dialog_msg, smart_unicode
from jsonrpc_calls import get_thumbnail_path, get_fanart_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy
from xbmcvfs import mkdirs as _makedirs
from xbmcvfs import listdir


def check_size(path, type, size_w, size_h):
    # size check is disabled because currently fanart.tv always returns size=1000
    # ref: https://forum.fanart.tv/viewtopic.php?f=4&t=403
    file_name = get_filename(type, path, "auto")
    source = os.path.join(path, file_name)
    if exists(source):
        log("size check n.a. in new fanart.tv API, returning False for %s" % source)
        return False
    else:
        log("size check n.a. in new fanart.tv API, returning True for %s" % source)
        return True

#    # first copy from source to work directory since Python does not support SMB://
#    file_name = get_filename(type, path, "auto")
#    destination = os.path.join(addon_work_folder, "temp", file_name)
#    source = os.path.join(path, file_name)
#    log("Checking Size", xbmc.LOGDEBUG)
#    if exists(source):
#        file_copy(source, destination)
#    else:
#        return True
#    try:
#        # Helix: PIL is not available in Helix 14.1 on Android
#        if (pil_is_available):
#            # Helix: not really a Helix problem but file cannot be removed after Image.open locking it
#            with open(str(destination), 'rb') as destf:
#                artwork = Image.open(destf)
#            log("Image Size: %s px(W) X %s px(H)" % (artwork.size[0], artwork.size[1]), xbmc.LOGDEBUG)
#            if artwork.size[0] < size_w and artwork.size[
#                1] < size_h:  # if image is smaller than 1000 x 1000 and the image on fanart.tv = 1000
#                delete_file(destination)
#                log("Image is smaller", xbmc.LOGDEBUG)
#                return True
#            else:
#                delete_file(destination)
#                log("Image is same size or larger", xbmc.LOGDEBUG)
#                return False
#        else:
#            log("PIL not available, skipping size check", xbmc.LOGDEBUG)
#            return False
#    except:
#        log("artwork does not exist. Source: %s" % source, xbmc.LOGDEBUG)
#        return True


def get_filename(type, url, mode):
    if type == "cdart":
        file_name = "cdart.png"
    elif type == "cover":
        file_name = "folder.jpg"
    elif type == "fanart":
        if mode == "auto":
            file_name = os.path.basename(url)
        else:
            file_name = "fanart.jpg"
    elif type == "clearlogo":
        file_name = "logo.png"
    elif type == "artistthumb":
        file_name = "folder.jpg"
    elif type == "musicbanner":
        file_name = "banner.jpg"
    else:
        file_name = "unknown"
    return file_name


def make_music_path(artist):
    # Helix: paths MUST end with trailing slash
    path = os.path.join(music_path, artist).replace("\\\\", "\\")
    path2 = os.path.join(music_path, str.lower(artist)).replace("\\\\", "\\")
    if not exists(path2):
        if not exists(path):
            if _makedirs(path):
                log("Path to music artist made", xbmc.LOGDEBUG)
                return True
            else:
                log("unable to make path to music artist", xbmc.LOGDEBUG)
                return False
    else:
        if not exists(path):
            if _makedirs(path):
                log("Path to music artist made", xbmc.LOGDEBUG)
                return True
            else:
                log("unable to make path to music artist", xbmc.LOGDEBUG)
                return False


def download_art(url_cdart, album, database_id, type, mode, size, background=False):
    log("Downloading artwork... ", xbmc.LOGDEBUG)
    download_success = False
    thumb_path = ""
    percent = 1
    is_canceled = False
    if mode == "auto":
        dialog_msg("update", percent=percent, background=background)
    else:
        dialog_msg("create", heading=__language__(32047), background=background)
        # Onscreen Dialog - "Downloading...."
    file_name = get_filename(type, url_cdart, mode)
    # Helix: paths MUST end with trailing slash
    path = os.path.join(album["path"].replace("\\\\", "\\"), '')
    if file_name == "unknown":
        log("Unknown Type ", xbmc.LOGDEBUG)
        message = [__language__(32026), __language__(32025), "File: %s" % get_unicode(path),
                   "Url: %s" % get_unicode(url_cdart)]
        return message, download_success
    if type in ("artistthumb", "cover"):
        thumbnail_path = get_thumbnail_path(database_id, type)
    else:
        thumbnail_path = ""
    if type == "fanart" and mode in ("manual", "single"):
        thumbnail_path = get_fanart_path(database_id, type)
    if not exists(path):
        try:
            pathsuccess = _makedirs(album["path"].replace("\\\\", "\\"))
        except:
            pass
    log("Path: %s" % path, xbmc.LOGDEBUG)
    log("Filename: %s" % file_name, xbmc.LOGDEBUG)
    log("url: %s" % url_cdart, xbmc.LOGDEBUG)

    # cosmetic: use subfolder for downloading instead of work folder
    if not exists(os.path.join(tempgfx_folder, '').replace("\\\\", "\\")):
        _makedirs(os.path.join(tempgfx_folder, '').replace("\\\\", "\\"))
    destination = os.path.join(tempgfx_folder, file_name).replace("\\\\", "\\")  # download to work folder first
    final_destination = os.path.join(path, file_name).replace("\\\\", "\\")
    try:
        # this give the ability to use the progress bar by retrieving the downloading information
        # and calculating the percentage
        def _report_hook(count, blocksize, totalsize):
            try:
                percent = int(float(count * blocksize * 100) / totalsize)
                if percent < 1:
                    percent = 1
                if percent > 100:
                    percent = 100
            except:
                percent = 1
            if type in ("fanart", "clearlogo", "artistthumb", "musicbanner"):
                dialog_msg("update", percent=percent,
                           line1="%s%s" % (__language__(32038), get_unicode(album["artist"])), background=background)
            else:
                dialog_msg("update", percent=percent,
                           line1="%s%s" % (__language__(32038), get_unicode(album["artist"])),
                           line2="%s%s" % (__language__(32039), get_unicode(album["title"])), background=background)
            if mode == "auto":
                if dialog_msg("iscanceled", background=background):
                    is_canceled = True

        if exists(path):
            log("Fetching image: %s" % url_cdart, xbmc.LOGDEBUG)
            fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
            # message = ["Download Sucessful!"]
            message = [__language__(32023), __language__(32024), "File: %s" % get_unicode(path), "Url: %s" % get_unicode(url_cdart)]
            success = file_copy(destination, final_destination)  # copy it to album folder
            # update database
            try:
                conn = sqlite3.connect(addon_db)
                c = conn.cursor()
                if type == "cdart":
                    c.execute('''UPDATE alblist SET cdart="True" WHERE path="%s"''' % (get_unicode(album["path"])))
                elif type == "cover":
                    c.execute('''UPDATE alblist SET cover="True" WHERE path="%s"''' % (get_unicode(album["path"])))
                conn.commit()
                c.close()
            except:
                log("Error updating database", xbmc.LOGDEBUG)
                print_exc()
            download_success = True

        else:
            log("Path error", xbmc.LOGDEBUG)
            log("    file path: %s" % repr(destination), xbmc.LOGDEBUG)
            message = [__language__(32026), __language__(32025), "File: %s" % get_unicode(path), "Url: %s" % get_unicode(url_cdart)]
            # message = Download Problem, Check file paths - Artwork Not Downloaded]
        # always cleanup downloaded files
        # if type == "fanart":
        delete_file(destination)
    except:
        log("General download error", xbmc.LOGDEBUG)
        message = [__language__(32026), __language__(32025), "File: %s" % get_unicode(path),
                   "Url: %s" % get_unicode(url_cdart)]
        # message = [Download Problem, Check file paths - Artwork Not Downloaded]
        # print_exc()
    if mode == "auto" or mode == "single":
        return message, download_success, final_destination, is_canceled  # returns one of the messages built based on success or lack of
    else:
        dialog_msg("close", background=background)
        return message, download_success, is_canceled


def cdart_search(cdart_url, id, disc):
    cdart = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id and item["disc"] == disc:
            cdart = item
            break
    return cdart


# Automatic download of non existing cdarts and refreshes addon's db
def auto_download(type, artist_list, background=False):
    is_canceled = False
    log("Autodownload", xbmc.LOGDEBUG)
    try:
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        d_error = False
        percent = 1
        successfully_downloaded = []
        if type in ("clearlogo_allartists", "artistthumb_allartists", "fanart_allartists", "musicbanner_allartists"):
            if type == "clearlogo_allartists":
                type = "clearlogo"
            elif type == "artistthumb_allartists":
                type = "artistthumb"
            elif type == "musicbanner_allartists":
                type = "musicbanner"
            else:
                type = "fanart"
        count_artist_local = len(artist_list)
        dialog_msg("create", heading=__language__(32046), background=background)
        # Onscreen Dialog - Automatic Downloading of Artwork
        key_label = type
        for artist in artist_list:
            if dialog_msg("iscanceled", background=background) or is_canceled:
                is_canceled = True
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
            log("Artist: %-40s Local ID: %-10s   Distant MBID: %s" % (artist["name"], artist["local_id"], artist["musicbrainz_artistid"]), xbmc.LOGNOTICE)
            if type in ("fanart", "clearlogo", "artistthumb", "musicbanner") and artist["has_art"]:
                dialog_msg("update", percent=percent, line1="%s%s" % (__language__(32038), get_unicode(artist["name"])),
                           background=background)
                auto_art = {}
                temp_art = {}
                temp_art["musicbrainz_artistid"] = artist["musicbrainz_artistid"]
                auto_art["musicbrainz_artistid"] = artist["musicbrainz_artistid"]
                temp_art["artist"] = artist["name"]
                auto_art["artist"] = artist["name"]
                path = os.path.join(music_path, change_characters(smart_unicode(artist["name"])))
                if type == "fanart":
                    art = remote_fanart_list(auto_art)
                elif type == "clearlogo":
                    art = remote_clearlogo_list(auto_art)
                    arthd = remote_hdlogo_list(auto_art)
                elif type == "musicbanner":
                    art = remote_banner_list(auto_art)
                else:
                    art = remote_artistthumb_list(auto_art)
                if art:
                    if type == "fanart":
                        temp_art["path"] = path
                        auto_art["path"] = os.path.join(path, "extrafanart").replace("\\\\", "\\")
                        if not exists(auto_art["path"]):
                            try:
                                if _makedirs(auto_art["path"]):
                                    log("extrafanart directory made", xbmc.LOGDEBUG)
                            except:
                                print_exc()
                                log("unable to make extrafanart directory", xbmc.LOGDEBUG)
                                continue
                        else:
                            log("extrafanart directory already exists", xbmc.LOGDEBUG)
                    else:
                        auto_art["path"] = path
                    if type == "fanart":
                        if enable_fanart_limit:
                            fanart_dir, fanart_files = listdir(auto_art["path"])
                            fanart_number = len(fanart_files)
                            if fanart_number == fanart_limit:
                                continue
                        if not exists(os.path.join(path, "fanart.jpg").replace("\\\\", "\\")):
                            message, d_success, final_destination, is_canceled = download_art(art[0], temp_art,
                                                                                              artist["local_id"],
                                                                                              "fanart", "single", 0,
                                                                                              background)
                        for artwork in art:
                            fanart = {}
                            if enable_fanart_limit and fanart_number == fanart_limit:
                                log("Fanart Limit Reached", xbmc.LOGNOTICE)
                                continue
                            if exists(os.path.join(auto_art["path"], os.path.basename(artwork))):
                                log("Fanart already exists, skipping", xbmc.LOGDEBUG)
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  artist["local_id"],
                                                                                                  "fanart", "auto", 0,
                                                                                                  background)
                            if d_success == 1:
                                if enable_fanart_limit:
                                    fanart_number += 1
                                download_count += 1
                                fanart["artist"] = auto_art["artist"]
                                fanart["path"] = final_destination
                                successfully_downloaded.append(fanart)
                            else:
                                log("Download Error...  Check Path.", xbmc.LOGDEBUG)
                                log("    Path: %s" % auto_art["path"], xbmc.LOGDEBUG)
                                d_error = True
                    else:
                        if type == "clearlogo":
                            if arthd and enable_hdlogos:
                                artwork = arthd[0]
                            else:
                                artwork = art[0]
                        else:
                            artwork = art[0]
                        if type == "artistthumb":
                            if resizeondownload:
                                low_res = check_size(auto_art["path"], key_label, 1000, 1000)
                            # Fixed always redownloading Thumbs
                            else:
                                low_res = False
                            if exists(os.path.join(auto_art["path"], "folder.jpg")) and not low_res:
                                log("Artist Thumb already exists, skipping", xbmc.LOGDEBUG)
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  artist["local_id"],
                                                                                                  "artistthumb", "auto",
                                                                                                  0, background)
                        elif type == "clearlogo":
                            if enable_hdlogos and resizeondownload and arthd:
                                low_res = check_size(auto_art["path"], key_label, 800, 310)
                            else:
                                low_res = False
                            if exists(os.path.join(auto_art["path"], "logo.png")) and not low_res:
                                log("ClearLOGO already exists, skipping", xbmc.LOGDEBUG)
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  artist["local_id"],
                                                                                                  "clearlogo", "auto",
                                                                                                  0, background)
                        elif type == "musicbanner":
                            if exists(os.path.join(auto_art["path"], "banner.jpg")):
                                log("Music Banner already exists, skipping", xbmc.LOGDEBUG)
                                continue
                            else:
                                message, d_success, final_destination, is_canceled = download_art(artwork, auto_art,
                                                                                                  artist["local_id"],
                                                                                                  "musicbanner", "auto",
                                                                                                  0, background)
                        if d_success == 1:
                            download_count += 1
                            auto_art["path"] = final_destination
                            successfully_downloaded.append(auto_art)
                        else:
                            log("Download Error...  Check Path.", xbmc.LOGDEBUG)
                            log("    Path: %s" % auto_art["path"], xbmc.LOGDEBUG)
                            d_error = True
                else:
                    log("Artist Match not found", xbmc.LOGDEBUG)
            elif type in ("cdart", "cover") and artist["has_art"]:
                local_album_list = get_local_albums_db(artist["name"], background)
                if type == "cdart":
                    remote_art_url = remote_cdart_list(artist)
                else:
                    remote_art_url = remote_coverart_list(artist)
                for album in local_album_list:
                    low_res = True
                    if dialog_msg("iscanceled", background=background):
                        break
                    if not remote_art_url:
                        log("No artwork found", xbmc.LOGDEBUG)
                        break
                    album_count += 1
                    if not album["musicbrainz_albumid"]:
                        continue
                    dialog_msg("update", percent=percent,
                               line1="%s%s" % (__language__(32038), get_unicode(artist["name"])),
                               line2="%s%s" % (__language__(32039), get_unicode(album["title"])), background=background)
                    name = artist["name"]
                    title = album["title"]
                    log("Album: %s" % album["title"], xbmc.LOGDEBUG)
                    if not album[key_label] or resizeondownload:
                        musicbrainz_albumid = album["musicbrainz_albumid"]
                        art = artwork_search(remote_art_url, musicbrainz_albumid, album["disc"], key_label)
                        if art:
                            if resizeondownload:
                                low_res = check_size(album["path"].replace("\\\\", "\\"), key_label, art["size"], art["size"])
                            if art["picture"]:
                                log("ALBUM MATCH ON FANART.TV FOUND", xbmc.LOGDEBUG)
                                # log( "test_album[0]: %s" % test_album[0], xbmc.LOGDEBUG )
                                if low_res:
                                    message, d_success, final_destination, is_canceled = download_art(art["picture"],
                                                                                                      album,
                                                                                                      album["local_id"],
                                                                                                      key_label, "auto",
                                                                                                      0, background)
                                    if d_success == 1:
                                        download_count += 1
                                        album[key_label] = True
                                        album["path"] = final_destination
                                        successfully_downloaded.append(album)
                                    else:
                                        log("Download Error...  Check Path.", xbmc.LOGDEBUG)
                                        log("    Path: %s" % repr(album["path"]), xbmc.LOGDEBUG)
                                        d_error = True
                                else:
                                    pass
                            else:
                                log("ALBUM NOT MATCHED ON FANART.TV", xbmc.LOGDEBUG)
                        else:
                            log("ALBUM NOT MATCHED ON FANART.TV", xbmc.LOGDEBUG)
                    else:
                        log("%s artwork file already exists, skipping..." % key_label, xbmc.LOGDEBUG)
        dialog_msg("close", background=background)
        if d_error:
            dialog_msg("ok", line1=__language__(32026), line2="%s: %s" % (__language__(32041), download_count),
                       background=background)
        else:
            dialog_msg("ok", line1=__language__(32040), line2="%s: %s" % (__language__(32041), download_count),
                       background=background)
        return download_count, successfully_downloaded
    except:
        print_exc()
        dialog_msg("close", background=background)
