# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

"""Entry point when called as video plugin
"""

import os
import sys

import routing
import xbmcgui
import xbmcplugin
from resources.kutil131 import addon

from resources.kutil131 import utils
from resources.lib import process

MOVIEDB_IMAGE = os.path.join(addon.MEDIA_PATH, "moviedb.png")
TRAKT_IMAGE = os.path.join(addon.MEDIA_PATH, "trakt.png")

plugin = routing.Plugin()


class Main:
    """Handles plugin list / listitem creation
    """

    def __init__(self):
        """Constructor gets actions from args to create the
        plugin list
        """
        utils.log(f"plugin version {addon.VERSION} started")
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
        elif args.find("&---"):
            delimiter = "&"
        else:
            delimiter = "&&"
        for arg in args.split(delimiter):
            if arg.startswith("---"):
                arg = arg[3:]
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(
                        param.split("=")[1:]).strip()
                except Exception:
                    pass


@plugin.route('/tmdb')
def tmdb():
    """_sets category options for tmdb
    """
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
        li = xbmcgui.ListItem(label=value)
        li.setArt({'thumb': 'DefaultFolder.png'})
        url = f'plugin://script.extendedinfo?info={key}'
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/trakt')
def trakt():
    """sets category options form trakt
    """
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
        li = xbmcgui.ListItem(label=value)
        li.setArt({'thumb': 'DefaultFolder.png'})
        url = f'plugin://script.extendedinfo?info={key}'
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/')
def root():
    """Sets root plugin folder for TMDB and Trakt
    """
    traktitem = xbmcgui.ListItem(label="Trakt")
    traktitem.setArt({'thumb': TRAKT_IMAGE})
    tmdbitem = xbmcgui.ListItem(label="TheMovieDB")
    tmdbitem.setArt({'thumb': MOVIEDB_IMAGE})
    items = [
        (plugin.url_for(trakt), traktitem, True),
        (plugin.url_for(tmdb), tmdbitem, True),
    ]
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addDirectoryItems(plugin.handle, items)
    xbmcplugin.endOfDirectory(plugin.handle)


if (__name__ == "__main__"):
    Main()
utils.log('finished')
