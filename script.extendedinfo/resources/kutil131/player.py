# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui

from resources.kutil131 import busy, utils


class VideoPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.stopped = False
        self.started = False

    def onPlayBackEnded(self):
        self.stopped = True

    def onPlayBackStopped(self):
        self.stopped = True

    def onPlayBackError(self):
        self.stopped = True

    def onAVStarted(self):
        self.started = True
        self.stopped = False

    @busy.set_busy
    def youtube_info_by_id(self, youtube_id):
        vid = utils.get_youtube_info(youtube_id)
        if not vid:
            return None, None
        listitem = xbmcgui.ListItem(label=vid.title)
        listitem.setArt({'thumb': vid.thumbnail})
        listitem.setInfo(type='video',
                         infoLabels={"genre": vid.sourceName,
                                     "plot": vid.description})
        return vid.streamURL(), listitem

    def wait_for_video_end(self):
        monitor: xbmc.Monitor = xbmc.Monitor()
        while not monitor.waitForAbort(1.0):
            if self.stopped:
                break

        self.stopped = False

    def wait_for_video_start(self):
        """Timer that checks if Youtube can play selected listitem
        Hard coded to 15 sec
        """
        monitor = xbmc.Monitor()
        timeout = 15
        while not monitor.waitForAbort(1.0):  #wait 10 sec to see if video starts
            if monitor.abortRequested():
                break
            timeout += -1
            if self.stopped or self.started:
                break
            if timeout == 0:
                self.stopped = True
                break
