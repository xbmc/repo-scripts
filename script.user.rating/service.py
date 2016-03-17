# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import json

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__icon__                = __addon__.getAddonInfo('icon')
__addonpath__           = xbmc.translatePath(__addon__.getAddonInfo('path'))

#name of script for this service work
serviceForScript = 'script.user.rating'

class Monitor(xbmc.Monitor):
    
    def __init__(self):
        xbmc.Monitor.__init__(self)
    
    def onNotification(self, sender, method, data):
        media = ['movie', 'episode']
        
        if method == 'VideoLibrary.OnUpdate':
            data = json.loads(data)
            if 'playcount' in data and data['playcount'] > 0:
                if 'item' in data and 'type' in data['item'] and data['item']['type'] in media and 'id' in data['item']:
                    idDB = data['item']['id']
                    mType = data['item']['type']
                    
                    xbmc.executebuiltin('XBMC.RunScript(' + serviceForScript + ', ' + method + ', ' + str(idDB) + ', ' + mType + ')')
    
monitor = Monitor()

while(not xbmc.abortRequested):
    xbmc.sleep(100)
    