import xbmc
import xbmcaddon
import xbmcgui

import quickjson
from themoviedb import TheMovieDatabase

addon = xbmcaddon.Addon()

def graball_stingertags():
    if addon.getSetting('fulllibrary_tagschecked') != 'false':
        return
    progress = xbmcgui.DialogProgress()
    progress.create(addon.getLocalizedString(32400), xbmc.getLocalizedString(314))
    movielist = quickjson.get_movies(listfilter=quickjson.nostingertags_filter)
    if not movielist:
        progress.close()
        return
    monitor = xbmc.Monitor()
    tmdb = TheMovieDatabase()
    tmdb.monitor = monitor
    count = 0
    cancelled = False
    for movie in movielist:
        if count % 5 == 0:
            progress.update(count * 100 / len(movielist), xbmc.getLocalizedString(194), movie['label'])
        tags = tmdb.get_stingertags(movie['imdbnumber'])
        if tags:
            tags.extend(movie['tag'])
            quickjson.set_movie_details(movie['movieid'], tag=tags)
        count += 1
        if progress.iscanceled() or monitor.waitForAbort(0.15):
            cancelled = True
            break

    progress.close()
    if not cancelled:
        xbmcgui.Dialog().ok(addon.getLocalizedString(32400), addon.getLocalizedString(32401))
        addon.setSetting('fulllibrary_tagschecked', 'true')
