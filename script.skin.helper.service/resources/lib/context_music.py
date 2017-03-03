# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Contextmenu for Music art
'''

import xbmc
import xbmcgui
from metadatautils import MetadataUtils
import time

# pylint: disable-msg=invalid-constant-name

# Kodi contextmenu item to configure music artwork
if __name__ == '__main__':

    win = xbmcgui.Window(10000)
    metadatautils = MetadataUtils()
    win.setProperty("SkinHelper.Artwork.ManualLookup", "busy")
    track = xbmc.getInfoLabel("ListItem.Title").decode('utf-8')
    album = xbmc.getInfoLabel("ListItem.Album").decode('utf-8')
    artist = xbmc.getInfoLabel("ListItem.Artist").decode('utf-8')
    disc = xbmc.getInfoLabel("ListItem.DiscNumber").decode('utf-8')
    metadatautils.music_artwork_options(artist, album, track, disc)
    metadatautils.close()
    # refresh music widgets
    timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    win.setProperty("widgetreload-music", timestr)
    win.setProperty("widgetreloadmusic", timestr)
    win.setProperty("widgetreload-albums", timestr)
    win.setProperty("widgetreload-songs", timestr)
    win.clearProperty("SkinHelper.Artwork.ManualLookup")
    del win
    del metadatautils
