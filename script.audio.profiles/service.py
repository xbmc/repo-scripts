# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')

class Player(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self) 
        
    def onPlayBackStarted(self):
        if 'true' in __addon__.getSetting('player_show'):
            xbmc.executebuiltin('XBMC.RunScript(' + __addon_id__ + ', service)')

player = Player()

while(not xbmc.abortRequested):
    xbmc.sleep(100)
    