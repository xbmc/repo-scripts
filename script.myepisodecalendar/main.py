#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc, xbmcaddon

mce_addon          = xbmcaddon.Addon()
# mce_addon_id       = mce_addon.getAddonInfo('id')
mce_addon_path     = mce_addon.getAddonInfo('path')
mce_addon_icon     = mce_addon.getAddonInfo('icon')
mce_addon_name     = mce_addon.getAddonInfo('name')
mce_addon_version  = mce_addon.getAddonInfo('version')
mce_lang           = mce_addon.getLocalizedString
mce_resource_path  = os.path.join(mce_addon_path, 'resources', 'lib')
mce_resource       = xbmc.translatePath(mce_resource_path).decode('utf-8')
# mce_datapath       = os.path.join(xbmc.translatePath('special://masterprofile/addon_data/').decode('utf-8'), mce_addon_id)

from resources.lib.myepisodecalendar import MyEpisodeCalendar

class Monitor(xbmc.Monitor):
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
        self.mye = self._loginMyEpisodeCalendar()
        if not self.mye.is_logged:
            return
        self.showid = self.episode = self.title = self.season = None
        self._totalTime = 999999
        self._lastPos = 0
        self._min_percent = int(mce_addon.getSetting('watched-percent'))
        self._tracker = None
        self._playbackLock = threading.Event()
        self._monitor = Monitor(action = self._reset)

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
        if hasattr(self, '_playbackLock'):
            self._playbackLock.clear()
        self._monitor = None
        if not hasattr(self, '_tracker'):
            return
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    @staticmethod
    def _loginMyEpisodeCalendar(silent=False):
        username = mce_addon.getSetting('Username')
        password = mce_addon.getSetting('Password')

        login_notif = mce_lang(32912)
        if username is "" or password is "":
            notif(login_notif, time=2500)
            return None

        showLoginNotif = True
        mye = MyEpisodeCalendar(username, password)
        if mye.is_logged:
            if mce_addon.getSetting('showNotif-login') != "true" or silent:
                showLoginNotif = False

            login_notif = "%s %s" % (username, mce_lang(32911))

        if showLoginNotif is True:
            notif(login_notif, time=2500)

        if mye.is_logged and (not mye.get_show_list()):
            notif(mce_lang(32927), time=2500)

        return mye

    def _mecReCheckAuth(self):
        if (not self.mye.is_logged):
            log("not logged in anymore")
            login_notif = mce_lang(32912)
            notif(login_notif, time=2500)
            return False
        return True

    def _addShow(self):
        # Add the show if it's not already in our account
        if self.showid in self.mye.shows.values():
            if mce_addon.getSetting('showNotif-found') == "true":
                notif(self.title, time=2000)
            return
        was_added = self.mye.add_show(self.showid)
        addedStringId = 32926

        showAddNotif = True
        if was_added:
            if mce_addon.getSetting('showNotif-autoadd') != "true":
                showAddNotif = False
            addedStringId = 32925

        log("show %s" % (mce_lang(addedStringId)))

        if showAddNotif is True:
            notif("%s %s" % (self.title, mce_lang(addedStringId)))

    def onPlayBackStarted(self):
        self._setUp()
        self._totalTime = self.getTotalTime()
        self._tracker.start()

        filename_full_path = self.getPlayingFile().decode('utf-8')

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

        if playlist.size() < 1:
            log('Playlist empty - this is probably a PVR channel. Abort.')
            self._tearDown()
            return

        currentPlaylistItemInfo = playlist[playlist.getposition()].getVideoInfoTag()

        mediaType = xbmc.getInfoLabel("ListItem.DBType") or currentPlaylistItemInfo.getMediaType()
        log('Player - MediaType: %s' % mediaType)

        # We don't want to take care of any URL because we can't really gain
        # information from it. We also only want to check TV episodes, so skip everything else.
        # (not explicitely checking for "episode", "season" or "tvshow", because sometimes it may return empty as well)
        if mediaType in ["movie", "musicvideo", "music", "song", "album", "artist"] or _is_excluded(filename_full_path):
            self._tearDown()
            return

        # Try to find the title with the help of XBMC (Theses came from
        # XBMC.Subtitles add-ons)
        # Falling back to currentPlaylistItemInfo, because getInfoLabel() seems to return empty values most of the time!
        self.season = str(xbmc.getInfoLabel("VideoPlayer.Season")) or currentPlaylistItemInfo.getSeason()
        log('Player - Season: %s' % self.season)
        self.episode = str(xbmc.getInfoLabel("VideoPlayer.Episode")) or currentPlaylistItemInfo.getEpisode()
        log('Player - Episode: %s' % self.episode)
        self.title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle") or currentPlaylistItemInfo.getTVShowTitle()
        log('Player - TVShow: %s' % self.title)
        if self.title == "":
            filename = os.path.basename(filename_full_path)
            log('Player - Filename: %s' % filename)
            self.title, self.season, self.episode = self.mye.get_info(filename)
            log('Player - TVShow: %s' % self.title)

        log("Title: %s - Season: %s - Ep: %s" % (self.title, self.season, self.episode))
        if not self.season and not self.episode:
            # It's not a show. If it should be recognised as one. Send a bug.
            self._tearDown()
            return

        self.title, self.showid = self.mye.find_show_id(self.title)
        if self.showid is None:
            notif("%s %s" % (self.title, mce_lang(32923)), time=3000)
            self._tearDown()
            return
        log('Player - Found : %s - %d (S%s E%s)' % (self.title,
                self.showid, self.season, self.episode))

        if mce_addon.getSetting('auto-add') == "true":
            self._addShow()

    def onPlayBackStopped(self):
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        self._tearDown()

        if self._totalTime == 0 or self._totalTime is None:
            log('could not get totalTime - assume finished')
            actual_percent = 100
        else: 
            actual_percent = (self._lastPos/self._totalTime)*100
            log('lastPos / totalTime : %s / %s = %s %%' % (self._lastPos,
                self._totalTime, actual_percent))
        if actual_percent < self._min_percent or self.showid is None or self.season is None or self.episode is None:
            return

        # Playback is finished, set the items to watched
        found = 32923
        showMarkedNotif = True
        if self.mye.set_episode_watched(self.showid, self.season, self.episode):
            if mce_addon.getSetting('showNotif-marked') != "true":
                showMarkedNotif = False
            found = 32924
        else:
            if (not self._mecReCheckAuth()):
                return False

        if showMarkedNotif is True:
            notif("%s (S%sE%s) %s" % (self.title, self.season.zfill(2), self.episode.zfill(2),
                mce_lang(found)))

def notif(msg, time=5000):
    notif_msg = "\"%s\", \"%s\", %i, %s" % ('MyEpisodeCalendar', msg.decode('utf-8', "replace"), time, mce_addon_icon)
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg.encode('utf-8'))

def log(msg):
    try:
        msg = msg.encode('utf-8')
    except:
        pass

    xbmc.log("### [%s] - %s" % (mce_addon_name, msg, ),
            level=xbmc.LOGDEBUG)

def _is_excluded(filename):
    log("_is_excluded(): Check if '%s' is a URL." % filename)
    excluded_protocols = ["pvr://", "http://", "https://"]
    return any(protocol in filename for protocol in excluded_protocols)


if ( __name__ == "__main__" ):
    monitor = xbmc.Monitor()
    player = Player()
    if not player.mye.is_logged:
        sys.exit(0)

    log( "[%s] - Version: %s Started" % (mce_addon_name, mce_addon_version))

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break

    player._tearDown()
    sys.exit(0)