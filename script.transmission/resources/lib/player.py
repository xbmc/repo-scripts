# -*- coding: utf-8 -*-
# Copyright (c) 2013 Paul Price, Artem Glebov

import os
import sys
import xbmc, xbmcaddon, xbmcgui
import transmissionrpc

__settings__ = xbmcaddon.Addon(id='script.transmission')

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

import common

class SubstitutePlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.prev_settings = {}
        self.refreshSettings()

    def onPlayBackStarted(self):
        self.refreshSettings()
        if self.active and xbmc.Player().isPlayingVideo():
            self.stopAllTorrents()

    def onPlayBackStopped(self):
        self.refreshSettings()
        if self.active:
            self.startAllTorrents()

    def startAllTorrents(self):
        if self.transmission:
            torrents = self.transmission.list()
            for tid, torrent in torrents.iteritems():
                self.transmission.start(tid)

    def stopAllTorrents(self):
        if self.transmission:
            torrents = self.transmission.list()
            for tid, torrent in torrents.iteritems():
                self.transmission.stop(tid)

    def refreshSettings(self):
        settings = common.get_settings()
        if settings != self.prev_settings:
            self.active = (settings['stop_all_on_playback'] == 'true')
            try:
                self.transmission = common.get_rpc_client()
            except:
                self.transmission = None
            self.prev_settings = settings

player = SubstitutePlayer()

while (not xbmc.abortRequested):
    xbmc.sleep(5000);
