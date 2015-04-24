import xbmc
import xbmcgui
from Utils import *
from TheMovieDB import *
from YouTube import *
from omdb import *
import DialogActorInfo
import DialogVideoList
from ImageTools import *
import threading


class DialogVideoInfo(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        if not ADDON.getSetting("first_start_infodialog"):
            ADDON.setSetting("first_start_infodialog", "True")
            xbmcgui.Dialog().ok(ADDON_NAME, ADDON.getLocalizedString(32140), ADDON.getLocalizedString(32141))
        self.movieplayer = VideoPlayer(popstack=True)
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        xbmcgui.WindowXMLDialog.__init__(self)
        self.monitor = SettingsMonitor()
        tmdb_id = kwargs.get('id')
        self.dbid = kwargs.get('dbid')
        imdb_id = kwargs.get('imdbid')
        self.name = kwargs.get('name')
        self.logged_in = checkLogin()
        self.movie = False
        if tmdb_id:
            self.tmdb_id = tmdb_id
        else:
            self.tmdb_id = get_movie_tmdb_id(imdb_id=imdb_id, dbid=self.dbid, name=self.name)
        if self.tmdb_id:
            self.movie = GetExtendedMovieInfo(self.tmdb_id, self.dbid)
            if "general" not in self.movie:
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                return None
            log("Blur image %s with radius %i" % (self.movie["general"]["Thumb"], 25))
            youtube_thread = Get_Youtube_Vids_Thread(self.movie["general"]["Label"] + " " + self.movie["general"]["Year"] + ", movie", "", "relevance", 15)
            sets_thread = Get_Set_Items_Thread(self.movie["general"]["SetId"])
            self.omdb_thread = Threaded_Function(GetOmdbMovieInfo, self.movie["general"]["imdb_id"])
            lists_thread = Threaded_Function(self.SortLists, self.movie["lists"])
            self.omdb_thread.start()
            sets_thread.start()
            youtube_thread.start()
            lists_thread.start()
            if "DBID" not in self.movie["general"]:
                poster_thread = Threaded_Function(Get_File, self.movie["general"]["Poster"])
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
            if "DBID" not in self.movie["general"]:
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
                    language_certs = cert_list[language]
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
            self.listitems = []
            self.listitems.append((1000, create_listitems(self.movie["actors"], 0)))
            self.listitems.append((150, create_listitems(self.movie["similar"], 0)))
            self.listitems.append((250, create_listitems(self.set_listitems, 0)))
            self.listitems.append((450, create_listitems(self.movie["lists"], 0)))
            self.listitems.append((550, create_listitems(self.movie["studios"], 0)))
            self.listitems.append((650, create_listitems(self.movie["releases"], 0)))
            self.listitems.append((750, create_listitems(self.crew_list)))
            self.listitems.append((850, create_listitems(self.movie["genres"], 0)))
            self.listitems.append((950, create_listitems(self.movie["keywords"], 0)))
            self.listitems.append((1050, create_listitems(self.movie["reviews"], 0)))
            self.listitems.append((1150, create_listitems(self.movie["videos"], 0)))
            self.listitems.append((1250, create_listitems(self.movie["images"], 0)))
            self.listitems.append((1350, create_listitems(self.movie["backdrops"], 0)))
            self.listitems.append((350, create_listitems(self.youtube_vids, 0)))
        else:
            Notify(ADDON.getLocalizedString(32143))
            self.close()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        if not self.movie:
            self.close()
            return
        HOME.setProperty("movie.ImageColor", self.movie["general"]["ImageColor"])
        self.windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.windowid)
        self.window.setProperty("tmdb_logged_in", self.logged_in)
        self.window.setProperty("type", "movie")
        passDictToSkin(self.movie["general"], "movie.", False, False, self.windowid)
        xbmc.sleep(200)
        passDictToSkin(self.setinfo, "movie.set.", False, False, self.windowid)
        for container_id, listitems in self.listitems:
            try:
                self.getControl(container_id).addItems(listitems)
            except:
                log("Notice: No container with id %i available" % container_id)
        self.UpdateStates(False)
        self.join_omdb = Join_Omdb_Thread(self.omdb_thread, self.windowid)
        self.join_omdb.start()

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()
        # elif action == xbmcgui.ACTION_CONTEXT_MENU:
        #     if focusid == 450:
        #         list_id = self.getControl(focusid).getSelectedItem().getProperty("id")
        #         listitems = ["Add To Account Lists"]
        #         context_menu = ContextMenu.ContextMenu(u'script-globalsearch-contextmenu.xml', ADDON_PATH, labels=listitems)
        #         context_menu.doModal()
        #         if context_menu.selection == 0:
        #             Notify(list_id)
        #         selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(32151), listitems)

    def onClick(self, controlID):
        control = self.getControl(controlID)
        if controlID in [1000, 750]:
            actorid = control.getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % ADDON_NAME, ADDON_PATH, id=actorid)
            dialog.doModal()
        elif controlID in [150, 250]:
            movieid = control.getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogVideoInfo(u'script-%s-DialogVideoInfo.xml' % ADDON_NAME, ADDON_PATH, id=movieid)
            dialog.doModal()
        elif controlID in [1250, 1350]:
            image = control.getSelectedItem().getProperty("original")
            dialog = SlideShow(u'script-%s-SlideShow.xml' % ADDON_NAME, ADDON_PATH, image=image)
            dialog.doModal()
        elif controlID in [350, 1150]:
            AddToWindowStack(self)
            self.close()
            listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
            listitem.setInfo('video', {'Title': xbmc.getLocalizedString(20410), 'Genre': 'Youtube Video'})
            youtube_id = control.getSelectedItem().getProperty("youtube_id")
            if youtube_id:
                self.movieplayer.playYoutubeVideo(youtube_id, control.getSelectedItem(), True)
                self.movieplayer.wait_for_video_end()
                PopWindowStack()
            else:
                Notify(ADDON.getLocalizedString(32052))
        # elif controlID in [8]:
        #     AddToWindowStack(self)
        #     self.close()
        #     listitem = create_listitems([self.movie["general"]])[0]
        #     self.movieplayer.play(item=self.movie["general"]['FilenameAndPath'], listitem=listitem)
        #     self.movieplayer.wait_for_video_end()
        elif controlID == 550:
            company_id = control.getSelectedItem().getProperty("id")
            company_name = control.getSelectedItem().getLabel()
            filters = [{"id": company_id,
                        "type": "with_companies",
                        "typelabel": xbmc.getLocalizedString(20388),
                        "label": company_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 1050:
            author = control.getSelectedItem().getProperty("author")
            text = "[B]" + author + "[/B][CR]" + cleanText(control.getSelectedItem().getProperty("content"))
            w = TextViewer_Dialog('DialogTextViewer.xml', ADDON_PATH, header=xbmc.getLocalizedString(185), text=text, color=self.movie["general"]['ImageColor'])
            w.doModal()
        elif controlID == 950:
            keyword_id = control.getSelectedItem().getProperty("id")
            keyword_name = control.getSelectedItem().getLabel()
            filters = [{"id": keyword_id,
                        "type": "with_keywords",
                        "typelabel": ADDON.getLocalizedString(32114),
                        "label": keyword_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 850:
            genre_id = control.getSelectedItem().getProperty("id")
            genre_name = control.getSelectedItem().getLabel()
            filters = [{"id": genre_id,
                        "type": "with_genres",
                        "typelabel": xbmc.getLocalizedString(135),
                        "label": genre_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 650:
            country = control.getSelectedItem().getProperty("iso_3166_1")
            certification = control.getSelectedItem().getProperty("certification")
            year = control.getSelectedItem().getProperty("year")
            filters = [{"id": country,
                        "type": "certification_country",
                        "typelabel": ADDON.getLocalizedString(32153),
                        "label": country},
                       {"id": certification,
                        "type": "certification",
                        "typelabel": ADDON.getLocalizedString(32127),
                        "label": certification},
                       {"id": year,
                        "type": "year",
                        "typelabel": xbmc.getLocalizedString(345),
                        "label": year}]
            self.OpenVideoList(filters=filters)
        elif controlID == 450:
            list_id = control.getSelectedItem().getProperty("id")
            list_title = control.getSelectedItem().getLabel()
            self.OpenVideoList(mode="list", list_id=list_id, filter_label=list_title)
        elif controlID == 6001:
            rating = get_rating_from_user()
            if rating:
                send_rating_for_media_item("movie", self.tmdb_id, rating)
                self.UpdateStates()
        elif controlID == 6002:
            listitems = [ADDON.getLocalizedString(32134), ADDON.getLocalizedString(32135)]
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            account_lists = GetAccountLists()
            for item in account_lists:
                listitems.append("%s (%i)" % (item["name"], item["item_count"]))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32136), listitems)
            if index == -1:
                pass
            elif index == 0:
                AddToWindowStack(self)
                self.close()
                dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, mode="favorites", color=self.movie["general"]['ImageColor'])
                dialog.doModal()
            elif index == 1:
                AddToWindowStack(self)
                self.close()
                dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, mode="rating", color=self.movie["general"]['ImageColor'])
                dialog.doModal()
            else:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                list_id = account_lists[index - 2]["id"]
                list_title = account_lists[index - 2]["name"]
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                self.OpenVideoList(mode="list", list_id=list_id, filter_label=list_title, force=True)
        elif controlID == 8:
            self.close()
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %i }, "options":{ "resume": %s } }, "id": 1 }' % (self.movie["general"]['DBID'], "false"))
        elif controlID == 9:
            self.close()
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %i }, "options":{ "resume": %s } }, "id": 1 }' % (self.movie["general"]['DBID'], "true"))
        elif controlID == 445:
            self.ShowManageDialog()
        elif controlID == 132:
            w = TextViewer_Dialog('DialogTextViewer.xml', ADDON_PATH, header=xbmc.getLocalizedString(207), text=self.movie["general"]["Plot"], color=self.movie["general"]['ImageColor'])
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
            listitems = [ADDON.getLocalizedString(32139)]
            account_lists = GetAccountLists()
            for item in account_lists:
                listitems.append("%s (%i)" % (item["name"], item["item_count"]))
            listitems.append(ADDON.getLocalizedString(32138))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32136), listitems)
            if index == 0:
                listname = xbmcgui.Dialog().input(ADDON.getLocalizedString(32137), type=xbmcgui.INPUT_ALPHANUM)
                if listname:
                    list_id = CreateList(listname)
                    xbmc.sleep(1000)
                    ChangeListStatus(list_id, self.tmdb_id, True)
            elif index == len(listitems) - 1:
                self.RemoveListDialog(account_lists)
            elif index > 0:
                ChangeListStatus(account_lists[index - 1]["id"], self.tmdb_id, True)
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
            self.update = GetExtendedMovieInfo(self.tmdb_id, self.dbid, 0)
            self.movie["account_states"] = self.update["account_states"]
        if self.movie["account_states"]:
            if self.movie["account_states"]["favorite"]:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32155))
                self.window.setProperty("movie.favorite", "True")
            else:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32154))
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
        index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32138), listitems)
        if index >= 0:
            # ChangeListStatus(account_lists[index]["id"], self.tmdb_id, False)
            RemoveList(account_lists[index]["id"])
            self.UpdateStates()

    def ShowRatedMovies(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        list_items = GetRatedMedia("movies")
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=list_items, color=self.movie["general"]['ImageColor'])
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        dialog.doModal()

    def OpenVideoList(self, listitems=None, filters=[], mode="filter", list_id=False, filter_label="", force=False):
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=listitems, color=self.movie["general"]['ImageColor'], filters=filters, mode=mode, list_id=list_id, force=force, filter_label=filter_label)
        dialog.doModal()

    def ShowManageDialog(self):
        manage_list = []
        listitems = []
        movie_id = str(self.movie["general"].get("DBID", ""))
        # filename = self.movie["general"].get("FilenameAndPath", False)
        imdb_id = str(self.movie["general"].get("imdb_id", ""))
        if movie_id:
            manage_list += [[xbmc.getLocalizedString(413), "RunScript(script.artwork.downloader,mode=gui,mediatype=movie,dbid=" + movie_id + ")"],
                            [xbmc.getLocalizedString(14061), "RunScript(script.artwork.downloader, mediatype=movie, dbid=" + movie_id + ")"],
                            [ADDON.getLocalizedString(32101), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ",extrathumbs)"],
                            [ADDON.getLocalizedString(32100), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ")"]]
        else:
            manage_list += [[ADDON.getLocalizedString(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=" + imdb_id + ")||Notification(script.extendedinfo,Added Movie To CouchPota))"]]
        # if xbmc.getCondVisibility("system.hasaddon(script.tvtunes)") and movie_id:
        #     manage_list.append([ADDON.getLocalizedString(32102), "RunScript(script.tvtunes,mode=solo&amp;tvpath=$ESCINFO[Window.Property(movie.FilenameAndPath)]&amp;tvname=$INFO[Window.Property(movie.TVShowTitle)])"])
        if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and movie_id:
            manage_list.append([ADDON.getLocalizedString(32103), "RunScript(script.libraryeditor,DBID=" + movie_id + ")"])
        manage_list.append([xbmc.getLocalizedString(1049), "Addon.OpenSettings(script.extendedinfo)"])
        for item in manage_list:
            listitems.append(item[0])
        selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(32133), listitems)
        if selection > -1:
            for item in manage_list[selection][1].split("||"):
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
