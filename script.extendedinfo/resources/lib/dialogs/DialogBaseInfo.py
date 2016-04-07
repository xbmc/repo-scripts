# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from .. import Utils
from .. import TheMovieDB as tmdb
from .. import addon
from ..WindowManager import wm
from ActionHandler import ActionHandler
from .. import YouTube
ch = ActionHandler()

ID_LIST_YOUTUBE = 350
ID_LIST_VIDEOS = 1150
ID_LIST_IMAGES = 1250
ID_LIST_BACKDROPS = 1350


class DialogBaseInfo(object):
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        super(DialogBaseInfo, self).__init__(*args, **kwargs)
        self.logged_in = tmdb.Login.check_login()
        self.dbid = kwargs.get('dbid')
        self.bouncing = False
        self.last_focus = None
        self.data = None
        self.yt_listitems = []
        self.info = Utils.ListItem()

    def onInit(self, *args, **kwargs):
        super(DialogBaseInfo, self).onInit()
        addon.set_global("ImageColor", self.info.get_property('ImageColor'))
        addon.set_global("infobackground", self.info.get_art('fanart'))
        self.setProperty("type", self.type)
        self.setProperty("tmdb_logged_in", "true" if self.logged_in else "")

    def onAction(self, action):
        ch.serve_action(action, self.getFocusId(), self)

    def onClick(self, control_id):
        ch.serve(control_id, self)

    def onFocus(self, control_id):
        if control_id == 20000:
            if not self.bouncing:
                self.bounce("up")
            self.setFocusId(self.last_focus)
        elif control_id == 20001:
            if not self.bouncing:
                self.bounce("down")
            self.setFocusId(self.last_focus)
        self.last_focus = control_id

    @Utils.run_async
    def bounce(self, identifier):
        self.bouncing = True
        self.setProperty("Bounce.%s" % identifier, "true")
        xbmc.sleep(200)
        self.clearProperty("Bounce.%s" % identifier)
        self.bouncing = False

    def fill_lists(self):
        for container_id, listitems in self.listitems:
            try:
                self.getControl(container_id).reset()
                self.getControl(container_id).addItems([i.get_listitem() for i in listitems])
            except Exception:
                Utils.log("Notice: No container with id %i available" % container_id)

    @ch.click(ID_LIST_IMAGES)
    @ch.click(ID_LIST_BACKDROPS)
    def open_image(self):
        pos = wm.open_slideshow(listitems=next((v for (i, v) in self.listitems if i == self.control_id)),
                                index=self.control.getSelectedPosition())
        self.control.selectItem(pos)

    @ch.action("contextmenu", ID_LIST_IMAGES)
    def thumbnail_options(self):
        if not self.info.get("dbid"):
            return None
        selection = xbmcgui.Dialog().select(heading=addon.LANG(22080),
                                            list=[addon.LANG(32006)])
        if selection == 0:
            media_type = self.getProperty("type")
            art = {"poster": self.listitem.getProperty("original")}
            Utils.get_kodi_json(method="VideoLibrary.Set%sDetails" % media_type,
                                params={"art": art, "%sid" % media_type.lower(): self.info['dbid']})

    @ch.action("contextmenu", ID_LIST_BACKDROPS)
    def fanart_options(self):
        if not self.info.get("dbid"):
            return None
        selection = xbmcgui.Dialog().select(heading=addon.LANG(22080),
                                            list=[addon.LANG(32007)])
        if selection == 0:
            media_type = self.getProperty("type")
            art = {"fanart": self.listitem.getProperty("original")}
            Utils.get_kodi_json(method="VideoLibrary.Set%sDetails" % media_type,
                                params={"art": art, "%sid" % media_type.lower(): self.info['dbid']})

    @ch.action("contextmenu", ID_LIST_VIDEOS)
    @ch.action("contextmenu", ID_LIST_YOUTUBE)
    def download_video(self):
        selection = xbmcgui.Dialog().select(heading=addon.LANG(22080),
                                            list=[addon.LANG(33003)])
        if selection == 0:
            import YDStreamExtractor
            vid = YDStreamExtractor.getVideoInfo(self.listitem.getProperty("youtube_id"),
                                                 quality=1)
            YDStreamExtractor.handleDownload(vid)

    @ch.action("parentdir", "*")
    @ch.action("parentfolder", "*")
    def previous_menu(self):
        onback = self.getProperty("%i_onback" % self.control_id)
        if onback:
            xbmc.executebuiltin(onback)
        else:
            self.close()
            wm.pop_stack()

    @ch.action("previousmenu", "*")
    def exit_script(self):
        wm.cancel(self)

    @Utils.run_async
    def get_youtube_vids(self, search_str):
        try:
            youtube_list = self.getControl(ID_LIST_YOUTUBE)
        except Exception:
            return None
        if not self.yt_listitems:
            result = YouTube.search(search_str, limit=15)
            self.yt_listitems = result.get("listitems", [])
            if "videos" in self.data:
                vid_ids = [item.get_property("key") for item in self.data["videos"]]
                self.yt_listitems = [i for i in self.yt_listitems if i.get_property("youtube_id") not in vid_ids]
        youtube_list.reset()
        youtube_list.addItems(Utils.create_listitems(self.yt_listitems))

    def open_credit_dialog(self, credit_id):
        info = tmdb.get_credit_info(credit_id)
        listitems = []
        if "seasons" in info["media"]:
            listitems += tmdb.handle_seasons(info["media"]["seasons"])
        if "episodes" in info["media"]:
            listitems += tmdb.handle_episodes(info["media"]["episodes"])
        if not listitems:
            listitems += [{"label": addon.LANG(19055)}]
        listitem, index = wm.open_selectdialog(listitems=listitems)
        if listitem["mediatype"] == "episode":
            wm.open_episode_info(prev_window=self,
                                 season=listitems[index]["season"],
                                 episode=listitems[index]["episode"],
                                 tvshow_id=info["media"]["id"])
        elif listitem["mediatype"] == "season":
            wm.open_season_info(prev_window=self,
                                season=listitems[index]["season"],
                                tvshow_id=info["media"]["id"])

    def update_states(self):
        if not self.account_states:
            return None
        Utils.pass_dict_to_skin(data=tmdb.get_account_props(self.account_states),
                                window_id=self.window_id)

    @ch.action("contextmenu", "*")
    def movie_context_menu(self):
        if self.listitem.getVideoInfoTag().getMediaType() == "movie":
            selection = xbmcgui.Dialog().select(heading=addon.LANG(22080),
                                                list=[addon.LANG(32083)])
            if selection == 0:
                account_lists = get_account_lists()
                listitems = ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
                index = xbmcgui.Dialog().select(addon.LANG(32136), listitems)
                change_list_status(list_id=account_lists[index]["id"],
                                   movie_id=self.listitem.getProperty("id"),
                                   status=True)
