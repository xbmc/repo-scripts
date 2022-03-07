# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

import os
import re
from typing import Optional

import xbmc
import xbmcgui
import xbmcvfs

from kutils import addon, busy, local_db, player, utils, windows

from . import TheMovieDB as tmdb

INFO_XML_CLASSIC = 'script-%s-DialogVideoInfo.xml' % (addon.ID)
LIST_XML_CLASSIC = 'script-%s-VideoList.xml' % (addon.ID)
ACTOR_XML_CLASSIC = 'script-%s-DialogInfo.xml' % (addon.ID)
if addon.bool_setting("force_native_layout") and addon.setting("xml_version") != addon.VERSION:
    addon.set_setting("xml_version", addon.VERSION)
    INFO_XML = 'script-%s-DialogVideoInfo-classic.xml' % (addon.ID)
    LIST_XML = 'script-%s-VideoList-classic.xml' % (addon.ID)
    ACTOR_XML = 'script-%s-DialogInfo-classic.xml' % (addon.ID)
    path = os.path.join(addon.PATH, "resources", "skins", "Default", "1080i")
    xbmcvfs.copy(strSource=os.path.join(path, INFO_XML_CLASSIC),
                 strDestination=os.path.join(path, INFO_XML))
    xbmcvfs.copy(strSource=os.path.join(path, LIST_XML_CLASSIC),
                 strDestination=os.path.join(path, LIST_XML))
    xbmcvfs.copy(strSource=os.path.join(path, ACTOR_XML_CLASSIC),
                 strDestination=os.path.join(path, ACTOR_XML))
else:
    INFO_XML = INFO_XML_CLASSIC
    LIST_XML = LIST_XML_CLASSIC
    ACTOR_XML = ACTOR_XML_CLASSIC


