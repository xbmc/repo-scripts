# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Contextmenu for Animated art
'''

import xbmc
import xbmcgui
from metadatautils import MetadataUtils
from utils import log_msg

# pylint: disable-msg=invalid-constant-name


def get_imdb_id(win, metadatautils):
    '''get imdbnumber for listitem'''
    content_type = win.getProperty("contenttype")
    imdb_id = xbmc.getInfoLabel("ListItem.IMDBNumber").decode('utf-8')
    if not imdb_id:
        imdb_id = xbmc.getInfoLabel("ListItem.Property(IMDBNumber)").decode('utf-8')
    if imdb_id and not imdb_id.startswith("tt"):
        imdb_id = ""
    if not imdb_id:
        year = xbmc.getInfoLabel("ListItem.Year").decode('utf-8')
        title = xbmc.getInfoLabel("ListItem.Title").decode('utf-8').split(",")[0].split("(")[0]
        if content_type in ["episodes", "seasons"]:
            title = xbmc.getInfoLabel("ListItem.TvShowTitle").decode('utf-8')
        if title:
            log_msg("Animated Art: lookup imdbid by title and year: (%s - %s)" % (title, year), xbmc.LOGNOTICE)
            imdb_id = metadatautils.get_omdb_info("", title, year, content_type).get("imdbnumber", "")
        if not imdb_id:
            return title
    return imdb_id

# Kodi contextmenu item to configure the artwork
if __name__ == '__main__':
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    log_msg("Contextmenu for Animated Art opened", xbmc.LOGNOTICE)
    ARTUTILS = MetadataUtils()
    WIN = xbmcgui.Window(10000)
    imdb_id = get_imdb_id(WIN, ARTUTILS)
    WIN.setProperty("SkinHelper.Artwork.ManualLookup", "busy")
    log_msg("Animated Art: Query animated art by IMDBID: %s" % imdb_id, xbmc.LOGNOTICE)
    artwork = ARTUTILS.get_animated_artwork(imdb_id, ignore_cache=True, manual_select=True)
    log_msg("Animated Art result: %s" % artwork, xbmc.LOGNOTICE)
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    xbmc.executebuiltin("Container.Refresh")
    WIN.clearProperty("SkinHelper.Artwork.ManualLookup")
    del WIN
    ARTUTILS.close()
