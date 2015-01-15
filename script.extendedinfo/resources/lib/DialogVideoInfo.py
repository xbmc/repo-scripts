import xbmc
import xbmcaddon
import xbmcgui
from Utils import *
from TheMovieDB import *
from YouTube import *
from omdb import *
import DialogActorInfo
import DialogVideoList
from ImageTools import *
import threading
homewindow = xbmcgui.Window(10000)
selectdialog = xbmcgui.Window(12000)
busydialog = xbmcgui.Window(10138)

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')
addon_version = addon.getAddonInfo('version')
addon_strings = addon.getLocalizedString
addon_path = addon.getAddonInfo('path').decode("utf-8")


class DialogVideoInfo(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        if not addon.getSetting("first_start_infodialog"):
            addon.setSetting("first_start_infodialog", "True")
            xbmcgui.Dialog().ok(addon_name, addon.getLocalizedString(32140), addon.getLocalizedString(32141))
        self.movieplayer = VideoPlayer(popstack=True)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        xbmcgui.WindowXMLDialog.__init__(self)
        self.monitor = SettingsMonitor()
        tmdb_id = kwargs.get('id')
        self.dbid = kwargs.get('dbid')
        imdb_id = kwargs.get('imdbid')
        self.name = kwargs.get('name')
        self.logged_in = checkLogin()
        if tmdb_id:
            self.MovieId = tmdb_id
        elif self.dbid and (int(self.dbid) > 0):
            self.MovieId = GetImdbIDFromDatabase("movie", self.dbid)
            log("IMDBId from local DB:" + str(self.MovieId))
        elif imdb_id:
            self.MovieId = GetMovieDBID(imdb_id)
        elif self.name:
            self.MovieId = search_media(kwargs.get('name'))
        else:
            self.MovieId = ""
        if self.MovieId:
            self.movie = GetExtendedMovieInfo(self.MovieId, self.dbid)
            if not "general" in self.movie:
                self.close()
            log("Blur image %s with radius %i" % (self.movie["general"]["Thumb"], 25))
            youtube_thread = Get_Youtube_Vids_Thread(self.movie["general"]["Label"] + " " + self.movie["general"]["Year"] + ", movie", "", "relevance", 15)
            sets_thread = Get_Set_Items_Thread(self.movie["general"]["SetId"])
            self.omdb_thread = Get_ListItems_Thread(GetOmdbMovieInfo, self.movie["general"]["imdb_id"])
            lists_thread = Get_ListItems_Thread(self.SortLists, self.movie["lists"])
            self.omdb_thread.start()
            sets_thread.start()
            youtube_thread.start()
            lists_thread.start()
            if not "DBID" in self.movie["general"]:
                poster_thread = Get_ListItems_Thread(Get_File, self.movie["general"]["Poster"])
                poster_thread.start()
            vid_id_list = []
            for item in self.movie["videos"]:
                vid_id_list.append(item["key"])
            self.crew_list = []
            crew_id_list = []
            for item in self.movie["crew"]:
                if item["id"] not in crew_id_list:
                    crew_id_list.append(item["id"])
                    self.crew_list.append(item)
                else:
                    index = crew_id_list.index(item["id"])
                    self.crew_list[index]["job"] = self.crew_list[index]["job"] + " / " + item["job"]
            if not "DBID" in self.movie["general"]:
                poster_thread.join()
                self.movie["general"]['Poster'] = poster_thread.listitems
            filter_thread = Filter_Image_Thread(self.movie["general"]["Thumb"], 25)
            filter_thread.start()
            lists_thread.join()
            self.movie["lists"] = lists_thread.listitems
            sets_thread.join()
            cert_list = get_certification_list("movie")
            for item in self.movie["releases"]:
                if item["iso_3166_1"] in cert_list:
                    language = item["iso_3166_1"]
                    certification = item["certification"]
                    language_certs = cert_list[item["iso_3166_1"]]
                    hit = dictfind(language_certs, "certification", certification)
                    if hit:
                        item["meaning"] = hit["meaning"]
            self.set_listitems = sets_thread.listitems
            self.setinfo = sets_thread.setinfo
            id_list = sets_thread.id_list
            self.movie["similar"] = [item for item in self.movie["similar"] if item["ID"] not in id_list]
            youtube_thread.join()
            self.youtube_vids = youtube_thread.listitems
            self.youtube_vids = [item for item in self.youtube_vids if item["youtube_id"] not in vid_id_list]
            filter_thread.join()
            self.movie["general"]['ImageFilter'], self.movie["general"]['ImageColor'] = filter_thread.image, filter_thread.imagecolor
        else:
            Notify(addon.getLocalizedString(32143))
            self.close()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        homewindow.setProperty("movie.ImageColor", self.movie["general"]["ImageColor"])
        self.windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.windowid)
        self.window.setProperty("tmdb_logged_in", self.logged_in)
        self.window.setProperty("type", "movie")
        passDictToSkin(self.movie["general"], "movie.", False, False, self.windowid)
        xbmc.sleep(200)
        passDictToSkin(self.setinfo, "movie.set.", False, False, self.windowid)
        self.getControl(1000).addItems(CreateListItems(self.movie["actors"], 0))
        self.getControl(150).addItems(CreateListItems(self.movie["similar"], 0))
        self.getControl(250).addItems(CreateListItems(self.set_listitems, 0))
        self.getControl(450).addItems(CreateListItems(self.movie["lists"], 0))
        self.getControl(550).addItems(CreateListItems(self.movie["studios"], 0))
        self.getControl(650).addItems(CreateListItems(self.movie["releases"], 0))
        self.getControl(750).addItems(CreateListItems(self.crew_list, 0))
        self.getControl(850).addItems(CreateListItems(self.movie["genres"], 0))
        self.getControl(950).addItems(CreateListItems(self.movie["keywords"], 0))
        self.getControl(1050).addItems(CreateListItems(self.movie["reviews"], 0))
        self.getControl(1150).addItems(CreateListItems(self.movie["videos"], 0))
        self.getControl(1250).addItems(CreateListItems(self.movie["images"], 0))
        self.getControl(1350).addItems(CreateListItems(self.movie["backdrops"], 0))
        self.getControl(350).addItems(CreateListItems(self.youtube_vids, 0))
        self.UpdateStates(False)
        self.join_omdb = Join_Omdb_Thread(self.omdb_thread, self.windowid)
        self.join_omdb.start()

    def onAction(self, action):
        action_id = action.getId()
        focusid = self.getFocusId()
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()
        # elif action == xbmcgui.ACTION_CONTEXT_MENU:
        #     if focusid == 450:
        #         list_id = self.getControl(focusid).getSelectedItem().getProperty("id")
        #         listitems = ["Add To Account Lists"]
        #         context_menu = ContextMenu.ContextMenu(u'script-globalsearch-contextmenu.xml', addon_path, labels=listitems)
        #         context_menu.doModal()
        #         if context_menu.selection == 0:
        #             Notify(list_id)
        #         selection = xbmcgui.Dialog().select(addon.getLocalizedString(32151), listitems)


    def onClick(self, controlID):
        # selectdialog.setProperty("WindowColor", xbmc.getInfoLabel("Window(home).Property(movie.ImageColor)"))
        # busydialog.setProperty("WindowColor", xbmc.getInfoLabel("Window(home).Property(movie.ImageColor)"))
        if controlID in [1000, 750]:
            actorid = self.getControl(controlID).getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % addon_name, addon_path, id=actorid)
            dialog.doModal()
        elif controlID in [150, 250]:
            movieid = self.getControl(controlID).getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogVideoInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=movieid)
            dialog.doModal()
        elif controlID in [1250, 1350]:
            image = self.getControl(controlID).getSelectedItem().getProperty("original")
            dialog = SlideShow(u'script-%s-SlideShow.xml' % addon_name, addon_path, image=image)
            dialog.doModal()
        elif controlID in [350, 1150]:
            AddToWindowStack(self)
            self.close()
            listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
            listitem.setInfo('video', {'Title': xbmc.getLocalizedString(20410), 'Genre': 'Youtube Video'})
            youtube_id = self.getControl(controlID).getSelectedItem().getProperty("youtube_id")
            if youtube_id:
                self.movieplayer.playYoutubeVideo(youtube_id, self.getControl(controlID).getSelectedItem(), True)
                self.movieplayer.WaitForVideoEnd()
                PopWindowStack()
            else:
                Notify(addon.getLocalizedString(32052))
        # elif controlID in [8]:
        #     AddToWindowStack(self)
        #     self.close()
        #     listitem = CreateListItems([self.movie["general"]])[0]
        #     self.movieplayer.play(item=self.movie["general"]['FilenameAndPath'], listitem=listitem)
        #     self.movieplayer.WaitForVideoEnd()
        elif controlID == 550:
            company_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            company_name = self.getControl(controlID).getSelectedItem().getLabel()
            filters = [{"id": company_id,
                        "type": "with_companies",
                        "typelabel": xbmc.getLocalizedString(20388),
                        "label": company_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 1050:
            author = self.getControl(controlID).getSelectedItem().getProperty("author")
            text = "[B]" + author + "[/B][CR]" + cleanText(self.getControl(controlID).getSelectedItem().getProperty("content"))
            w = TextViewer_Dialog('DialogTextViewer.xml', addon_path, header=xbmc.getLocalizedString(185), text=text, color=self.movie["general"]['ImageColor'])
            w.doModal()
        elif controlID == 950:
            keyword_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            keyword_name = self.getControl(controlID).getSelectedItem().getLabel()
            filters = [{"id": keyword_id,
                        "type": "with_keywords",
                        "typelabel": addon.getLocalizedString(32114),
                        "label": keyword_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 850:
            genre_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            genre_name = self.getControl(controlID).getSelectedItem().getLabel()
            filters = [{"id": genre_id,
                        "type": "with_genres",
                        "typelabel": xbmc.getLocalizedString(135),
                        "label": genre_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 650:
            country = self.getControl(controlID).getSelectedItem().getProperty("iso_3166_1")
            certification = self.getControl(controlID).getSelectedItem().getProperty("certification")
            year = self.getControl(controlID).getSelectedItem().getProperty("year")
            filters = [{"id": country,
                        "type": "certification_country",
                        "typelabel": addon.getLocalizedString(32153),
                        "label": country},
                       {"id": certification,
                        "type": "certification",
                        "typelabel": addon.getLocalizedString(32127),
                        "label": certification},
                       {"id": year,
                        "type": "year",
                        "typelabel": xbmc.getLocalizedString(345),
                        "label": year}]
            self.OpenVideoList(filters=filters)
        elif controlID == 450:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            list_items = GetMoviesFromList(self.getControl(controlID).getSelectedItem().getProperty("id"))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(list_items, [])
        elif controlID == 6001:
            ratings = []
            for i in range(0, 21):
                ratings.append(str(float(i * 0.5)))
            rating = xbmcgui.Dialog().select(addon.getLocalizedString(32129), ratings)
            if rating > -1:
                rating = float(rating) * 0.5
                RateMedia("movie", self.MovieId, rating)
                self.UpdateStates()
        elif controlID == 6002:
            listitems = [addon.getLocalizedString(32134), addon.getLocalizedString(32135)]
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            account_lists = GetAccountLists()
            for item in account_lists:
                listitems.append("%s (%i)" % (item["name"], item["item_count"]))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(addon.getLocalizedString(32136), listitems)
            if index == -1:
                pass
            elif index == 0:
                AddToWindowStack(self)
                self.close()
                dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, mode="favorites", color=self.movie["general"]['ImageColor'])
                dialog.doModal()
            elif index == 1:
                AddToWindowStack(self)
                self.close()
                dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, mode="rating", color=self.movie["general"]['ImageColor'])
                dialog.doModal()
            else:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                list_items = GetMoviesFromList(account_lists[index - 2]["id"], 0)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                self.OpenVideoList(list_items, [])
        elif controlID == 8:
            self.close()
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %i }, "options":{ "resume": %s } }, "id": 1 }' % (self.movie["general"]['DBID'], "false"))
        elif controlID == 9:
            self.close()
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %i }, "options":{ "resume": %s } }, "id": 1 }' % (self.movie["general"]['DBID'], "true"))
        elif controlID == 445:
            self.ShowManageDialog()
        elif controlID == 132:
            w = TextViewer_Dialog('DialogTextViewer.xml', addon_path, header="Plot", text=self.movie["general"]["Plot"], color=self.movie["general"]['ImageColor'])
            w.doModal()
        elif controlID == 6003:
            if self.movie["account_states"]["favorite"]:
                ChangeFavStatus(self.movie["general"]["ID"], "movie", "false")
            else:
                ChangeFavStatus(self.movie["general"]["ID"], "movie", "true")
            self.UpdateStates()
        elif controlID == 6006:
            self.ShowRatedMovies()
        elif controlID == 6005:
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
                    ChangeListStatus(list_id, self.MovieId, True)
            elif index == len(listitems) - 1:
                self.RemoveListDialog(account_lists)
            elif index > 0:
                ChangeListStatus(account_lists[index - 1]["id"], self.MovieId, True)
                self.UpdateStates()

    def onFocus(self, controlID):
        pass

    def SortLists(self, lists):
        if not self.logged_in:
            return lists
        account_list = GetAccountLists(10)  # use caching here, forceupdate everywhere else
        id_list = []
        own_lists = []
        misc_lists = []
        for item in account_list:
            id_list.append(item["id"])
        for item in lists:
            if item["ID"] in id_list:
                item["account"] = "True"
                own_lists.append(item)
            else:
                misc_lists.append(item)
        # own_lists = [item for item in lists if item["ID"] in id_list]
        # misc_lists = [item for item in lists if item["ID"] not in id_list]
        return own_lists + misc_lists

    def UpdateStates(self, forceupdate=True):
        if forceupdate:
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            self.update = GetExtendedMovieInfo(self.MovieId, self.dbid, 0)
            self.movie["account_states"] = self.update["account_states"]
        if self.movie["account_states"]:
            if self.movie["account_states"]["favorite"]:
                self.window.setProperty("FavButton_Label", addon.getLocalizedString(32155))
                self.window.setProperty("movie.favorite", "True")
            else:
                self.window.setProperty("FavButton_Label", addon.getLocalizedString(32154))
                self.window.setProperty("movie.favorite", "")
            if self.movie["account_states"]["rated"]:
                self.window.setProperty("movie.rated", str(self.movie["account_states"]["rated"]["value"]))
            else:
                self.window.setProperty("movie.rated", "")
            self.window.setProperty("movie.watchlist", str(self.movie["account_states"]["watchlist"]))
            # Notify(str(self.movie["account_states"]["rated"]["value"]))

    def RemoveListDialog(self, account_lists):
        listitems = []
        for item in account_lists:
            listitems.append("%s (%i)" % (item["name"], item["item_count"]))
        prettyprint(account_lists)
        index = xbmcgui.Dialog().select(addon.getLocalizedString(32138), listitems)
        if index >= 0:
            # ChangeListStatus(account_lists[index]["id"], self.MovieId, False)
            RemoveList(account_lists[index]["id"])
            self.UpdateStates()

    def ShowRatedMovies(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        list_items = GetRatedMedia("movies")
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=list_items, color=self.movie["general"]['ImageColor'])
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        dialog.doModal()

    def OpenVideoList(self, listitems=None, filters=[]):
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=listitems, color=self.movie["general"]['ImageColor'], filters=filters)
        dialog.doModal()

    def ShowManageDialog(self):
        manage_list = []
        listitems = []
        movie_id = str(self.movie["general"].get("DBID", ""))
        filename = self.movie["general"].get("FilenameAndPath", False)
        imdb_id = str(self.movie["general"].get("imdb_id", ""))
        if movie_id:
            temp_list = [[xbmc.getLocalizedString(413), "RunScript(script.artwork.downloader,mode=gui,mediatype=movie,dbid=" + movie_id + ")"],
                         [xbmc.getLocalizedString(14061), "RunScript(script.artwork.downloader, mediatype=movie, dbid=" + movie_id + ")"],
                         [addon.getLocalizedString(32101), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ",extrathumbs)"],
                         [addon.getLocalizedString(32100), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ")"]]
            manage_list += temp_list
        else:
            temp_list = [[addon.getLocalizedString(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=" + imdb_id + ")||Notification(script.extendedinfo,Added Movie To CouchPota))"]]
            manage_list += temp_list
        # if xbmc.getCondVisibility("system.hasaddon(script.tvtunes)") and movie_id:
        #     manage_list.append([addon.getLocalizedString(32102), "RunScript(script.tvtunes,mode=solo&amp;tvpath=$ESCINFO[Window.Property(movie.FilenameAndPath)]&amp;tvname=$INFO[Window.Property(movie.TVShowTitle)])"])
        if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and movie_id:
            manage_list.append([addon.getLocalizedString(32103), "RunScript(script.libraryeditor,DBID=" + movie_id + ")"])
        manage_list.append([xbmc.getLocalizedString(1049), "Addon.OpenSettings(script.extendedinfo)"])
        for item in manage_list:
            listitems.append(item[0])
        selection = xbmcgui.Dialog().select(addon.getLocalizedString(32133), listitems)
        if selection > -1:
            builtin_list = manage_list[selection][1].split("||")
            for item in builtin_list:
                xbmc.executebuiltin(item)

class Join_Omdb_Thread(threading.Thread):

    def __init__(self, omdb_thread, windowid):
        threading.Thread.__init__(self)
        self.omdb_thread = omdb_thread
        self.windowid = windowid

    def run(self):
        self.omdb_thread.join()
        if xbmcgui.getCurrentWindowDialogId() == self.windowid:
            passDictToSkin(self.omdb_thread.listitems, "movie.omdb.", False, False, self.windowid)


class Get_Set_Items_Thread(threading.Thread):

    def __init__(self, set_id=""):
        threading.Thread.__init__(self)
        self.set_id = set_id

    def run(self):
        self.id_list = []
        if self.set_id:
            self.listitems, self.setinfo = GetSetMovies(self.set_id)
            for item in self.listitems:
                self.id_list.append(item["ID"])
        else:
            self.listitems = []
            self.setinfo = {}


class SettingsMonitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        xbmc.sleep(300)
