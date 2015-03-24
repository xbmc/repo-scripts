import xbmc
import xbmcaddon
import xbmcgui
from Utils import *
import DialogVideoInfo
import DialogTVShowInfo
import DialogActorInfo
homewindow = xbmcgui.Window(10000)
from TheMovieDB import *

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')
addon_version = addon.getAddonInfo('version')
addon_strings = addon.getLocalizedString
addon_path = addon.getAddonInfo('path').decode("utf-8")
include_adult = str(addon.getSetting("include_adults")).lower()
sorts = {"movie": {addon.getLocalizedString(32110): "popularity",
                   xbmc.getLocalizedString(172): "release_date",
                   addon.getLocalizedString(32108): "revenue",
                   # "Release Date": "primary_release_date",
                   xbmc.getLocalizedString(20376): "original_title",
                   addon.getLocalizedString(32111): "vote_average",
                   addon.getLocalizedString(32111): "vote_count"},
            "tv": {addon.getLocalizedString(32110): "popularity",
                   xbmc.getLocalizedString(20416): "first_air_date",
                   addon.getLocalizedString(32111): "vote_average",
                   addon.getLocalizedString(32111): "vote_count"},
     "favorites": {addon.getLocalizedString(32157): "created_at"},
     "list": {addon.getLocalizedString(32157): "created_at"},
     "rating": {addon.getLocalizedString(32157): "created_at"}}
translations = {"movie": xbmc.getLocalizedString(20338),
                "tv": xbmc.getLocalizedString(20364)}

