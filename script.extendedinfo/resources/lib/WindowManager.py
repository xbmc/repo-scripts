# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *
import xbmcaddon
from dialogs.BaseClasses import *

from local_db import get_imdb_id_from_db
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
            dialog = self.window_stack.pop()
            xbmc.sleep(300)
            dialog.doModal()
        elif self.reopen_window:
            xbmc.sleep(500)
            xbmc.executebuiltin("Action(Info)")

    def open_movie_info(self, prev_window=None, movie_id=None, dbid=None, name=None, imdb_id=None):
        """
        open movie info, deal with window stack
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogVideoInfo
        from TheMovieDB import get_movie_tmdb_id
        if not movie_id:
            movie_id = get_movie_tmdb_id(imdb_id=imdb_id,
                                         dbid=dbid,
                                         name=name)
        movieclass = DialogVideoInfo.get_movie_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        dialog = movieclass(INFO_DIALOG_FILE, ADDON_PATH,
                            id=movie_id,
                            dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_tvshow_info(self, prev_window=None, tvshow_id=None, dbid=None, tvdb_id=None, imdb_id=None, name=None):
        """
        open tvshow info, deal with window stack
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogTVShowInfo
        from TheMovieDB import get_show_tmdb_id, search_media
        tmdb_id = None
        if tvshow_id:
            tmdb_id = tvshow_id
        elif tvdb_id:
            tmdb_id = get_show_tmdb_id(tvdb_id)
        elif imdb_id:
            tmdb_id = get_show_tmdb_id(tvdb_id=imdb_id,
                                       source="imdb_id")
        elif dbid and (int(dbid) > 0):
            tvdb_id = get_imdb_id_from_db(media_type="tvshow",
                                          dbid=dbid)
            if tvdb_id:
                tmdb_id = get_show_tmdb_id(tvdb_id)
        elif name:
            tmdb_id = search_media(media_name=name,
                                   year="",
                                   media_type="tv")
        tvshow_class = DialogTVShowInfo.get_tvshow_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        dialog = tvshow_class(INFO_DIALOG_FILE, ADDON_PATH,
                              tmdb_id=tmdb_id,
                              dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_season_info(self, prev_window=None, tvshow_id=None, season=None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs *season AND (*tvshow_id OR *tvshow)
        """
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from dialogs import DialogSeasonInfo
        from TheMovieDB import get_tmdb_data
        if not tvshow_id:
            response = get_tmdb_data("search/tv?query=%s&language=%s&" % (url_quote(tvshow), SETTING("LanguageID")), 30)
            if response["results"]:
                tvshow_id = str(response['results'][0]['id'])
            else:
                tvshow = re.sub('\(.*?\)', '', tvshow)
                response = get_tmdb_data("search/tv?query=%s&language=%s&" % (url_quote(tvshow), SETTING("LanguageID")), 30)
                if response["results"]:
                    tvshow_id = str(response['results'][0]['id'])

        season_class = DialogSeasonInfo.get_season_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        dialog = season_class(INFO_DIALOG_FILE, ADDON_PATH,
                              id=tvshow_id,
                              season=season,
                              dbid=dbid)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_episode_info(self, prev_window=None, tvshow_id=None, season=None, episode=None, tvshow=None, dbid=None):
        """
        open season info, deal with window stack
        needs *tvshow_id AND *season AND *episode
        """
        from dialogs import DialogEpisodeInfo
        from TheMovieDB import get_tmdb_data
        ep_class = DialogEpisodeInfo.get_episode_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        if not tvshow_id and tvshow:
            response = get_tmdb_data("search/tv?query=%s&language=%s&" % (urllib.quote_plus(tvshow), SETTING("LanguageID")), 30)
            if response["results"]:
                tvshow_id = str(response['results'][0]['id'])
        dialog = ep_class(INFO_DIALOG_FILE, ADDON_PATH,
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
        from TheMovieDB import get_person_info
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
            actor_info = get_person_info(name)
            if actor_info:
                actor_id = actor_info["id"]
        else:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
        actor_class = DialogActorInfo.get_actor_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        dialog = actor_class(ACTOR_DIALOG_FILE, ADDON_PATH,
                             id=actor_id)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        self.open_dialog(dialog, prev_window)

    def open_video_list(self, prev_window=None, listitems=None, filters=[], mode="filter", list_id=False, filter_label="", force=False, media_type="movie"):
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
        browser_class = DialogVideoList.get_tmdb_window(WindowXML if SETTING("window_mode") == "true" else DialogXML)
        dialog = browser_class(LIST_DIALOG_FILE, ADDON_PATH,
                               listitems=listitems,
                               color=color,
                               filters=filters,
                               mode=mode,
                               list_id=list_id,
                               force=force,
                               filter_label=filter_label,
                               type=media_type)
        if prev_window:
            self.add_to_stack(prev_window)
            prev_window.close()
        dialog.doModal()

    def open_youtube_list(self, prev_window=None, search_str="", filters=[], sort="relevance", filter_label="", media_type="video"):
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
        youtube_class = DialogYoutubeList.get_youtube_window(WindowXML)
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
            if xbmc.getCondVisibility("Window.IsVisible(movieinformation)"):
                xbmc.executebuiltin("Dialog.Close(movieinformation)")
                self.reopen_window = True
            check_version()
            if prev_window:
                self.add_to_stack(prev_window)
                prev_window.close()
            dialog.doModal()
        else:
            notify(LANG(32143))

wm = WindowManager()
