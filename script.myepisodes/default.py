# -*- coding: utf-8 -*-

import os
import sys
import threading
import logging

import xbmc
import xbmcaddon

import utils
import kodilogging

from myepisodes import MyEpisodes

_addon = xbmcaddon.Addon()
_cwd = _addon.getAddonInfo('path')
_language = _addon.getLocalizedString
_resource_path = os.path.join(_cwd, 'resources', 'lib')
_resource = xbmc.translatePath(_resource_path).decode('utf-8')

kodilogging.config()
logger = logging.getLogger(__name__)

class MyeMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.action = kwargs['action']

    def onSettingsChanged(self):
        logger.debug('User changed settings')
        self.action()

def _initMyEpisodes():
    username = _addon.getSetting('Username').decode('utf-8', 'replace')
    password = _addon.getSetting('Password')

    login_notif = _language(32912)
    if not username or not password:
        utils.notif(login_notif, time=2500)
        return None

    mye = MyEpisodes(username, password)
    mye.login()
    if mye.is_logged:
        login_notif = "%s %s" % (username, _language(32911))
    utils.notif(login_notif, time=2500)

    if mye.is_logged and (not mye.populate_shows()):
        utils.notif(_language(32927), time=2500)
    return mye


class MyePlayer(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self)
        logger.debug('MyePlayer - init')

        self.mye = _initMyEpisodes()
        if not self.mye.is_logged:
            return

        logger.debug('MyePlayer - account is logged successfully.')

        self.showid = self.episode = self.title = self.season = None
        self.is_excluded = False
        self._total_time = sys.maxsize
        self._last_pos = 0
        self._min_percent = int(_addon.getSetting('watched-percent'))
        self._tracker = None
        self._playback_lock = threading.Event()
        self.monitor = MyeMonitor(action=self._reset)

    def _reset(self):
        logger.debug('_reset called')
        self.tearDown()
        if self.mye:
            del self.mye
        self.__init__()

    def _trackPosition(self):
        while self._playback_lock.isSet() and not self.monitor.abortRequested():
            try:
                self._last_pos = self.getTime()
            except:
                self._playback_lock.clear()
            logger.debug('Tracker time = %f', self._last_pos)
            xbmc.sleep(250)
        logger.debug('Tracker time (ended) = %f', self._last_pos)

    def setUp(self):
        self._playback_lock.set()
        self._tracker = threading.Thread(target=self._trackPosition)

    def tearDown(self):
        if hasattr(self, '_playback_lock'):
            self._playback_lock.clear()
        if not hasattr(self, '_tracker'):
            return
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    def _addShow(self):

        if _addon.getSetting('auto-add') != "true":
            logger.debug('Auto-add function disabled.')
            return

        # Update the show dict to check if it has already been added somehow.
        self.mye.populate_shows()

        # Add the show if it's not already in our account
        if self.showid in self.mye.shows.values():
            logger.debug('Show is already in the account.')
            return

        was_added = self.mye.add_show(self.showid)
        added = 32926
        if was_added:
            added = 32925
        utils.notif("%s %s" % (self.title, _language(added)))

    def onPlayBackStarted(self):
        self.setUp()
        self._total_time = self.getTotalTime()
        self._tracker.start()

        filename_full_path = self.getPlayingFile().decode('utf-8')
        # We don't want to take care of any URL because we can't really gain
        # information from it.
        self.is_excluded = False
        if utils.is_excluded(filename_full_path):
            self.is_excluded = True
            self.tearDown()
            return

        # Try to find the title with the help of XBMC (Theses came from
        # XBMC.Subtitles add-ons)
        self.season = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        logger.debug('Player - Season: %s', self.season)
        self.episode = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
        logger.debug('Player - Episode: %s', self.episode)
        self.title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
        logger.debug('Player - TVShow: %s', self.title)
        if self.title == "":
            filename = os.path.basename(filename_full_path)
            logger.debug('Player - Filename: %s', filename)
            self.title, self.season, self.episode = self.mye.get_info(filename)
            logger.debug('Player - TVShow: %s', self.title)

        logger.debug("Title: %s - Season: %s - Ep: %s",
                     self.title, self.season, self.episode)
        if not self.season and not self.episode:
            # It's not a show. If it should be recognised as one. Send a bug.
            self.tearDown()
            return

        self.showid = self.mye.find_show_id(self.title)
        if self.showid is None:
            utils.notif("%s %s" % (self.title, _language(32923)), time=3000)
            self.tearDown()
            return
        logger.debug('Player - Found : %s - %d (S%s E%s)',
                     self.title, self.showid, self.season, self.episode)

        utils.notif(self.title, time=2000)
        self._addShow()

    def onPlayBackStopped(self):
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        self.tearDown()

        logger.debug('onPlayBackEnded: is_exluded: %s', self.is_excluded)
        if self.is_excluded:
            return

        actual_percent = (self._last_pos/self._total_time)*100
        logger.debug('last_pos / total_time : %s / %s = %s %%',
                     self._last_pos, self._total_time, actual_percent)
        if actual_percent < self._min_percent:
            return

        # In case it was deleted or whatever happened during playback
        self._addShow()

        # Playback is finished, set the items to watched
        found = 32923
        if self.mye.set_episode_watched(self.showid, self.season, self.episode):
            found = 32924
        utils.notif("{0.title} ({0.season} - {0.episode}) {1}".format(self, _language(found)))

if __name__ == "__main__":
    player = MyePlayer()
    if not player.mye.is_logged:
        sys.exit(0)

    logger.debug("[%s] - Version: %s Started", _addon.getAddonInfo('name'),
                 _addon.getAddonInfo('version'))

    while not player.monitor.abortRequested():
        if player.monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break

    player.tearDown()
    sys.exit(0)
