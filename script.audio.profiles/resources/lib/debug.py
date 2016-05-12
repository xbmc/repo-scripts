# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

__addon__               = xbmcaddon.Addon()
__icon__                = __addon__.getAddonInfo('icon')
__addonname__           = __addon__.getAddonInfo('name')

def debug(msg):
    if 'true' in __addon__.getSetting('debug'):
        xbmc.log('..::' + __addonname__ + '::.. ' + msg)
    
def notify(msg, force=False, title=''):
    if 'true' in __addon__.getSetting('notify') or force is True:
        xbmc.executebuiltin('Notification(' + __addonname__ + (' - ' + title.encode('utf-8') if len(title) > 0 else '') + ', ' + msg.encode('utf-8') + ', 4000, ' + __icon__ + ')')