# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

from __future__ import annotations

import threading

import xbmc
import xbmcgui
from resources.kutil131 import ActionHandler, addon, busy, kodijson

from resources.kutil131 import imagetools, utils
from resources.lib import themoviedb as tmdb
from resources.lib import omdb
from resources.lib.windowmanager import wm

from .dialogvideoinfo import DialogVideoInfo

ID_LIST_SIMILAR = 150
ID_LIST_SETS = 250
ID_LIST_YOUTUBE = 350
ID_LIST_LISTS = 450
ID_LIST_STUDIOS = 550
ID_LIST_CERTS = 650
ID_LIST_CREW = 750
ID_LIST_GENRES = 850
ID_LIST_KEYWORDS = 950
ID_LIST_ACTORS = 1000
ID_LIST_REVIEWS = 1050
ID_LIST_VIDEOS = 1150
ID_LIST_IMAGES = 1250
ID_LIST_BACKDROPS = 1350

ID_BUTTON_PLAY_NORESUME = 8
ID_BUTTON_PLAY_RESUME = 9
ID_BUTTON_TRAILER = 10
ID_BUTTON_SETRATING = 6001
ID_BUTTON_OPENLIST = 6002
ID_BUTTON_ADDTOLIST = 6005
ID_BUTTON_RATED = 6006

ch = ActionHandler()


