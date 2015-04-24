import xbmc
import xbmcgui
from Utils import *
from local_db import GetImdbIDFromDatabase
from ImageTools import *
from TheMovieDB import *
from YouTube import *
import DialogActorInfo
import DialogVideoList
import DialogSeasonInfo


class DialogTVShowInfo(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.movieplayer = VideoPlayer(popstack=True)
        xbmcgui.WindowXMLDialog.__init__(self)
        self.tmdb_id = None
        tmdb_id = kwargs.get('id', False)
        dbid = kwargs.get('dbid')
        imdb_id = kwargs.get('imdbid')
        tvdb_id = kwargs.get('tvdb_id')
        self.name = kwargs.get('name')
        self.tvshow = False
        if tmdb_id:
            self.tmdb_id = tmdb_id
        elif dbid and (int(dbid) > 0):
            tvdb_id = GetImdbIDFromDatabase("tvshow", dbid)
            log("IMDBId from local DB:" + str(tvdb_id))
            if tvdb_id:
                self.tmdb_id = get_show_tmdb_id(tvdb_id)
                log("tvdb_id to tmdb_id: %s --> %s" % (str(tvdb_id), str(self.tmdb_id)))
        elif tvdb_id:
            self.tmdb_id = get_show_tmdb_id(tvdb_id)
            log("tvdb_id to tmdb_id: %s --> %s" % (str(tvdb_id), str(self.tmdb_id)))
        elif imdb_id:
            self.tmdb_id = get_show_tmdb_id(imdb_id, "imdb_id")
            log("imdb_id to tmdb_id: %s --> %s" % (str(imdb_id), str(self.tmdb_id)))
        elif self.name:
            self.tmdb_id = search_media(kwargs.get('name'), "", "tv")
            log("search string to tmdb_id: %s --> %s" % (str(self.name), str(self.tmdb_id)))
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        if self.tmdb_id:
            self.tvshow = GetExtendedTVShowInfo(self.tmdb_id)
            if not self.tvshow:
                self.close()
            youtube_thread = Get_Youtube_Vids_Thread(self.tvshow["general"]["Title"] + " tv", "", "relevance", 15)
            youtube_thread.start()
            cert_list = get_certification_list("tv")
            for item in self.tvshow["certifications"]:
                if item["iso_3166_1"] in cert_list:
                    # language = item["iso_3166_1"]
                    rating = item["certification"]
                    language_certs = cert_list[item["iso_3166_1"]]
                    hit = dictfind(language_certs, "certification", rating)
                    if hit:
                        item["meaning"] = hit["meaning"]
            if "DBID" not in self.tvshow["general"]:  # need to add comparing for tvshows
                # Notify("download Poster")
                poster_thread = Threaded_Function(Get_File, self.tvshow["general"]["Poster"])
                poster_thread.start()
            if "DBID" not in self.tvshow["general"]:
                poster_thread.join()
                self.tvshow["general"]['Poster'] = poster_thread.listitems
            filter_thread = Filter_Image_Thread(self.tvshow["general"]["Poster"], 25)
            filter_thread.start()
            youtube_thread.join()
            self.youtube_vids = youtube_thread.listitems
            filter_thread.join()
            self.tvshow["general"]['ImageFilter'], self.tvshow["general"]['ImageColor'] = filter_thread.image, filter_thread.imagecolor
        else:
            Notify(ADDON.getLocalizedString(32143))
            self.close()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        if not self.tvshow:
            self.close()
            return
        HOME.setProperty("movie.ImageColor", self.tvshow["general"]["ImageColor"])
        self.windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.windowid)
        passDictToSkin(self.tvshow["general"], "movie.", False, False, self.windowid)
        self.window.setProperty("tmdb_logged_in", checkLogin())
        self.window.setProperty("type", "tvshow")
        self.getControl(1000).addItems(create_listitems(self.tvshow["actors"], 0))
        xbmc.sleep(200)
        prettyprint(self.tvshow["certifications"])
        self.getControl(150).addItems(create_listitems(self.tvshow["similar"], 0))
        self.getControl(250).addItems(create_listitems(self.tvshow["seasons"], 0))
        self.getControl(550).addItems(create_listitems(self.tvshow["studios"], 0))
        self.getControl(1450).addItems(create_listitems(self.tvshow["networks"], 0))
        self.getControl(650).addItems(create_listitems(self.tvshow["certifications"], 0))
        self.getControl(750).addItems(create_listitems(self.tvshow["crew"], 0))
        self.getControl(850).addItems(create_listitems(self.tvshow["genres"], 0))
        self.getControl(950).addItems(create_listitems(self.tvshow["keywords"], 0))
        self.getControl(1150).addItems(create_listitems(self.tvshow["videos"], 0))
        self.getControl(350).addItems(create_listitems(self.youtube_vids, 0))
        self.getControl(1250).addItems(create_listitems(self.tvshow["images"], 0))
        self.getControl(1350).addItems(create_listitems(self.tvshow["backdrops"], 0))
        self.UpdateStates(False)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()

    def onClick(self, controlID):
        HOME.setProperty("WindowColor", xbmc.getInfoLabel("Window(home).Property(movie.ImageColor)"))
        control = self.getControl(controlID)
        if controlID in [1000, 750]:
            actor_id = control.getSelectedItem().getProperty("id")
            credit_id = control.getSelectedItem().getProperty("credit_id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % ADDON_NAME, ADDON_PATH, id=actor_id, credit_id=credit_id)
            dialog.doModal()
        elif controlID in [150]:
            tmdb_id = control.getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogTVShowInfo(u'script-%s-DialogVideoInfo.xml' % ADDON_NAME, ADDON_PATH, id=tmdb_id)
            dialog.doModal()
        elif controlID in [250]:
            season = control.getSelectedItem().getProperty("Season")
            AddToWindowStack(self)
            self.close()
            dialog = DialogSeasonInfo.DialogSeasonInfo(u'script-%s-DialogVideoInfo.xml' % ADDON_NAME, ADDON_PATH, id=self.tmdb_id, season=season, tvshow=self.tvshow["general"]["Title"])
            dialog.doModal()
        elif controlID in [350, 1150]:
            listitem = control.getSelectedItem()
            AddToWindowStack(self)
            self.close()
            self.movieplayer.playYoutubeVideo(listitem.getProperty("youtube_id"), listitem, True)
            self.movieplayer.wait_for_video_end()
            PopWindowStack()
        elif controlID == 550:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = GetCompanyInfo(control.getSelectedItem().getProperty("id"))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(listitems=listitems)
            # xbmc.executebuiltin("ActivateWindow(busydialog)")
            # filters = {"with_networks": control.getSelectedItem().getProperty("id")}
            # listitems = GetCompanyInfo(control.getSelectedItem().getProperty("id"))
            # xbmc.executebuiltin("Dialog.Close(busydialog)")
            # self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID == 950:
            keyword_id = control.getSelectedItem().getProperty("id")
            keyword_name = control.getSelectedItem().getLabel()
            filters = [{"id": keyword_id,
                        "type": "with_keywords",
                        "typelabel": ADDON.getLocalizedString(32114),
                        "label": keyword_name}]
            self.OpenVideoList(filters=filters)
        elif controlID == 850:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            genreid = control.getSelectedItem().getProperty("id")
            genrename = control.getSelectedItem().getLabel()
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            filters = [{"id": genreid,
                        "type": "with_genres",
                        "typelabel": xbmc.getLocalizedString(135),
                        "label": genrename}]
            self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID in [1250, 1350]:
            image = control.getSelectedItem().getProperty("original")
            dialog = SlideShow(u'script-%s-SlideShow.xml' % ADDON_NAME, ADDON_PATH, image=image)
            dialog.doModal()
        elif controlID == 1450:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            company_id = control.getSelectedItem().getProperty("id")
            company_name = control.getSelectedItem().getLabel()
            filters = [{"id": company_id,
                        "type": "with_networks",
                        "typelabel": ADDON.getLocalizedString(32152),
                        "label": company_name}]
            listitems = GetCompanyInfo(company_id)
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID == 445:
            self.ShowManageDialog()
        elif controlID == 6001:
            rating = get_rating_from_user()
            if rating:
                send_rating_for_media_item("tv", self.tmdb_id, rating)
                self.UpdateStates()
        elif controlID == 6002:
            listitems = [ADDON.getLocalizedString(32144), ADDON.getLocalizedString(32145)]
            index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32136), listitems)
            if index == -1:
                pass
            elif index == 0:
                self.OpenVideoList(media_type="tv", mode="favorites")
            elif index == 1:
                self.ShowRatedTVShows()
        elif controlID == 6003:
            ChangeFavStatus(self.tvshow["general"]["ID"], "tv", "true")
            self.UpdateStates()
        elif controlID == 6006:
            self.ShowRatedTVShows()
        elif controlID == 132:
            w = TextViewer_Dialog('DialogTextViewer.xml', ADDON_PATH, header=ADDON.getLocalizedString(32037), text=self.tvshow["general"]["Plot"], color=self.tvshow["general"]['ImageColor'])
            w.doModal()
        # elif controlID == 650:
        #     xbmc.executebuiltin("ActivateWindow(busydialog)")
        #     country = control.getSelectedItem().getProperty("iso_3166_1")
        #     certification = self.getControl(controlID).getSelectedItem().getProperty("certification")
        #     cert_items = GetMoviesWithCertification(country, certification)
        #     AddToWindowStack(self)
        #     self.close()
        #     dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=cert_items)
        #     xbmc.executebuiltin("Dialog.Close(busydialog)")
        #     dialog.doModal()
        # elif controlID == 450:
        #     xbmc.executebuiltin("ActivateWindow(busydialog)")
        #     list_items = GetMoviesFromList(self.getControl(controlID).getSelectedItem().getProperty("id"))
        #     self.close()
        #     AddToWindowStack(self)
        #     dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=list_items)
        #     xbmc.executebuiltin("Dialog.Close(busydialog)")
        #     dialog.doModal()

    def UpdateStates(self, forceupdate=True):
        if forceupdate:
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            self.update = GetExtendedTVShowInfo(self.tmdb_id, 0)
            self.tvshow["account_states"] = self.update["account_states"]
        if self.tvshow["account_states"]:
            if self.tvshow["account_states"]["favorite"]:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32155))
                self.window.setProperty("movie.favorite", "True")
            else:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32154))
                self.window.setProperty("movie.favorite", "")
            if self.tvshow["account_states"]["rated"]:
                self.window.setProperty("movie.rated", str(self.tvshow["account_states"]["rated"]["value"]))
            else:
                self.window.setProperty("movie.rated", "")
            self.window.setProperty("movie.watchlist", str(self.tvshow["account_states"]["watchlist"]))
            # Notify(str(self.tvshow["account_states"]["rated"]["value"]))

    def ShowManageDialog(self):
        manage_list = []
        listitems = []
        tvshow_dbid = str(self.tvshow["general"].get("DBID", ""))
        title = self.tvshow["general"].get("TVShowTitle", "")
        # imdb_id = str(self.tvshow["general"].get("imdb_id", ""))
        # filename = self.tvshow["general"].get("FilenameAndPath", False)
        if tvshow_dbid:
            temp_list = [[xbmc.getLocalizedString(413), "RunScript(script.artwork.downloader,mode=gui,mediatype=tv,dbid=" + tvshow_dbid + ")"],
                         [xbmc.getLocalizedString(14061), "RunScript(script.artwork.downloader, mediatype=tv, dbid=" + tvshow_dbid + ")"],
                         [ADDON.getLocalizedString(32101), "RunScript(script.artwork.downloader,mode=custom,mediatype=tv,dbid=" + tvshow_dbid + ",extrathumbs)"],
                         [ADDON.getLocalizedString(32100), "RunScript(script.artwork.downloader,mode=custom,mediatype=tv,dbid=" + tvshow_dbid + ")"]]
            manage_list += temp_list
        else:
            manage_list += [[ADDON.getLocalizedString(32166), "RunScript(special://home/addons/plugin.program.sickbeard/resources/lib/addshow.py," + title + ")"]]
        # if xbmc.getCondVisibility("system.hasaddon(script.tvtunes)") and tvshow_dbid:
        #     manage_list.append([ADDON.getLocalizedString(32102), "RunScript(script.tvtunes,mode=solo&amp;tvpath=$ESCINFO[Window.Property(movie.FilenameAndPath)]&amp;tvname=$INFO[Window.Property(movie.TVShowTitle)])"])
        if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and tvshow_dbid:
            manage_list.append([ADDON.getLocalizedString(32103), "RunScript(script.libraryeditor,DBID=" + tvshow_dbid + ")"])
        manage_list.append([xbmc.getLocalizedString(1049), "Addon.OpenSettings(script.extendedinfo)"])
        for item in manage_list:
            listitems.append(item[0])
        selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(32133), listitems)
        if selection > -1:
            builtin_list = manage_list[selection][1].split("||")
            for item in builtin_list:
                xbmc.executebuiltin(item)

    def ShowRatedTVShows(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        list_items = GetRatedMedia("tv")
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=list_items, color=self.tvshow["general"]['ImageColor'], media_type="tv")
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        dialog.doModal()

    def onFocus(self, controlID):
        pass

    def OpenVideoList(self, listitems=None, filters=[], media_type="movie", mode="filter"):
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % ADDON_NAME, ADDON_PATH, listitems=listitems, color=self.tvshow["general"]['ImageColor'], filters=filters, type=media_type, mode=mode)
        dialog.doModal()
