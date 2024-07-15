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
        self.started = False

    def onPlayBackStopped(self):
        self.stopped = True
        self.started = False

    def onPlayBackError(self):
        self.stopped = True
        self.started = False

    def onAVStarted(self):
        self.started = True
        self.stopped = False

    def onPlayBackStarted(self):
        self.started = True
        self.stopped = False

    @busy.set_busy
    def youtube_info_by_id(self, youtube_id) -> None:
        """function uses inop YTStreamextractor

        Args:
            youtube_id (_type_): _description_

        Returns:
            _type_: function retained for future use
        """
        #vid = utils.get_youtube_info(youtube_id)
        vid = {}
        if not vid:
            return None, None
        #listitem = xbmcgui.ListItem(label=vid.title)
        #listitem.setArt({'thumb': vid.thumbnail})
        #listitem.setInfo(type='video',
        #                 infoLabels={"genre": vid.sourceName,
        #                             "plot": vid.description})
        #return vid.streamURL(), listitem

    def wait_for_video_end(self):
        monitor: xbmc.Monitor = xbmc.Monitor()
        while not monitor.waitForAbort(1.0):
            if monitor.abortRequested():
                break
            if self.stopped:
                break
        self.stopped = False

    def wait_for_video_start(self):
        """Timer that checks if Youtube can play selected listitem
        Hard coded to 15 sec
        """
        monitor = xbmc.Monitor()
        timeout = 15
        while not monitor.waitForAbort(1.5):  #wait to see if video starts
            if monitor.abortRequested():
                break
            timeout += -1
            if self.started:
                break
            if timeout == 0:
                self.stopped = True
                break

    def wait_for_kodivideo_start(self):
        """Timer called from dialogmovieinfo that checks if Kodi can play selected listitem
        Sets a 20 sec timer to attempt play local db media.  If
        timer ends videoplayer self.stopped is set
        """
        monitor = xbmc.Monitor()
        timeout = 20
        while not monitor.waitForAbort(1):  #wait to see if video starts
            if monitor.abortRequested():
                break
            timeout += -1
            if self.started:
                break
            if timeout == 0:
                self.stopped = True
                break
