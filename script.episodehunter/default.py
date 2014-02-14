""" Default menu """

import xbmcgui
import xbmcaddon

from resources.lib import helper
import sync

__settings__ = xbmcaddon.Addon("script.episodehunter")
__language__ = __settings__.getLocalizedString
__title__ = "EpisodeHunter"

def menu():

    if not helper.is_settings_okey():
        __settings__.openSettings()
        return

    # [Movie, TV, Settings]
    options = [__language__(32009), __language__(32010), __language__(32011)]

    while True:
        select = xbmcgui.Dialog().select(__title__, options)
        if select == -1:
            return
        else:
            if select == 0:  # Movie
                sync.sync_watched_movies(True)
            elif select == 1:  # TV
                sync.sync_watched_series(True)
            elif select == 2:  # Settings
                __settings__.openSettings()

menu()
