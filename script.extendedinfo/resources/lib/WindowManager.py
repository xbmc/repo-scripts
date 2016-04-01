# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import Utils
import xbmc
import xbmcgui
import xbmcvfs
import os
import re

from dialogs import BaseClasses
from LocalDB import local_db

import TheMovieDB
import addon

INFO_DIALOG_FILE_CLASSIC = u'script-%s-DialogVideoInfo.xml' % (addon.NAME)
LIST_DIALOG_FILE_CLASSIC = u'script-%s-VideoList.xml' % (addon.NAME)
ACTOR_DIALOG_FILE_CLASSIC = u'script-%s-DialogInfo.xml' % (addon.NAME)
if addon.bool_setting("force_native_layout"):
    INFO_DIALOG_FILE = u'script-%s-DialogVideoInfo-classic.xml' % (addon.NAME)
    LIST_DIALOG_FILE = u'script-%s-VideoList-classic.xml' % (addon.NAME)
    ACTOR_DIALOG_FILE = u'script-%s-DialogInfo-classic.xml' % (addon.NAME)
    path = os.path.join(addon.PATH, "resources", "skins", "Default", "1080i")
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
        self.active_dialog = None
        self.saved_background = addon.get_global("infobackground")

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
        else:
            addon.set_global("infobackground", self.saved_background)

    def cancel(self, window):
        addon.set_global("infobackground", self.saved_background)
        window.close()

    def open_movie_info(self, prev_window=None, movie_id=None, dbid=None,
                        name=None, imdb_id=None):
        """
        open movie info, deal with window stack
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogMovieInfo
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        if not movie_id:
            movie_id = TheMovieDB.get_movie_tmdb_id(imdb_id=imdb_id,
                                                    dbid=dbid,
                                                    name=name)
        movie_class = DialogMovieInfo.get_window(BaseClasses.DialogXML)
        dialog = movie_class(INFO_DIALOG_FILE,
                             addon.PATH,
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
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        from dialogs import DialogTVShowInfo
        if tmdb_id:
            pass
        elif tvdb_id:
            tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id)
        elif imdb_id:
            tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id=imdb_id,
                                                  source="imdb_id")
        elif dbid:
            tvdb_id = local_db.get_imdb_id(media_type="tvshow",
                                           dbid=dbid)
            if tvdb_id:
                tmdb_id = TheMovieDB.get_show_tmdb_id(tvdb_id)
        elif name:
            tmdb_id = TheMovieDB.search_media(media_name=name,
                                              year="",
                                              media_type="tv")
        tvshow_class = DialogTVShowInfo.get_window(BaseClasses.DialogXML)
        dialog = tvshow_class(INFO_DIALOG_FILE,
                              addon.PATH,
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
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        if not tvshow_id:
            params = {"query": tvshow,
                      "language": addon.setting("language")}
            response = TheMovieDB.get_data(url="search/tv",
                                           params=params,
                                           cache_days=30)
            if response["results"]:
                tvshow_id = str(response['results'][0]['id'])
            else:
                params = {"query": re.sub('\(.*?\)', '', tvshow),
                          "language": addon.setting("language")}
                response = TheMovieDB.get_data(url="search/tv",
                                               params=params,
                                               cache_days=30)
                if response["results"]:
                    tvshow_id = str(response['results'][0]['id'])

        season_class = DialogSeasonInfo.get_window(BaseClasses.DialogXML)
        dialog = season_class(INFO_DIALOG_FILE,
                              addon.PATH,
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
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        ep_class = DialogEpisodeInfo.get_window(BaseClasses.DialogXML)
        if not tvshow_id and tvshow:
            tvshow_id = TheMovieDB.search_media(media_name=tvshow,
                                                media_type="tv",
                                                cache_days=7)
        dialog = ep_class(INFO_DIALOG_FILE,
                          addon.PATH,
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
            name = name.split(" " + addon.LANG(20347) + " ")
            names = name[0].strip().split(" / ")
            if len(names) > 1:
                ret = xbmcgui.Dialog().select(heading=addon.LANG(32027),
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
        actor_class = DialogActorInfo.get_window(BaseClasses.DialogXML)
        dialog = actor_class(ACTOR_DIALOG_FILE,
                             addon.PATH,
                             id=actor_id)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_video_list(self, prev_window=None, listitems=None, filters=None, mode="filter", list_id=False,
                        filter_label="", force=False, media_type="movie", search_str=""):
        """
        open video list, deal with window stack and color
        """
        filters = [] if not filters else filters
        from dialogs import DialogVideoList
        if prev_window:
            try:  # TODO rework
                color = prev_window.data["general"]['ImageColor']
            except:
                color = "FFFFFFFF"
        else:
            color = "FFFFFFFF"
        Utils.check_version()
        browser_class = DialogVideoList.get_window(BaseClasses.DialogXML)
        dialog = browser_class(LIST_DIALOG_FILE,
                               addon.PATH,
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

    def open_youtube_list(self, prev_window=None, search_str="", filters=None, sort="relevance",
                          filter_label="", media_type="video"):
        """
        open video list, deal with window stack and color
        """
        filters = [] if not filters else filters
        from dialogs import DialogYoutubeList
        if prev_window:
            try:  # TODO rework
                color = prev_window.data["general"]['ImageColor']
            except:
                color = "FFFFFFFF"
        else:
            color = "FFFFFFFF"
        youtube_class = DialogYoutubeList.get_window(BaseClasses.WindowXML)
        dialog = youtube_class(u'script-%s-YoutubeList.xml' % addon.NAME, addon.PATH,
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
        dialog = SlideShow.SlideShow(u'script-%s-SlideShow.xml' % addon.NAME, addon.PATH,
                                     listitems=listitems,
                                     index=index)
        dialog.doModal()
        return dialog.position

    def open_selectdialog(self, listitems):
        """
        open selectdialog, return listitem dict and index
        """
        from dialogs.SelectDialog import SelectDialog
        w = SelectDialog('DialogSelect.xml', addon.PATH,
                         listing=listitems)
        w.doModal()
        return w.listitem, w.index

    def open_dialog(self, dialog, prev_window):
        if dialog.data:
            self.active_dialog = dialog
            Utils.check_version()
            if prev_window:
                self.add_to_stack(prev_window)
                prev_window.close()
            dialog.doModal()
        else:
            self.active_dialog = None
            Utils.notify(addon.LANG(32143))

wm = WindowManager()
