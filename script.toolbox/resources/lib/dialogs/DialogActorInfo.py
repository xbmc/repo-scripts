# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from ..Utils import *
from ..ImageTools import *
from ..TheMovieDB import *
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from .. import VideoPlayer
from ..OnClickHandler import OnClickHandler

PLAYER = VideoPlayer.VideoPlayer()
ch = OnClickHandler()


def get_actor_window(window_type):

    class DialogActorInfo(DialogBaseInfo, window_type):

        def __init__(self, *args, **kwargs):
            super(DialogActorInfo, self).__init__(*args, **kwargs)
            self.id = kwargs.get('id', False)
            self.type = "Actor"
            data = extended_actor_info(actor_id=self.id)
            if not data:
                return None
            self.info, self.data = data
            self.info['ImageFilter'], self.info['ImageColor'] = filter_image(input_img=self.info.get("thumb", ""),
                                                                             radius=25)
            self.listitems = [(150, self.data["movie_roles"]),
                              (250, self.data["tvshow_roles"]),
                              (450, self.data["images"]),
                              (550, merge_dict_lists(self.data["movie_crew_roles"])),
                              (650, merge_dict_lists(self.data["tvshow_crew_roles"])),
                              (750, self.data["tagged_images"])]

        def onInit(self):
            self.get_youtube_vids(self.info["name"])
            super(DialogActorInfo, self).onInit()
            pass_dict_to_skin(data=self.info,
                              prefix="actor.",
                              window_id=self.window_id)
            self.fill_lists()

        def onClick(self, control_id):
            super(DialogActorInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super(DialogActorInfo, self).onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        @ch.click(150)
        @ch.click(550)
        def open_movie_info(self):
            wm.open_movie_info(prev_window=self,
                               movie_id=self.listitem.getProperty("id"),
                               dbid=self.listitem.getProperty("dbid"))

        @ch.click(250)
        @ch.click(650)
        def open_tvshow_dialog(self):
            selection = xbmcgui.Dialog().select(heading=LANG(32151),
                                                list=[LANG(32148), LANG(32147)])
            if selection == 0:
                wm.open_tvshow_info(prev_window=self,
                                    tvshow_id=self.listitem.getProperty("id"),
                                    dbid=self.listitem.getProperty("dbid"))
            if selection == 1:
                self.open_credit_dialog(credit_id=self.listitem.getProperty("credit_id"))

        @ch.click(450)
        @ch.click(750)
        def open_image(self):
            listitems = next((v for (i, v) in self.listitems if i == self.control_id), None)
            index = self.control.getSelectedPosition()
            pos = wm.open_slideshow(listitems=listitems, index=index)
            self.control.selectItem(pos)

        @ch.click(350)
        def play_youtube_video(self):
            PLAYER.play_youtube_video(youtube_id=self.listitem.getProperty("youtube_id"),
                                      listitem=self.listitem,
                                      window=self)

        @ch.click(132)
        def show_plot(self):
            wm.open_textviewer(header=LANG(32037),
                               text=self.info["biography"],
                               color=self.info['ImageColor'])

        @ch.action("contextmenu", 150)
        @ch.action("contextmenu", 550)
        def add_movie_to_account(self):
            movie_id = self.listitem.getProperty("id")
            add_movie_to_list(movie_id)

    return DialogActorInfo