class WindowManager:
    window_stack = []

    def __init__(self):
        self.active_dialog = None
        self.saved_background = addon.get_global("infobackground")
        self.saved_control = xbmc.getInfoLabel("System.CurrentControlId")
        self.saved_dialogstate = xbmc.getCondVisibility(
            "Window.IsActive(Movieinformation)")
        # self.monitor = SettingsMonitor()
        self.monitor = xbmc.Monitor()

    def open_movie_info(self, movie_id=None, dbid=None, name=None, imdb_id=None):
        """
        opens movie info dialog, deal with window stack
        """
        busy.show_busy()
        from .dialogs.DialogMovieInfo import DialogMovieInfo
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        if not movie_id:
            movie_id = tmdb.get_movie_tmdb_id(imdb_id=imdb_id,
                                              dbid=dbid,
                                              name=name)
        dialog = DialogMovieInfo(INFO_XML,
                                 addon.PATH,
                                 id=movie_id,
                                 dbid=dbid)
        busy.hide_busy()
        self.open_infodialog(dialog)

    def open_tvshow_info(self, tmdb_id=None, dbid=None, tvdb_id=None, imdb_id=None, name=None):
        """
        open tvshow info, deal with window stack
        """
        busy.show_busy()
        dbid = int(dbid) if dbid and int(dbid) > 0 else None
        from .dialogs.DialogTVShowInfo import DialogTVShowInfo
        if tmdb_id:
            pass
        elif tvdb_id:
            tmdb_id = tmdb.get_show_tmdb_id(tvdb_id)
        elif imdb_id:
            tmdb_id = tmdb.get_show_tmdb_id(tvdb_id=imdb_id,
                                            source="imdb_id")
        elif dbid:
            tvdb_id = local_db.get_imdb_id(media_type="tvshow",
                                           dbid=dbid)
            if tvdb_id:
                tmdb_id = tmdb.get_show_tmdb_id(tvdb_id)
        elif name:
            tmdb_id = tmdb.search_media(media_name=name,
                                        year="",
                                        media_type="tv")
        dialog = DialogTVShowInfo(INFO_XML,
                                  addon.PATH,
                                  tmdb_id=tmdb_id,
                                  dbid=dbid)
        busy.hide_busy()
        self.open_infodialog(dialog)

    def open_season_info(self, tvshow_id=None, season: Optional[int] = None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs *season AND (*tvshow_id OR *tvshow)
        """
        busy.show_busy()
        from .dialogs.DialogSeasonInfo import DialogSeasonInfo
        if not tvshow_id:
            params = {"query": tvshow,
                      "language": addon.setting("language")}
            response = tmdb.get_data(url="search/tv",
                                     params=params,
                                     cache_days=30)
            if response["results"]:
                tvshow_id = str(response['results'][0]['id'])
            else:
                params = {"query": re.sub(r'\(.*?\)', '', tvshow),
                          "language": addon.setting("language")}
                response = tmdb.get_data(url="search/tv",
                                         params=params,
                                         cache_days=30)
                if response["results"]:
                    tvshow_id = str(response['results'][0]['id'])

        dialog = DialogSeasonInfo(INFO_XML,
                                  addon.PATH,
                                  id=tvshow_id,
                                  season=max(0, season),
                                  dbid=int(dbid) if dbid and int(dbid) > 0 else None)
        busy.hide_busy()
        self.open_infodialog(dialog)

    def open_episode_info(self, tvshow_id=None, season=None, episode=None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs (*tvshow_id OR *tvshow) AND *season AND *episode
        """
        from .dialogs.DialogEpisodeInfo import DialogEpisodeInfo
        if not tvshow_id and tvshow:
            tvshow_id = tmdb.search_media(media_name=tvshow,
                                          media_type="tv",
                                          cache_days=7)
        dialog = DialogEpisodeInfo(INFO_XML,
                                   addon.PATH,
                                   tvshow_id=tvshow_id,
                                   season=max(0, season),
                                   episode=episode,
                                   dbid=int(dbid) if dbid and int(dbid) > 0 else None)
        self.open_infodialog(dialog)

    def open_actor_info(self, actor_id: str=None, name: str=None):
        """opens info dialog window for an actor, deals with window stack
        A new dialog instance of DialogActorInfo is created and the xml window
        (DialogInfo.xml) is opened

        Args:
            actor_id (str, optional): tmdb actor id. Defaults to None.
            name (str, optional): a string of name or name[ separator name]. 
            if name is a multiple a select dialog is presented to user to
            get a single actor.  If name is provided, attempts to get a tmdb
            for it.  Defaults to None.

        Returns:
            None: if no tmdb actor id could be found
        """
        from .dialogs.DialogActorInfo import DialogActorInfo
        if not actor_id:
            name = name.split(" %s " % addon.LANG(20347))
            names = name[0].strip().split(" / ")
            if len(names) > 1:
                ret = xbmcgui.Dialog().select(heading=addon.LANG(32027),
                                              list=names)
                if ret == -1:
                    return None
                name = names[ret]
            else:
                name = names[0]
            busy.show_busy()
            actor_info = tmdb.get_person_info(name)
            if not actor_info:
                return None
            actor_id = actor_info["id"]
        else:
            busy.show_busy()
        dialog = DialogActorInfo(ACTOR_XML,
                                 addon.PATH,
                                 id=actor_id)
        busy.hide_busy()
        self.open_infodialog(dialog)

    def open_video_list(self, listitems=None, filters=None, mode="filter", list_id=False,
                        filter_label="", force=False, media_type="movie", search_str=""):
        """opens video list  deals with window stack items

        Args:
            listitems (dict, optional): [description]. Defaults to None.
            filters ([type], optional): [description]. Defaults to None.
            mode (str, optional): [description]. Defaults to "filter".
            list_id (bool, optional): [description]. Defaults to False.
            filter_label (str, optional): [description]. Defaults to "".
            force (bool, optional): [description]. Defaults to False.
            media_type (str, optional): [description]. Defaults to "movie".
            search_str (str, optional): [description]. Defaults to "".
        """
        # utils.log('wm open_video_list listitems: {}'.format(listitems))  #debug
        from .dialogs import DialogVideoList
        Browser = DialogVideoList.get_window(windows.DialogXML)
        dialog = Browser(LIST_XML,
                         addon.PATH,
                         listitems=listitems,
                         filters=[] if not filters else filters,
                         mode=mode,
                         list_id=list_id,
                         force=force,
                         filter_label=filter_label,
                         search_str=search_str,
                         type=media_type)
        self.open_dialog(dialog)

    def open_youtube_list(self, search_str="", filters=None, filter_label="", media_type="video"):
        """
        open video list, deal with window stack
        """
        from .dialogs import DialogYoutubeList
        YouTube = DialogYoutubeList.get_window(windows.DialogXML)
        dialog = YouTube('script-%s-YoutubeList.xml' % addon.ID, addon.PATH,
                         search_str=search_str,
                         filters=[] if not filters else filters,
                         type=media_type)
        self.open_dialog(dialog)

    def open_infodialog(self, dialog):
        if dialog.info:
            self.open_dialog(dialog)
        else:
            self.active_dialog = None
            utils.notify(addon.LANG(32143))

    def open_dialog(self, dialog):
        if self.active_dialog:
            self.window_stack.append(self.active_dialog)
            self.active_dialog.close()
        utils.check_version()
        if not addon.setting("first_start_infodialog"):
            addon.set_setting("first_start_infodialog", "True")
            xbmcgui.Dialog().ok(heading=addon.NAME,
                                message=addon.LANG(32140) + '[CR]' + addon.LANG(32141))
        self.active_dialog = dialog
        try:
            dialog.doModal()
        except SystemExit:
            pass
#        if dialog.canceled:
#            addon.set_global("infobackground", self.saved_background)
#            self.window_stack = []
#            return None
        if self.window_stack and not self.monitor.abortRequested():
            self.active_dialog = self.window_stack.pop()
            xbmc.sleep(300)
            try:
                self.active_dialog.doModal()
            except SystemExit:
                pass
        else:
            addon.set_global("infobackground", self.saved_background)

    def play_youtube_video(self, youtube_id="", listitem=None):
        """
        play youtube vid with info from *listitem
        """
        if self.active_dialog and self.active_dialog.window_type == "dialog":
            self.active_dialog.close()
        xbmc.executebuiltin("Dialog.Close(movieinformation)")
        xbmc.executebuiltin("RunPlugin(plugin://plugin.video.youtube/play/?video_id=" +
                            youtube_id + "&screensaver=true&incognito=true)")
        if self.active_dialog and self.active_dialog.window_type == "dialog":
            player.wait_for_video_end()
            self.active_dialog.doModal()


wm = WindowManager()
