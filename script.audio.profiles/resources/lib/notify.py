# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

from kodi_six import xbmc, xbmcaddon, xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')


def popup(msg, force=False, title=''):
    if 'true' in ADDON.getSetting('notify') or force is True:
        if title:
            title = '%s - %s' % (ADDON_NAME, title)
        else:
            title = ADDON_NAME
        xbmcgui.Dialog().notification(title, msg, icon=ADDON_ICON)


def logInfo(msg):
    xbmc.log('[%s] %s' % (ADDON_NAME, msg), level=xbmc.LOGINFO)


def logError(msg):
    xbmc.log('[%s] %s' % (ADDON_NAME, msg), level=xbmc.LOGERROR)


def logDebug(msg):
    if ADDON.getSetting('debug').lower() == 'true':
        xbmc.log('[%s] %s' % (ADDON_NAME, msg), level=xbmc.LOGDEBUG)


