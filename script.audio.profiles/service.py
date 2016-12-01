# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

ADDON               = xbmcaddon.Addon()
ADDON_ID            = ADDON.getAddonInfo('id')

class Player(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self) 
        
    def onPlayBackStarted(self):
        if 'true' in ADDON.getSetting('player_show'):
            xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', service)')

player = Player()

while(not xbmc.abortRequested):
    xbmc.sleep(100)
    