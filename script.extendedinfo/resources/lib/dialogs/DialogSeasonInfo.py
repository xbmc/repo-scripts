# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from resources.lib import TheMovieDB as tmdb
from DialogVideoInfo import DialogVideoInfo

from kodi65 import imagetools
from kodi65 import utils
from kodi65 import addon
from kodi65 import ActionHandler

ch = ActionHandler()


class DialogSeasonInfo(DialogVideoInfo):
    TYPE = "Season"
    LISTS = [(1000, "actors"),
             (750, "crew"),
             (2000, "episodes"),
             (1150, "videos"),
             (1250, "images"),
             (1350, "backdrops")]

    def __init__(self, *args, **kwargs):
        super(DialogSeasonInfo, self).__init__(*args, **kwargs)
        self.tvshow_id = kwargs.get('id')
        data = tmdb.extended_season_info(tvshow_id=self.tvshow_id,
                                         season_number=kwargs.get('season'))
        if not data:
            return None
        self.info, self.lists = data
        if not self.info.get_info("dbid"):  # need to add comparing for seasons
            poster = utils.get_file(url=self.info.get_art("poster"))
            self.info.set_art("poster", poster)
        self.info.update_properties(imagetools.blur(self.info.get_art("poster")))

    def onInit(self):
        self.get_youtube_vids("%s %s tv" % (self.info.get_info("tvshowtitle"), self.info.get_info('title')))
        super(DialogSeasonInfo, self).onInit()

    def onClick(self, control_id):
        super(DialogSeasonInfo, self).onClick(control_id)
        ch.serve(control_id, self)

    def get_manage_options(self):
        return [(addon.LANG(1049), "Addon.OpenSettings(script.extendedinfo)")]
