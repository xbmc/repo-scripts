# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
import Utils
from .. import TheMovieDB as tmdb
from .. import ImageTools
from .. import addon
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from ActionHandler import ActionHandler
from ..VideoPlayer import PLAYER

ID_LIST_ACTORS = 1000
ID_LIST_CREW = 750
ID_LIST_VIDEOS = 1150
ID_LIST_BACKDROPS = 1350
ID_CONTROL_PLOT = 132
ID_CONTROL_SETRATING = 6001
ID_CONTROL_RATINGLISTS = 6006

ch = ActionHandler()


def get_window(window_type):

    class DialogEpisodeInfo(DialogBaseInfo, window_type):

        @Utils.busy_dialog
        def __init__(self, *args, **kwargs):
            super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
            self.type = "Episode"
            self.tvshow_id = kwargs.get('show_id')
            data = tmdb.extended_episode_info(tvshow_id=self.tvshow_id,
                                              season=kwargs.get('season'),
                                              episode=kwargs.get('episode'))
            if not data:
                return None
            self.info, self.data, self.account_states = data
            self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(self.info.get("thumb"))
            self.listitems = [(ID_LIST_ACTORS, self.data["actors"] + self.data["guest_stars"]),
                              (ID_LIST_CREW, self.data["crew"]),
                              (ID_LIST_VIDEOS, self.data["videos"]),
                              (ID_LIST_BACKDROPS, self.data["images"])]

        def onInit(self):
            super(DialogEpisodeInfo, self).onInit()
            Utils.pass_dict_to_skin(data=self.info,
                                    debug=False,
                                    precache=False,
                                    window_id=self.window_id)
            super(DialogEpisodeInfo, self).update_states()
            self.get_youtube_vids("%s tv" % (self.info['title']))
            self.fill_lists()

        def onClick(self, control_id):
            super(DialogEpisodeInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        @ch.click(ID_LIST_CREW)
        @ch.click(ID_LIST_ACTORS)
        def open_actor_info(self):
            wm.open_actor_info(prev_window=self,
                               actor_id=self.listitem.getProperty("id"))

        @ch.click(ID_CONTROL_PLOT)
        def open_text(self):
            xbmcgui.Dialog().textviewer(heading=addon.LANG(32037),
                                        text=self.info["Plot"])

        @ch.click(ID_CONTROL_SETRATING)
        def set_rating_dialog(self):
            if tmdb.set_rating_prompt(media_type="episode",
                                      media_id=[self.tvshow_id, self.info["season"], self.info["episode"]]):
                self.update_states()

        @ch.click(ID_CONTROL_RATINGLISTS)
        def open_rating_list(self):
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = tmdb.get_rated_media_items("tv/episodes")
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            wm.open_video_list(prev_window=self,
                               listitems=listitems)

        @ch.click(ID_LIST_VIDEOS)
        def play_youtube_video(self):
            PLAYER.play_youtube_video(youtube_id=self.listitem.getProperty("youtube_id"),
                                      listitem=self.listitem,
                                      window=self)

        def update_states(self):
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            _, __, self.account_states = tmdb.extended_episode_info(tvshow_id=self.tvshow_id,
                                                                    season=self.info["season"],
                                                                    episode=self.info["episode"],
                                                                    cache_time=0)
            super(DialogEpisodeInfo, self).update_states()

    return DialogEpisodeInfo
