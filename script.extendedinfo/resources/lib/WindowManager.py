# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os

from dialogs import BaseClasses
from LocalDB import local_db

import TheMovieDB

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
INFO_DIALOG_FILE_CLASSIC = u'script-%s-DialogVideoInfo.xml' % (ADDON_NAME)
LIST_DIALOG_FILE_CLASSIC = u'script-%s-VideoList.xml' % (ADDON_NAME)
ACTOR_DIALOG_FILE_CLASSIC = u'script-%s-DialogInfo.xml' % (ADDON_NAME)
if SETTING("force_native_layout") == "true":
    INFO_DIALOG_FILE = u'script-%s-DialogVideoInfo-classic.xml' % (ADDON_NAME)
    LIST_DIALOG_FILE = u'script-%s-VideoList-classic.xml' % (ADDON_NAME)
    ACTOR_DIALOG_FILE = u'script-%s-DialogInfo-classic.xml' % (ADDON_NAME)
    path = os.path.join(ADDON_PATH, "resources", "skins", "Default", "1080i")
    if not xbmcvfs.exists(os.path.join(path, INFO_DIALOG_FILE)):
        xbmcvfs.copy(strSource=os.path.join(path, INFO_DIALOG_FILE_CLASSIC),
                     strDestnation=os.path.join(path, INFO_DIALOG_FILE))
    if not xbmcvfs.exists(os.path.join(path, LIST_DIALOG_FILE)):
        xbmcvfs.copy(strSource=os.path.join(path, LIST_DIALOG_FILE_CLASSIC),
                     strDestnation=os.path.join(path, LIST_DIALOG_FILE))
    if not xbmcvfs.exists(os.path.join(path, ACTOR_DIALOG_FILE)):
        xbmcvfs.copy(strSource=os.path.join(path, ACTOR_DIALOG_FILE_CLASSIC),
                     strDestnation=os.path.join(path, ACTOR_DIALOG_FILE))
else:
    INFO_DIALOG_FILE = INFO_DIALOG_FILE_CLASSIC
    LIST_DIALOG_FILE = LIST_DIALOG_FILE_CLASSIC
    ACTOR_DIALOG_FILE = ACTOR_DIALOG_FILE_CLASSIC


