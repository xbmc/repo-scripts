# -*- coding: utf-8 -*-
# Copyright (c) 2013 Paul Price, Artem Glebov

from kodi_six import xbmc
from resources.lib import common
from resources.lib import transmissionrpc
from six import iteritems
import sys


class SubstitutePlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.prev_settings = {}
        self.refreshSettings()

    def onAVStarted(self):
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
            for tid, torrent in iteritems(torrents):
                self.transmission.start(tid)

    def stopAllTorrents(self):
        if self.transmission:
            torrents = self.transmission.list()
            for tid, torrent in iteritems(torrents):
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

while not xbmc.Monitor().waitForAbort(1):
    del player
    sys.exit(0)
