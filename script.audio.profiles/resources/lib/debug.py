# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

ADDON               = xbmcaddon.Addon()
ADDON_ICON          = ADDON.getAddonInfo('icon')
ADDON_NAME          = ADDON.getAddonInfo('name')

def notice(msg):
    xbmc.log('..::' + ADDON_NAME + '::.. ' + msg, level=xbmc.LOGNOTICE)

def debug(msg):
    xbmc.log('..::' + ADDON_NAME + '::.. ' + msg, level=xbmc.LOGDEBUG)

def error(msg):
    xbmc.log('..::' + ADDON_NAME + '::.. ' + msg, level=xbmc.LOGERROR)

def notify(msg, force=False, title=''):
    if 'true' in ADDON.getSetting('notify') or force is True:
        xbmc.executebuiltin('Notification(' + ADDON_NAME + (' - ' + title.encode('utf-8') if len(title) > 0 else '') + ', ' + msg.encode('utf-8') + ', 4000, ' + ADDON_ICON + ')')