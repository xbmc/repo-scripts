# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Contextmenu for Pvr art
'''

import xbmc
import xbmcgui
from metadatautils import MetadataUtils

# pylint: disable-msg=invalid-constant-name

# Kodi contextmenu item to configure pvr artwork
if __name__ == '__main__':

    ##### PVR Artwork ########
    win = xbmcgui.Window(10000)
    win.setProperty("SkinHelper.Artwork.ManualLookup", "busy")
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    title = xbmc.getInfoLabel("ListItem.Title").decode('utf-8')
    if not title:
        title = xbmc.getInfoLabel("ListItem.Label").decode('utf-8')
    channel = xbmc.getInfoLabel("ListItem.ChannelName").decode('utf-8')
    genre = xbmc.getInfoLabel("ListItem.Genre").decode('utf-8')
    metadatautils = MetadataUtils()
    metadatautils.pvr_artwork_options(title, channel, genre)
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    win.clearProperty("SkinHelper.Artwork.ManualLookup")
    metadatautils.close()
    del win
