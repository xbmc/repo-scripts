# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import sys
import os

import xbmcplugin
import xbmcgui

from resources.lib import process

from kodi65 import addon
from kodi65 import utils
import routing

MOVIEDB_IMAGE = os.path.join(addon.MEDIA_PATH, "moviedb.png")
TRAKT_IMAGE = os.path.join(addon.MEDIA_PATH, "trakt.png")

plugin = routing.Plugin()


class Main:

    def __init__(self):
        utils.log("version %s started" % addon.VERSION)
        addon.set_global("extendedinfo_running", "true")
        self._parse_argv()
        for info in self.infos:
            listitems = process.start_info_actions(info, self.params)
            if listitems:
                listitems.set_plugin_list(plugin.handle)
            break
        else:
            plugin.run()
        addon.clear_global("extendedinfo_running")

    def _parse_argv(self):
        args = sys.argv[2][1:]
        self.infos = []
        self.params = {"handle": plugin.handle}
        if args.startswith("---"):
            delimiter = "&"
            args = args[3:]
        else:
            delimiter = "&&"
        for arg in args.split(delimiter):
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip().decode('utf-8')
                except Exception:
                    pass


@plugin.route('/tmdb')
def tmdb():
    xbmcplugin.setPluginCategory(plugin.handle, "TheMovieDB")
    items = [("incinemamovies", addon.LANG(32042)),
             ("upcomingmovies", addon.LANG(32043)),
             ("topratedmovies", addon.LANG(32046)),
             ("popularmovies", addon.LANG(32044)),
             ("ratedmovies", addon.LANG(32135)),
             ("airingtodaytvshows", addon.LANG(32038)),
             ("onairtvshows", addon.LANG(32039)),
             ("topratedtvshows", addon.LANG(32040)),
             ("populartvshows", addon.LANG(32041)),
             ("ratedtvshows", addon.LANG(32145)),
             ("ratedepisodes", addon.LANG(32093))]
    login = [("starredmovies", addon.LANG(32134)),
             ("starredtvshows", addon.LANG(32144)),
             ("accountlists", addon.LANG(32045))]
    if addon.setting("tmdb_username") and addon.setting("tmdb_password"):
        items += login
    for key, value in items:
        li = xbmcgui.ListItem(label=value,
                              thumbnailImage="DefaultFolder.png")
        url = 'plugin://script.extendedinfo?info=%s' % key
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/trakt')
def trakt():
    xbmcplugin.setPluginCategory(plugin.handle, "Trakt")
    items = [("trendingmovies", addon.LANG(32047)),
             ("traktpopularmovies", addon.LANG(32044)),
             ("mostplayedmovies", addon.LANG(32089)),
             ("mostwatchedmovies", addon.LANG(32090)),
             ("mostcollectedmovies", addon.LANG(32091)),
             ("mostanticipatedmovies", addon.LANG(32092)),
             ("traktboxofficemovies", addon.LANG(32055)),
             ("trendingshows", addon.LANG(32032)),
             ("popularshows", addon.LANG(32041)),
             ("anticipatedshows", addon.LANG(32085)),
             ("mostplayedshows", addon.LANG(32086)),
             ("mostcollectedshows", addon.LANG(32087)),
             ("mostwatchedshows", addon.LANG(32088)),
             ("airingepisodes", addon.LANG(32028)),
             ("premiereepisodes", addon.LANG(32029))]
    for key, value in items:
        li = xbmcgui.ListItem(label=value,
                              thumbnailImage="DefaultFolder.png")
        url = 'plugin://script.extendedinfo?info=%s' % key
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/')
def root():
    items = [
        (plugin.url_for(trakt), xbmcgui.ListItem(label="Trakt",
                                                 thumbnailImage=TRAKT_IMAGE), True),
        (plugin.url_for(tmdb), xbmcgui.ListItem(label="TheMovieDB",
                                                thumbnailImage=MOVIEDB_IMAGE), True),
    ]
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addDirectoryItems(plugin.handle, items)
    xbmcplugin.endOfDirectory(plugin.handle)


if (__name__ == "__main__"):
    Main()
utils.log('finished')
