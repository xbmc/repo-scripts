# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from ..Utils import *
from .. import TheMovieDB as tmdb
from ..WindowManager import wm
from ActionHandler import ActionHandler
from .. import YouTube
ch = ActionHandler()


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
        self.info = {}

    def onInit(self, *args, **kwargs):
        super(DialogBaseInfo, self).onInit()
        HOME.setProperty("ImageColor", self.info.get('ImageColor', ""))
        self.window = xbmcgui.Window(self.window_id)
        self.setProperty("type", self.type)
        if self.logged_in:
            self.setProperty("tmdb_logged_in", "true")
        else:
            self.clearProperty("tmdb_logged_in")
        # present for jurialmunkey
        HOME.setProperty("ExtendedInfo_fanart", self.info.get("fanart", ""))

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

    @run_async
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
                self.getControl(container_id).addItems(create_listitems(listitems))
            except:
                log("Notice: No container with id %i available" % container_id)

    @ch.click(1250)
    @ch.click(1350)
    def open_image(self):
        pos = wm.open_slideshow(listitems=next((v for (i, v) in self.listitems if i == self.control_id)),
                                index=self.control.getSelectedPosition())
        self.control.selectItem(pos)

    @ch.action("contextmenu", 1250)
    def thumbnail_options(self):
        if not self.info.get("dbid"):
            return None
        selection = xbmcgui.Dialog().select(heading=LANG(22080),
                                            list=[LANG(32006)])
        if selection == 0:
            media_type = self.getProperty("type")
            params = '"art": {"poster": "%s"}' % self.listitem.getProperty("original")
            get_kodi_json(method="VideoLibrary.Set%sDetails" % media_type,
                          params='{ %s, "%sid":%s }' % (params, media_type.lower(), self.info['dbid']))

    @ch.action("contextmenu", 1350)
    def fanart_options(self):
        if not self.info.get("dbid"):
            return None
        selection = xbmcgui.Dialog().select(heading=LANG(22080),
                                            list=[LANG(32007)])
        if selection == 0:
            media_type = self.getProperty("type")
            params = '"art": {"fanart": "%s"}' % self.listitem.getProperty("original")
            get_kodi_json(method="VideoLibrary.Set%sDetails" % media_type,
                          params='{ %s, "%sid":%s }' % (params, media_type.lower(), self.info['dbid']))

    @ch.action("contextmenu", 1150)
    @ch.action("contextmenu", 350)
    def download_video(self):
        selection = xbmcgui.Dialog().select(heading=LANG(22080),
                                            list=[LANG(33003)])
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
        self.close()

    @run_async
    def get_youtube_vids(self, search_str):
        try:
            youtube_list = self.getControl(350)
        except:
            return None
        result = YouTube.search(search_str, limit=15)
        if not self.yt_listitems:
            self.yt_listitems = result.get("listitems", [])
            if "videos" in self.data:
                vid_ids = [item["key"] for item in self.data["videos"]]
                self.yt_listitems = [i for i in self.yt_listitems if i["youtube_id"] not in vid_ids]
        youtube_list.reset()
        youtube_list.addItems(create_listitems(self.yt_listitems))

    def open_credit_dialog(self, credit_id):
        info = tmdb.get_credit_info(credit_id)
        listitems = []
        if "seasons" in info["media"]:
            listitems += tmdb.handle_seasons(info["media"]["seasons"])
        if "episodes" in info["media"]:
            listitems += tmdb.handle_episodes(info["media"]["episodes"])
        if not listitems:
            listitems += [{"label": LANG(19055)}]
        listitem, index = wm.open_selectdialog(listitems=listitems)
        if listitem["media_type"] == "episode":
            wm.open_episode_info(prev_window=self,
                                 season=listitems[index]["season"],
                                 episode=listitems[index]["episode"],
                                 tvshow_id=info["media"]["id"])
        elif listitem["media_type"] == "season":
            wm.open_season_info(prev_window=self,
                                season=listitems[index]["season"],
                                tvshow_id=info["media"]["id"])

    def update_states(self):
        if not self.account_states:
            return None
        pass_dict_to_skin(data=tmdb.get_account_props(self.account_states),
                          window_id=self.window_id)
