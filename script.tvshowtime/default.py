#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc
import xbmcaddon
import unicodedata

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo("icon")
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

from resources.lib.tvshowtime import FindEpisode
from resources.lib.tvshowtime import MarkAsWatched
from resources.lib.tvshowtime import GetUserInformations

class Monitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']

    def onSettingsChanged( self ):
        log('#DEBUG# onSettingsChanged')
        Player()._reset()
        self.action()

class Player(xbmc.Player):

    def __init__ (self):
        xbmc.Player.__init__(self)
        log('Player - init')
        self.token = __addon__.getSetting('token')
        self.facebook = __addon__.getSetting('facebook')
        self.twitter = __addon__.getSetting('twitter')
        self.notifications = __addon__.getSetting('notifications')
        self.tvst = self._loginTVST()
        if not self.tvst.is_connected:
            return
        self.showid = self.episode = self.title = self.season = None
        self._totalTime = 999999
        self._lastPos = 0
        self._min_percent = int(__addon__.getSetting('watched-percent'))
        self._tracker = None
        self._playbackLock = threading.Event()
        self._monitor = Monitor(action = self._reset)
        
    def _reset(self):
        self._tearDown()
        self.__init__()
        
    def _trackPosition(self):
        while self._playbackLock.isSet() and not xbmc.abortRequested:
            try:
                self._lastPos = self.getTime()
            except:
                self._playbackLock.clear()
            if self._totalTime > 0:
                actual_percent = (self._lastPos/self._totalTime)*100
                log('#DEBUG# actual_percent=%s' % actual_percent)
                if (actual_percent >= self._min_percent):
                    log('#DEBUG# episode.is_found=%s' % self.episode.is_found)
                    if self.episode.is_found:        
                        checkin = MarkAsWatched(self.token, self.filename, __addon__.getSetting('facebook'), __addon__.getSetting('twitter'))
                        log('#DEBUG# checkin.is_marked:=%s' % checkin.is_marked)
                        if checkin.is_marked:
                            if self.notifications:
                                notif('%s %s S%sE%s' % (__language__(32906), self.episode.showname, formatNumber(self.episode.season_number), formatNumber(self.episode.number)), time=2500)
                        else:
                            if self.notifications:
                                notif(__language__(32907), time=2500)
            
                    self._tearDown()
            xbmc.sleep(250)

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
        #if self._tracker.isAlive():
        #    self._tracker.join()
        self._tracker = None

    def _loginTVST(self):
        log('#DEBUG# _loginTVST')
        if self.token is '':
            notif(__language__(32901), time=2500)
            return None
        tvst = GetUserInformations(self.token)
        log('#DEBUG# tvst.is_connected=%s' % tvst.is_connected)
        if tvst.is_connected:
            if self.notifications:
                notif('%s %s' % (__language__(32902), tvst.username), time=2500)
        else:
            notif(__language__(32903), time=2500)
            self._tearDown()
        return tvst

    def onPlayBackStarted(self):
        log('#DEBUG# onPlayBackStarted')
        self._setUp()
        self._totalTime = self.getTotalTime()
        self._tracker.start()
    	  
        filename_full_path = self.getPlayingFile().decode('utf-8')
    	  
        if _is_excluded(filename_full_path):
            self._tearDown()
            return
        	   
        self.filename = os.path.basename(filename_full_path)
        log('#DEBUG# episode=%s' % self.filename)
        self.episode = FindEpisode(self.token, self.filename)
        log('#DEBUG# episode.is_found=%s' % self.episode.is_found)
        if not self.episode.is_found:
            tvshowtitle = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
            season = str(xbmc.getInfoLabel("VideoPlayer.Season"))
            episode = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
            if len(tvshowtitle) > 0 and len(season) >0 and len(episode) > 0:
                self.filename = '%s.S%sE%s' % (formatName(tvshowtitle), season, episode)
                log('#DEBUG# episode=%s' % self.filename)
                self.episode = FindEpisode(self.token, self.filename)
                log('#DEBUG# episode.is_found=%s' % self.episode.is_found)
    
        if self.episode.is_found:
            if self.notifications:            
                notif('%s %s S%sE%s' % (__language__(32904), self.episode.showname, formatNumber(self.episode.season_number), formatNumber(self.episode.number)), time=2500)
        else:
            if self.notifications:
                notif(__language__(32905), time=2500)
            self._tearDown()
            return

    def onPlayBackStopped(self):
        log('#DEBUG# onPlayBackStopped')
        self.onPlayBackEnded()

    def onQueueNextItem(self):
        log('#DEBUG# onQueueNextItem')
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        log('#DEBUG# onPlayBackEnded')
        self._tearDown()

def formatNumber(number):
    if len(number) < 2:
         number = '0%s' % number
    return number
	 
def formatName(filename):
    filename = filename.strip()
    filename = filename.replace(' ', '.')
    return filename	 
    
def notif(msg, time=5000):
    notif_msg = "%s, %s, %i, %s" % ('TVShow Time', msg, time, __icon__)
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg.encode('utf-8'))

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg.encode('utf-8'), ),
            level=xbmc.LOGDEBUG)

def _is_excluded(filename):
    log("_is_excluded(): Check if '%s' is a URL." % filename)
    excluded_protocols = ["pvr://", "http://", "https://"]
    return any(protocol in filename for protocol in excluded_protocols)

if ( __name__ == "__main__" ):
    player = Player()
    log( "[%s] - Version: %s Started" % (__scriptname__, __version__))

    while not xbmc.abortRequested:
        xbmc.sleep(100)

    player._tearDown()
    sys.exit(0)

