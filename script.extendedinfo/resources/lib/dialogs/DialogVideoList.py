# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui

from resources.lib import TheMovieDB as tmdb
from resources.lib.WindowManager import wm

from kodi65 import addon
from kodi65 import utils
from kodi65 import busy
from kodi65 import confirmdialog
from kodi65 import selectdialog
from kodi65 import ActionHandler
from kodi65 import DialogBaseList

ID_BUTTON_SORT = 5001
ID_BUTTON_GENREFILTER = 5002
ID_BUTTON_YEARFILTER = 5003
ID_BUTTON_ORDER = 5004
ID_BUTTON_CERTFILTER = 5006
ID_BUTTON_ACTORFILTER = 5008
ID_BUTTON_KEYWORDFILTER = 5009
ID_BUTTON_COMPANYFILTER = 5010
ID_BUTTON_RUNTIMEFILTER = 5011
ID_BUTTON_VOTECOUNTFILTER = 5012
ID_BUTTON_ACCOUNT = 7000

ch = ActionHandler()

include_adult = addon.setting("include_adults").lower()


def get_window(window_type):

    class DialogVideoList(DialogBaseList, window_type):

        TYPES = ["movie", "tv"]

        FILTERS = {"certification_country": addon.LANG(32153),
                   "certification": addon.LANG(32127),
                   "year": addon.LANG(562),
                   "with_genres": addon.LANG(135),
                   "with_people": addon.LANG(32156),
                   "with_companies": addon.LANG(20388),
                   "with_networks": addon.LANG(32152),
                   "with_keywords": addon.LANG(32114),
                   "first_air_date": addon.LANG(20416),
                   "with_runtime": xbmc.getLocalizedString(2050),
                   "primary_release_date": addon.LANG(345),
                   "vote_count": addon.LANG(32111)}

        TRANSLATIONS = {"movie": addon.LANG(20338),
                        "tv": addon.LANG(20364),
                        "person": addon.LANG(32156)}

        SORTS = {"movie": {"popularity": addon.LANG(32110),
                           "release_date": addon.LANG(172),
                           "revenue": addon.LANG(32108),
                           # "Release Date": "primary_release_date",
                           "original_title": addon.LANG(20376),
                           "vote_average": addon.LANG(32112),
                           "vote_count": addon.LANG(32111)},
                 "tv": {"popularity": addon.LANG(32110),
                        "first_air_date": addon.LANG(20416),
                        "vote_average": addon.LANG(32112)},
                 "favorites": {"created_at": addon.LANG(32157)},
                 "list": {"created_at": addon.LANG(32157)},
                 "rating": {"created_at": addon.LANG(32157)}}

        LABEL2 = {"popularity": lambda x: x.get_property("popularity"),
                  "release_date": lambda x: x.get_info("premiered"),
                  "revenue": lambda x: x.get_info("genre"),
                  "vote_average": lambda x: x.get_info("rating"),
                  "vote_count": lambda x: "{} {}".format(x.get_info("votes"), addon.LANG(32082)),
                  "first_air_date": lambda x: x.get_info("premiered"),
                  "created_at": lambda x: x.get_property("created_at"),
                  "original_title": lambda x: x.get_info("originaltitle")}

        @busy.set_busy
        def __init__(self, *args, **kwargs):
            self.type = kwargs.get('type', "movie")
            self.list_id = kwargs.get("list_id", False)
            self.logged_in = tmdb.Login.check_login()
            super(DialogVideoList, self).__init__(*args, **kwargs)

        def onClick(self, control_id):
            super(DialogVideoList, self).onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super(DialogVideoList, self).onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        def update_ui(self):
            super(DialogVideoList, self).update_ui()
            self.getControl(ID_BUTTON_CERTFILTER).setVisible(self.type != "tv")
            self.getControl(ID_BUTTON_ACTORFILTER).setVisible(self.type != "tv")
            self.getControl(ID_BUTTON_KEYWORDFILTER).setVisible(self.type != "tv")
            self.getControl(ID_BUTTON_COMPANYFILTER).setVisible(self.type != "tv")

        @ch.context("tvshow")
        @ch.context("movie")
        def context_menu(self, control_id):
            item_id = self.FocusedItem(control_id).getProperty("id")
            media_type = self.FocusedItem(control_id).getVideoInfoTag().getMediaType()
            listitems = [addon.LANG(32169)] if media_type == "tvshow" else [addon.LANG(32113)]
            if self.logged_in:
                listitems += [addon.LANG(14076)]
                if not self.type == "tv":
                    listitems += [addon.LANG(32107)]
                if self.mode == "list":
                    listitems += [addon.LANG(32035)]
            index = xbmcgui.Dialog().contextmenu(list=listitems)
            if index == 0:
                # HACK until we can get userrating from listitem via python
                rating = utils.get_infolabel("listitem.userrating")
                rating = utils.input_userrating(preselect=int(rating) if rating.isdigit() else -1)
                if rating == -1:
                    return None
                if tmdb.set_rating(media_type="tv" if media_type == "tvshow" else "movie",
                                   media_id=item_id,
                                   rating=rating,
                                   dbid=self.FocusedItem(control_id).getVideoInfoTag().getDbId()):
                    xbmc.sleep(2000)
                    self.update(force_update=True)
                    self.setCurrentListPosition(self.position)
            elif index == 1:
                tmdb.change_fav_status(media_id=item_id,
                                       media_type=self.type,
                                       status="true")
            elif index == 2:
                self.list_dialog(item_id)
            elif index == 3:
                tmdb.change_list_status(list_id=self.list_id,
                                        movie_id=item_id,
                                        status=False)
                self.update(force_update=True)
                self.setCurrentListPosition(self.position)

        def list_dialog(self, movie_id):
            busy.show_busy()
            listitems = [addon.LANG(32139)]
            account_lists = tmdb.get_account_lists()
            listitems += ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            listitems.append(addon.LANG(32138))
            busy.hide_busy()
            index = xbmcgui.Dialog().select(heading=addon.LANG(32136),
                                            list=listitems)
            if index == 0:
                listname = xbmcgui.Dialog().input(heading=addon.LANG(32137),
                                                  type=xbmcgui.INPUT_ALPHANUM)
                if listname:
                    xbmc.sleep(1000)
                    tmdb.change_list_status(list_id=tmdb.create_list(listname),
                                            movie_id=movie_id,
                                            status=True)
            elif index == len(listitems) - 1:
                tmdb.remove_list_dialog(tmdb.handle_lists(account_lists))
            elif index > 0:
                tmdb.change_list_status(list_id=account_lists[index - 1]["id"],
                                        movie_id=movie_id,
                                        status=True)

        @property
        def sort_key(self):
            return self.mode if self.mode in ["favorites", "rating", "list"] else self.type

        @property
        def default_sort(self):
            return "created_at" if self.mode in ["favorites", "rating", "list"] else "popularity"

        @ch.click(ID_BUTTON_SORT)
        def get_sort_type(self, control_id):
            if not self.choose_sort_method(self.sort_key):
                return None
            if self.sort == "vote_average":
                self.add_filter(key="vote_count.gte",
                                value="10",
                                label="10",
                                reset=False)
            self.update()

        def add_filter(self, **kwargs):
            key = kwargs["key"].replace(".gte", "").replace(".lte", "")
            kwargs["typelabel"] = self.FILTERS[key]
            if kwargs["key"].endswith(".lte"):
                kwargs["label"] = "< %s" % kwargs["label"]
            if kwargs["key"].endswith(".gte"):
                kwargs["label"] = "> %s" % kwargs["label"]
            super(DialogVideoList, self).add_filter(force_overwrite=kwargs["key"].endswith((".gte", ".lte")),
                                                    **kwargs)

        @ch.click(ID_BUTTON_ORDER)
        def toggle_order(self, control_id):
            self.order = "desc" if self.order == "asc" else "asc"
            self.update()

        @ch.click(ID_BUTTON_ACCOUNT)
        def open_account_menu(self, control_id):
            if self.type == "tv":
                listitems = [addon.LANG(32145)]
                if self.logged_in:
                    listitems.append(addon.LANG(32144))
            else:
                listitems = [addon.LANG(32135)]
                if self.logged_in:
                    listitems.append(addon.LANG(32134))
            busy.show_busy()
            if self.logged_in:
                account_lists = tmdb.get_account_lists()
                listitems += ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            busy.hide_busy()
            index = xbmcgui.Dialog().select(heading=addon.LANG(32136),
                                            list=listitems)
            if index == -1:
                pass
            elif index == 0:
                self.set_sort("created_at")
                self.filters = []
                self.reset("rating")
            elif index == 1:
                self.set_sort("created_at")
                self.filters = []
                self.reset("favorites")
            else:
                self.close()
                dialog = wm.open_video_list(filters=[],
                                            mode="list",
                                            list_id=account_lists[index - 2]["id"],
                                            filter_label=account_lists[index - 2]["name"])
                dialog.doModal()

        @ch.click(ID_BUTTON_GENREFILTER)
        def set_genre_filter(self, control_id):
            params = {"language": addon.setting("LanguageID")}
            response = tmdb.get_data(url="genre/%s/list" % (self.type),
                                     params=params,
                                     cache_days=100)
            selected = [i["id"] for i in self.filters if i["type"] == "with_genres"]
            ids = [item["id"] for item in response["genres"]]
            labels = [item["name"] for item in response["genres"]]
            preselect = [ids.index(int(i)) for i in selected[0].split(",")] if selected else []
            indexes = xbmcgui.Dialog().multiselect(heading=addon.LANG(32151),
                                                   options=labels,
                                                   preselect=preselect)
            if indexes is None:
                return None
            self.filters = [i for i in self.filters if i["type"] != "with_genres"]
            for i in indexes:
                self.add_filter(key="with_genres",
                                value=ids[i],
                                label=labels[i],
                                reset=False)
            self.reset()

        @ch.click(ID_BUTTON_VOTECOUNTFILTER)
        def set_vote_count_filter(self, control_id):
            ret = True
            if not self.type == "tv":
                ret = confirmdialog.open(header=addon.LANG(32151),
                                         text=addon.LANG(32106),
                                         nolabel=addon.LANG(32150),
                                         yeslabel=addon.LANG(32149))
            if ret == -1:
                return None
            result = xbmcgui.Dialog().input(heading=addon.LANG(32111),
                                            type=xbmcgui.INPUT_NUMERIC)
            if result:
                self.add_filter(key="vote_count.lte" if ret == 1 else "vote_count.gte",
                                value=result,
                                label=result)

        @ch.click(ID_BUTTON_YEARFILTER)
        def set_year_filter(self, control_id):
            ret = confirmdialog.open(header=addon.LANG(32151),
                                     text=addon.LANG(32106),
                                     nolabel=addon.LANG(32150),
                                     yeslabel=addon.LANG(32149))
            if ret == -1:
                return None
            result = xbmcgui.Dialog().input(heading=addon.LANG(345),
                                            type=xbmcgui.INPUT_NUMERIC)
            if not result:
                return None
            value = "{}-12-31" if ret == 1 else "{}-01-01"
            key = "first_air_date" if self.type == "tv" else "primary_release_date"
            self.add_filter(key="%s.%s" % (key, "lte" if ret == 1 else "gte"),
                            value=value.format(result),
                            label=result)

        @ch.click(ID_BUTTON_RUNTIMEFILTER)
        def set_runtime_filter(self, control_id):
            ret = confirmdialog.open(header=addon.LANG(32151),
                                     text=addon.LANG(32106),
                                     nolabel=addon.LANG(32150),
                                     yeslabel=addon.LANG(32149))
            if ret == -1:
                return None
            result = xbmcgui.Dialog().input(heading=xbmc.getLocalizedString(2050),
                                            type=xbmcgui.INPUT_NUMERIC)
            if not result:
                return None
            self.add_filter(key="with_runtime.%s" % ("lte" if ret == 1 else "gte"),
                            value=result,
                            label="{} min".format(result))

        @ch.click(ID_BUTTON_ACTORFILTER)
        def set_actor_filter(self, control_id):
            result = xbmcgui.Dialog().input(heading=addon.LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result == -1:
                return None
            response = tmdb.get_person_info(result)
            if not response:
                return None
            self.add_filter(key="with_people",
                            value=response["id"],
                            label=response["name"])

        @ch.info("movie")
        @ch.click_by_type("movie")
        def open_movie(self, control_id):
            wm.open_movie_info(movie_id=self.FocusedItem(control_id).getProperty("id"),
                               dbid=self.FocusedItem(control_id).getVideoInfoTag().getDbId())

        @ch.info("tvshow")
        @ch.click_by_type("tvshow")
        def open_tvshow(self, control_id):
            wm.open_tvshow_info(tmdb_id=self.FocusedItem(control_id).getProperty("id"),
                                dbid=self.FocusedItem(control_id).getVideoInfoTag().getDbId())

        @ch.info("artist")
        @ch.click_by_type("artist")
        def open_media(self, control_id):
            wm.open_actor_info(actor_id=self.FocusedItem(control_id).getProperty("id"))

        @ch.click(ID_BUTTON_COMPANYFILTER)
        def set_company_filter(self, control_id):
            result = xbmcgui.Dialog().input(heading=addon.LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result < 0:
                return None
            items = tmdb.search_companies(result)
            if len(items) > 1:
                index = selectdialog.open(header=addon.LANG(32151),
                                          listitems=items)
                if index > -1:
                    item = items[index]
            elif items:
                item = items[0]
            else:
                utils.notify("No company found")
            self.add_filter(key="with_companies",
                            value=item.get_property("id"),
                            label=item.get_label())

        @ch.click(ID_BUTTON_KEYWORDFILTER)
        def set_keyword_filter(self, control_id):
            result = xbmcgui.Dialog().input(heading=addon.LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if not result or result == -1:
                return None
            keywords = tmdb.get_keywords(result)
            if not keywords:
                return None
            if len(keywords) > 1:
                index = xbmcgui.Dialog().select(heading=addon.LANG(32114),
                                                list=[item["name"] for item in keywords])
                keyword = keywords[index] if index > -1 else None
                if not keyword:
                    return None
            else:
                keyword = keywords[0]
            self.add_filter(key="with_keywords",
                            value=keyword["id"],
                            label=keyword["name"])

        @ch.click(ID_BUTTON_CERTFILTER)
        def set_certification_filter(self, control_id):
            response = tmdb.get_certification_list(self.type)
            countries = [key for key in response.keys()]
            index = xbmcgui.Dialog().select(heading=addon.LANG(21879),
                                            list=countries)
            if index == -1:
                return None
            country = countries[index]
            certs = ["%s  -  %s" % (i["certification"], i["meaning"]) for i in response[country]]
            index = xbmcgui.Dialog().select(heading=addon.LANG(32151),
                                            list=certs)
            if index == -1:
                return None
            cert = certs[index].split("  -  ")[0]
            self.add_filter(key="certification_country",
                            value=country,
                            label=country,
                            reset=False)
            self.add_filter(key="certification",
                            value=cert,
                            label=cert)

        def fetch_data(self, force=False):  # TODO: rewrite
            sort_by = self.sort + "." + self.order
            temp = "tv" if self.type == "tv" else "movies"
            if self.mode == "search":
                self.filter_label = addon.LANG(32146) % self.search_str if self.search_str else ""
                return tmdb.multi_search(search_str=self.search_str,
                                         page=self.page,
                                         cache_days=0 if force else 2)
            elif self.mode == "list":
                return tmdb.get_list_movies(list_id=self.list_id,
                                            force=force)
            elif self.mode == "favorites":
                self.filter_label = addon.LANG(32144) if self.type == "tv" else addon.LANG(32134)
                return tmdb.get_fav_items(media_type=temp,
                                          sort_by=sort_by,
                                          page=self.page)
            elif self.mode == "rating":
                self.filter_label = addon.LANG(32145) if self.type == "tv" else addon.LANG(32135)
                return tmdb.get_rated_media_items(media_type=temp,
                                                  sort_by=sort_by,
                                                  page=self.page,
                                                  cache_days=0)
            else:
                self.set_filter_label()
                params = {"sort_by": sort_by,
                          "language": addon.setting("LanguageID"),
                          "page": self.page,
                          "include_adult": include_adult}
                filters = {item["type"]: item["id"] for item in self.filters}
                response = tmdb.get_data(url="discover/%s" % (self.type),
                                         params=utils.merge_dicts(params, filters),
                                         cache_days=0 if force else 2)

                if not response["results"]:
                    utils.notify(addon.LANG(284))
                    return None
                if self.type == "movie":
                    itemlist = tmdb.handle_movies(results=response["results"],
                                                  local_first=False,
                                                  sortkey=None)
                else:
                    itemlist = tmdb.handle_tvshows(results=response["results"],
                                                   local_first=False,
                                                   sortkey=None)
                itemlist.set_totals(response["total_results"])
                itemlist.set_total_pages(response["total_pages"])
                return itemlist

    return DialogVideoList
