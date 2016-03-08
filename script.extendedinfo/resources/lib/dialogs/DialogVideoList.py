# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from ..Utils import *
from .. import TheMovieDB as tmdb
from DialogBaseList import DialogBaseList
from ..WindowManager import wm
from ActionHandler import ActionHandler

C_MAIN_LIST = [50, 51, 52, 53, 54, 55, 500]
C_BUTTON_SORT = 5001
C_BUTTON_ORDER = 5004
C_BUTTON_ACCOUNT = 7000

ch = ActionHandler()

SORTS = {"movie": {"popularity": LANG(32110),
                   "release_date": LANG(172),
                   "revenue": LANG(32108),
                   # "Release Date": "primary_release_date",
                   "original_title": LANG(20376),
                   "vote_average": LANG(32112),
                   "vote_count": LANG(32111)},
         "tv": {"popularity": LANG(32110),
                "first_air_date": LANG(20416),
                "vote_average": LANG(32112),
                "vote_count": LANG(32111)},
         "favorites": {"created_at": LANG(32157)},
         "list": {"created_at": LANG(32157)},
         "rating": {"created_at": LANG(32157)}}
TRANSLATIONS = {"movie": LANG(20338),
                "tv": LANG(20364),
                "person": LANG(32156)}

include_adult = SETTING("include_adults").lower()


