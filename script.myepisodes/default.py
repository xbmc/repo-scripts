#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import xbmc
import xbmcaddon

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon_path__     = __addon__.getAddonInfo("icon")
__icon__          = xbmc.translatePath(__icon_path__).decode('utf-8')
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

from resources.lib.myepisodes import MyEpisodes

class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.action = kwargs['action']

    def onSettingsChanged(self):
        log('#DEBUG# onSettingsChanged')
        self.action()

class Player(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self)
        log('Player - init')
        self.mye = self._loginMyEpisodes()
        if not self.mye.is_logged:
            return
        self.showid = self.episode = self.title = self.season = None
        self._total_time = 999999
        self._last_pos = 0
        self._min_percent = int(__addon__.getSetting('watched-percent'))
        self._tracker = None
        self._playback_lock = threading.Event()
        self._monitor = Monitor(action=self._reset)

    def _reset(self):
        self._tearDown()
        if self.mye:
            del self.mye
        self.__init__()

    def _trackPosition(self):
        while self._playback_lock.isSet() and not xbmc.abortRequested:
            try:
                self._last_pos = self.getTime()
            except:
                self._playback_lock.clear()
            log('Inside Player. Tracker time = %s' % self._last_pos)
            xbmc.sleep(250)
        log('Position tracker ending with last_pos = %s' % self._last_pos)

    def _setUp(self):
        self._playback_lock.set()
        self._tracker = threading.Thread(target=self._trackPosition)
        self.mye.is_title_filename = False

    def _tearDown(self):
        if hasattr(self, '_playback_lock'):
            self._playback_lock.clear()
        self._monitor = None
        if not hasattr(self, '_tracker'):
            return
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    def _loginMyEpisodes(self):
        username = __addon__.getSetting('Username').decode('utf-8', 'replace')
        password = __addon__.getSetting('Password')

        login_notif = __language__(32912)
        if username is "" or password is "":
            notif(login_notif, time=2500)
            return None

        mye = MyEpisodes(username, password)
        if mye.is_logged:
            login_notif = "%s %s" % (username, __language__(32911))
        notif(login_notif, time=2500)

        if mye.is_logged and (not mye.get_show_list()):
            notif(__language__(32927), time=2500)
        return mye

    def _addShow(self):
        # Add the show if it's not already in our account
        if self.showid in self.mye.shows.values():
            notif(self.title, time=2000)
            return
        was_added = self.mye.add_show(self.showid)
        added = 32926
        if was_added:
            added = 32925
        notif("%s %s" % (self.title, __language__(added)))

    def onPlayBackStarted(self):
        self._setUp()
        self._total_time = self.getTotalTime()
        self._tracker.start()

        filename_full_path = self.getPlayingFile().decode('utf-8')
        # We don't want to take care of any URL because we can't really gain
        # information from it.
        if _is_excluded(filename_full_path):
            self._tearDown()
            return

        # Try to find the title with the help of XBMC (Theses came from
        # XBMC.Subtitles add-ons)
        self.season = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        log('Player - Season: %s' % self.season)
        self.episode = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
        log('Player - Episode: %s' % self.episode)
        self.title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
        log('Player - TVShow: %s' % self.title)
        if self.title == "":
            filename = os.path.basename(filename_full_path)
            log('Player - Filename: %s' % filename)
            self.title, self.season, self.episode = self.mye.get_info(filename)
            log('Player - TVShow: %s' % self.title)

        log("Title: %s - Season: %s - Ep: %s" % (self.title,
                                                 self.season,
                                                 self.episode))
        if not self.season and not self.episode:
            # It's not a show. If it should be recognised as one. Send a bug.
            self._tearDown()
            return

        self.showid = self.mye.find_show_id(self.title)
        if self.showid is None:
            notif("%s %s" % (self.title, __language__(32923)), time=3000)
            self._tearDown()
            return
        log('Player - Found : %s - %d (S%s E%s)' % (self.title,
                                                    self.showid,
                                                    self.season,
                                                    self.episode))

        if __addon__.getSetting('auto-add') == "true":
            self._addShow()

    def onPlayBackStopped(self):
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        self._tearDown()

        actual_percent = (self._last_pos/self._total_time)*100
        log('last_pos / total_time : %s / %s = %s %%' % (self._last_pos,
                                                         self._total_time,
                                                         actual_percent))
        if actual_percent < self._min_percent:
            return

        # Playback is finished, set the items to watched
        found = 32923
        if self.mye.set_episode_watched(self.showid, self.season, self.episode):
            found = 32924
        notif("%s (%s - %s) %s" % (self.title, self.season, self.episode,
                                   __language__(found)))

def notif(msg, time=5000):
    notif_msg = "%s, %s, %i, %s" % ('MyEpisodes', msg, time, __icon__)
    notif_msg = notif_msg.encode('utf-8', 'replace')
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg)

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg.encode('utf-8'), ),
             level=xbmc.LOGDEBUG)

def _is_excluded(filename):
    log("_is_excluded(): Check if '%s' is a URL." % filename)
    excluded_protocols = ["pvr://", "http://", "https://"]
    if any(protocol in filename for protocol in excluded_protocols):
        return True

    for setting_name in ["ExcludePath", "ExcludePath2", "ExcludePath3"]:
        exclude = __addon__.getSetting(setting_name)
        if exclude == "":
            continue
        excludepath = xbmc.translatePath(exclude).decode('utf-8')
        if excludepath in filename:
            log("_is_excluded(): Video is excluded (%s)." % setting_name)
            return True

if __name__ == "__main__":
    player = Player()
    if not player.mye.is_logged:
        sys.exit(0)

    log("[%s] - Version: %s Started" % (__scriptname__, __version__))

    while not xbmc.abortRequested:
        xbmc.sleep(100)

    player._tearDown()
    sys.exit(0)

