## -*- coding: utf-8 -*-
import xbmc
import xbmcvfs
import xbmcgui
import os

themepath =  os.path.join(xbmc.getInfoLabel( "listitem.path" ), "theme" + ".mp3")

if xbmcvfs.exists(themepath):
    xbmc.executebuiltin( "SetProperty(theme_ready,true,home)" )