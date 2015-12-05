# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from ..Utils import *
from ..TheMovieDB import *
from ..omdb import *
from ..ImageTools import *
import threading
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from ActionHandler import ActionHandler
from .. import VideoPlayer

PLAYER = VideoPlayer.VideoPlayer()
ch = ActionHandler()


def get_movie_window(window_type):

    class DialogVideoInfo(DialogBaseInfo, window_type):

        def __init__(self, *args, **kwargs):
            super(DialogVideoInfo, self).__init__(*args, **kwargs)
            self.type = "Movie"
            data = extended_movie_info(movie_id=kwargs.get('id'),
                                       dbid=self.dbid)
            if not data:
                return None
            self.info, self.data, self.account_states = data
            sets_thread = SetItemsThread(self.info["SetId"])
            self.omdb_thread = FunctionThread(get_omdb_movie_info, self.info["imdb_id"])
            lists_thread = FunctionThread(self.sort_lists, self.data["lists"])
            filter_thread = FilterImageThread(self.info.get("thumb", ""), 25)
            for thread in [self.omdb_thread, sets_thread, lists_thread, filter_thread]:
                thread.start()
            if "dbid" not in self.info:
                self.info['poster'] = get_file(self.info.get("poster", ""))
            sets_thread.join()
            self.setinfo = sets_thread.setinfo
            self.data["similar"] = [i for i in self.data["similar"] if i["id"] not in sets_thread.id_list]
            filter_thread.join()
            self.info['ImageFilter'] = filter_thread.image
            self.info['ImageColor'] = filter_thread.imagecolor
            lists_thread.join()
            self.listitems = [(1000, self.data["actors"]),
                              (150, self.data["similar"]),
                              (250, sets_thread.listitems),
                              (450, lists_thread.listitems),
                              (550, self.data["studios"]),
                              (650, merge_with_cert_desc(self.data["releases"], "movie")),
                              (750, merge_dict_lists(self.data["crew"])),
                              (850, self.data["genres"]),
                              (950, self.data["keywords"]),
                              (1050, self.data["reviews"]),
                              (1150, self.data["videos"]),
                              (1250, self.data["images"]),
                              (1350, self.data["backdrops"])]

        def onInit(self):
            super(DialogVideoInfo, self).onInit()
            pass_dict_to_skin(data=self.info,
                              window_id=self.window_id)
            super(DialogVideoInfo, self).update_states()
            self.get_youtube_vids("%s %s, movie" % (self.info["Label"], self.info["year"]))
            self.fill_lists()
            pass_dict_to_skin(data=self.setinfo,
                              prefix="set.",
                              window_id=self.window_id)
            self.join_omdb_async()

        def onClick(self, control_id):
            super(DialogVideoInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super(DialogVideoInfo, self).onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        @ch.action("contextmenu", 150)
        @ch.action("contextmenu", 250)
        def add_movie_to_account(self):
            movie_id = self.listitem.getProperty("id")
            add_movie_to_list(movie_id)

        @ch.click(1000)
        @ch.click(750)
        def open_actor_info(self):
            wm.open_actor_info(prev_window=self,
                               actor_id=self.listitem.getProperty("id"))

        @ch.click(150)
        @ch.click(250)
        def open_movie_info(self):
            wm.open_movie_info(prev_window=self,
                               movie_id=self.listitem.getProperty("id"),
                               dbid=self.listitem.getProperty("dbid"))

        @ch.click(10)
        def play_trailer(self):
            PLAYER.play_youtube_video(youtube_id=youtube_id,
                                      listitem=self.getControl(1150).getListItem(0).getProperty("youtube_id"),
                                      window=self)

        @ch.click(550)
        def open_company_list(self):
            filters = [{"id": self.listitem.getProperty("id"),
                        "type": "with_companies",
                        "typelabel": LANG(20388),
                        "label": self.listitem.getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(1050)
        def show_review(self):
            author = self.listitem.getProperty("author")
            text = "[B]%s[/B][CR]%s" % (author, clean_text(self.listitem.getProperty("content")))
            xbmcgui.Dialog().textviewer(heading=LANG(207),
                                        text=text)

        @ch.click(950)
        def open_keyword_list(self):
            filters = [{"id": self.listitem.getProperty("id"),
                        "type": "with_keywords",
                        "typelabel": LANG(32114),
                        "label": self.listitem.getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(850)
        def open_genre_list(self):
            filters = [{"id": self.listitem.getProperty("id"),
                        "type": "with_genres",
                        "typelabel": LANG(135),
                        "label": self.listitem.getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(650)
        def open_cert_list(self):
            filters = [{"id": self.listitem.getProperty("iso_3166_1"),
                        "type": "certification_country",
                        "typelabel": LANG(32153),
                        "label": self.listitem.getProperty("iso_3166_1")},
                       {"id": self.listitem.getProperty("certification"),
                        "type": "certification",
                        "typelabel": LANG(32127),
                        "label": self.listitem.getProperty("certification")},
                       {"id": self.listitem.getProperty("year"),
                        "type": "year",
                        "typelabel": LANG(345),
                        "label": self.listitem.getProperty("year")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(450)
        def open_lists_list(self):
            wm.open_video_list(prev_window=self,
                               mode="list",
                               list_id=self.listitem.getProperty("id"),
                               filter_label=self.listitem.getLabel())

        @ch.click(6002)
        def show_list_dialog(self):
            listitems = [LANG(32134), LANG(32135)]
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            account_lists = get_account_lists()
            for item in account_lists:
                listitems.append("%s (%i)" % (item["name"], item["item_count"]))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(LANG(32136), listitems)
            if index == -1:
                pass
            elif index == 0:
                wm.open_video_list(prev_window=self,
                                   mode="favorites")
            elif index == 1:
                wm.open_video_list(prev_window=self,
                                   mode="rating")
            else:
                wm.open_video_list(prev_window=self,
                                   mode="list",
                                   list_id=account_lists[index - 2]["id"],
                                   filter_label=account_lists[index - 2]["name"],
                                   force=True)

        @ch.click(132)
        def show_plot(self):
            xbmcgui.Dialog().textviewer(heading=LANG(207),
                                        text=self.info["Plot"])

        @ch.click(6001)
        def set_rating_dialog(self):
            if set_rating_prompt("movie", self.info["id"]):
                self.update_states()

        @ch.click(6005)
        def add_to_list_dialog(self):
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            account_lists = get_account_lists()
            listitems = ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            listitems.insert(0, LANG(32139))
            listitems.append(LANG(32138))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(heading=LANG(32136),
                                            list=listitems)
            if index == 0:
                listname = xbmcgui.Dialog().input(heading=LANG(32137),
                                                  type=xbmcgui.INPUT_ALPHANUM)
                if not listname:
                    return None
                list_id = create_list(listname)
                xbmc.sleep(1000)
                change_list_status(list_id=list_id,
                                   movie_id=self.info["id"],
                                   status=True)
            elif index == len(listitems) - 1:
                self.remove_list_dialog(account_lists)
            elif index > 0:
                change_list_status(account_lists[index - 1]["id"], self.info["id"], True)
                self.update_states()

        @ch.click(6003)
        def change_list_status(self):
            change_fav_status(media_id=self.info["id"],
                              media_type="movie",
                              status=str(not bool(self.account_states["favorite"])).lower())
            self.update_states()

        @ch.click(6006)
        def open_rating_list(self):
            wm.open_video_list(prev_window=self,
                               mode="rating")

        @ch.click(9)
        def play_movie_resume(self):
            self.close()
            get_kodi_json(method="Player.Open",
                          params='{"item": {"movieid": %s}, "options":{"resume": %s}}' % (self.info['dbid'], "true"))

        @ch.click(8)
        def play_movie_no_resume(self):
            self.close()
            get_kodi_json(method="Player.Open",
                          params='{"item": {"movieid": %s}, "options":{"resume": %s}}' % (self.info['dbid'], "false"))

        @ch.click(445)
        def show_manage_dialog(self):
            manage_list = []
            movie_id = str(self.info.get("dbid", ""))
            imdb_id = str(self.info.get("imdb_id", ""))
            if movie_id:
                artwork_call = "RunScript(script.artwork.downloader,%s)"
                manage_list += [[LANG(413), artwork_call % ("mode=gui,mediatype=movie,dbid=" + movie_id + ")")],
                                [LANG(14061), artwork_call % ("mediatype=movie, dbid=" + movie_id + ")")],
                                [LANG(32101), artwork_call % ("mode=custom,mediatype=movie,dbid=" + movie_id + ",extrathumbs)")],
                                [LANG(32100), artwork_call % ("mode=custom,mediatype=movie,dbid=" + movie_id + ")")]]
            else:
                manage_list += [[LANG(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=" + imdb_id + ")||Notification(script.extendedinfo,%s))" % LANG(32059)]]
            if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and movie_id:
                manage_list.append([LANG(32103), "RunScript(script.libraryeditor,DBID=" + movie_id + ")"])
            manage_list.append([LANG(1049), "Addon.OpenSettings(script.extendedinfo)"])
            selection = xbmcgui.Dialog().select(heading=LANG(32133),
                                                list=[i[0] for i in manage_list])
            if selection > -1:
                for item in manage_list[selection][1].split("||"):
                    xbmc.executebuiltin(item)

        def sort_lists(self, lists):
            if not self.logged_in:
                return lists
            account_list = get_account_lists(10)  # use caching here, forceupdate everywhere else
            id_list = [item["id"] for item in account_list]
            own_lists = [item for item in lists if item["id"] in id_list]
            own_lists = [dict({"account": "True"}, **item) for item in own_lists]
            misc_lists = [item for item in lists if item["id"] not in id_list]
            return own_lists + misc_lists

        def update_states(self):
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            _, __, self.account_states = extended_movie_info(self.info["id"], self.dbid, 0)
            super(DialogVideoInfo, self).update_states()

        def remove_list_dialog(self, account_lists):
            listitems = ["%s (%i)" % (d["name"], d["item_count"]) for d in account_lists]
            index = xbmcgui.Dialog().select(LANG(32138), listitems)
            if index >= 0:
                remove_list(account_lists[index]["id"])
                self.update_states()

        @run_async
        def join_omdb_async(self):
            self.omdb_thread.join()
            pass_dict_to_skin(data=self.omdb_thread.listitems,
                              prefix="omdb.",
                              window_id=self.window_id)

    class SetItemsThread(threading.Thread):

        def __init__(self, set_id=""):
            threading.Thread.__init__(self)
            self.set_id = set_id

        def run(self):
            if self.set_id:
                self.listitems, self.setinfo = get_set_movies(self.set_id)
                self.id_list = [item["id"] for item in self.listitems]
            else:
                self.id_list = []
                self.listitems = []
                self.setinfo = {}

    return DialogVideoInfo
