# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

ADDON               = xbmcaddon.Addon()
ADDON_ICON          = ADDON.getAddonInfo('icon')
ADDON_NAME          = ADDON.getAddonInfo('name')

def debug(msg):
    if 'true' in ADDON.getSetting('debug'):
        xbmc.log('..::' + ADDON_NAME + '::.. ' + msg)
    
def notify(msg, force=False, title=''):
    if 'true' in ADDON.getSetting('notify') or force is True:
        xbmc.executebuiltin('Notification(' + ADDON_NAME + (' - ' + title.encode('utf-8') if len(title) > 0 else '') + ', ' + msg.encode('utf-8') + ', 4000, ' + ADDON_ICON + ')')