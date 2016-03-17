# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

__addon__               = xbmcaddon.Addon()
__icon__                = __addon__.getAddonInfo('icon')
__addonname__           = __addon__.getAddonInfo('name')

def debug(msg):
    if 'true' in __addon__.getSetting('debug'):
        xbmc.log('..::' + __addonname__ + '::.. ' + msg)
    
def notify(msg):
    xbmc.executebuiltin('Notification(' + __addonname__ + ', ' + msg + ', 4000, ' + __icon__ + ')')