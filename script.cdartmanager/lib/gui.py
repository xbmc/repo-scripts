# -*- coding: utf-8 -*-
# system imports
import calendar
import os
import traceback
import copy
from datetime import datetime

import xbmc
import xbmcgui
import xbmcvfs

import json

import cdam
import cdam_utils as cu
import cdam_fs
import cdam_db

import download
import ftv_scraper
import mb_utils

from cdam_utils import log, dialog_msg
from cdam_fs import sanitize
from cdam import Color, ArtType, FileName

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()
__lng__ = __cdam__.getLocalizedString

kb = xbmc.Keyboard()
KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467


class GUI(xbmcgui.WindowXMLDialog):

    def __init__(self, xml_filename, script_path):
        super(GUI, self).__init__(xml_filename, script_path)
        log("# Setting up Script", xbmc.LOGNOTICE)
        self.image = __cdam__.file_icon()
        self.background = False
        self.menu_mode = 0
        self.artist_menu = {}
        self.album_menu = {}
        self.remote_cdart_url = []
        self.all_artists = []
        self.cdart_url = []
        self.local_artists = []
        self.local_albums = []
        self.label_1 = ""
        self.label_2 = self.image
        self.cdartimg = ""
        self.artwork_type = ""
        self.artists = []
        self.albums = []
        self.album_artists = []
        self.all_artists_list = []
        self.recognized_artists = []
        self.selected_item = 0

    def onInit(self):
        # checking to see if addon_db exists, if not, run database_setup()
        if xbmcvfs.exists(sanitize(__cdam__.file_addon_db()).encode("utf-8")):
            log("Addon Db found - Loading Counts", xbmc.LOGNOTICE)
            _, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
        else:
            log("Addon Db Not Found - Building New Addon Db", xbmc.LOGNOTICE)
            local_album_count, local_artist_count, local_cdart_count = cdam_db.database_setup(self.background)
            self.local_artists = cdam_db.get_local_artists_db()  # retrieve data from addon's database
            self.setFocusId(100)  # set menu selection to the first option(cdARTs)
            local_artists = cdam_db.get_local_artists_db(mode="album_artists")
            if __cfg__.enable_all_artists():
                all_artists = cdam_db.get_local_artists_db(mode="all_artists")
            else:
                all_artists = []
            ftv_scraper.first_check(all_artists, local_artists)
        self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
        self.local_artists = cdam_db.get_local_artists_db()  # retrieve data from addon's database
        self.setFocusId(100)  # set menu selection to the first option(cdARTs)
        album_artists = cdam_db.get_local_artists_db(mode="album_artists")
        if __cfg__.enable_all_artists():
            all_artists = cdam_db.get_local_artists_db(mode="all_artists")
        else:
            all_artists = []
        present_datecode = calendar.timegm(datetime.utcnow().utctimetuple())
        new_artwork, _ = ftv_scraper.check_fanart_new_artwork(present_datecode)
        if new_artwork:
            self.all_artists_list, self.album_artists = ftv_scraper.get_recognized(all_artists, album_artists)
        else:
            self.all_artists_list = all_artists
            self.album_artists = album_artists

    # creates the album list on the skin
    def populate_album_list(self, art_url, focus_item, _type):
        log("Populating Album List", xbmc.LOGNOTICE)
        self.getControl(122).reset()
        if not art_url:
            # no cdart found
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            xbmcgui.Window(10001).clearProperty("artwork")
            dialog_msg("ok", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031))
            # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
            # return
        else:
            local_album_list = cdam_db.get_local_albums_db(art_url[0]["local_name"], self.background)
            log("Building album list", xbmc.LOGNOTICE)
            empty_list = False
            check = False
            try:
                for album in local_album_list:
                    if _type == ArtType.CDART:
                        art_image = __cdam__.file_missing_cdart()
                        filename = FileName.CDART
                    else:
                        art_image = __cdam__.file_missing_cover()
                        filename = FileName.FOLDER
                    empty_list = False
                    if album["disc"] > 1:
                        label1 = "%s - %s %s" % (album["title"], __lng__(32016), album["disc"])
                    else:
                        label1 = album["title"]
                    musicbrainz_albumid = album["musicbrainz_albumid"]
                    if not musicbrainz_albumid:
                        empty_list = True
                        continue
                    else:
                        check = True
                    # check to see if there is a thumb
                    artwork = cdam_db.artwork_search(art_url, musicbrainz_albumid, album["disc"], _type)
                    if not artwork:
                        temp_path = sanitize(os.path.join(album["path"], filename))
                        if xbmcvfs.exists(temp_path):
                            url = art_image = temp_path
                            color = Color.ORANGE
                        else:
                            url = art_image
                            color = Color.WHITE
                    else:
                        if artwork["picture"]:
                            # check to see if artwork already exists
                            # set the matched colour local and distant colour
                            # colour the label to the matched colour if not
                            url = artwork["picture"]
                            if album[_type]:
                                art_image = sanitize(os.path.join(album["path"], filename))
                                color = Color.YELLOW
                            else:
                                art_image = url + "/preview"
                                color = Color.GREEN
                        else:
                            url = ""
                            if album[_type]:
                                art_image = sanitize(os.path.join(album["path"], filename))
                                color = Color.ORANGE
                            else:
                                art_image = url
                                color = Color.WHITE

                    data = copy.deepcopy(album)
                    data['url'] = url
                    cu.clear_image_cache(art_image)
                    listitem = xbmcgui.ListItem(label=cu.coloring(label1, color),
                                                label2=json.dumps(data), thumbnailImage=art_image)
                    self.getControl(122).addItem(listitem)
                    self.cdart_url = art_url
            except Exception as e:
                log("Error in script occured", xbmc.LOGNOTICE)
                log(e.message, xbmc.LOGWARNING)
                traceback.print_exc()
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            if (not empty_list) or check:
                self.setFocus(self.getControl(122))
                self.getControl(122).selectItem(focus_item)
            else:
                xbmcgui.Window(10001).clearProperty("artwork")
                dialog_msg("ok", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031))
                # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
        return

    def populate_album_list_mbid(self, local_album_list, selected_item=0):
        log("MBID Edit - Populating Album List", xbmc.LOGNOTICE)
        if not local_album_list:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            return
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        try:
            for album in local_album_list:
                label2 = "%s MBID: %s[CR][COLOR=7fffffff]%s MBID: %s[/COLOR]" % (
                    __lng__(32138), album["musicbrainz_albumid"], __lng__(32137),
                    album["musicbrainz_artistid"])
                label1 = "%s: %s[CR][COLOR=7fffffff]%s: %s[/COLOR][CR][COLOR=FFE85600]%s[/COLOR]" % (
                    __lng__(32138), album["title"], __lng__(32137), album["artist"], album["path"])
                listitem = xbmcgui.ListItem(label=label1, label2=label2)
                self.getControl(145).addItem(listitem)
                listitem.setLabel(label1)
                listitem.setLabel2(label2)
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.setFocus(self.getControl(145))
        self.getControl(145).selectItem(selected_item)
        return

    def populate_search_list_mbid(self, mbid_list, _type="artist", selected_item=0):
        log("MBID Search - Populating Search List", xbmc.LOGNOTICE)
        if not mbid_list:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            return
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        if _type == "artists":
            try:
                for item in mbid_list:
                    label2 = "MBID: %s" % item["id"]
                    label1 = "%-3s%%: %s" % (item["score"], item["name"])
                    li = xbmcgui.ListItem(label=cu.coloring(label1, Color.WHITE), label2=label2)
                    self.getControl(161).addItem(li)
                    li.setLabel(cu.coloring(label1, Color.WHITE))
                    li.setLabel2(label2)
            except Exception as e:
                log("Error in script occured", xbmc.LOGNOTICE)
                log(e.message, xbmc.LOGWARNING)
                traceback.print_exc()
        elif _type == "albums":
            try:
                for item in mbid_list:
                    label2 = "%s MBID: %s[CR][COLOR=7fffffff]%s MBID: %s[/COLOR]" % (
                        __lng__(32138), item["id"], __lng__(32137), item["artist_id"])
                    label1 = "%-3s%%  %s: %s[CR][COLOR=7fffffff]%s: %s[/COLOR]" % (
                        item["score"], __lng__(32138), item["title"], __lng__(32137), item["artist"])
                    li = xbmcgui.ListItem(label=label1, label2=label2)
                    self.getControl(161).addItem(li)
                    li.setLabel(label1)
                    li.setLabel2(label2)
            except Exception as e:
                log("Error in script occured", xbmc.LOGNOTICE)
                log(e.message, xbmc.LOGWARNING)
                traceback.print_exc()
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.setFocus(self.getControl(161))
        self.getControl(161).selectItem(selected_item)
        return

    def populate_artist_list_mbid(self, local_artist_list, selected_item=0):
        log("MBID Edit - Populating Artist List", xbmc.LOGNOTICE)
        if not local_artist_list:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            return
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        try:
            for artist in local_artist_list:
                label2 = "MBID: %s" % artist["musicbrainz_artistid"]
                label1 = artist["name"]
                listitem = xbmcgui.ListItem(label=label1, label2=label2)
                self.getControl(145).addItem(listitem)
                listitem.setLabel(label1)
                listitem.setLabel2(label2)
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.setFocus(self.getControl(145))
        self.getControl(145).selectItem(selected_item)
        return

    # creates the artist list on the skin
    def populate_artist_list(self, local_artist_list):
        log("Populating Artist List", xbmc.LOGNOTICE)
        if not local_artist_list:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            return
        try:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            for artist in local_artist_list:
                if artist["has_art"] != "False":
                    listitem = xbmcgui.ListItem(label=cu.coloring(artist["name"], Color.GREEN))
                    self.getControl(120).addItem(listitem)
                    listitem.setLabel(cu.coloring(artist["name"], Color.GREEN))
                else:
                    listitem = xbmcgui.ListItem(label=artist["name"])
                    self.getControl(120).addItem(listitem)
                    listitem.setLabel(cu.coloring(artist["name"], Color.WHITE))
        except KeyError:
            for artist in local_artist_list:
                label2 = "MBID: %s" % artist["musicbrainz_artistid"]
                label1 = artist["name"]
                listitem = xbmcgui.ListItem(label=label1, label2=label2)
                self.getControl(120).addItem(listitem)
                listitem.setLabel(label1)
                listitem.setLabel2(label2)
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.setFocus(self.getControl(120))
        self.getControl(120).selectItem(0)
        return

    def populate_fanarts(self, artist_menu, focus_item):
        log("Populating Fanart List", xbmc.LOGNOTICE)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(160).reset()
        try:
            fanart = ftv_scraper.remote_fanart_list(artist_menu)
            if fanart:
                for artwork in fanart:
                    data = copy.deepcopy(artist_menu)
                    data['url'] = artwork
                    listitem = xbmcgui.ListItem(label=os.path.basename(artwork),
                                                label2=json.dumps(data),
                                                thumbnailImage=artwork + "/preview")
                    self.getControl(160).addItem(listitem)
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    self.setFocus(self.getControl(160))
                    self.getControl(160).selectItem(focus_item)
            else:
                log("[script.cdartmanager - No Fanart for this artist", xbmc.LOGNOTICE)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmcgui.Window(10001).clearProperty("artwork")
                dialog_msg("ok", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031))
                # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def populate_musicbanners(self, artist_menu, focus_item):
        log("Populating Music Banner List", xbmc.LOGNOTICE)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(202).reset()
        try:
            banner = ftv_scraper.remote_banner_list(artist_menu)
            if banner:
                for artwork in banner:
                    cu.clear_image_cache(artwork)
                    data = copy.deepcopy(artist_menu)
                    data['url'] = artwork
                    listitem = xbmcgui.ListItem(label=os.path.basename(artwork),
                                                label2=json.dumps(data),
                                                thumbnailImage=artwork + "/preview")
                    self.getControl(202).addItem(listitem)
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    self.setFocus(self.getControl(202))
                    self.getControl(202).selectItem(focus_item)
            else:
                log("[script.cdartmanager - No Music Banners for this artist", xbmc.LOGNOTICE)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmcgui.Window(10001).clearProperty("artwork")
                dialog_msg("ok", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031))
                # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def populate_clearlogos(self, artist_menu, focus_item):
        log("Populating ClearLOGO List", xbmc.LOGNOTICE)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(167).reset()
        not_found = False
        try:
            clearlogo = ftv_scraper.remote_clearlogo_list(artist_menu)
            hdlogo = ftv_scraper.remote_hdlogo_list(artist_menu)
            if clearlogo:
                for artwork in clearlogo:
                    cu.clear_image_cache(artwork)
                    data = copy.deepcopy(artist_menu)
                    data['url'] = artwork
                    listitem = xbmcgui.ListItem(label=__lng__(32169), label2=json.dumps(data),
                                                thumbnailImage=artwork + "/preview")
                    self.getControl(167).addItem(listitem)
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    self.setFocus(self.getControl(167))
                    self.getControl(167).selectItem(focus_item)
            else:
                not_found = True
            if hdlogo:
                for artwork in hdlogo:
                    cu.clear_image_cache(artwork)
                    data = copy.deepcopy(artist_menu)
                    data['url'] = artwork
                    listitem = xbmcgui.listitem = xbmcgui.ListItem(label=__lng__(32170), label2=json.dumps(data),
                                                                   thumbnailImage=artwork + "/preview")
                    self.getControl(167).addItem(listitem)
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    self.setFocus(self.getControl(167))
                    self.getControl(167).selectItem(focus_item)
            else:
                if not_found:
                    not_found = True
            if not_found:
                log("[script.cdartmanager - No ClearLOGO for this artist", xbmc.LOGNOTICE)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmcgui.Window(10001).clearProperty("artwork")
                dialog_msg("ok", heading=__lng__(32033), line1=__lng__(32030), line2=__lng__(32031))
                # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def populate_artistthumbs(self, artist_menu, focus_item):
        log("Populating artist thumb List", xbmc.LOGNOTICE)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(199).reset()
        try:
            artistthumb = ftv_scraper.remote_artistthumb_list(artist_menu)
            if artistthumb:
                for artwork in artistthumb:
                    cu.clear_image_cache(artwork)
                    data = copy.deepcopy(artist_menu)
                    data['url'] = artwork
                    listitem = xbmcgui.ListItem(label=os.path.basename(artwork), label2=json.dumps(data),
                                                thumbnailImage=artwork + "/preview")
                    self.getControl(199).addItem(listitem)
                    listitem.setLabel(os.path.basename(artwork))
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    self.setFocus(self.getControl(199))
                    self.getControl(199).selectItem(focus_item)
            else:
                log("[script.cdartmanager - No artist thumb for this artist", xbmc.LOGNOTICE)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmcgui.Window(10001).clearProperty("artwork")
                xbmcgui.Dialog().ok(__lng__(32033), __lng__(32030), __lng__(32031))
                # Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except Exception as e:
            cu.log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            traceback.print_exc()
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def populate_downloaded(self, successfully_downloaded, _type):
        log("Populating downloaded items", xbmc.LOGNOTICE)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(404).reset()
        xbmcgui.Window(10001).setProperty("artwork", _type)
        for item in successfully_downloaded:
            try:
                try:
                    listitem = xbmcgui.ListItem(label=item["artist"], label2=item["title"], thumbnailImage=item["path"])
                except Exception as e:
                    listitem = xbmcgui.ListItem(label=item["artist"], label2="", thumbnailImage=item["path"])
                    log(e.message)
                self.getControl(404).addItem(listitem)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                self.setFocus(self.getControl(404))
                self.getControl(404).selectItem(0)
            except Exception as e:
                log("Error in script occured", xbmc.LOGNOTICE)
                log(e.message, xbmc.LOGWARNING)
                traceback.print_exc()
                xbmc.executebuiltin("Dialog.Close(busydialog)")

    def populate_local_cdarts(self, focus_item=None):
        log("Populating Local cdARTS", xbmc.LOGNOTICE)
        l_artist = cdam_db.get_local_albums_db("all artists", self.background)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.getControl(140).reset()
        for album in l_artist:
            if album[ArtType.CDART]:
                cdart_img = os.path.join(album["path"], FileName.CDART)
                data = copy.deepcopy(album)
                data['cdart_img'] = cdart_img
                label1 = "%s * %s" % (data["artist"], data["title"])
                if album["disc"] > 1:
                    label1 += " * DISC%s" % album["disc"]
                listitem = xbmcgui.ListItem(label=cu.coloring(label1, Color.YELLOW), label2=json.dumps(data),
                                            thumbnailImage=cdart_img)
                self.getControl(140).addItem(listitem)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.setFocus(self.getControl(140))
        if focus_item is not None:
            self.getControl(140).selectItem(focus_item)
        return

    @staticmethod
    def cdart_delete(fn, path):
        if cdam_fs.cdart_single_delete(fn):
            cdam_db.unset_cdart(path)

    # backup all cdArt
    def restore_cdart(self):
        log("Copying cdARTs from Backup folder", xbmc.LOGNOTICE)
        albums = cdam_db.get_local_albums_db("all artists", self.background)
        total = 0
        copied = 0
        dialog_msg("create", heading=__lng__(32069))
        for album in albums:
            if dialog_msg("iscanceled"):
                break
            total += 1
            target = sanitize(os.path.join(album["path"], FileName.CDART))
            if cdam_fs.cdart_single_restore(target, album["artist"], album["title"], album["disc"]):
                copied += 1
                cdam_db.set_has_art(ArtType.CDART, album["path"])
            dialog_msg("update", percent=cu.percent_of(total, len(albums)), line1="%s" % target,
                       line2="%s: %s" % (__lng__(32056), copied))
        dialog_msg("close")
        dialog_msg("ok", heading=__lng__(32057), line1="%s: %s" % (__lng__(32058), __cfg__.path_backup_path()),
                   line2="%s %s" % (copied, __lng__(32059)))
        return

    # backup all cdArt
    def backup_cdart(self):
        log("Copying cdARTs to Backup folder", xbmc.LOGNOTICE)
        albums = cdam_db.get_local_albums_db("all artists", self.background)
        total = 0
        copied = 0
        dialog_msg("create", heading=__lng__(32060))
        for album in albums:
            if dialog_msg("iscanceled"):
                break
            total += 1
            if album[ArtType.CDART]:
                source = sanitize(os.path.join(album["path"], FileName.CDART))
                if cdam_fs.cdart_single_backup(source, album["artist"], album["title"], album["disc"]):
                    copied += 1
                dialog_msg("update", percent=cu.percent_of(total, len(albums)), line1="%s" % source,
                           line2="%s: %s" % (__lng__(32056), copied))
            else:
                pass
        dialog_msg("close")
        dialog_msg("ok", heading=__lng__(32057), line1="%s: %s" % (__lng__(32058), __cfg__.path_backup_path()),
                   line2="%s %s" % (copied, __lng__(32059)))
        return

    # Search for missing cdARTs and save to missing.txt in Missing List path
    def missing_list(self):
        log("Saving missing.txt file", xbmc.LOGNOTICE)
        count = 0
        percent = 0
        missing_path = __cfg__.path_missing_path()
        albums = cdam_db.get_local_albums_db("all artists", self.background)
        artists = cdam_db.get_local_artists_db(mode="local_artists")
        if not artists:
            artists = cdam_db.get_local_artists_db(mode="album_artists")
        dialog_msg("create", heading=__lng__(32103), line1=__lng__(20186), line2="", line3="")
        temp_destination = os.path.join(__cdam__.path_profile(), "missing.txt")
        try:
            missing = open(temp_destination, "wb")
            dialog_msg("update", percent=percent)
            missing.write("Albums Missing Artwork\r\n")
            missing.write("\r")
            missing.write("|  %-45s|  %-75s              |  %-50s|  cdART  |  Cover  |\r\n" % (
                "MusicBrainz ID", "Album Title", "Album Artist"))
            missing.write("-" * 214)
            missing.write("\r\n")
            for album in albums:
                count += 1
                if dialog_msg("iscanceled"):
                    break
                dialog_msg("update", percent=cu.percent_of(count, len(albums)), line1=__lng__(32103),
                           line2=" %s: %s" % (__lng__(32039), cu.get_unicode(album["title"])), line3="")
                if album[ArtType.CDART] and album[ArtType.COVER]:
                    continue
                else:
                    cdart = "X" if album[ArtType.CDART] else " "
                    cover = "X" if album[ArtType.COVER] else " "
                    if int(album["disc"]) > 1:
                        line = "|  %-45s| %-75s     disc#: %2s |  %-50s|    %s    |    %s    |\r\n" % (
                            album["musicbrainz_albumid"], album["title"], album["disc"], album["artist"], cdart, cover)
                    elif int(album["disc"]) == 1:
                        line = "|  %-45s| %-75s               |  %-50s|    %s    |    %s    |\r\n" % (
                            album["musicbrainz_albumid"], album["title"], album["artist"], cdart, cover)
                    else:
                        line = ""
                    if line:
                        try:
                            missing.write(line.encode("utf8"))
                        except Exception as e:
                            log("Error in script occured", xbmc.LOGNOTICE)
                            log(e.message, xbmc.LOGWARNING)
                            missing.write(repr(line))
                        missing.write("-" * 214)
                        missing.write("\r\n")
            missing.write("\r\n")
            dialog_msg("update", percent=50)
            missing.write("Artists Missing Artwork\r\n")
            missing.write("\r\n")
            missing.write("|  %-45s| %-70s| Fanart | clearLogo | Artist Thumb | Music Banner |\r\n" % (
                "MusicBrainz ID", "Artist Name"))
            missing.write("-" * 172)
            missing.write("\r\n")
            count = 0
            for artist in artists:
                count += 1
                if dialog_msg("iscanceled"):
                    break
                dialog_msg("update", percent=cu.percent_of(count, len(artists)), line1=__lng__(32103),
                           line2=" %s: %s" % (__lng__(32038), cu.get_unicode(artist["name"])), line3="")

                line = ""
                fanart = "X" if xbmcvfs.exists(cdam_fs.get_artist_path(artist["name"], FileName.FANART)) else " "
                clearlogo = "X" if xbmcvfs.exists(cdam_fs.get_artist_path(artist["name"], FileName.LOGO)) else " "
                thumb = "X" if xbmcvfs.exists(cdam_fs.get_artist_path(artist["name"], FileName.FOLDER)) else " "
                banner = "X" if xbmcvfs.exists(cdam_fs.get_artist_path(artist["name"], FileName.BANNER)) else " "

                if fanart == " " or clearlogo == " " or thumb == " " or banner == " ":
                    line = "|  %-45s| %-70s|    %s   |    %s      |      %s       |      %s       |\r\n" % (
                        artist["musicbrainz_artistid"], artist["name"], fanart, clearlogo, thumb, banner)
                if line:
                    try:
                        missing.write(line.encode("utf8"))
                    except Exception as ex:
                        log(ex.message)
                        missing.write(repr(line))
                    missing.write("-" * 172)
                    missing.write("\r\n")
            missing.close()
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            log("Error saving missing.txt file", xbmc.LOGNOTICE)
            traceback.print_exc()
        if xbmcvfs.exists(temp_destination) and missing_path:
            if missing_path:
                xbmcvfs.copy(temp_destination, os.path.join(missing_path, "missing.txt"))
            else:
                log("Path for missing.txt file not provided", xbmc.LOGNOTICE)
        dialog_msg("close")

    def refresh_counts(self, local_album_count, local_artist_count, local_cdart_count):
        log("Refreshing Counts", xbmc.LOGNOTICE)
        self.getControl(109).setLabel(__lng__(32007) % local_artist_count)
        self.getControl(110).setLabel(__lng__(32010) % local_album_count)
        self.getControl(112).setLabel(__lng__(32008) % local_cdart_count)

    # This selects which cdART image shows up in the display box (image id 210)
    def cdart_icon(self):
        try:  # If there is information in label 2 of list id 140(local album list)
            label2 = self.getControl(140).getSelectedItem().getLabel2()
            data = cu.from_json_simple(label2)
            cdart = sanitize(data['cdart_img'])
            log("# cdART image: %s" % cdart, xbmc.LOGDEBUG)
            if cdart and xbmcvfs.exists(cdart):  # Test to see if there is a path in local_cdart
                self.getControl(210).setImage(cdart)
            else:
                self.getControl(210).setImage(self.image)
        except Exception as ex:  # If there is not any information in any of those locations, no image.
            log(ex.message)
            traceback.print_exc()
            self.getControl(210).setImage(self.image)

    def clear_artwork(self):
        self.getControl(211).setImage(self.image)
        self.getControl(210).setImage(self.image)

    @staticmethod
    def popup(header, line1, line2, line3):
        dialog_msg("create", heading=header, line1=line1, line2=line2, line3=line3)
        xbmc.sleep(2000)
        dialog_msg("close")

    def get_mbid_keyboard(self, type_="artist"):
        mbid = "canceled"
        if type_ == "artist":
            kb.setHeading(__lng__(32159))
        elif type_ == "albumartist":
            kb.setHeading(__lng__(32159))
        elif type_ == "album":
            kb.setHeading(__lng__(32166))
        kb.doModal()
        while 1:
            if not (kb.isConfirmed()):
                canceled = True
                break
            else:
                mbid = kb.getText()
                if type_ == "artist":
                    if len(mbid) == 0 and len(self.artist_menu["musicbrainz_artistid"]) != 0:
                        if dialog_msg("yesno", heading=__lng__(32163),
                                      line1=self.artist_menu["musicbrainz_artistid"]):
                            canceled = False
                            break
                elif type_ == "albumartist":
                    if len(mbid) == 0 and len(self.artist_menu["musicbrainz_artistid"]) != 0:
                        if dialog_msg("yesno", heading=__lng__(32163),
                                      line1=self.album_menu["musicbrainz_artistid"]):
                            canceled = False
                            break
                elif type_ == "album":
                    if len(mbid) == 0 and len(self.artist_menu["musicbrainz_albumid"]) != 0:
                        if dialog_msg("yesno", heading=__lng__(32163),
                                      line1=self.album_menu["musicbrainz_albumid"]):
                            canceled = False
                            break
                if len(mbid) == 36:
                    if dialog_msg("yesno", heading=__lng__(32162), line1=mbid):
                        canceled = False
                        break
                    else:
                        mbid = "canceled"
                        kb.doModal()
                        continue
                if len(mbid) == 32:  # user did not enter dashes
                    temp_mbid = list(mbid)
                    temp_mbid.insert(8, "-")
                    temp_mbid.insert(13, "-")
                    temp_mbid.insert(18, "-")
                    temp_mbid.insert(23, "-")
                    mbid = "".join(temp_mbid)
                else:
                    mbid = "canceled"
                    if dialog_msg("yesno", heading=__lng__(32160), line1=__lng__(32161)):
                        kb.doModal()
                        continue
                    else:
                        canceled = True
                        break
        return mbid, canceled

    def onClick(self, ctrl_id):
        # print ctrl_id
        empty = []
        if ctrl_id in (105, 150):  # cdARTs Search Artists
            if ctrl_id == 105:
                self.menu_mode = 1
                self.artwork_type = ArtType.CDART
            elif ctrl_id == 150:
                self.menu_mode = 3
                self.artwork_type = ArtType.COVER
            self.local_artists = self.album_artists
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.getControl(120).reset()
            self.getControl(140).reset()
            self.populate_artist_list(self.album_artists)
        if ctrl_id == 120:  # Retrieving information from Artists List
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.artist_menu = {
                "local_id": (self.local_artists[self.getControl(120).getSelectedPosition()]["local_id"]),
                "name": cu.get_unicode(
                    self.local_artists[self.getControl(120).getSelectedPosition()]["name"]),
                "musicbrainz_artistid": cu.get_unicode(
                    self.local_artists[self.getControl(120).getSelectedPosition()]["musicbrainz_artistid"])}
            if self.menu_mode not in (10, 11, 12, 14):
                self.artist_menu["has_art"] = self.local_artists[self.getControl(120).getSelectedPosition()]["has_art"]
                if not self.artist_menu["musicbrainz_artistid"]:
                    self.artist_menu["musicbrainz_artistid"] = mb_utils.update_musicbrainz_id("artist",
                                                                                              self.artist_menu)
            artist_name = cu.get_unicode(self.artist_menu["name"])
            self.getControl(204).setLabel(__lng__(32038) + "[CR]%s" % artist_name)
            if self.menu_mode == 1:
                self.remote_cdart_url = ftv_scraper.remote_cdart_list(self.artist_menu)
                xbmcgui.Window(10001).setProperty("artwork", ArtType.CDART)
                self.populate_album_list(self.remote_cdart_url, 0, ArtType.CDART)
            elif self.menu_mode == 3:
                self.remote_cdart_url = ftv_scraper.remote_coverart_list(self.artist_menu)
                xbmcgui.Window(10001).setProperty("artwork", ArtType.COVER)
                self.populate_album_list(self.remote_cdart_url, 0, ArtType.COVER)
            elif self.menu_mode == 6:
                xbmcgui.Window(10001).setProperty("artwork", ArtType.FANART)
                self.populate_fanarts(self.artist_menu, 0)
            elif self.menu_mode == 7:
                xbmcgui.Window(10001).setProperty("artwork", ArtType.CLEARLOGO)
                self.populate_clearlogos(self.artist_menu, 0)
            elif self.menu_mode == 9:
                xbmcgui.Window(10001).setProperty("artwork", ArtType.THUMB)
                self.populate_artistthumbs(self.artist_menu, 0)
            elif self.menu_mode == 11:
                self.local_albums = cdam_db.get_local_albums_db(self.artist_menu["name"])
                self.getControl(145).reset()
                self.populate_album_list_mbid(self.local_albums)
            elif self.menu_mode == 13:
                xbmcgui.Window(10001).setProperty("artwork", ArtType.BANNER)
                self.populate_musicbanners(self.artist_menu, 0)
        if ctrl_id == 145:
            self.selected_item = self.getControl(145).getSelectedPosition()
            if self.menu_mode == 10:  # Artist
                self.artist_menu = {"local_id": (
                    self.local_artists[self.getControl(145).getSelectedPosition()]["local_id"]),
                    "name": cu.get_unicode(self.local_artists[self.getControl(145).getSelectedPosition()]["name"]),
                    "musicbrainz_artistid": cu.get_unicode(
                        self.local_artists[self.getControl(145).getSelectedPosition()]["musicbrainz_artistid"])}
                self.setFocusId(157)
                try:
                    self.getControl(156).setLabel(
                        __lng__(32038) + "[CR]%s" % cu.get_unicode(self.artist_menu["name"]))
                except Exception as ex:
                    log(ex.message)
                    self.getControl(156).setLabel(__lng__(32038) + "[CR]%s" % repr(self.artist_menu["name"]))
            if self.menu_mode in (11, 12):  # Album
                self.album_menu = {"local_id": (
                    self.local_albums[self.getControl(145).getSelectedPosition()]["local_id"]),
                    "title": cu.get_unicode(self.local_albums[self.getControl(145).getSelectedPosition()]["title"]),
                    "musicbrainz_albumid": cu.get_unicode(
                        self.local_albums[self.getControl(145).getSelectedPosition()]["musicbrainz_albumid"]),
                    "artist": cu.get_unicode(
                        self.local_albums[self.getControl(145).getSelectedPosition()]["artist"]),
                    "path": cu.get_unicode(self.local_albums[self.getControl(145).getSelectedPosition()]["path"]),
                    "musicbrainz_artistid": cu.get_unicode(
                        self.local_albums[self.getControl(145).getSelectedPosition()]["musicbrainz_artistid"])}
                self.setFocusId(157)
                try:
                    self.getControl(156).setLabel(
                        __lng__(32039) + "[CR]%s" % cu.get_unicode(self.album_menu["title"]))
                except Exception as ex:
                    log(ex.message)
                    self.getControl(156).setLabel(__lng__(32039) + "[CR]%s" % repr(self.album_menu["title"]))
        if ctrl_id == 157:  # Manual Edit
            if self.menu_mode == 10:  # Artist
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                mbid, canceled = self.get_mbid_keyboard("artist")
                if not canceled:
                    cdam_db.update_artist_mbid(mbid, self.artist_menu["local_id"],
                                               old_mbid=self.artist_menu["musicbrainz_artistid"])
            if self.menu_mode == 11:  # album
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                artist_mbid, canceled = self.get_mbid_keyboard("albumartist")
                if not canceled:
                    album_mbid, canceled = self.get_mbid_keyboard("album")
                    if not canceled:
                        cdam_db.manual_update_album(album_mbid, artist_mbid, self.album_menu["local_id"],
                                                    self.album_menu["path"])
            local_artists = cdam_db.get_local_artists_db(mode="album_artists")
            if __cfg__.enable_all_artists():
                all_artists = cdam_db.get_local_artists_db(mode="all_artists")
            else:
                all_artists = []
            self.all_artists_list, self.album_artists = ftv_scraper.get_recognized(all_artists, local_artists)
            if self.menu_mode == 11:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                self.getControl(145).reset()
                self.local_albums = cdam_db.get_local_albums_db(self.album_menu["artist"])
                self.populate_album_list_mbid(self.local_albums, self.selected_item)
            elif self.menu_mode == 10:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                self.getControl(145).reset()
                if __cfg__.enable_all_artists():
                    self.local_artists = all_artists
                else:
                    self.local_artists = local_artists
                self.populate_artist_list_mbid(self.local_artists)
        if ctrl_id == 122:  # Retrieving information from Album List
            self.getControl(140).reset()
            data = cu.from_json_simple(self.getControl(122).getSelectedItem().getLabel2())
            url = data['url']
            log(url, xbmc.LOGNOTICE)
            self.selected_item = self.getControl(122).getSelectedPosition()
            if not url == "":  # If it is a recognized Album...
                # make sure the url is remote before attemting to download it
                if url.lower().startswith("http"):
                    message = None
                    if self.menu_mode == 1:
                        message, _, _ = download.download_art(url, data, ArtType.CDART, "manual")
                    elif self.menu_mode == 3:
                        message, _, _ = download.download_art(url, data, ArtType.COVER, "manual")
                    dialog_msg("close")
                    if message is not None:  # and do not crash if there's somethin wrong with this url
                        dialog_msg("ok", heading=message[0], line1=message[1], line2=message[2], line3=message[3])
                    else:
                        log("Download must have failed, message is None")
            else:  # If it is not a recognized Album...
                log("Oops --  Some how I got here... - ControlID(122)")
            all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
            self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
            artist_name = cu.get_unicode(self.artist_menu["name"])
            self.getControl(204).setLabel(__lng__(32038) + "[CR]%s" % artist_name)
            if self.menu_mode == 1:
                self.remote_cdart_url = ftv_scraper.remote_cdart_list(self.artist_menu)
                xbmcgui.Window(10001).setProperty("artwork", ArtType.CDART)
                self.populate_album_list(self.remote_cdart_url, self.selected_item, ArtType.CDART)
            elif self.menu_mode == 3:
                self.remote_cdart_url = ftv_scraper.remote_coverart_list(self.artist_menu)
                xbmcgui.Window(10001).setProperty("artwork", ArtType.COVER)
                self.populate_album_list(self.remote_cdart_url, self.selected_item, ArtType.COVER)
        if ctrl_id == 132:  # Clean Music database selected from Advanced Menu
            log("#  Executing Built-in - CleanLibrary(music)", xbmc.LOGNOTICE)
            xbmc.executebuiltin("CleanLibrary(music)")
        if ctrl_id == 133:  # Update Music database selected from Advanced Menu
            log("#  Executing Built-in - UpdateLibrary(music)", xbmc.LOGNOTICE)
            xbmc.executebuiltin("UpdateLibrary(music)")
        if ctrl_id == 135:  # Back up cdART selected from Advanced Menu
            self.backup_cdart()
        if ctrl_id == 134:
            log("No function here anymore", xbmc.LOGNOTICE)
        if ctrl_id == 131:  # Modify Local Database
            self.setFocusId(190)  # change when other options
        if ctrl_id == 190:  # backup database
            cdam_db.backup_database()
            xbmc.executebuiltin(
                "Notification( %s, %s, %d, %s)" % (__lng__(32042), __lng__(32139), 2000, self.image))
        if ctrl_id == 191:  # Refresh Local database selected from Advanced Menu
            cdam_db.refresh_db(False)
            dialog_msg("close")
            local_artists = cdam_db.get_local_artists_db(mode="album_artists")
            if __cfg__.enable_all_artists():
                all_artists = cdam_db.get_local_artists_db(mode="all_artists")
            else:
                all_artists = []
            self.all_artists_list, self.album_artists = ftv_scraper.get_recognized(all_artists, local_artists)
            all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
            self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
        if ctrl_id == 192:  # Update database
            cdam_db.update_database(False)
            dialog_msg("close")
            local_artists = cdam_db.get_local_artists_db(mode="album_artists")
            if __cfg__.enable_all_artists():
                all_artists = cdam_db.get_local_artists_db(mode="all_artists")
            else:
                all_artists = []
            ftv_scraper.first_check(all_artists, local_artists, background=False, update_db=True)
            self.all_artists_list, self.album_artists = ftv_scraper.get_recognized(all_artists, local_artists)
            all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
            self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
        if ctrl_id == 136:  # Restore from Backup
            self.restore_cdart()
            all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
            self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
        if ctrl_id == 137:  # Local cdART List
            self.getControl(122).reset()
            self.menu_mode = 8
            xbmcgui.Window(10001).setProperty("artwork", ArtType.CDART)
            self.populate_local_cdarts(0)
        if ctrl_id == 107:
            self.setFocusId(200)
        if ctrl_id == 108:
            self.setFocusId(200)
        if ctrl_id == 130:  # cdART Backup Menu
            self.setFocusId(135)
        if ctrl_id == 140:  # Local cdART selection
            self.cdart_icon()
            self.setFocusId(142)
        if ctrl_id in (142, 143):
            data = cu.from_json_simple(self.getControl(140).getSelectedItem().getLabel2())
            cdart = data['cdart_img']
            artist = data['artist']
            title = data['title']
            disc = data['disc']
            path = data['path']
            if ctrl_id == 143:  # Delete cdART
                self.cdart_delete(cdart, path)
                all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
                self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
                popup_label = __lng__(32075)
            else:  # Backup to backup folder
                cdam_fs.cdart_single_backup(cdart, artist, title, disc)
                popup_label = __lng__(32074)
            self.popup(popup_label, self.getControl(140).getSelectedItem().getLabel(), "", "")
            self.setFocusId(140)
            self.populate_local_cdarts()
        if ctrl_id == 100:  # cdARTS
            self.artwork_type = ArtType.CDART
            self.setFocusId(105)
        if ctrl_id == 101:  # Cover Arts
            self.artwork_type = ArtType.COVER
            self.setFocusId(150)
        if ctrl_id == 154:  # Muscic Banner
            self.artwork_type = ArtType.BANNER
            self.setFocusId(200)
        if ctrl_id == 103:  # Advanced
            self.setFocusId(130)
        if ctrl_id == 104:  # Settings
            self.menu_mode = 5
            __cfg__.open()
        if ctrl_id == 111:  # Exit
            self.menu_mode = 0
            if __cfg__.enable_missing():
                self.missing_list()
            self.close()
        if ctrl_id in (180, 181):  # fanart Search Album Artists
            self.menu_mode = 6
        if ctrl_id in (184, 185):  # Clear Logo Search Artists
            self.menu_mode = 7
        if ctrl_id in (197, 198):  # Artist Thumb Search Artists
            self.menu_mode = 9
        if ctrl_id in (205, 207):  # Artist Music Banner Select Artists
            self.menu_mode = 13
        if ctrl_id == 102:
            self.artwork_type = ArtType.FANART
            self.setFocusId(170)
        if ctrl_id == 170:
            self.setFocusId(180)
        if ctrl_id == 171:
            self.setFocusId(182)
        if ctrl_id == 168:
            self.setFocusId(184)
        if ctrl_id == 169:
            self.setFocusId(186)
        if ctrl_id == 193:
            self.setFocusId(197)
        if ctrl_id == 194:
            self.setFocusId(195)
        if ctrl_id == 200:
            self.setFocusId(205)
        if ctrl_id == 201:
            self.setFocusId(207)
        if ctrl_id == 152:
            self.artwork_type = ArtType.CLEARLOGO
            xbmcgui.Window(10001).setProperty("artwork", ArtType.CLEARLOGO)
            self.menu_mode = 7
            self.setFocusId(168)
        if ctrl_id == 153:
            self.artwork_type = ArtType.THUMB
            xbmcgui.Window(10001).setProperty("artwork", ArtType.THUMB)
            self.menu_mode = 9
            self.setFocusId(193)
        if ctrl_id in (180, 181, 184, 185, 197, 198, 205, 206):
            if ctrl_id in (180, 184, 197, 205):
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                self.getControl(120).reset()
                self.local_artists = self.album_artists
                self.populate_artist_list(self.local_artists)
            elif ctrl_id in (181, 185, 198, 206) and __cfg__.enable_all_artists():
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                self.getControl(120).reset()
                self.local_artists = self.all_artists_list
                self.populate_artist_list(self.local_artists)
        if ctrl_id == 167:  # clearLOGO
            if self.menu_mode == 7:
                data = cu.from_json_simple(self.getControl(167).getSelectedItem().getLabel2())
                url = data['url']
                data['artist'] = data['name']
                data['path'] = cdam_fs.get_artist_path(data['name'])
                selected_item = self.getControl(167).getSelectedPosition()
                if url:
                    message, _, _ = download.download_art(url, data, ArtType.CLEARLOGO, "manual")
                    dialog_msg("close")
                    dialog_msg("ok", heading=message[0], line1=message[1], line2=message[2], line3=message[3])
                else:
                    log("Nothing to download")
                xbmcgui.Window(10001).setProperty("artwork", ArtType.CLEARLOGO)
                self.populate_clearlogos(self.artist_menu, selected_item)
        if ctrl_id == 202:  # Music Banner
            if self.menu_mode == 13:
                data = cu.from_json_simple(self.getControl(202).getSelectedItem().getLabel2())
                url = data['url']
                data['artist'] = data['name']
                data['path'] = cdam_fs.get_artist_path(data['name'])
                selected_item = self.getControl(202).getSelectedPosition()
                if url:
                    message, success, is_canceled = download.download_art(url, data, ArtType.BANNER, "manual")
                    dialog_msg("close")
                    dialog_msg("ok", heading=message[0], line1=message[1], line2=message[2], line3=message[3])
                else:
                    log("Nothing to download")
                xbmcgui.Window(10001).setProperty("artwork", ArtType.BANNER)
                self.populate_musicbanners(self.artist_menu, selected_item)
        if ctrl_id == 160:  # Fanart Download
            if self.menu_mode == 6:
                data = cu.from_json_simple(self.getControl(160).getSelectedItem().getLabel2())
                url = data['url']
                data['artist'] = data['name']
                data['path'] = cdam_fs.get_artist_path(data['name'])
                selected_item = self.getControl(160).getSelectedPosition()
                if url:
                    message, success, is_canceled = download.download_art(url, data, ArtType.FANART, "manual")
                    dialog_msg("close")
                    dialog_msg("ok", heading=message[0], line1=message[1], line2=message[2], line3=message[3])
                else:
                    log("Nothing to download")
                xbmcgui.Window(10001).setProperty("artwork", ArtType.FANART)
                self.populate_fanarts(self.artist_menu, selected_item)
        if ctrl_id == 199:  # Artist Thumb
            if self.menu_mode == 9:
                data = cu.from_json_simple(self.getControl(199).getSelectedItem().getLabel2())
                url = data['url']
                data['artist'] = data['name']
                data['path'] = cdam_fs.get_artist_path(data['name'])
                selected_item = self.getControl(199).getSelectedPosition()
                if url:
                    message, success, is_canceled = download.download_art(url, data, ArtType.THUMB, "manual")
                    dialog_msg("close")
                    dialog_msg("ok", heading=message[0], line1=message[1], line2=message[2], line3=message[3])
                else:
                    log("Nothing to download")
                xbmcgui.Window(10001).setProperty("artwork", ArtType.THUMB)
                self.populate_artistthumbs(self.artist_menu, selected_item)
        if ctrl_id in (182, 186, 187, 183, 106, 151, 195, 196, 207, 208):  # Automatic Download
            self.artwork_type = ""
            if ctrl_id in (106, 151, 186, 182, 195, 207):
                self.local_artists = self.album_artists
                if ctrl_id == 106:  # cdARTs
                    self.menu_mode = 2
                    self.artwork_type = ArtType.CDART
                elif ctrl_id == 151:  # cover arts
                    self.menu_mode = 4
                    self.artwork_type = ArtType.COVER
                elif ctrl_id == 186:  # ClearLOGOs
                    self.artwork_type = ArtType.CLEARLOGO
                elif ctrl_id == 182:  # Fanarts
                    self.artwork_type = ArtType.FANART
                elif ctrl_id == 195:  # Artist Thumbs
                    self.artwork_type = ArtType.THUMB
                elif ctrl_id == 207:  # Artist banner
                    self.artwork_type = ArtType.BANNER
                _, successfully_downloaded = download.auto_download(self.artwork_type, self.local_artists)
                all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
                self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
                if successfully_downloaded:
                    self.populate_downloaded(successfully_downloaded, self.artwork_type)
            if ctrl_id in (183, 187, 196, 208) and __cfg__.enable_all_artists():
                self.local_artists = self.all_artists_list
                if ctrl_id == 187:  # ClearLOGOs All Artists
                    self.artwork_type = "clearlogo_allartists"
                elif ctrl_id == 183:  # Fanarts All Artists
                    self.artwork_type = "fanart_allartists"
                elif ctrl_id == 196:  # Artist Thumbs All Artists
                    self.artwork_type = "artistthumb_allartists"
                elif ctrl_id == 208:  # Artist Banners All Artists
                    self.artwork_type = "musicbanner_allartists"
                _, successfully_downloaded = download.auto_download(self.artwork_type, self.local_artists)
                all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
                self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)
                if successfully_downloaded:
                    self.populate_downloaded(successfully_downloaded, self.artwork_type)
        if ctrl_id == 113:
            self.setFocusId(107)
        if ctrl_id == 114:  # Refresh Artist MBIDs
            self.setFocusId(138)  # change to 138 when selected artist is added to script
        if ctrl_id == 189:  # Edit By Album
            self.setFocusId(123)
        if ctrl_id == 115:  # Find Missing Artist MBIDs
            if __cfg__.enable_all_artists():
                updated_artists, canceled = cdam_db.update_missing_artist_mbid(empty, False, mode="all_artists")
            else:
                updated_artists, canceled = cdam_db.update_missing_artist_mbid(empty, False, mode="album_artists")
            for updated_artist in updated_artists:
                if updated_artist["musicbrainz_artistid"]:
                    cdam_db.update_artist_mbid(updated_artist["musicbrainz_artistid"], updated_artist["local_id"],
                                               artist_name=updated_artist["name"])
        if ctrl_id == 139:  # Automatic Refresh Artist MBIDs
            cdam_db.check_artist_mbid(empty, False, mode="album_artists")
        if ctrl_id == 123:
            self.setFocusId(126)
        if ctrl_id == 124:  # Refresh Album MBIDs
            self.setFocusId(147)  # change to 147 when selected album is added to script
        if ctrl_id == 125:
            updated_albums, canceled = cdam_db.update_missing_album_mbid(empty, False)
            for updated_album in updated_albums:
                if updated_album["musicbrainz_albumid"]:
                    cdam_db.set_album_mbids(updated_album["local_id"], updated_album["musicbrainz_albumid"],
                                            updated_album["musicbrainz_artistid"])
        if ctrl_id == 126:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.getControl(120).reset()
            self.menu_mode = 11
            self.local_artists = cdam_db.get_local_artists_db("album_artists")
            self.populate_artist_list(self.local_artists)
        if ctrl_id == 127:  # Change Album MBID
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.getControl(145).reset()
            self.local_albums = cdam_db.get_local_albums_db("all artists")
            self.menu_mode = 12
            self.populate_album_list_mbid(self.local_albums)
        if ctrl_id == 148:  # Automatic Refresh Album MBIDs
            cdam_db.check_album_mbid(empty, False)
        if ctrl_id == 113:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.getControl(145).reset()
            self.menu_mode = 10
            if __cfg__.enable_all_artists():
                self.local_artists = cdam_db.get_local_artists_db("all_artists")
            else:
                self.local_artists = cdam_db.get_local_artists_db("album_artists")
            self.populate_artist_list_mbid(self.local_artists)
        if ctrl_id == 158:
            self.getControl(161).reset()
            artist = ""
            album = ""
            if self.menu_mode == 10:
                kb.setHeading(__lng__(32164))
                try:
                    kb.setDefault(self.artist_menu["name"])
                except Exception as ex:
                    log(ex.message)
                    kb.setDefault(repr(self.artist_menu["name"]))
                kb.doModal()
                while True:
                    if not (kb.isConfirmed()):
                        canceled = True
                        break
                    else:
                        artist = kb.getText()
                        canceled = False
                        break
                if not canceled:
                    self.artists = mb_utils.get_musicbrainz_artists(artist, __cfg__.mbid_match_number())
                    if self.artists:
                        self.populate_search_list_mbid(self.artists, "artists")
            if self.menu_mode in (11, 12):
                kb.setHeading(__lng__(32165))
                try:
                    kb.setDefault(self.album_menu["title"])
                except Exception as ex:
                    log(ex.message)
                    kb.setDefault(repr(self.album_menu["title"]))
                kb.doModal()
                while True:
                    if not (kb.isConfirmed()):
                        canceled = True
                        break
                    else:
                        album = kb.getText()
                        canceled = False
                        break
                if not canceled:
                    kb.setHeading(__lng__(32164))
                    try:
                        kb.setDefault(self.album_menu["artist"])
                    except Exception as ex:
                        log(ex.message)
                        kb.setDefault(repr(self.album_menu["artist"]))
                    kb.doModal()
                    while True:
                        if not (kb.isConfirmed()):
                            canceled = True
                            break
                        else:
                            artist = kb.getText()
                            canceled = False
                            break
                    if not canceled:
                        album, self.albums = mb_utils.get_musicbrainz_album(album, artist, 0,
                                                                            __cfg__.mbid_match_number())
                if self.albums:
                    self.populate_search_list_mbid(self.albums, "albums")
        if ctrl_id == 159:
            self.getControl(161).reset()
            if self.menu_mode == 10:
                self.artists = mb_utils.get_musicbrainz_artists(self.artist_menu["name"], __cfg__.mbid_match_number())
                if self.artists:
                    self.populate_search_list_mbid(self.artists, "artists")
            if self.menu_mode in (11, 12):
                album, self.albums = mb_utils.get_musicbrainz_album(self.album_menu["title"],
                                                                    self.album_menu["artist"], 0,
                                                                    __cfg__.mbid_match_number())
                if self.albums:
                    self.populate_search_list_mbid(self.albums, "albums")
        if ctrl_id == 161:
            if self.menu_mode == 10:
                artist_details = {
                    "musicbrainz_artistid": self.artists[self.getControl(161).getSelectedPosition()]["id"],
                    "name": self.artists[self.getControl(161).getSelectedPosition()]["name"],
                    "local_id": self.artist_menu["local_id"]}
                cdam_db.user_updates(artist_details, type_="artist")
                self.getControl(145).reset()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if __cfg__.enable_all_artists():
                    self.local_artists = cdam_db.get_local_artists_db("all_artists")
                else:
                    self.local_artists = cdam_db.get_local_artists_db("album_artists")
                self.populate_artist_list_mbid(self.local_artists, self.selected_item)
            if self.menu_mode in (11, 12):
                album_details = {"artist": self.albums[self.getControl(161).getSelectedPosition()]["artist"],
                                 "title": self.albums[self.getControl(161).getSelectedPosition()]["title"],
                                 "musicbrainz_artistid": self.albums[self.getControl(161).getSelectedPosition()][
                                     "artist_id"],
                                 "musicbrainz_albumid": self.albums[self.getControl(161).getSelectedPosition()]["id"],
                                 "path": self.album_menu["path"], "local_id": self.album_menu["local_id"]}
                cdam_db.user_updates(album_details, type_="album")
                self.getControl(145).reset()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if self.menu_mode == 12:
                    self.local_albums = cdam_db.get_local_albums_db("all artists")
                    self.populate_album_list_mbid(self.local_albums, self.selected_item)
                else:
                    self.local_albums = cdam_db.get_local_albums_db(self.artist_menu["name"])
                    self.populate_album_list_mbid(self.local_albums, self.selected_item)
        if ctrl_id == 141:
            local_artists = cdam_db.get_local_artists_db(mode="album_artists")
            if __cfg__.enable_all_artists():
                all_artists = cdam_db.get_local_artists_db(mode="all_artists")
            else:
                all_artists = []
            ftv_scraper.first_check(all_artists, local_artists, background=False, update_db=True)
            self.all_artists_list, self.album_artists = ftv_scraper.get_recognized(all_artists, local_artists)
            all_artist_count, local_album_count, local_artist_count, local_cdart_count = cdam_db.new_local_count()
            self.refresh_counts(local_album_count, local_artist_count, local_cdart_count)

    def onFocus(self, control_id):
        if control_id not in (122, 140, 160, 167, 199):
            xbmcgui.Window(10001).clearProperty("artwork")
        if control_id == 140:
            self.cdart_icon()
        if control_id in (100, 101, 152, 103, 104, 111):
            xbmcgui.Window(10001).clearProperty("artwork")
            self.menu_mode = 0

    def onAction(self, action):
        if self.menu_mode == 8:
            self.cdart_icon()
        button_code = action.getButtonCode()
        action_id = action.getId()
        if action_id == 10 or button_code in (KEY_BUTTON_BACK, KEY_KEYBOARD_ESC):
            self.close()
            log("Closing", xbmc.LOGNOTICE)
            if __cfg__.enable_missing():
                self.missing_list()
