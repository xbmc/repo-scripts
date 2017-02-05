#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    kodi_monitor.py
    monitor kodi events to auto refresh widgets
'''

from utils import log_msg
import xbmc
import time
import json


class KodiMonitor(xbmc.Monitor):
    '''Monitor all events in Kodi'''
    update_widgets_busy = False

    def __init__(self, **kwargs):
        xbmc.Monitor.__init__(self)
        self.win = kwargs.get("win")

    def onDatabaseUpdated(self, database):
        '''builtin function for the xbmc.Monitor class'''
        log_msg("Kodi_Monitor: %s database updated" % database)
        if database == "music":
            self.refresh_music_widgets("")
        else:
            self.refresh_video_widgets("")

    def onNotification(self, sender, method, data):
        '''builtin function for the xbmc.Monitor class'''
        try:
            log_msg("Kodi_Monitor: sender %s - method: %s  - data: %s" % (sender, method, data))
            data = json.loads(data.decode('utf-8'))
            mediatype = ""
            if data and isinstance(data, dict):
                if data.get("item"):
                    mediatype = data["item"].get("type", "")
                elif data.get("type"):
                    mediatype = data["type"]

            if method == "VideoLibrary.OnUpdate":
                self.refresh_video_widgets(mediatype)

            if method == "AudioLibrary.OnUpdate":
                self.refresh_music_widgets(mediatype)

            if method == "Player.OnStop":
                if mediatype in ["movie", "episode", "musicvideo"]:
                    self.refresh_video_widgets(mediatype)

        except Exception as exc:
            log_msg("Exception in KodiMonitor: %s" % exc, xbmc.LOGERROR)

    def refresh_music_widgets(self, media_type):
        '''refresh music widgets'''
        log_msg("Music database changed - type: %s - refreshing widgets...." % media_type)
        timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        self.win.setProperty("widgetreload-music", timestr)
        self.win.setProperty("widgetreloadmusic", timestr)
        if media_type:
            self.win.setProperty("widgetreload-%ss" % media_type, timestr)

    def refresh_video_widgets(self, media_type):
        '''refresh video widgets'''
        log_msg("Video database changed - type: %s - refreshing widgets...." % media_type)
        timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        self.win.setProperty("widgetreload", timestr)
        if media_type:
            self.win.setProperty("widgetreload-%ss" % media_type, timestr)
            if "episode" in media_type:
                self.win.setProperty("widgetreload-tvshows", timestr)
