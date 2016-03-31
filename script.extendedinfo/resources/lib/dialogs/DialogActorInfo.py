# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from .. import Utils
from .. import ImageTools
from .. import addon
from .. import TheMovieDB as tmdb
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from ..VideoPlayer import PLAYER
from ActionHandler import ActionHandler

ID_LIST_MOVIE_ROLES = 150
ID_LIST_TV_ROLES = 250
ID_LIST_YOUTUBE = 350
ID_LIST_IMAGES = 450
ID_LIST_MOVIE_CREW = 550
ID_LIST_TV_CREW = 650
ID_LIST_TAGGED_IMAGES = 750
ID_LIST_BACKDROPS = 1350
ID_CONTROL_PLOT = 132

ch = ActionHandler()


def get_window(window_type):

    class DialogActorInfo(DialogBaseInfo, window_type):

        def __init__(self, *args, **kwargs):
            super(DialogActorInfo, self).__init__(*args, **kwargs)
            self.id = kwargs.get('id', False)
            self.type = "Actor"
            data = tmdb.extended_actor_info(actor_id=self.id)
            if not data:
                return None
            self.info, self.data = data
            self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(self.info.get("thumb"))
            self.listitems = [(ID_LIST_MOVIE_ROLES, self.data["movie_roles"]),
                              (ID_LIST_TV_ROLES, self.data["tvshow_roles"]),
                              (ID_LIST_IMAGES, self.data["images"]),
                              (ID_LIST_MOVIE_CREW, Utils.merge_dict_lists(self.data["movie_crew_roles"])),
                              (ID_LIST_TV_CREW, Utils.merge_dict_lists(self.data["tvshow_crew_roles"])),
                              (ID_LIST_TAGGED_IMAGES, self.data["tagged_images"])]

        def onInit(self):
            self.get_youtube_vids(self.info["label"])
            super(DialogActorInfo, self).onInit()
            Utils.pass_dict_to_skin(data=self.info,
                                    window_id=self.window_id)
            self.fill_lists()

        def onClick(self, control_id):
            super(DialogActorInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super(DialogActorInfo, self).onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        @ch.click(ID_LIST_MOVIE_ROLES)
        @ch.click(ID_LIST_MOVIE_CREW)
        def open_movie_info(self):
            wm.open_movie_info(prev_window=self,
                               movie_id=self.listitem.getProperty("id"),
                               dbid=self.listitem.getProperty("dbid"))

        @ch.click(ID_LIST_TV_ROLES)
        @ch.click(ID_LIST_TV_CREW)
        def open_tvshow_dialog(self):
            selection = xbmcgui.Dialog().select(heading=addon.LANG(32151),
                                                list=[addon.LANG(32148), addon.LANG(32147)])
            if selection == 0:
                wm.open_tvshow_info(prev_window=self,
                                    tmdb_id=self.listitem.getProperty("id"),
                                    dbid=self.listitem.getProperty("dbid"))
            if selection == 1:
                self.open_credit_dialog(credit_id=self.listitem.getProperty("credit_id"))

        @ch.click(ID_LIST_IMAGES)
        @ch.click(ID_LIST_TAGGED_IMAGES)
        def open_image(self):
            listitems = next((v for (i, v) in self.listitems if i == self.control_id), None)
            pos = wm.open_slideshow(listitems=listitems,
                                    index=self.control.getSelectedPosition())
            self.control.selectItem(pos)

        @ch.click(ID_LIST_YOUTUBE)
        def play_youtube_video(self):
            PLAYER.play_youtube_video(youtube_id=self.listitem.getProperty("youtube_id"),
                                      listitem=self.listitem,
                                      window=self)

        @ch.click(ID_CONTROL_PLOT)
        def show_plot(self):
            xbmcgui.Dialog().textviewer(heading=addon.LANG(32037),
                                        text=self.info["biography"])

        @ch.action("contextmenu", ID_LIST_MOVIE_ROLES)
        @ch.action("contextmenu", ID_LIST_MOVIE_CREW)
        def movie_context_menu(self):
            tmdb.add_movie_to_list(self.listitem.getProperty("id"))

    return DialogActorInfo
