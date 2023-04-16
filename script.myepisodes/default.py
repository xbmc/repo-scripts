# -*- coding: utf-8 -*-

import os
import sys
import threading
import logging
from typing import Callable

import xbmc
import xbmcvfs
import xbmcaddon

import utils
import kodilogging

from myepisodes import MyEpisodes, SHOW_ID_ERR

_addon = xbmcaddon.Addon()
_kodiversion = float(xbmcaddon.Addon("xbmc.addon").getAddonInfo("version")[0:4])
_cwd = _addon.getAddonInfo("path")
_language = _addon.getLocalizedString
_resource_path = os.path.join(_cwd, "resources", "lib")
_resource = xbmcvfs.translatePath(_resource_path)

kodilogging.config()
logger = logging.getLogger(__name__)


class MEMonitor(xbmc.Monitor):
    def __init__(self, *args: int, **kwargs: Callable) -> None:
        xbmc.Monitor.__init__(self)
        self.action = kwargs["action"]

    def onSettingsChanged(self) -> None:
        logger.debug("User changed settings")
        self.action()


class MEProperties:
    def __init__(self) -> None:
        self.showid = self.episode = self.season = 0
        self.title = ""
        self.is_excluded = False
        self.total_time = sys.maxsize
        self.last_pos = 0


class MEPlayer(xbmc.Player):
    def __init__(self) -> None:
        xbmc.Player.__init__(self)
        logger.debug("MEPlayer - init")
        self._tracker = threading.Thread(target=self._track_position)
        self._reset()

    def _reset(self) -> None:
        logger.debug("_reset called")
        self.resetTracker()
        if hasattr(self, "mye"):
            del self.mye
        self.monitor = MEMonitor(action=self._reset)
        self.props = MEProperties()
        self._playback_lock = threading.Event()
        self.mye: MyEpisodes = MEPlayer.initMyEpisodes()
        if not self.mye.is_logged:
            return
        logger.debug("MyePlayer - account is logged successfully.")

    def resetTracker(self) -> None:
        if hasattr(self, "_playback_lock"):
            self._playback_lock.clear()
        if not hasattr(self, "_tracker"):
            return
        if self._tracker.is_alive():
            self._tracker.join()
        self._tracker = threading.Thread(target=self._track_position)

    @classmethod
    def initMyEpisodes(cls) -> MyEpisodes:
        username = utils.getSetting("Username")
        password = utils.getSetting("Password")

        login_notif = _language(32912)
        if not username or not password:
            utils.notif(login_notif, time=2500)
            return MyEpisodes("", "")

        mye = MyEpisodes(username, password)
        mye.login()
        if mye.is_logged:
            login_notif = f"{username} {_language(32911)}"
        utils.notif(login_notif, time=2500)

        if mye.is_logged and (not mye.populate_shows()):
            utils.notif(_language(32927), time=2500)
        return mye

    def _track_position(self) -> None:
        while self._playback_lock.is_set() and not self.monitor.abortRequested():
            try:
                self.props.last_pos = self.getTime()
            except:
                self._playback_lock.clear()
            logger.debug("Tracker time = %d", self.props.last_pos)
            xbmc.sleep(250)
        logger.debug("Tracker time (ended) = %d", self.props.last_pos)

    def _add_show(self) -> None:
        if not utils.getSettingAsBool("auto-add"):
            logger.debug("Auto-add function disabled.")
            return

        # Update the show dict to check if it has already been added somehow.
        self.mye.populate_shows()

        # Add the show if it's not already in our account
        if self.props.showid in list(self.mye.shows.values()):
            logger.debug("Show is already in the account.")
            return

        was_added = self.mye.add_show(self.props.showid)
        added = 32926
        if was_added:
            added = 32925
        utils.notif(f"{self.props.title} {_language(added)}")

    # For backward compatibility
    def onPlayBackStarted(self) -> None:
        if _kodiversion >= 17.9:
            return
        # This call is only for Krypton and below
        self.onAVStarted()

    # Only available in Leia (18) and up
    def onAVStarted(self) -> None:
        self._playback_lock.set()
        self.props.total_time = self.getTotalTime()
        self._tracker.start()

        filename_full_path = self.getPlayingFile()
        # We don't want to take care of any URL because we can't really gain
        # information from it.
        self.props.is_excluded = False
        if utils.is_excluded(filename_full_path):
            self.props.is_excluded = True
            self.resetTracker()
            return

        # Try to find the title with the help of Kodi (Theses came from
        # Kodi.Subtitles add-ons)
        try:
            self.props.season = int(xbmc.getInfoLabel("VideoPlayer.Season"))
        except ValueError:
            self.props.season = 0
        logger.debug("Player - Season: %02d", self.props.season)

        try:
            self.props.episode = int(xbmc.getInfoLabel("VideoPlayer.Episode"))
        except ValueError:
            self.props.episode = 0
        logger.debug("Player - Episode: %02d", self.props.episode)

        self.props.title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
        logger.debug("Player - TVShow: %s", self.props.title)

        if self.props.title == "":
            filename = os.path.basename(filename_full_path)
            logger.debug("Player - Filename: '%s'", filename)
            self.props.title, self.props.season, self.props.episode = self.mye.get_info(
                filename
            )
            logger.debug("Player - TVShow: '%s'", self.props.title)

        logger.debug(
            "Title: '%s' - Season: %02d - Ep: %02d ",
            self.props.title,
            self.props.season,
            self.props.episode,
        )
        if not self.props.season and not self.props.episode:
            # It's not a show. If it should be recognised as one. Send a bug.
            self.resetTracker()
            return

        self.props.showid = self.mye.find_show_id(self.props.title)
        if self.props.showid == SHOW_ID_ERR:
            utils.notif(f"{self.props.title} {_language(32923)}", time=3000)
            self.resetTracker()
            return
        logger.debug(
            "Player - Found : '%s' - %02d (S%02d E%02d",
            self.props.title,
            self.props.showid,
            self.props.season,
            self.props.episode,
        )

        utils.notif(self.props.title, time=2000)
        self._add_show()

    def onPlayBackStopped(self) -> None:
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self) -> None:
        self.resetTracker()

        logger.debug("onPlayBackEnded: is_exluded: %r", self.props.is_excluded)
        if self.props.is_excluded:
            return

        logger.debug(
            "last_pos / total_time : %d / %d",
            self.props.last_pos,
            self.props.total_time,
        )

        actual_percent = (self.props.last_pos / self.props.total_time) * 100
        logger.debug(
            "last_pos / total_time : %d / %d = %d%%",
            self.props.last_pos,
            self.props.total_time,
            actual_percent,
        )

        min_percent = min(utils.getSettingAsInt("watched-percent"), 95)
        logger.debug("min_percent: %d%%", min_percent)
        if actual_percent < min_percent:
            return

        # In case it was deleted or whatever happened during playback
        self._add_show()

        # Playback is finished, set the items to watched
        found = 32923
        if self.mye.set_episode_watched(
            self.props.showid, self.props.season, self.props.episode
        ):
            found = 32924
        utils.notif(
            f"{self.props.title} ({self.props.season:02} - {self.props.episode:02}) {_language(found)}"
        )


if __name__ == "__main__":
    player = MEPlayer()
    if not player.mye.is_logged:
        sys.exit(0)

    logger.debug(
        "[%s] - Version: %s Started",
        _addon.getAddonInfo("name"),
        _addon.getAddonInfo("version"),
    )

    while not player.monitor.abortRequested():
        if player.monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break

    player.resetTracker()
    sys.exit(0)
