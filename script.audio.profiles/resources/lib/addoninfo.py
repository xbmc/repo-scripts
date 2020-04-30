from kodi_six import xbmc, xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))
ADDON_PATH_DATA = xbmc.translatePath( ADDON.getAddonInfo('profile') )
ADDON_LANG = ADDON.getLocalizedString