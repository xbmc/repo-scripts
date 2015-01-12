import xbmc
import xbmcaddon
import xbmcgui
from Utils import *
from ImageTools import *
from TheMovieDB import *
from YouTube import *
import DialogActorInfo
import DialogVideoList
import DialogSeasonInfo
homewindow = xbmcgui.Window(10000)

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')
addon_version = addon.getAddonInfo('version')
addon_strings = addon.getLocalizedString
addon_path = addon.getAddonInfo('path').decode("utf-8")


class DialogTVShowInfo(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.movieplayer = VideoPlayer(popstack=True)
        xbmcgui.WindowXMLDialog.__init__(self)
        tmdb_id = kwargs.get('id')
        dbid = kwargs.get('dbid')
        imdb_id = kwargs.get('imdbid')
        tvdb_id = kwargs.get('tvdb_id')
        self.name = kwargs.get('name')
        if tmdb_id:
            self.tmdb_id = tmdb_id
        elif dbid and (int(dbid) > -1):
            tvdb_id = GetImdbIDFromDatabase("tvshow", dbid)
            log("IMDBId from local DB:" + str(tvdb_id))
            self.tmdb_id = Get_Show_TMDB_ID(tvdb_id)
            log("tvdb_id to tmdb_id: %s --> %s" % (str(tvdb_id), str(self.tmdb_id)))
        elif tvdb_id:
            self.tmdb_id = Get_Show_TMDB_ID(tvdb_id)
            log("tvdb_id to tmdb_id: %s --> %s" % (str(tvdb_id), str(self.tmdb_id)))
        elif imdb_id:
            self.tmdb_id = Get_Show_TMDB_ID(imdb_id, "imdb_id")
            log("imdb_id to tmdb_id: %s --> %s" % (str(imdb_id), str(self.tmdb_id)))
        elif self.name:
            self.tmdb_id = search_media(kwargs.get('name'), "", "tv")
            log("search string to tmdb_id: %s --> %s" % (str(self.name), str(self.tmdb_id)))
        else:
            self.tmdb_id = ""
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
            if not "DBID" in self.tvshow["general"]:  # need to add comparing for tvshows
                # Notify("download Poster")
                poster_thread = Get_ListItems_Thread(Get_File, self.tvshow["general"]["Poster"])
                poster_thread.start()
            if not "DBID" in self.tvshow["general"]:
                poster_thread.join()
                self.tvshow["general"]['Poster'] = poster_thread.listitems
            filter_thread = Filter_Image_Thread(self.tvshow["general"]["Poster"], 25)
            filter_thread.start()
            youtube_thread.join()
            self.youtube_vids = youtube_thread.listitems
            filter_thread.join()
            self.tvshow["general"]['ImageFilter'], self.tvshow["general"]['ImageColor'] = filter_thread.image, filter_thread.imagecolor
        else:
            Notify(addon.getLocalizedString(32143))
            self.close()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        homewindow.setProperty("movie.ImageColor", self.tvshow["general"]["ImageColor"])
        self.windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.windowid)
        passDictToSkin(self.tvshow["general"], "movie.", False, False, self.windowid)
        self.window.setProperty("tmdb_logged_in", checkLogin())
        self.window.setProperty("type", "tvshow")
        self.getControl(1000).addItems(CreateListItems(self.tvshow["actors"], 0))
        xbmc.sleep(200)
        prettyprint(self.tvshow["certifications"])
        self.getControl(150).addItems(CreateListItems(self.tvshow["similar"], 0))
        self.getControl(250).addItems(CreateListItems(self.tvshow["seasons"], 0))
        self.getControl(550).addItems(CreateListItems(self.tvshow["studios"], 0))
        self.getControl(1450).addItems(CreateListItems(self.tvshow["networks"], 0))
        self.getControl(650).addItems(CreateListItems(self.tvshow["certifications"], 0))
        self.getControl(750).addItems(CreateListItems(self.tvshow["crew"], 0))
        self.getControl(850).addItems(CreateListItems(self.tvshow["genres"], 0))
        self.getControl(950).addItems(CreateListItems(self.tvshow["keywords"], 0))
        self.getControl(1150).addItems(CreateListItems(self.tvshow["videos"], 0))
        self.getControl(350).addItems(CreateListItems(self.youtube_vids, 0))
        self.getControl(1250).addItems(CreateListItems(self.tvshow["images"], 0))
        self.getControl(1350).addItems(CreateListItems(self.tvshow["backdrops"], 0))
        self.UpdateStates(False)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()

    def onClick(self, controlID):
        homewindow.setProperty("WindowColor", xbmc.getInfoLabel("Window(home).Property(movie.ImageColor)"))
        if controlID in [1000, 750]:
            actor_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            credit_id = self.getControl(controlID).getSelectedItem().getProperty("credit_id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % addon_name, addon_path, id=actor_id, credit_id=credit_id)
            dialog.doModal()
        elif controlID in [150]:
            tmdb_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogTVShowInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=tmdb_id)
            dialog.doModal()
        elif controlID in [250]:
            season = self.getControl(controlID).getSelectedItem().getProperty("Season")
            AddToWindowStack(self)
            self.close()
            dialog = DialogSeasonInfo.DialogSeasonInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=self.tmdb_id, season=season, tvshow=self.tvshow["general"]["Title"])
            dialog.doModal()
        elif controlID in [350, 1150]:
            listitem = self.getControl(controlID).getSelectedItem()
            AddToWindowStack(self)
            self.close()
            self.movieplayer.playYoutubeVideo(listitem.getProperty("youtube_id"), listitem, True)
            self.movieplayer.WaitForVideoEnd()
            PopWindowStack()
        elif controlID == 550:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = GetCompanyInfo(self.getControl(controlID).getSelectedItem().getProperty("id"))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(listitems=listitems)
            # xbmc.executebuiltin("ActivateWindow(busydialog)")
            # filters = {"with_networks": self.getControl(controlID).getSelectedItem().getProperty("id")}
            # listitems = GetCompanyInfo(self.getControl(controlID).getSelectedItem().getProperty("id"))
            # xbmc.executebuiltin("Dialog.Close(busydialog)")
            # self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID == 950:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = GetMoviesWithKeyword(self.getControl(controlID).getSelectedItem().getProperty("id"))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(listitems=listitems)
        elif controlID == 850:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            genreid = self.getControl(controlID).getSelectedItem().getProperty("id")
            genrename = self.getControl(controlID).getSelectedItem().getLabel()
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            filters = [{"id": genreid,
                        "type": "with_genres",
                        "typelabel": xbmc.getLocalizedString(135),
                        "label": genrename}]
            self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID in [1250, 1350]:
            image = self.getControl(controlID).getSelectedItem().getProperty("original")
            dialog = SlideShow(u'script-%s-SlideShow.xml' % addon_name, addon_path, image=image)
            dialog.doModal()
        elif controlID == 1450:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            company_id = self.getControl(controlID).getSelectedItem().getProperty("id")
            company_name = self.getControl(controlID).getSelectedItem().getLabel()
            filters = [{"id": company_id,
                        "type": "with_networks",
                        "typelabel": addon.getLocalizedString(32152),
                        "label": company_name}]
            listitems = GetCompanyInfo(company_id)
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            self.OpenVideoList(filters=filters, media_type="tv")
        elif controlID == 445:
            self.ShowManageDialog()
        elif controlID == 6001:
            ratings = []
            for i in range(0, 21):
                ratings.append(str(float(i * 0.5)))
            rating = xbmcgui.Dialog().select(addon.getLocalizedString(32129), ratings)
            if rating > -1:
                rating = float(rating) * 0.5
                RateMedia("tv", self.tmdb_id, rating)
                self.UpdateStates()
        elif controlID == 6002:
            listitems = [addon.getLocalizedString(32144), addon.getLocalizedString(32145)]
            index = xbmcgui.Dialog().select(addon.getLocalizedString(32136), listitems)
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
            w = TextViewer_Dialog('DialogTextViewer.xml', addon_path, header="Overview", text=self.tvshow["general"]["Plot"], color=self.tvshow["general"]['ImageColor'])
            w.doModal()
        # elif controlID == 650:
        #     xbmc.executebuiltin("ActivateWindow(busydialog)")
        #     country = self.getControl(controlID).getSelectedItem().getProperty("iso_3166_1")
        #     certification = self.getControl(controlID).getSelectedItem().getProperty("certification")
        #     cert_items = GetMoviesWithCertification(country, certification)
        #     AddToWindowStack(self)
        #     self.close()
        #     dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=cert_items)
        #     xbmc.executebuiltin("Dialog.Close(busydialog)")
        #     dialog.doModal()
        # elif controlID == 450:
        #     xbmc.executebuiltin("ActivateWindow(busydialog)")
        #     list_items = GetMoviesFromList(self.getControl(controlID).getSelectedItem().getProperty("id"))
        #     self.close()
        #     AddToWindowStack(self)
        #     dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=list_items)
        #     xbmc.executebuiltin("Dialog.Close(busydialog)")
        #     dialog.doModal()

    def UpdateStates(self, forceupdate=True):
        if forceupdate:
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            self.update = GetExtendedTVShowInfo(self.tmdb_id, 0)
            self.tvshow["account_states"] = self.update["account_states"]
        if self.tvshow["account_states"]:
            if self.tvshow["account_states"]["favorite"]:
                self.window.setProperty("FavButton_Label", addon.getLocalizedString(32155))
                self.window.setProperty("movie.favorite", "True")
            else:
                self.window.setProperty("FavButton_Label", addon.getLocalizedString(32154))
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
        tvshow_dbid = self.tvshow["general"].get("DBID", False)
        imdb_id = self.tvshow["general"].get("imdb_id", False)
        title = self.tvshow["general"].get("TVShowTitle", "")

        # filename = self.tvshow["general"].get("FilenameAndPath", False)
        if tvshow_dbid:
            temp_list = [[xbmc.getLocalizedString(413), "RunScript(script.artwork.downloader,mode=gui,mediatype=tv,dbid=" + tvshow_dbid + ")"],
                         [xbmc.getLocalizedString(14061), "RunScript(script.artwork.downloader, mediatype=tv, dbid=" + tvshow_dbid + ")"],
                         [addon.getLocalizedString(32101), "RunScript(script.artwork.downloader,mode=custom,mediatype=tv,dbid=" + tvshow_dbid + ",extrathumbs)"],
                         [addon.getLocalizedString(32100), "RunScript(script.artwork.downloader,mode=custom,mediatype=tv,dbid=" + tvshow_dbid + ")"]]
            manage_list += temp_list
        else:
            manage_list += [[addon.getLocalizedString(32166), "RunScript(special://home/addons/plugin.program.sickbeard/resources/lib/addshow.py," + title + ")"]]
        # if xbmc.getCondVisibility("system.hasaddon(script.tvtunes)") and tvshow_dbid:
        #     manage_list.append([addon.getLocalizedString(32102), "RunScript(script.tvtunes,mode=solo&amp;tvpath=$ESCINFO[Window.Property(movie.FilenameAndPath)]&amp;tvname=$INFO[Window.Property(movie.TVShowTitle)])"])
        if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and tvshow_dbid:
            manage_list.append([addon.getLocalizedString(32103), "RunScript(script.libraryeditor,DBID=" + tvshow_dbid + ")"])
        manage_list.append([xbmc.getLocalizedString(1049), "Addon.OpenSettings(script.extendedinfo)"])
        for item in manage_list:
            listitems.append(item[0])
        selection = xbmcgui.Dialog().select(addon.getLocalizedString(32133), listitems)
        if selection > -1:
            builtin_list = manage_list[selection][1].split("||")
            for item in builtin_list:
                xbmc.executebuiltin(item)

    def ShowRatedTVShows(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        list_items = GetRatedMedia("tv")
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=list_items, color=self.tvshow["general"]['ImageColor'], media_type="tv")
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        dialog.doModal()

    def onFocus(self, controlID):
        pass

    def OpenVideoList(self, listitems=None, filters=[], media_type="movie", mode="filter"):
        AddToWindowStack(self)
        self.close()
        dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path, listitems=listitems, color=self.tvshow["general"]['ImageColor'], filters=filters, type=media_type, mode=mode)
        dialog.doModal()