def get_window(window_type):

    class DialogVideoList(DialogBaseList, window_type):

        @busy_dialog
        def __init__(self, *args, **kwargs):
            super(DialogVideoList, self).__init__(*args, **kwargs)
            self.type = kwargs.get('type', "movie")
            self.list_id = kwargs.get("list_id", False)
            self.sort = kwargs.get('sort', "popularity")
            self.sort_label = kwargs.get('sort_label', LANG(32110))
            self.order = kwargs.get('order', "desc")
            self.logged_in = tmdb.Login.check_login()
            if self.listitem_list:
                self.listitems = create_listitems(self.listitem_list)
                self.total_items = len(self.listitem_list)
            else:
                self.update_content(force_update=kwargs.get('force', False))

        def onClick(self, control_id):
            super(DialogVideoList, self).onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super(DialogVideoList, self).onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        def update_ui(self):
            super(DialogVideoList, self).update_ui()
            self.setProperty("Type", TRANSLATIONS[self.type])
            self.getControl(5006).setVisible(self.type != "tv")
            self.getControl(5008).setVisible(self.type != "tv")
            self.getControl(5009).setVisible(self.type != "tv")
            self.getControl(5010).setVisible(self.type != "tv")

        @ch.action("contextmenu", C_MAIN_LIST)
        def context_menu(self):
            item_id = self.listitem.getProperty("id")
            listitems = [LANG(32169)] if self.type == "tv" else [LANG(32113)]
            if self.logged_in:
                listitems += [LANG(14076)]
                if not self.type == "tv":
                    listitems += [LANG(32107)]
                if self.mode == "list":
                    listitems += [LANG(32035)]
            selection = xbmcgui.Dialog().select(heading=LANG(32151),
                                                list=listitems)
            if selection == 0:
                if tmdb.set_rating_prompt(media_type=self.type,
                                          media_id=item_id,
                                          dbid=self.listitem.getProperty("dbid")):
                    xbmc.sleep(2000)
                    self.update(force_update=True)
                    self.setCurrentListPosition(self.position)
            elif selection == 1:
                tmdb.change_fav_status(media_id=item_id,
                                       media_type=self.type,
                                       status="true")
            elif selection == 2:
                self.list_dialog(item_id)
            elif selection == 3:
                tmdb.change_list_status(list_id=self.list_id,
                                        movie_id=item_id,
                                        status=False)
                self.update(force_update=True)
                self.setCurrentListPosition(self.position)

        def list_dialog(self, movie_id):
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = [LANG(32139)]
            account_lists = tmdb.get_account_lists()
            listitems += ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            listitems.append(LANG(32138))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(heading=LANG(32136),
                                            list=listitems)
            if index == 0:
                listname = xbmcgui.Dialog().input(heading=LANG(32137),
                                                  type=xbmcgui.INPUT_ALPHANUM)
                if listname:
                    list_id = tmdb.create_list(listname)
                    xbmc.sleep(1000)
                    tmdb.change_list_status(list_id=list_id,
                                            movie_id=movie_id,
                                            status=True)
            elif index == len(listitems) - 1:
                self.remove_list_dialog(account_lists)
            elif index > 0:
                tmdb.change_list_status(list_id=account_lists[index - 1]["id"],
                                        movie_id=movie_id,
                                        status=True)

        @ch.click(C_BUTTON_SORT)
        def get_sort_type(self):
            sort_key = self.mode if self.mode in ["favorites", "rating", "list"] else self.type
            listitems = [k for k in self.SORTS[sort_key].values()]
            sort_strings = [v for v in self.SORTS[sort_key].keys()]
            index = xbmcgui.Dialog().select(heading=LANG(32104),
                                            list=listitems)
            if index == -1:
                return None
            if sort_strings[index] == "vote_average":
                self.add_filter(key="vote_count.gte",
                                value="10",
                                typelabel="%s (%s)" % (LANG(32111), LANG(21406)),
                                label="10")
            self.sort = sort_strings[index]
            self.sort_label = listitems[index]
            self.update()

        def add_filter(self, **kwargs):
            super(DialogVideoList, self).add_filter(force_overwrite=kwargs["key"].endswith((".gte", ".lte")),
                                                    **kwargs)

        @ch.click(C_BUTTON_ORDER)
        def toggle_order(self):
            self.order = "desc" if self.order == "asc" else "asc"
            self.update()

        @ch.click(5007)
        def toggle_media_type(self):
            self.filters = []
            self.page = 1
            self.mode = "filter"
            self.type = "movie" if self.type == "tv" else "tv"
            self.update()

        @ch.click(C_BUTTON_ACCOUNT)
        def open_account_menu(self):
            if self.type == "tv":
                listitems = [LANG(32145)]
                if self.logged_in:
                    listitems.append(LANG(32144))
            else:
                listitems = [LANG(32135)]
                if self.logged_in:
                    listitems.append(LANG(32134))
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            if self.logged_in:
                account_lists = tmdb.get_account_lists()
                listitems += ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(heading=LANG(32136),
                                            list=listitems)
            if index == -1:
                pass
            elif index == 0:
                self.mode = "rating"
                self.sort = "created_at"
                self.sort_label = LANG(32157)
                self.filters = []
                self.page = 1
                self.update()
            elif index == 1:
                self.mode = "favorites"
                self.sort = "created_at"
                self.sort_label = LANG(32157)
                self.filters = []
                self.page = 1
                self.update()
            else:
                self.close()
                dialog = DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH,
                                         color=self.color,
                                         filters=[],
                                         mode="list",
                                         list_id=account_lists[index - 2]["id"],
                                         filter_label=account_lists[index - 2]["name"])
                dialog.doModal()

        @ch.click(5002)
        def set_genre_filter(self):
            params = {"language": SETTING("LanguageID")}
            response = tmdb.get_data(url="genre/%s/list" % (self.type),
                                     params=params,
                                     cache_days=10)
            ids = [item["id"] for item in response["genres"]]
            labels = [item["name"] for item in response["genres"]]
            index = xbmcgui.Dialog().select(heading=LANG(32151),
                                            list=labels)
            if index == -1:
                return None
            self.add_filter(key="with_genres",
                            value=str(ids[index]),
                            typelabel=LANG(135),
                            label=labels[index])
            self.mode = "filter"
            self.page = 1
            self.update()

        @ch.click(5012)
        def set_vote_count_filter(self):
            ret = True
            if not self.type == "tv":
                ret = xbmcgui.Dialog().yesno(heading=LANG(32151),
                                             line1=LANG(32106),
                                             nolabel=LANG(32150),
                                             yeslabel=LANG(32149))
            result = xbmcgui.Dialog().input(heading=LANG(32111),
                                            type=xbmcgui.INPUT_NUMERIC)
            if result:
                self.add_filter(key="vote_count.lte" if ret else "vote_count.gte",
                                value=result,
                                typelabel=LANG(32111),
                                label=" < " + result if ret else " > " + result)
                self.mode = "filter"
                self.page = 1
                self.update()

        @ch.click(5003)
        def set_year_filter(self):
            ret = xbmcgui.Dialog().yesno(heading=LANG(32151),
                                         line1=LANG(32106),
                                         nolabel=LANG(32150),
                                         yeslabel=LANG(32149))
            result = xbmcgui.Dialog().input(heading=LANG(345),
                                            type=xbmcgui.INPUT_NUMERIC)
            if not result:
                return None
            if ret:
                order = "lte"
                value = "%s-12-31" % result
                label = " < " + result
            else:
                order = "gte"
                value = "%s-01-01" % result
                label = " > " + result
            if self.type == "tv":
                self.add_filter(key="first_air_date.%s" % order,
                                value=value,
                                typelabel=LANG(20416),
                                label=label)
            else:
                self.add_filter(key="primary_release_date.%s" % order,
                                value=value,
                                typelabel=LANG(345),
                                label=label)
            self.mode = "filter"
            self.page = 1
            self.update()

        @ch.click(5008)
        def set_actor_filter(self):
            result = xbmcgui.Dialog().input(heading=LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result == -1:
                return None
            response = tmdb.get_person_info(result)
            if not response:
                return None
            self.add_filter(key="with_people",
                            value=str(response["id"]),
                            typelabel=LANG(32156),
                            label=response["name"])
            self.mode = "filter"
            self.page = 1
            self.update()

        @ch.click(C_MAIN_LIST)
        def open_media(self):
            self.last_position = self.control.getSelectedPosition()
            media_type = self.listitem.getProperty("mediatype")
            if media_type == "tvshow":
                wm.open_tvshow_info(prev_window=self,
                                    tmdb_id=self.listitem.getProperty("id"),
                                    dbid=self.listitem.getProperty("dbid"))
            elif media_type == "actor":
                wm.open_actor_info(prev_window=self,
                                   actor_id=self.listitem.getProperty("id"))
            elif media_type == "movie":
                wm.open_movie_info(prev_window=self,
                                   movie_id=self.listitem.getProperty("id"),
                                   dbid=self.listitem.getProperty("dbid"))

        @ch.click(5010)
        def set_company_filter(self):
            result = xbmcgui.Dialog().input(heading=LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result < 0:
                return None
            response = tmdb.search_company(result)
            if len(response) > 1:
                selection = xbmcgui.Dialog().select(heading=LANG(32151),
                                                    list=[item["name"] for item in response])
                if selection > -1:
                    response = response[selection]
            elif response:
                response = response[0]
            else:
                notify("No company found")
            self.add_filter(key="with_companies",
                            value=str(response["id"]),
                            typelabel=LANG(20388),
                            label=response["name"])
            self.mode = "filter"
            self.page = 1
            self.update()

        @ch.click(5009)
        def set_keyword_filter(self):
            result = xbmcgui.Dialog().input(heading=LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result == -1:
                return None
            response = tmdb.get_keyword_id(result)
            if not response:
                return None
            self.add_filter(key="with_keywords",
                            value=str(response["id"]),
                            typelabel=LANG(32114),
                            label=response["name"])
            self.mode = "filter"
            self.page = 1
            self.update()

        @ch.click(5006)
        def set_certification_filter(self):
            response = tmdb.get_certification_list(self.type)
            countries = [key for key in response.keys()]
            index = xbmcgui.Dialog().select(heading=LANG(21879),
                                            list=countries)
            if index == -1:
                return None
            country = countries[index]
            certs = ["%s  -  %s" % (i["certification"], i["meaning"]) for i in response[country]]
            index = xbmcgui.Dialog().select(heading=LANG(32151),
                                            list=certs)
            if index == -1:
                return None
            cert = certs[index].split("  -  ")[0]
            self.add_filter(key="certification_country",
                            value=country,
                            typelabel=LANG(32153),
                            label=country)
            self.add_filter(key="certification",
                            value=cert,
                            typelabel=LANG(32127),
                            label=cert)
            self.page = 1
            self.mode = "filter"
            self.update()

        def fetch_data(self, force=False):  # TODO: rewrite
            sort_by = self.sort + "." + self.order
            if self.type == "tv":
                temp = "tv"
                rated = LANG(32145)
                starred = LANG(32144)
            else:
                temp = "movies"
                rated = LANG(32135)
                starred = LANG(32134)
            if self.mode == "search":
                params = {"query": self.search_str,
                          "include_adult": include_adult,
                          "page": self.page}
                url = "search/multi"
                self.filter_label = LANG(32146) % self.search_str if self.search_str else ""
            elif self.mode == "list":
                params = {"language": SETTING("LanguageID")}
                url = "list/%s" % (self.list_id)
                # self.filter_label = LANG(32036)
            elif self.mode == "favorites":
                params = {"sort_by": sort_by,
                          "language": SETTING("LanguageID"),
                          "page": self.page,
                          "session_id": tmdb.Login.get_session_id()}
                url = "account/%s/favorite/%s" % (tmdb.Login.get_account_id(), temp)
                self.filter_label = starred
            elif self.mode == "rating":
                force = True  # workaround, should be updated after setting rating
                if self.logged_in:
                    session_id = tmdb.Login.get_session_id()
                    if not session_id:
                        notify("Could not get session id")
                        return {"listitems": [],
                                "results_per_page": 0,
                                "total_results": 0}
                    params = {"sort_by": sort_by,
                              "language": SETTING("LanguageID"),
                              "page": self.page,
                              "session_id": session_id}
                    url = "account/%s/rated/%s" % (tmdb.Login.get_account_id(), temp)
                else:
                    session_id = tmdb.Login.get_guest_session_id()
                    if not session_id:
                        notify("Could not get session id")
                        return {"listitems": [],
                                "results_per_page": 0,
                                "total_results": 0}
                    params = {"language": SETTING("LanguageID")}
                    url = "guest_session/%s/rated_movies" % (session_id)
                self.filter_label = rated
            else:
                self.set_filter_label()
                params = {"sort_by": sort_by,
                          "language": SETTING("LanguageID"),
                          "page": self.page,
                          "include_adult": include_adult}
                filters = dict((item["type"], item["id"]) for item in self.filters)
                params = merge_dicts(params, filters)
                url = "discover/%s" % (self.type)
            response = tmdb.get_data(url=url,
                                     params=params,
                                     cache_days=0 if force else 2)
            if not response:
                return None
            if self.mode == "list":
                info = {"listitems": tmdb.handle_movies(results=response["items"],
                                                        local_first=True,
                                                        sortkey=None),
                        "results_per_page": 1,
                        "total_results": len(response["items"])}
                return info
            if "results" not in response:
                # self.close()
                return {"listitems": [],
                        "results_per_page": 0,
                        "total_results": 0}
            if not response["results"]:
                notify(LANG(284))
            if self.mode == "search":
                listitems = tmdb.handle_multi_search(response["results"])
            elif self.type == "movie":
                listitems = tmdb.handle_movies(results=response["results"],
                                               local_first=False,
                                               sortkey=None)
            else:
                listitems = tmdb.handle_tvshows(results=response["results"],
                                                local_first=False,
                                                sortkey=None)
            info = {"listitems": listitems,
                    "results_per_page": response["total_pages"],
                    "total_results": response["total_results"]}
            return info

    return DialogVideoList