class DialogMovieInfo(DialogVideoInfo):
    """ Class that creates a new movie info dialog

    Args:
        DialogVideoInfo: The super class

    Returns:
        DialogMmovieInfo: an instance
    """
    TYPE = "Movie"
    TYPE_ALT = "movie"
    LISTS = [(ID_LIST_ACTORS, "actors"),
             (ID_LIST_SIMILAR, "similar"),
             (ID_LIST_SETS, "sets"),
             (ID_LIST_LISTS, "lists"),
             (ID_LIST_STUDIOS, "studios"),
             (ID_LIST_CERTS, "releases"),
             (ID_LIST_CREW, "crew"),
             (ID_LIST_GENRES, "genres"),
             (ID_LIST_KEYWORDS, "keywords"),
             (ID_LIST_REVIEWS, "reviews"),
             (ID_LIST_VIDEOS, "videos"),
             (ID_LIST_IMAGES, "images"),
             (ID_LIST_BACKDROPS, "backdrops")]

    # BUTTONS = [ID_BUTTON_OPENLIST,
    #            ID_BUTTON_ADDTOLIST]

    def __init__(self, *args, **kwargs) -> DialogMovieInfo:
        """Creates a new instance of DialogMovieInfo

        kwargs:
            id(int): the tmdb movie id
            dbid(int): the local Kodi dbid

        Returns:  dialogmovieinfo
        """
        super().__init__(*args, **kwargs)
        data: tuple | None = tmdb.extended_movie_info(movie_id=kwargs.get('id'),
                                                        dbid=kwargs.get('dbid'))
        if not data:
            return None
        self.info, self.lists, self.states = data
        sets_thread = SetItemsThread(self.info.get_property("set_id"))
        self.omdb_thread = utils.FunctionThread(function=omdb.get_movie_info,
                                                param=self.info.get_property("imdb_id"))
        self.omdb_thread.start()
        sets_thread.start()
        self.info.update_properties(
            imagetools.blur(self.info.get_art("thumb")))
        if not self.info.get_info("dbid"):
            self.info.set_art("poster", utils.get_file(
                self.info.get_art("poster")))
        sets_thread.join()
        self.info.update_properties(
                {f"set.{k}": v for k, v in list(sets_thread.setinfo.items())})
        set_ids = [item.get_property("id") for item in sets_thread.listitems]
        if self.lists and self.lists.get('similar'):
            self.lists["similar"] = [i for i in self.lists["similar"]
                                     if i.get_property("id") not in set_ids]
        self.lists["sets"] = sets_thread.listitems

    def onInit(self):
        super().onInit()
        super().update_states()
        self.get_youtube_vids("%s %s, movie" % (self.info.label,
                                                self.info.get_info("year")))
        self.set_omdb_infos_async()

    def onClick(self, control_id):
        super().onClick(control_id)
        ch.serve(control_id, self)

    def set_buttons(self):
        super().set_buttons()
        condition = self.info.get_info("dbid") and int(
            self.info.get_property("percentplayed")) > 0
        self.set_visible(ID_BUTTON_PLAY_RESUME, condition)
        self.set_visible(ID_BUTTON_PLAY_NORESUME, self.info.get_info("dbid"))
        self.set_visible(ID_BUTTON_TRAILER, self.info.get_info("trailer"))
        self.set_visible(ID_BUTTON_SETRATING, True)
        self.set_visible(ID_BUTTON_RATED, True)
        self.set_visible(ID_BUTTON_ADDTOLIST, True)
        self.set_visible(ID_BUTTON_OPENLIST, True)

    @ch.click(ID_BUTTON_TRAILER)
    def youtube_button(self, control_id):
        wm.play_youtube_video(youtube_id=self.info.get_property("trailer"),
                              listitem=self.info.get_listitem())

    @ch.click(ID_LIST_STUDIOS)
    def company_list(self, control_id):
        filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                    "type": "with_companies",
                    "label": self.FocusedItem(control_id).getLabel()}]
        wm.open_video_list(filters=filters)

    @ch.click(ID_LIST_REVIEWS)
    def reviews_list(self, control_id):
        author = self.FocusedItem(control_id).getProperty("author")
        text = "[B]%s[/B][CR]%s" % (author,
                                    self.FocusedItem(control_id).getProperty("content"))
        xbmcgui.Dialog().textviewer(heading=addon.LANG(183),
                                    text=text)

    @ch.click(ID_LIST_KEYWORDS)
    def keyword_list(self, control_id):
        filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                    "type": "with_keywords",
                    "label": self.FocusedItem(control_id).getLabel()}]
        wm.open_video_list(filters=filters)

    @ch.click(ID_LIST_GENRES)
    def genre_list(self, control_id):
        filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                    "type": "with_genres",
                    "label": self.FocusedItem(control_id).getLabel()}]
        wm.open_video_list(filters=filters)

    @ch.click(ID_LIST_CERTS)
    def cert_list(self, control_id):
        filters = [{"id": self.FocusedItem(control_id).getProperty("iso_3166_1"),
                    "type": "certification_country",
                    "label": self.FocusedItem(control_id).getProperty("iso_3166_1")},
                   {"id": self.FocusedItem(control_id).getProperty("certification"),
                    "type": "certification",
                    "label": self.FocusedItem(control_id).getProperty("certification")}]
        wm.open_video_list(filters=filters)

    @ch.click(ID_LIST_LISTS)
    def movielists_list(self, control_id):
        wm.open_video_list(mode="list",
                           list_id=self.FocusedItem(
                               control_id).getProperty("id"),
                           filter_label=self.FocusedItem(control_id).getLabel())

    @ch.click(ID_BUTTON_OPENLIST)
    def open_list_button(self, control_id):
        busy.show_busy()
        movie_lists = tmdb.get_account_lists()
        listitems = ["%s (%i)" % (i["name"], i["item_count"])
                     for i in movie_lists]
        listitems = [addon.LANG(32134), addon.LANG(32135)] + listitems
        busy.hide_busy()
        index = xbmcgui.Dialog().select(addon.LANG(32136), listitems)
        if index == -1:
            pass
        elif index < 2:
            wm.open_video_list(mode="favorites" if index == 0 else "rating")
        else:
            wm.open_video_list(mode="list",
                               list_id=movie_lists[index - 2]["id"],
                               filter_label=movie_lists[index - 2]["name"],
                               force=True)

    @ch.click(ID_BUTTON_ADDTOLIST)
    def add_to_list_button(self, control_id):
        busy.show_busy()
        account_lists = tmdb.get_account_lists()
        listitems = ["%s (%i)" % (i["name"], i["item_count"])
                     for i in account_lists]
        listitems.insert(0, addon.LANG(32139))
        listitems.append(addon.LANG(32138))
        busy.hide_busy()
        index = xbmcgui.Dialog().select(heading=addon.LANG(32136),
                                        list=listitems)
        if index == 0:
            listname = xbmcgui.Dialog().input(heading=addon.LANG(32137),
                                              type=xbmcgui.INPUT_ALPHANUM)
            if not listname:
                return None
            list_id = tmdb.create_list(listname)
            xbmc.sleep(1000)
            tmdb.change_list_status(list_id=list_id,
                                    movie_id=self.info.get_property("id"),
                                    status=True)
        elif index == len(listitems) - 1:
            if tmdb.remove_list_dialog(tmdb.handle_lists(account_lists)):
                self.update_states()
        elif index > 0:
            tmdb.change_list_status(
                account_lists[index - 1]["id"], self.info.get_property("id"), True)
            self.update_states()

    @ch.click(ID_BUTTON_RATED)
    def rating_button(self, control_id):
        wm.open_video_list(mode="rating")

    @ch.click(ID_BUTTON_PLAY_RESUME)
    def play_noresume_button(self, control_id):
        self.exit_script()
        xbmc.executebuiltin("Dialog.Close(movieinformation)")
        kodijson.play_media("movie", self.info["dbid"], True)

    @ch.click(ID_BUTTON_PLAY_NORESUME)
    def play_resume_button(self, control_id):
        self.exit_script()
        xbmc.executebuiltin("Dialog.Close(movieinformation)")
        kodijson.play_media("movie", self.info["dbid"], False)

    def get_manage_options(self):
        options = []
        movie_id = self.info.get_info("dbid")
        imdb_id = self.info.get_property("imdb_id")
        #options += [(addon.LANG(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=%s)" % imdb_id),
        #            (addon.LANG(32170), "RunPlugin(plugin://plugin.video.trakt_list_manager/watchlist/movies/add?imdb_id=%s)" % imdb_id)]
        options.append(
            (addon.LANG(1049), "Addon.OpenSettings(script.extendedinfo)"))
        return options

    def update_states(self):
        xbmc.sleep(2000)  # delay because MovieDB takes some time to update
        info = tmdb.get_movie(movie_id=self.info.get_property("id"),
                              cache_days=0)
        self.states = info.get("account_states")
        super().update_states()

    @utils.run_async
    def set_omdb_infos_async(self) -> None:
        """ sets home window properties such as tomato for OMDb response items
        """
        self.omdb_thread.join()
        utils.dict_to_windowprops(data=self.omdb_thread.listitems,
                                  prefix="omdb.",
                                  window_id=self.window_id)


class SetItemsThread(threading.Thread):
    """Thread fetches movies in set from tmdb

    Args:
        threading.Thead (super class): python thread class
    """

    def __init__(self, set_id="") -> SetItemsThread:
        """Creates a new SetItemsThread instance to run async
            returns: SetItemsThread instance
        """
        threading.Thread.__init__(self)
        self.set_id = set_id
        self.listitems = []
        self.setinfo = {}

    def run(self):
        if self.set_id and self.set_id != 0:
            self.listitems, self.setinfo = tmdb.get_set_movies(self.set_id)
