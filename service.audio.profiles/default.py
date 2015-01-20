# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import json
import time

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__icon__                = __addon__.getAddonInfo('icon')
__addonpath__           = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')

# name of script for this service work
serviceForScript = 'script.audio.profiles, m'

class Player(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self) 
        
    def onPlayBackStarted(self):
        # get script.audio.profiles settings
        addon2              = xbmcaddon.Addon('script.audio.profiles')
        choice              = addon2.getSetting('player_choice')
        player_choice_d     = addon2.getSetting('player_choice_d')
        player_choice_t     = addon2.getSetting('player_choice_t')
        
        if choice == 'true':
            xbmc.executebuiltin('XBMC.RunScript(' + serviceForScript + ')')
            if player_choice_d == 'true':
                xbmcgui.Window(10000).setProperty('audio_profiles_menu', 'True')
                time.sleep(int(player_choice_t))
                if xbmcgui.Window(10000).getProperty('audio_profiles_menu') == 'True':
                    jsonGetSysSettings = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.ExecuteAction", "params":["back"]},"id":1}')
                    xbmcgui.Window(10000).clearProperty('audio_profiles_menu')

player = Player()

while(not xbmc.abortRequested):
    xbmc.sleep(100)
    