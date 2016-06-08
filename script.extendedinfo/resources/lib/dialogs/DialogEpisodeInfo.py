# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc

from resources.lib import TheMovieDB as tmdb
from resources.lib.WindowManager import wm
from DialogVideoInfo import DialogVideoInfo

from kodi65 import imagetools
from kodi65 import busy
from kodi65 import addon
from kodi65 import ActionHandler

ID_BUTTON_RATED = 6006

ch = ActionHandler()


class DialogEpisodeInfo(DialogVideoInfo):
    TYPE = "Episode"
    TYPE_ALT = "episode"
    LISTS = [(1000, "actors"),
             (750, "crew"),
             (1150, "videos"),
             (1350, "images")]

    @busy.set_busy
    def __init__(self, *args, **kwargs):
        super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
        self.tvshow_id = kwargs.get('tvshow_id')
        tv_info = tmdb.get_tvshow(self.tvshow_id, light=True)
        data = tmdb.extended_episode_info(tvshow_id=self.tvshow_id,
                                          season=kwargs.get('season'),
                                          episode=kwargs.get('episode'))
        if not data:
            return None
        self.info, self.lists, self.states = data
        self.info.set_info("tvshowtitle", tv_info["name"])
        image_info = imagetools.blur(self.info.get_art("thumb"))
        self.info.update_properties(image_info)

    def onInit(self):
        super(DialogEpisodeInfo, self).onInit()
        search_str = '{} "Season {}" "Episode {}"'.format(self.info.get_info("tvshowtitle"),
                                                          self.info.get_info('season'),
                                                          self.info.get_info('episode'))
        self.get_youtube_vids(search_str)
        super(DialogEpisodeInfo, self).update_states()

    def onClick(self, control_id):
        super(DialogEpisodeInfo, self).onClick(control_id)
        ch.serve(control_id, self)

    @ch.click(ID_BUTTON_RATED)
    def open_rating_list(self, control_id):
        busy.show_busy()
        listitems = tmdb.get_rated_media_items("tv/episodes")
        busy.hide_busy()
        wm.open_video_list(listitems=listitems)

    def get_identifier(self):
        return [self.tvshow_id,
                self.info.get_info("season"),
                self.info.get_info("episode")]

    def update_states(self):
        xbmc.sleep(2000)  # delay because MovieDB takes some time to update
        info = tmdb.get_episode(tvshow_id=self.tvshow_id,
                                season=self.info.get_info("season"),
                                episode=self.info.get_info("episode"),
                                cache_days=0)
        self.states = info.get("account_states")
        super(DialogEpisodeInfo, self).update_states()

    def get_manage_options(self):
        return [(addon.LANG(1049), "Addon.OpenSettings(script.extendedinfo)")]
