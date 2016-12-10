# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui

from kodi65 import busy
from kodi65 import utils


class VideoPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        super(VideoPlayer, self).__init__()
        self.stopped = False

    def onPlayBackEnded(self):
        self.stopped = True

    def onPlayBackStopped(self):
        self.stopped = True

    def onPlayBackStarted(self):
        self.stopped = False

    @busy.set_busy
    def youtube_info_by_id(self, youtube_id):
        vid = utils.get_youtube_info(youtube_id)
        if not vid:
            return None, None
        listitem = xbmcgui.ListItem(label=vid.title,
                                    thumbnailImage=vid.thumbnail)
        listitem.setInfo(type='video',
                         infoLabels={"genre": vid.sourceName,
                                     "plot": vid.description})
        return vid.streamURL(), listitem

    def wait_for_video_end(self):
        xbmc.sleep(500)
        while not self.stopped:
            xbmc.sleep(100)
        self.stopped = False
