# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import sys
import xbmc
import xbmcplugin
import xbmcgui
from resources.lib.process import start_info_actions
from resources.lib.Utils import *


class Main:

    def __init__(self):
        xbmc.log("version %s started" % ADDON_VERSION)
        HOME.setProperty("extendedinfo_running", "true")
        self._parse_argv()
        for info in self.infos:
            if info.endswith("shows"):
                xbmcplugin.setContent(self.handle, 'tvshows')
            elif info.endswith("episodes"):
                xbmcplugin.setContent(self.handle, 'episodes')
            elif info.endswith("movies"):
                xbmcplugin.setContent(self.handle, 'movies')
            elif info.endswith("lists"):
                xbmcplugin.setContent(self.handle, 'sets')
            else:
                xbmcplugin.setContent(self.handle, '')
            listitems = start_info_actions(info, self.params)
            pass_list_to_skin(name=info,
                              data=listitems,
                              prefix=self.params.get("prefix", ""),
                              handle=self.handle,
                              limit=self.params.get("limit", 20))
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_TITLE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_DURATION)
        else:
            movie = {"intheatermovies": "%s [I](RottenTomatoes)[/I]" % LANG(32042),
                     "boxofficemovies": "%s [I](RottenTomatoes)[/I]" % LANG(32055),
                     "openingmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32048),
                     "comingsoonmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32043),
                     "toprentalmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32056),
                     "currentdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32049),
                     "newdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32053),
                     "upcomingdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32054),
                     # tmdb
                     "incinemamovies": "%s [I](TheMovieDB)[/I]" % LANG(32042),
                     "upcomingmovies": "%s [I](TheMovieDB)[/I]" % LANG(32043),
                     "topratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32046),
                     "popularmovies": "%s [I](TheMovieDB)[/I]" % LANG(32044),
                     "accountlists": "%s [I](TheMovieDB)[/I]" % LANG(32045),
                     # trakt
                     "trendingmovies": "%s [I](Trakt.tv)[/I]" % LANG(32047),
                     # tmdb
                     "starredmovies": "%s [I](TheMovieDB)[/I]" % LANG(32134),
                     "ratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32135),
                     }
            tvshow = {"airingepisodes": "%s [I](Trakt.tv)[/I]" % LANG(32028),
                      "premiereepisodes": "%s [I](Trakt.tv)[/I]" % LANG(32029),
                      "trendingshows": "%s [I](Trakt.tv)[/I]" % LANG(32032),
                      "airingtodaytvshows": "%s [I](TheMovieDB)[/I]" % LANG(32038),
                      "onairtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32039),
                      "topratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32040),
                      "populartvshows": "%s [I](TheMovieDB)[/I]" % LANG(32041),
                      "starredtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32144),
                      "ratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32145),
                      }

            xbmcplugin.setContent(self.handle, '')
            items = merge_dicts(movie, tvshow)
            for key, value in items.iteritems():
                li = xbmcgui.ListItem(value, iconImage='DefaultFolder.png')
                url = 'plugin://script.extendedinfo?info=%s' % key
                xbmcplugin.addDirectoryItem(handle=self.handle, url=url,
                                            listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(self.handle)
        HOME.clearProperty("extendedinfo_running")

    def _parse_argv(self):
        args = sys.argv[2][1:]
        self.handle = int(sys.argv[1])
        self.infos = []
        self.params = {"handle": self.handle}
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
                except:
                    pass

if (__name__ == "__main__"):
    Main()
xbmc.log('finished')
