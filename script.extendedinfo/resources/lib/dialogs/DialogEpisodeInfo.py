# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from ..Utils import *
from .. import TheMovieDB
from .. import ImageTools
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from ActionHandler import ActionHandler
from ..VideoPlayer import PLAYER

ch = ActionHandler()


def get_window(window_type):

    class DialogEpisodeInfo(DialogBaseInfo, window_type):

        @busy_dialog
        def __init__(self, *args, **kwargs):
            super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
            self.type = "Episode"
            self.tvshow_id = kwargs.get('show_id')
            data = TheMovieDB.extended_episode_info(tvshow_id=self.tvshow_id,
                                                    season=kwargs.get('season'),
                                                    episode=kwargs.get('episode'))
            if not data:
                return None
            self.info, self.data, self.account_states = data
            self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(input_img=self.info.get("thumb", ""),
                                                                                        radius=25)
            self.listitems = [(1000, self.data["actors"] + self.data["guest_stars"]),
                              (750, self.data["crew"]),
                              (1150, self.data["videos"]),
                              (1350, self.data["images"])]

        def onInit(self):
            super(DialogEpisodeInfo, self).onInit()
            pass_dict_to_skin(data=self.info,
                              debug=False,
                              precache=False,
                              window_id=self.window_id)
            super(DialogEpisodeInfo, self).update_states()
            self.get_youtube_vids("%s tv" % (self.info['title']))
            self.fill_lists()

        def onClick(self, control_id):
            super(DialogEpisodeInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        @ch.click(750)
        @ch.click(1000)
        def open_actor_info(self):
            wm.open_actor_info(prev_window=self,
                               actor_id=self.listitem.getProperty("id"))

        @ch.click(132)
        def open_text(self):
            xbmcgui.Dialog().textviewer(heading=LANG(32037),
                                        text=self.info["Plot"])

        @ch.click(6001)
        def set_rating_dialog(self):
            if TheMovieDB.set_rating_prompt(media_type="episode",
                                            media_id=[self.tvshow_id, self.info["season"], self.info["episode"]]):
                self.update_states()

        @ch.click(6006)
        def open_rating_list(self):
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = TheMovieDB.get_rated_media_items("tv/episodes")
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            wm.open_video_list(prev_window=self,
                               listitems=listitems)

        @ch.click(1150)
        def play_youtube_video(self):
            PLAYER.play_youtube_video(youtube_id=self.listitem.getProperty("youtube_id"),
                                      listitem=self.listitem,
                                      window=self)

        def update_states(self):
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            _, __, self.account_states = TheMovieDB.extended_episode_info(tvshow_id=self.tvshow_id,
                                                                          season=self.info["season"],
                                                                          episode=self.info["episode"],
                                                                          cache_time=0)
            super(DialogEpisodeInfo, self).update_states()

    return DialogEpisodeInfo
