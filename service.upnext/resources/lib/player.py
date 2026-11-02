# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from xbmc import getCondVisibility, Player, PlayList, Monitor
from api import Api
from state import State
from utils import get_setting_bool


class UpNextPlayer(Player):
    """Service class for playback monitoring"""
    last_file = None
    track = False

    def __init__(self):
        self.api = Api()
        self.state = State()
        self.monitor = Monitor()
        Player.__init__(self)

    def set_last_file(self, filename):
        self.state.last_file = filename

    def get_last_file(self):
        return self.state.last_file

    def is_tracking(self):
        return self.state.track

    def disable_tracking(self):
        self.state.track = False

    def enable_tracking(self):
        self.state.track = True

    def reset_queue(self):
        if self.state.queued:
            self.api.reset_queue()
            self.state.queued = False

    def is_trackable(self):
        """Return True for a library episode, or for any video with a next item in a playlist Up Next follows"""
        if getCondVisibility('videoplayer.content(episodes)'):
            return True
        # Non-library videos (files played from a folder, "Play from here") only have a playlist to go on
        if not get_setting_bool('enablePlaylist') or not self.isPlayingVideo():
            return False
        playlist = PlayList(self.api.get_playlistid(playlistid_cache=[None]))
        return 0 <= playlist.getposition() < playlist.size() - 1

    def _check_video(self):
        self.monitor.waitForAbort(5)
        if not self.is_trackable():
            return
        self.state.track = True

    if callable(getattr(Player, 'onAVStarted', None)):
        def onAVStarted(self):  # pylint: disable=invalid-name
            """Will be called when Kodi has a video or audiostream"""
            self._check_video()

        def onPlayBackStarted(self):  # pylint: disable=invalid-name
            """Will be called when kodi starts playing a file"""
            self.reset_queue()
    else:
        def onPlayBackStarted(self):  # pylint: disable=invalid-name
            """Will be called when kodi starts playing a file"""
            self.reset_queue()
            self._check_video()

    def onPlayBackPaused(self):  # pylint: disable=invalid-name
        self.state.pause = True

    def onPlayBackResumed(self):  # pylint: disable=invalid-name
        self.state.pause = False
        if self.api.has_addon_data() or self.is_trackable():
            self.enable_tracking()

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        """Will be called when user stops playing a file"""
        self.reset_queue()
        self.api.reset_addon_data()
        self.state = State()  # Reset state

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        """Will be called when Kodi has ended playing a file"""
        self.reset_queue()
        # Only reset state if not playing the next episode
        if not self.state.playing_next:
            self.api.reset_addon_data()
            self.state = State()  # Reset state

    def onPlayBackError(self):  # pylint: disable=invalid-name
        """Will be called when when playback stops due to an error"""
        self.reset_queue()
        self.api.reset_addon_data()
        self.state = State()  # Reset state
