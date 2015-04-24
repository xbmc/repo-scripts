import xbmc
import xbmcgui
from Utils import *
from TheMovieDB import *
from YouTube import *
import DialogActorInfo
import DialogEpisodeInfo
from ImageTools import *


class DialogSeasonInfo(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        xbmcgui.WindowXMLDialog.__init__(self)
        self.movieplayer = VideoPlayer(popstack=True)
        self.tmdb_id = kwargs.get('id')
        self.season = kwargs.get('season')
        self.showname = kwargs.get('tvshow')
        self.logged_in = checkLogin()
        if self.tmdb_id or (self.season and self.showname):
            self.season = GetSeasonInfo(self.tmdb_id, self.showname, self.season)
            if not self.season:
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                return
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            search_string = "%s %s tv" % (self.season["general"]["TVShowTitle"], self.season["general"]["Title"])
            youtube_thread = Get_Youtube_Vids_Thread(search_string, "", "relevance", 15)
            youtube_thread.start()
            if "DBID" not in self.season["general"]:  # need to add comparing for seasons
                poster_thread = Threaded_Function(Get_File, self.season["general"]["Poster"])
                poster_thread.start()
            if "DBID" not in self.season["general"]:
                poster_thread.join()
                self.season["general"]['Poster'] = poster_thread.listitems
            filter_thread = Filter_Image_Thread(self.season["general"]["Poster"], 25)
            filter_thread.start()
            youtube_thread.join()
            self.youtube_vids = youtube_thread.listitems
            filter_thread.join()
            self.season["general"]['ImageFilter'], self.season["general"]['ImageColor'] = filter_thread.image, filter_thread.imagecolor
        else:
            Notify(ADDON.getLocalizedString(32143))
            self.close()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onInit(self):
        if not self.season:
            self.close()
            return
        HOME.setProperty("movie.ImageColor", self.season["general"]["ImageColor"])
        windowid = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(windowid)
        self.window.setProperty("tmdb_logged_in", self.logged_in)
        self.window.setProperty("type", "season")
        passDictToSkin(self.season["general"], "movie.", False, False, windowid)
        self.getControl(1000).addItems(create_listitems(self.season["actors"], 0))
        self.getControl(750).addItems(create_listitems(self.season["crew"], 0))
        self.getControl(1150).addItems(create_listitems(self.season["videos"], 0))
        self.getControl(350).addItems(create_listitems(self.youtube_vids, 0))
        self.getControl(1250).addItems(create_listitems(self.season["images"], 0))
        self.getControl(1350).addItems(create_listitems(self.season["backdrops"], 0))
        self.getControl(2000).addItems(create_listitems(self.season["episodes"], 0))

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
            PopWindowStack()
        elif action in self.ACTION_EXIT_SCRIPT:
            self.close()

    def onClick(self, controlID):
        control = self.getControl(controlID)
        HOME.setProperty("WindowColor", xbmc.getInfoLabel("Window(home).Property(movie.ImageColor)"))
        if controlID in [1000, 750]:
            actor_id = control.getSelectedItem().getProperty("id")
            credit_id = control.getSelectedItem().getProperty("credit_id")
            AddToWindowStack(self)
            self.close()
            dialog = DialogActorInfo.DialogActorInfo(u'script-%s-DialogInfo.xml' % ADDON_NAME, ADDON_PATH, id=actor_id, credit_id=credit_id)
            dialog.doModal()
        elif controlID in [2000]:
            episode = control.getSelectedItem().getProperty("episode")
            season = control.getSelectedItem().getProperty("season")
            if not self.tmdb_id:
                response = GetMovieDBData("search/tv?query=%s&language=%s&" % (urllib.quote_plus(self.showname), ADDON.getSetting("LanguageID")), 30)
                self.tmdb_id = str(response['results'][0]['id'])
            AddToWindowStack(self)
            self.close()
            dialog = DialogEpisodeInfo.DialogEpisodeInfo(u'script-%s-DialogVideoInfo.xml' % ADDON_NAME, ADDON_PATH, show_id=self.tmdb_id, season=season, episode=episode)
            dialog.doModal()
        elif controlID in [350, 1150]:
            listitem = control.getSelectedItem()
            AddToWindowStack(self)
            self.close()
            self.movieplayer.playYoutubeVideo(listitem.getProperty("youtube_id"), listitem, True)
            self.movieplayer.wait_for_video_end()
            PopWindowStack()
        elif controlID in [1250, 1350]:
            image = control.getSelectedItem().getProperty("original")
            dialog = SlideShow(u'script-%s-SlideShow.xml' % ADDON_NAME, ADDON_PATH, image=image)
            dialog.doModal()
        elif controlID == 132:
            w = TextViewer_Dialog('DialogTextViewer.xml', ADDON_PATH, header=ADDON.getLocalizedString(32037), text=self.season["general"]["Plot"], color=self.season["general"]['ImageColor'])
            w.doModal()

    def onFocus(self, controlID):
        pass
