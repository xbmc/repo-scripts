# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import json

ADDON               = xbmcaddon.Addon()
ADDON_ID            = ADDON.getAddonInfo('id')

profiles = ['1', '2', '3', '4', '5']
susppend_auto_change = False

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        
        # gui
        if ADDON.getSetting('auto_gui') in profiles:
            xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_gui') + ')')
            
    def onNotification(self, sender, method, data):
        global susppend_auto_change
        
        data = json.loads(data)
        
        if 'Player.OnStop' in method or 'System.OnWake' in method:
            # resume auto change
            susppend_auto_change = False
            
            # gui
            if ADDON.getSetting('auto_gui') in profiles:
                xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_gui') + ')')
        
        if 'Player.OnPlay' in method:
            
            if susppend_auto_change is not True:
                
                # susppend auto change
                susppend_auto_change = True
                
                # auto show dialog
                if 'true' in ADDON.getSetting('player_show'):
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', service)')
                
                # movies
                if ADDON.getSetting('auto_movies') in profiles and 'item' in data and 'type' in data['item'] and 'movie' in data['item']['type']:
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_movies') + ')')
            
                # tvshows
                if ADDON.getSetting('auto_tvshows') in profiles and 'item' in data and 'type' in data['item'] and 'episode' in data['item']['type']:
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_tvshows') + ')')
            
                # tvshows
                if ADDON.getSetting('auto_pvr') in profiles and 'item' in data and 'channeltype' in data['item']:
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_pvr') + ')')
                    
                # music
                if ADDON.getSetting('auto_music') in profiles and 'item' in data and 'type' in data['item'] and 'song' in data['item']['type']:
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_ID + ', ' + ADDON.getSetting('auto_music') + ')')
                
monitor = Monitor()

while(not xbmc.abortRequested):
    xbmc.sleep(100)
    