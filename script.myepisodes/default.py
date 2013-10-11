#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import xbmc
import xbmcaddon

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo("icon")
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

from resources.lib.myepisodes import MyEpisodes

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']

    def onSettingsChanged( self ):
        log('#DEBUG# onSettingsChanged')
        self.action()

class Player(xbmc.Player):

    def __init__ (self):
        xbmc.Player.__init__(self)
        log('Player - init')
        self.mye = self._loginMyEpisodes()
        if self.mye is None:
            return None
        self.showid = self.episode = self.title = self.season = None
        self._totalTime = 999999
        self._lastPos = 0
        self._min_percent = int(__addon__.getSetting('watched-percent'))
        self._tracker = None
        self._playbackLock = threading.Event()
        self.Monitor = MyMonitor(action = self._reset)

    def _reset(self):
        self._tearDown()
        if self.mye:
            del self.mye
        self.__init__()

    def _trackPosition(self):
        while self._playbackLock.isSet() and not xbmc.abortRequested:
            try:
                self._lastPos = self.getTime()
            except:
                self._playbackLock.clear()
            log('Inside Player. Tracker time = %s' % self._lastPos)
            xbmc.sleep(250)
        log('Position tracker ending with lastPos = %s' % self._lastPos)

    def _setUp(self):
        self._playbackLock.set()
        self._tracker = threading.Thread(target=self._trackPosition)

    def _tearDown(self):
        if self._playbackLock:
            self._playbackLock.clear()
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    def _loginMyEpisodes(self):
        username = __addon__.getSetting('Username')
        password = __addon__.getSetting('Password')

        login_notif = __language__(30912)
        if username is "" or password is "":
            notif(login_notif, time=2500)
            return None

        mye = MyEpisodes(username, password)
        is_logged = mye.login()
        if is_logged:
            login_notif = "%s %s" % (username, __language__(30911))
        notif(login_notif, time=2500)

        if is_logged and (not mye.get_show_list()):
            notif(__language__(30927), time=2500)
        return mye

    def _addShow(self):
        # Add the show if it's not already in our account
        if self.showid in self.mye.shows:
            notif(self.title, time=2000)
            return
        was_added = self.mye.add_show(self.showid)
        added = 30926
        if was_added:
            added = 30925
        notif("%s %s" % (self.title, __language__(added)))

    def onPlayBackStarted(self):
        self._setUp()
        self.title = self.getPlayingFile().decode('utf-8')
        self.title = os.path.basename(self.title)
        log('Player - Title : %s' % self.title)
        self._totalTime = self.getTotalTime()
        self._tracker.start()

        self.title, self.season, self.episode = self.mye.get_info(self.title)
        log("Title: %s - Season: %02d - Ep: %02d" % (self.title, self.season, self.episode))
        if (self.season is None) and (self.episode is None):
            # It's not a show. If it should be recognised as one. Send a bug.
            self._tearDown()
            return

        self.showid = self.mye.find_show_id(self.title)
        if self.showid is None:
            notif("%s %s" % (self.title, __language__(30923)), time=3000)
            self._tearDown()
            return
            log('Player - Found : %s - %d (S%02d E%02d)' % (self.title,
                self.showid, self.season, self.episode))
        self._addShow()

    def onPlayBackStopped(self):
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        self._tearDown()

        actual_percent = (self._lastPos/self._totalTime)*100
        log('lastPos / totalTime : %s / %s = %s %%' % (self._lastPos,
            self._totalTime, actual_percent))
        if (actual_percent < self._min_percent):
            return

        # Playback is finished, set the items to watched
        found = 30923
        if self.mye.set_episode_watched(self.showid, self.season, self.episode):
            found = 30924
        notif("%s (%02d - %02d) %s" % (self.title, self.season, self.episode,
            __language__(found)))

def notif(msg, time=5000):
    notif_msg = "%s, %s, %i, %s" % ('MyEpisodes', msg, time, __icon__)
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg)

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg, ), level=xbmc.LOGDEBUG)

if ( __name__ == "__main__" ):
    player = Player()
    if player is None:
        sys.exit(0)

    log( "[%s] - Version: %s Started" % (__scriptname__, __version__))

    while not xbmc.abortRequested:
        xbmc.sleep(100)

    player._tearDown()
    sys.exit(0)

