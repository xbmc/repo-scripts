#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from resources.lib import data
from resources.lib import router

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString


def log(txt):
    message = '%s: %s' % (ADDON_NAME, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


class Main:

    def __init__(self):
        self._init_vars()
        self._parse_argv()
        if not self.TYPE:
            router.run()
        for content_type in self.TYPE.split("+"):
            full_liz = list()
            if content_type == "randommovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                data.parse_movies('randommovies', 32004, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentmovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                data.parse_movies('recentmovies', 32005, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedmovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                data.parse_movies('recommendedmovies', 32006, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_tvshows_recommended('recommendedepisodes', 32010, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "favouriteepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_tvshows_favourite('favouriteepisodes', 32020, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_tvshows('recentepisodes', 32008, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_tvshows('randomepisodes', 32007, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'videos')
                listA = []
                listB = []
                dateListA = []
                dateListB = []
                data.parse_movies('recentmovies', 32005, listA, self.USECACHE, self.PLOT_ENABLE, self.LIMIT, dateListA, "dateadded")
                data.parse_tvshows('recentepisodes', 32008, listB, self.USECACHE, self.PLOT_ENABLE, self.LIMIT, dateListB, "dateadded")
                full_liz = data._combine_by_date(listA, dateListA, listB, dateListB, self.LIMIT, self.SETTINGSLIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                data.parse_albums('randomalbums', 32016, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                data.parse_albums('recentalbums', 32017, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                data.parse_albums('recommendedalbums', 32018, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomsongs":
                xbmcplugin.setContent(int(sys.argv[1]), 'songs')
                data.parse_song('randomsongs', 32015, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randommusicvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
                data.parse_musicvideos('randommusicvideos', 32022, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentmusicvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
                data.parse_musicvideos('recentmusicvideos', 32023, full_liz, self.USECACHE, self.PLOT_ENABLE, self.LIMIT)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "movie":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                data.parse_dbid('movie', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "episode":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_dbid('episode', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "song":
                xbmcplugin.setContent(int(sys.argv[1]), 'songs')
                data.parse_dbid('song', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == 'playliststats':
                data.get_playlist_stats(self.path)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == 'actors':
                data.get_actors(self.dbid, self.dbtype, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)

            # Play an albums
            elif content_type == "play_album":
                data.play_album(self.ALBUM)
                return
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.SETTINGSLIMIT = int(ADDON.getSetting("limit"))
        self.PLOT_ENABLE = ADDON.getSetting("plot_enable") == 'true'
        self.RANDOMITEMS_UNPLAYED = ADDON.getSetting("randomitems_unplayed") == 'true'

    def _parse_argv(self):
        try:
            params = dict(arg.split("=") for arg in sys.argv[2].split("&"))
        except:
            params = {}
        self.TYPE = params.get("?type", "")
        self.ALBUM = params.get("album", "")
        self.USECACHE = params.get("reload", False)
        self.path = params.get("id", "")
        if self.USECACHE is not False:
            self.USECACHE = True
        self.LIMIT = int(params.get("limit", "-1"))
        self.dbid = params.get("dbid", "")
        self.dbtype = params.get("dbtype", False)


log('script version %s started' % ADDON_VERSION)
Main()
log('script version %s stopped' % ADDON_VERSION)