class DialogVideoList(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.listitem_list = kwargs.get('listitems', None)
        self.color = kwargs.get('color', "FFAAAAAA")
        self.type = kwargs.get('type', "movie")
        self.search_string = kwargs.get('search_string', "")
        self.page = 1
        self.totalpages = 1
        self.totalitems = 0
        self.filter_label = kwargs.get("filter_label", "")
        self.mode = kwargs.get("mode", "filter")
        self.list_id = kwargs.get("list_id", False)
        self.sort = kwargs.get('sort', "popularity")
        self.sort_label = kwargs.get('sort_label', "Popularity")
        self.order = kwargs.get('order', "desc")
        force = kwargs.get('force', False)
        self.logged_in = checkLogin()
        self.filters = kwargs.get('filters', [])
        if self.listitem_list:
            self.listitems = create_listitems(self.listitem_list)
            self.totalitems = len(self.listitem_list)
        else:
            self.update_content(force_update=force)
            # Notify(str(self.totalpages))
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        homewindow.setProperty("WindowColor", self.color)
        self.windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.windowid)
        self.window.setProperty("WindowColor", self.color)
        self.update_ui()
        xbmc.sleep(200)
        if self.totalitems > 0:
            xbmc.executebuiltin("SetFocus(500)")
        else:
            xbmc.executebuiltin("SetFocus(6000)")

    def onAction(self, action):
        focusid = self.getFocusId()
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            if focusid == 500:
                item_id = self.getControl(focusid).getSelectedItem().getProperty("id")
                if self.type == "tv":
                    listitems = [addon.getLocalizedString(32169)]
                else:
                    listitems = [addon.getLocalizedString(32113)]
                if self.logged_in:
                    listitems += [xbmc.getLocalizedString(14076)]
                    if not self.type == "tv":
                        listitems += [addon.getLocalizedString(32107)]
                    if self.mode == "list":
                        listitems += [addon.getLocalizedString(32035)]
                # context_menu = ContextMenu.ContextMenu(u'DialogContextMenu.xml', addon_path, labels=listitems)
                # context_menu.doModal()
                selection = xbmcgui.Dialog().select(addon.getLocalizedString(32151), listitems)
                if selection == 0:
                    rating = get_rating_from_user()
                    if rating:
                        send_rating_for_media_item(self.type, item_id, rating)
                        xbmc.sleep(2000)
                        self.update_content(force_update=True)
                        self.update_ui()
                elif selection == 1:
                    ChangeFavStatus(item_id, self.type, "true")
                elif selection == 2:
                    xbmc.executebuiltin("ActivateWindow(busydialog)")
                    listitems = [addon.getLocalizedString(32139)]
                    account_lists = GetAccountLists()
                    for item in account_lists:
                        listitems.append("%s (%i)" % (item["name"], item["item_count"]))
                    listitems.append(addon.getLocalizedString(32138))
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    index = xbmcgui.Dialog().select(addon.getLocalizedString(32136), listitems)
                    if index == 0:
                        listname = xbmcgui.Dialog().input(addon.getLocalizedString(32137), type=xbmcgui.INPUT_ALPHANUM)
                        if listname:
                            list_id = CreateList(listname)
                            xbmc.sleep(1000)
                            ChangeListStatus(list_id, item_id, True)
                    elif index == len(listitems) - 1:
                        self.RemoveListDialog(account_lists)
                    elif index > 0:
                        ChangeListStatus(account_lists[index - 1]["id"], item_id, True)
                        # xbmc.sleep(2000)
                        # self.update_content(force_update=True)
                        # self.update_ui()
                elif selection == 3:
                    ChangeListStatus(self.list_id, item_id, False)
                    self.update_content(force_update=True)
                    self.update_ui()

    def onClick(self, controlID):
        if controlID in [500]:
            AddToWindowStack(self)
            self.close()
            media_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            media_type = self.getControl(controlID).getSelectedItem().getProperty("media_type")
            if media_type:
                self.type = media_type
            if self.type == "tv":
                dialog = DialogTVShowInfo.DialogTVShowInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=media_id)
            elif self.type == "person":
                dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % addon_name, addon_path, id=media_id)
            else:
                dialog = DialogVideoInfo.DialogVideoInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=media_id)
            dialog.doModal()
        elif controlID == 5001:
            self.get_sort_type()
            self.update_content()
            self.update_ui()
        elif controlID == 5002:
            self.get_genre()
            self.update_content()
            self.update_ui()
        elif controlID == 5003:
            dialog = xbmcgui.Dialog()
            ret = dialog.yesno(heading=addon.getLocalizedString(32151), line1=addon.getLocalizedString(32106), nolabel=addon.getLocalizedString(32150), yeslabel=addon.getLocalizedString(32149))
            result = xbmcgui.Dialog().input(xbmc.getLocalizedString(345), "", type=xbmcgui.INPUT_NUMERIC)
            if result:
                if ret:
                    order = "lte"
                    value = "%s-12-31" % result
                    label = " < " + result
                else:
                    order = "gte"
                    value = "%s-01-01" % result
                    label = " > " + result
                if self.type == "tv":
                    self.add_filter("first_air_date.%s" % order, value, xbmc.getLocalizedString(20416), label)
                else:
                    self.add_filter("primary_release_date.%s" % order, value, xbmc.getLocalizedString(345), label)
                self.mode = "filter"
                self.page = 1
                self.update_content()
                self.update_ui()
        # elif controlID == 5011:
        #     dialog = xbmcgui.Dialog()
        #     ret = True
        #     if not self.type == "tv":
        #         ret = dialog.yesno(heading=addon.getLocalizedString(32151), line1=addon.getLocalizedString(32106), nolabel=addon.getLocalizedString(32150), yeslabel=addon.getLocalizedString(32149))
        #     result = xbmcgui.Dialog().input(xbmc.getLocalizedString(32112), "", type=xbmcgui.INPUT_NUMERIC)
        #     if result:
        #         if ret:
        #             order = "lte"
        #             label = " < " + result
        #         else:
        #             order = "gte"
        #             label = " > " + result
        #         self.add_filter("vote_average.%s" % order, float(result) / 10.0, addon.getLocalizedString(32112), label)
        #         self.mode = "filter"
        #         self.page = 1
        #         self.update_content()
        #         self.update_ui()
        elif controlID == 5012:
            dialog = xbmcgui.Dialog()
            ret = True
            if not self.type == "tv":
                ret = dialog.yesno(heading=addon.getLocalizedString(32151), line1=addon.getLocalizedString(32106), nolabel=addon.getLocalizedString(32150), yeslabel=addon.getLocalizedString(32149))
            result = xbmcgui.Dialog().input(xbmc.getLocalizedString(32111), "", type=xbmcgui.INPUT_NUMERIC)
            if result:
                if ret:
                    order = "lte"
                    label = " < " + result
                else:
                    order = "gte"
                    label = " > " + result
                self.add_filter("vote_count.%s" % order, result, addon.getLocalizedString(32111), label)
                self.mode = "filter"
                self.page = 1
                self.update_content()
                self.update_ui()


        elif controlID == 5004:
            if self.order == "asc":
                self.order = "desc"
            else:
                self.order = "asc"
            self.update_content()
            self.update_ui()
        elif controlID == 5005:
            self.filters = []
            self.page = 1
            self.mode = "filter"
            self.update_content()
            self.update_ui()
        elif controlID == 5006:
            self.get_certification()
            self.update_content()
            self.update_ui()
        elif controlID == 5008:
            self.get_actor()
            self.update_content()
            self.update_ui()
        elif controlID == 5009:
            self.get_keyword()
            self.update_content()
            self.update_ui()
        elif controlID == 5010:
            self.get_company()
            self.update_content()
            self.update_ui()
        elif controlID == 5007:
            self.filters = []
            self.page = 1
            self.mode = "filter"
            if self.type == "tv":
                self.type = "movie"
                self.filters = []
            else:
                self.type = "tv"
                self.filters = []
            if self.mode == "list":
                self.mode = "filter"
            self.update_content()
            self.update_ui()
        elif controlID == 6000:
            result = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), "", type=xbmcgui.INPUT_ALPHANUM)
            if result and result > -1:
                self.search_string = result
                self.mode = "search"
                self.filters = []
                self.page = 1
                self.update_content()
                self.update_ui()
        elif controlID == 7000:
            if self.type == "tv":
                listitems = [addon.getLocalizedString(32145)]  # rated tv
                if self.logged_in:
                    listitems.append(addon.getLocalizedString(32144))   # starred tv
            else:
                listitems = [addon.getLocalizedString(32135)]  # rated movies
                if self.logged_in:
                    listitems.append(addon.getLocalizedString(32134))   # starred movies
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            if self.logged_in:
                account_lists = GetAccountLists()
                for item in account_lists:
                    listitems.append("%s (%i)" % (item["name"], item["item_count"]))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(addon.getLocalizedString(32136), listitems)
            if index == -1:
                pass
            elif index == 0:
                self.mode = "rating"
                self.sort = "created_at"
                self.sort_label = addon.getLocalizedString(32157)
                self.filters = []
                self.page = 1
                self.update_content()
                self.update_ui()
            elif index == 1:
                self.mode = "favorites"
                self.sort = "created_at"
                self.sort_label = addon.getLocalizedString(32157)
                self.filters = []
                self.page = 1
                self.update_content()
                self.update_ui()
            else:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
               # offset = len(listitems) - len(account_lists)
               # Notify(str(offset))
                list_id = account_lists[index - 2]["id"]
                list_title = account_lists[index - 2]["name"]
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                self.close()
                dialog = DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, color=self.color, filters=[], mode="list", list_id=list_id, filter_label=list_title)
                dialog.doModal()

    def onFocus(self, controlID):
        if controlID == 600:
            if self.page < self.totalpages:
                self.page += 1
            else:
                self.page = 1
                return
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.update_content()
            self.update_ui()
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        if controlID == 700:
            if self.page > 1:
                self.page -= 1
            else:
                return
            # else:
            #     self.page = self.totalpages
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.update_content()
            self.update_ui()
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def get_sort_type(self):
        listitems = []
        sort_strings = []
        if self.mode in ["favorites", "rating", "list"]:
            sort_key = self.mode
        else:
            sort_key = self.type
        for (key, value) in sorts[sort_key].iteritems():
            listitems.append(key)
            sort_strings.append(value)
        index = xbmcgui.Dialog().select(addon.getLocalizedString(32104), listitems)
        if index > -1:
            if sort_strings[index] == "vote_average":
                self.add_filter("vote_count.gte", "10", "Vote Count (greater)", "10")
            self.sort = sort_strings[index]
            self.sort_label = listitems[index]

    def add_filter(self, key, value, typelabel, label):
        index = -1
        if ".gte" in key or ".lte" in key:
            force_overwrite = True
        else:
            force_overwrite = False
        new_filter = {"id": value,
                      "type": key,
                      "typelabel": typelabel,
                      "label": label}
        for item in self.filters:
            if item == new_filter:
                return False
        for i, item in enumerate(self.filters):
            if item["type"] == key:
                index = i
                break
        if value:
            if index > -1:
                if not force_overwrite:
                    dialog = xbmcgui.Dialog()
                    ret = dialog.yesno(heading=xbmc.getLocalizedString(587), line1=addon.getLocalizedString(32106), nolabel="OR", yeslabel="AND")
                    if ret:
                        self.filters[index]["id"] = self.filters[index]["id"] + "," + urllib.quote_plus(str(value))
                        self.filters[index]["label"] = self.filters[index]["label"] + "," + str(label)
                    else:
                        self.filters[index]["id"] = self.filters[index]["id"] + "|" + urllib.quote_plus(str(value))
                        self.filters[index]["label"] = self.filters[index]["label"] + "|" + str(label)
                else:
                    self.filters[index]["id"] = urllib.quote_plus(str(value))
                    self.filters[index]["label"] = str(label)
            else:
                self.filters.append(new_filter)

    def set_filter_url(self):
        filter_list = []
        # prettyprint(self.filters)
        for item in self.filters:
            filter_list.append("%s=%s" % (item["type"], item["id"]))
        self.filter_url = "&".join(filter_list)
        if self.filter_url:
            self.filter_url += "&"

    def set_filter_label(self):
        filter_list = []
        # prettyprint(self.filters)
        for item in self.filters:
            filter_list.append("[COLOR FFAAAAAA]%s:[/COLOR] %s" % (item["typelabel"], item["label"].decode("utf-8").replace("|", " | ").replace(",", " + ")))
        self.filter_label = "  -  ".join(filter_list)

    def get_genre(self):
        response = GetMovieDBData("genre/%s/list?language=%s&" % (self.type, addon.getSetting("LanguageID")), 10)
        id_list = []
        label_list = []
        for item in response["genres"]:
            id_list.append(item["id"])
            label_list.append(item["name"])
        index = xbmcgui.Dialog().select(addon.getLocalizedString(32151), label_list)
        if index > -1:
            # return "with_genres=" + str(id_list[index])
            self.add_filter("with_genres", str(id_list[index]), xbmc.getLocalizedString(135), str(label_list[index]))
            self.mode = "filter"
            self.page = 1

    def get_actor(self):
        result = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), "", type=xbmcgui.INPUT_ALPHANUM)
        if result and result > -1:
            response = GetPersonID(result)
            # prettyprint(response)
            if result > -1:
                # return "with_genres=" + str(id_list[index])
                self.add_filter("with_people", str(response["id"]), addon.getLocalizedString(32156), response["name"])
                self.mode = "filter"
                self.page = 1

    def get_company(self):
        result = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), "", type=xbmcgui.INPUT_ALPHANUM)
        if result and result > -1:
            response = SearchforCompany(result)
            # prettyprint(response)
            if result > -1:
                if len(response) > 1:
                    names = []
                    for item in response:
                        names.append(item["name"])
                    selection = xbmcgui.Dialog().select(addon.getLocalizedString(32151), names)
                    if selection > -1:
                        response = response[selection]
                elif response:
                    response = response[0]
                else:
                    Notify("no company found")
                self.add_filter("with_companies", str(response["id"]), xbmc.getLocalizedString(20388), response["name"])
                self.mode = "filter"
                self.page = 1

    def get_keyword(self):
        result = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), "", type=xbmcgui.INPUT_ALPHANUM)
        if result and result > -1:
            response = GetKeywordID(result)
            if response:
                keyword_id = response["id"]
                name = response["name"]
                # prettyprint(response)
                if result > -1:
                    self.add_filter("with_keywords", str(keyword_id), addon.getLocalizedString(32114), name)
                    self.mode = "filter"
                    self.page = 1

    def get_certification(self):
        response = get_certification_list(self.type)
        country_list = []
        for (key, value) in response.iteritems():
            country_list.append(key)
        index = xbmcgui.Dialog().select(xbmc.getLocalizedString(21879), country_list)
        if index > -1:
            cert_list = []
            # for (key, value) in response[country_list[index]].iteritems():
            #     cert_list.append(key)
            country = country_list[index]
            for item in response[country]:
                label = "%s  -  %s" % (item["certification"], item["meaning"])
                cert_list.append(label)
            index = xbmcgui.Dialog().select(addon.getLocalizedString(32151), cert_list)
            if index > -1:
            # return "with_genres=" + str(id_list[index])
                cert = cert_list[index].split("  -  ")[0]
                self.add_filter("certification_country", country, addon.getLocalizedString(32153), country)
                self.add_filter("certification", cert, addon.getLocalizedString(32127), cert)
                self.page = 1
                self.mode = "filter"

    def update_content(self, add=False, force_update=False):
        if add:
            self.old_items = self.listitems
        else:
            self.old_items = []
        self.listitems, self.totalpages, self.totalitems = self.fetch_data(force=force_update)
        self.listitems = self.old_items + create_listitems(self.listitems)

    def update_ui(self):
        self.getControl(500).reset()
        self.getControl(500).addItems(self.listitems)
        self.window.setProperty("TotalPages", str(self.totalpages))
        self.window.setProperty("TotalItems", str(self.totalitems))
        self.window.setProperty("CurrentPage", str(self.page))
        self.window.setProperty("Type", translations[self.type])
        self.window.setProperty("Filter_Label", self.filter_label)
        self.window.setProperty("Sort_Label", self.sort_label)
        if self.page == self.totalpages:
            self.window.clearProperty("ArrowDown")
        else:
            self.window.setProperty("ArrowDown", "True")
        if self.page > 1:
            self.window.setProperty("ArrowUp", "True")
        else:
            self.window.clearProperty("ArrowUp")
        if self.order == "asc":
            self.window.setProperty("Order_Label", xbmc.getLocalizedString(584))
        else:
            self.window.setProperty("Order_Label", xbmc.getLocalizedString(585))
        if self.type == "tv":
            self.window.getControl(5006).setVisible(False)
            self.window.getControl(5008).setVisible(False)
            self.window.getControl(5009).setVisible(False)
            self.window.getControl(5010).setVisible(False)
        else:
            self.window.getControl(5006).setVisible(True)
            self.window.getControl(5008).setVisible(True)
            self.window.getControl(5009).setVisible(True)
            self.window.getControl(5010).setVisible(True)


    def fetch_data(self, force=False):
        sortby = self.sort + "." + self.order
        if self.type == "tv":
            temp = "tv"
            rated = addon.getLocalizedString(32145)
            starred = addon.getLocalizedString(32144)
        else:
            temp = "movies"
            rated = addon.getLocalizedString(32135)
            starred = addon.getLocalizedString(32134)
        if self.mode == "search":
            url = "search/multi?query=%s&page=%i&include_adult=%s&" % (urllib.quote_plus(self.search_string), self.page, include_adult)
            self.filter_label = addon.getLocalizedString(32146) % self.search_string
        elif self.mode == "list":
            url = "list/%s?language=%s&" % (str(self.list_id), addon.getSetting("LanguageID"))
            # self.filter_label = addon.getLocalizedString(32036)
        elif self.mode == "favorites":
            url = "account/%s/favorite/%s?language=%s&page=%i&session_id=%s&sort_by=%s&" % (get_account_info(), temp, addon.getSetting("LanguageID"), self.page, get_session_id(), sortby)
            self.filter_label = starred
        elif self.mode == "rating":
            if self.logged_in:
                session_id_string = "session_id=" + get_session_id()
                url = "account/%s/rated/%s?language=%s&page=%i&%s&sort_by=%s&" % (get_account_info(), temp, addon.getSetting("LanguageID"), self.page, session_id_string, sortby)
            else:
                url = "guest_session/%s/rated_movies?language=%s&" % (get_guest_session_id(), addon.getSetting("LanguageID"))
            self.filter_label = rated
        else:
            self.set_filter_url()
            self.set_filter_label()
            url = "discover/%s?sort_by=%s&%slanguage=%s&page=%i&include_adult=%s&" % (self.type, sortby, self.filter_url, addon.getSetting("LanguageID"), self.page, include_adult)
        if force:
            response = GetMovieDBData(url, 0)
        else:
            response = GetMovieDBData(url, 2)
        if self.mode == "list":
            return HandleTMDBMovieResult(response["items"]), 1, len(response["items"])
        if not "results" in response:
            self.close()
            return [], 0, 0
        if not response["results"]:
            Notify(xbmc.getLocalizedString(284))
        if self.mode == "search":
            return HandleTMDBMultiSearchResult(response["results"]), response["total_pages"], response["total_results"]
        elif self.type == "movie":
            return HandleTMDBMovieResult(response["results"], False, None), response["total_pages"], response["total_results"]
        else:
            return HandleTMDBTVShowResult(response["results"], False, None), response["total_pages"], response["total_results"]