class WindowManager(object):
    window_stack = []

    def __init__(self):
        self.reopen_window = False
        self.last_control = None
        self.active_dialog = None
        if SETTING("window_mode") == "true":
            self.window_type = BaseClasses.WindowXML
        else:
            self.window_type = BaseClasses.DialogXML

    def add_to_stack(self, window):
        """
        add window / dialog to global window stack
        """
        self.window_stack.append(window)

    def pop_stack(self):
        """
        get newest item from global window stack
        """
        if self.window_stack:
            self.active_dialog = self.window_stack.pop()
            xbmc.sleep(300)
            self.active_dialog.doModal()
        elif self.reopen_window:
            xbmc.sleep(600)
            xbmc.executebuiltin("Action(Info)")
            if self.last_control:
                xbmc.sleep(50)
                xbmc.executebuiltin("SetFocus(%s)" % self.last_control)

    def open_movie_info(self, prev_window=None, movie_id=None, dbid=None,
                        name=None, imdb_id=None):
        """
        open movie info, deal with window stack
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogMovieInfo
        if not movie_id:
            movie_id = TheMovieDB.get_movie_tmdb_id(imdb_id=imdb_id,
                                                    dbid=dbid,
                                                    name=name)
        movie_class = DialogMovieInfo.get_window(self.window_type)
        dialog = movie_class(INFO_DIALOG_FILE,
                             ADDON_PATH,
                             id=movie_id,
                             dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_tvshow_info(self, prev_window=None, tmdb_id=None, dbid=None,
                         tvdb_id=None, imdb_id=None, name=None):
        """
        open tvshow info, deal with window stack
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogTVShowInfo
        if tmdb_id:
            pass
        elif tvdb_id:
            tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id)
        elif imdb_id:
            tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id=imdb_id,
                                                  source="imdb_id")
        elif dbid and (int(dbid) > 0):
            tvdb_id = local_db.get_imdb_id(media_type="tvshow",
                                           dbid=dbid)
            if tvdb_id:
                tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id)
        elif name:
            tmdb_id = TheMovieDB.search_media(media_name=name,
                                              year="",
                                              media_type="tv")
        tvshow_class = DialogTVShowInfo.get_window(self.window_type)
        dialog = tvshow_class(INFO_DIALOG_FILE,
                              ADDON_PATH,
                              tmdb_id=tmdb_id,
                              dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_season_info(self, prev_window=None, tvshow_id=None,
                         season=None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs *season AND (*tvshow_id OR *tvshow)
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogSeasonInfo
        if not tvshow_id:
            params = {"query": tvshow,
                      "language": SETTING("language")}
            response = TheMovieDB.get_data(url="search/tv",
                                           params=params,
                                           cache_days=30)
            if response["results"]:
                tvshow_id = str(response['results'][0]['id'])
            else:
                params = {"query": re.sub('\(.*?\)', '', tvshow),
                          "language": SETTING("language")}
                response = TheMovieDB.get_data(url="search/tv",
                                               params=params,
                                               cache_days=30)
                if response["results"]:
                    tvshow_id = str(response['results'][0]['id'])

        season_class = DialogSeasonInfo.get_window(self.window_type)
        dialog = season_class(INFO_DIALOG_FILE,
                              ADDON_PATH,
                              id=tvshow_id,
                              season=season,
                              dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_episode_info(self, prev_window=None, tvshow_id=None, season=None,
                          episode=None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs (*tvshow_id OR *tvshow) AND *season AND *episode
        """
        from dialogs import DialogEpisodeInfo
        ep_class = DialogEpisodeInfo.get_window(self.window_type)
        if not tvshow_id and tvshow:
            tvshow_id = TheMovieDB.search_media(media_name=tvshow,
                                                media_type="tv",
                                                cache_days=7)
        dialog = ep_class(INFO_DIALOG_FILE,
                          ADDON_PATH,
                          show_id=tvshow_id,
                          season=season,
                          episode=episode,
                          dbid=dbid)
        self.open_dialog(dialog, prev_window)

    def open_actor_info(self, prev_window=None, actor_id=None, name=None):
        """
        open actor info, deal with window stack
        """
        from dialogs import DialogActorInfo
        if not actor_id:
            name = name.decode("utf-8").split(" " + LANG(20347) + " ")
            names = name[0].strip().split(" / ")
            if len(names) > 1:
                ret = xbmcgui.Dialog().select(heading=LANG(32027),
                                              list=names)
                if ret == -1:
                    return None
                name = names[ret]
            else:
                name = names[0]
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            actor_info = TheMovieDB.get_person_info(name)
            if actor_info:
                actor_id = actor_info["id"]
            else:
                return None
        else:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
        actor_class = DialogActorInfo.get_window(self.window_type)
        dialog = actor_class(ACTOR_DIALOG_FILE,
                             ADDON_PATH,
                             id=actor_id)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_video_list(self, prev_window=None, listitems=None, filters=[], mode="filter", list_id=False,
                        filter_label="", force=False, media_type="movie", search_str=""):
        """
        open video list, deal with window stack and color
        """
        from dialogs import DialogVideoList
        if prev_window:
            try:  # TODO rework
                color = prev_window.data["general"]['ImageColor']
            except:
                color = "FFFFFFFF"
        else:
            color = "FFFFFFFF"
        check_version()
        browser_class = DialogVideoList.get_window(self.window_type)
        dialog = browser_class(LIST_DIALOG_FILE,
                               ADDON_PATH,
                               listitems=listitems,
                               color=color,
                               filters=filters,
                               mode=mode,
                               list_id=list_id,
                               force=force,
                               filter_label=filter_label,
                               search_str=search_str,
                               type=media_type)
        if prev_window:
            self.add_to_stack(prev_window)
            prev_window.close()
        dialog.doModal()

    def open_youtube_list(self, prev_window=None, search_str="", filters=[], sort="relevance",
                          filter_label="", media_type="video"):
        """
        open video list, deal with window stack and color
        """
        from dialogs import DialogYoutubeList
        if prev_window:
            try:  # TODO rework
                color = prev_window.data["general"]['ImageColor']
            except:
                color = "FFFFFFFF"
        else:
            color = "FFFFFFFF"
        youtube_class = DialogYoutubeList.get_window(BaseClasses.WindowXML)
        dialog = youtube_class(u'script-%s-YoutubeList.xml' % ADDON_NAME, ADDON_PATH,
                               search_str=search_str,
                               color=color,
                               filters=filters,
                               filter_label=filter_label,
                               type=media_type)
        if prev_window:
            self.add_to_stack(prev_window)
            prev_window.close()
        dialog.doModal()

    def open_slideshow(self, listitems, index):
        """
        open slideshow dialog for single image
        """
        from dialogs import SlideShow
        dialog = SlideShow.SlideShow(u'script-%s-SlideShow.xml' % ADDON_NAME, ADDON_PATH,
                                     listitems=listitems,
                                     index=index)
        dialog.doModal()
        return dialog.position

    def open_selectdialog(self, listitems):
        """
        open selectdialog, return listitem dict and index
        """
        from dialogs.SelectDialog import SelectDialog
        w = SelectDialog('DialogSelect.xml', ADDON_PATH,
                         listing=listitems)
        w.doModal()
        return w.listitem, w.index

    def open_dialog(self, dialog, prev_window):
        if dialog.data:
            self.active_dialog = dialog
            if xbmc.getCondVisibility("Window.IsVisible(movieinformation)"):
                self.reopen_window = True
                self.last_control = get_infolabel("System.CurrentControlId")
                xbmc.executebuiltin("Dialog.Close(movieinformation)")
            check_version()
            if prev_window:
                self.add_to_stack(prev_window)
                prev_window.close()
            dialog.doModal()
        else:
            self.active_dialog = None
            notify(LANG(32143))

wm = WindowManager()
