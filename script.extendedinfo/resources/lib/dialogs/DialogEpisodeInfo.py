# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
from ..Utils import *
from ..TheMovieDB import *
from ..YouTube import *
from ..ImageTools import *
from DialogBaseInfo import DialogBaseInfo
from ..WindowManager import wm
from ..OnClickHandler import OnClickHandler
from .. import VideoPlayer

PLAYER = VideoPlayer.VideoPlayer()
ch = OnClickHandler()


def get_episode_window(window_type):

    class DialogEpisodeInfo(DialogBaseInfo, window_type):

        @busy_dialog
        def __init__(self, *args, **kwargs):
            super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
            self.type = "Episode"
            self.tvshow_id = kwargs.get('show_id')
            self.season = kwargs.get('season')
            self.episode_number = kwargs.get('episode')
            if not self.tvshow_id or not self.season or not self.episode_number:
                return None
            data = extended_episode_info(tvshow_id=self.tvshow_id,
                                         season=self.season,
                                         episode=self.episode_number)
            if data:
                self.info, self.data, self.account_states = data
            else:
                return None
            youtube_thread = GetYoutubeVidsThread(search_str="%s tv" % (self.info['title']))
            youtube_thread.start()  # TODO: rem threading here
            filter_thread = FilterImageThread(self.info.get("thumb", ""), 25)
            filter_thread.start()
            youtube_thread.join()
            filter_thread.join()
            self.info['ImageFilter'] = filter_thread.image
            self.info['ImageColor'] = filter_thread.imagecolor
            self.listitems = [(1000, self.data["actors"] + self.data["guest_stars"]),
                              (750, self.data["crew"]),
                              (1150, self.data["videos"]),
                              (1350, self.data["images"]),
                              (350, youtube_thread.listitems)]
            self.listitems = [(a, create_listitems(b)) for a, b in self.listitems]

        def onInit(self):
            super(DialogEpisodeInfo, self).onInit()
            pass_dict_to_skin(self.info, "movie.", False, False, self.window_id)
            self.fill_lists()
            super(DialogEpisodeInfo, self).update_states()

        @ch.click(750)
        @ch.click(1000)
        def open_actor_info(self):
            wm.open_actor_info(prev_window=self,
                               actor_id=self.listitem.getProperty("id"))

        @ch.click(132)
        def open_text(self):
            wm.open_textviewer(header=LANG(32037),
                               text=self.info["Plot"],
                               color=self.info['ImageColor'])

        @ch.click(6001)
        def set_rating_dialog(self):
            if set_rating_prompt(media_type="episode",
                                 media_id=[self.tvshow_id, self.season, self.info["episode"]]):
                self.update_states()

        @ch.click(6006)
        def open_rating_list(self):
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            listitems = get_rated_media_items("tv/episodes")
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            wm.open_video_list(prev_window=self,
                               listitems=listitems)

        def onClick(self, control_id):
            super(DialogEpisodeInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        def update_states(self):
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            _, __, self.account_states = extended_episode_info(tvshow_id=self.tvshow_id,
                                                               season=self.season,
                                                               episode=self.episode_number,
                                                               cache_time=0)
            super(DialogEpisodeInfo, self).update_states()

    return DialogEpisodeInfo
