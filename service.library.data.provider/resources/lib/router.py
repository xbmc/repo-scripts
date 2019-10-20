#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2017 BigNoid
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

import xbmcplugin
import xbmcgui
import xbmcaddon
import routing

ADDON_LANGUAGE = xbmcaddon.Addon().getLocalizedString


plugin = routing.Plugin()


def run():
    plugin.run()


@plugin.route('/')
def root():
    xbmcplugin.setPluginCategory(plugin.handle, "Media")
    items = [("randommovies", ADDON_LANGUAGE(32004), "DefaultMovies.png"),
             ("recentmovies", ADDON_LANGUAGE(32005), "DefaultRecentlyAddedMovies.png"),
             ("recommendedmovies", ADDON_LANGUAGE(32006), "DefaultMovieTitle.png"),
             ("randomepisodes", ADDON_LANGUAGE(32007), "DefaultTVShows.png"),
             ("recentepisodes", ADDON_LANGUAGE(32008), "DefaultRecentlyAddedEpisodes.png"),
             ("recommendedepisodes", ADDON_LANGUAGE(32010), "DefaultTVShowTitle.png"),
             ("favouriteepisodes", ADDON_LANGUAGE(32020), "DefaultTVShows.png"),
             ("recentvideos", ADDON_LANGUAGE(32019), "DefaultVideo.png"),
             ("randommusicvideos", ADDON_LANGUAGE(32022), "DefaultMusicVideos.png"),
             ("recentmusicvideos", ADDON_LANGUAGE(32023), "DefaultRecentlyAddedMusicVideos.png")]
    for call, title, thumb in items:
        liz = xbmcgui.ListItem(label=title,
                               thumbnailImage=thumb)
        url = 'plugin://service.library.data.provider?type=%s' % call
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=liz,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(plugin.handle)
