# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from WindowManager import wm
from Utils import *
import YDStreamExtractor


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

    def play(self, url, listitem, window=False):
        if window and window.window_type == "dialog":
            wm.add_to_stack(window)
            window.close()
        super(VideoPlayer, self).play(item=url,
                                      listitem=listitem,
                                      windowed=False,
                                      startpos=-1)
        if window and window.window_type == "dialog":
            self.wait_for_video_end()
            wm.pop_stack()

    def play_youtube_video(self, youtube_id="", listitem=None, window=False):
        """
        play youtube vid with info from *listitem
        """
        url, yt_listitem = self.youtube_info_by_id(youtube_id)
        if not listitem:
            listitem = yt_listitem
        if url:
            self.play(url=url,
                      listitem=listitem,
                      window=window)
        else:
            notify(header=LANG(257),
                   message="no youtube id found")

    @busy_dialog
    def youtube_info_by_id(self, youtube_id):
        vid = YDStreamExtractor.getVideoInfo(youtube_id,
                                             quality=1)
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
            xbmc.sleep(200)
        self.stopped = False

PLAYER = VideoPlayer()
