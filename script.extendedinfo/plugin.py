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
        xbmc.executebuiltin('SetProperty(extendedinfo_running,True,home)')
        self._parse_argv()
        if self.infos:
            start_info_actions(self.infos, self.params)
        else:
            movie = {"intheaters": "%s [I](RottenTomatoes)[/I]" % LANG(32042),
                     "boxoffice": "%s [I](RottenTomatoes)[/I]" % LANG(32055),
                     "opening": "%s [I](RottenTomatoes)[/I]" % LANG(32048),
                     "comingsoon": "%s [I](RottenTomatoes)[/I]" % LANG(32043),
                     "toprentals": "%s [I](RottenTomatoes)[/I]" % LANG(32056),
                     "currentdvdreleases": "%s [I](RottenTomatoes)[/I]" % LANG(32049),
                     "newdvdreleases": "%s [I](RottenTomatoes)[/I]" % LANG(32053),
                     "upcomingdvds": "%s [I](RottenTomatoes)[/I]" % LANG(32054),
                     # tmdb
                     "incinemas": "%s [I](TheMovieDB)[/I]" % LANG(32042),
                     "upcoming": "%s [I](TheMovieDB)[/I]" % LANG(32043),
                     "topratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32046),
                     "popularmovies": "%s [I](TheMovieDB)[/I]" % LANG(32044),
                     "accountlists": "%s [I](TheMovieDB)[/I]" % LANG(32045),
                     # trakt
                     "trendingmovies": "%s [I](Trakt.tv)[/I]" % LANG(32047),
                     # tmdb
                     "starredmovies": "%s [I](TheMovieDB)[/I]" % LANG(32134),
                     "ratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32135),
                     }
            tvshow = {"airingshows": "%s [I](Trakt.tv)[/I]" % LANG(32028),
                      "premiereshows": "%s [I](Trakt.tv)[/I]" % LANG(32029),
                      "trendingshows": "%s [I](Trakt.tv)[/I]" % LANG(32032),
                      "airingtodaytvshows": "%s [I](TheMovieDB)[/I]" % LANG(32038),
                      "onairtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32039),
                      "topratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32040),
                      "populartvshows": "%s [I](TheMovieDB)[/I]" % LANG(32041),
                      "starredtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32144),
                      "ratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32145),
                      }

            xbmcplugin.setContent(self.handle, 'files')

            # url = 'plugin://script.extendedinfo?info=extendedinfo&&id=233'
            # li = xbmcgui.ListItem('TheMovieDB database browser', iconImage='DefaultMovies.png')
            # xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=li)
            items = merge_dicts(movie, tvshow)
            for key, value in items.iteritems():
                li = xbmcgui.ListItem(value, iconImage='DefaultFolder.png')
                url = 'plugin://script.extendedinfo?info=%s' % key
                xbmcplugin.addDirectoryItem(handle=self.handle, url=url,
                                            listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(self.handle)
        xbmc.executebuiltin('ClearProperty(extendedinfo_running,home)')

    def _parse_argv(self):
        args = sys.argv[2][1:]
        self.handle = int(sys.argv[1])
        self.control = "plugin"
        self.infos = []
        self.params = {"handle": self.handle,
                       "control": self.control}
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
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip()
                except:
                    pass

if (__name__ == "__main__"):
    Main()
xbmc.log('finished')
