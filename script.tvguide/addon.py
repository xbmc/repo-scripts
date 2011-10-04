import xbmc
import xbmcaddon

import source
import gui
import notification

SOURCES = {
    'YouSee.tv' : source.YouSeeTvSource,
    'DR.dk' : source.DrDkSource,
    'TVTID.dk' : source.TvTidSource,
    'XMLTV' : source.XMLTVSource
    }

ADDON = xbmcaddon.Addon(id = 'script.tvguide')
sourceRef = SOURCES[ADDON.getSetting('source')]

SETTINGS = {
    'cache.path' : xbmc.translatePath(ADDON.getAddonInfo('profile')),
    'xmltv.file' : ADDON.getSetting('xmltv.file'),
    'youseetv.category' : ADDON.getSetting('youseetv.category'),
    'notifications.enabled' : ADDON.getSetting('notifications.enabled'),
    'cache.data.on.xbmc.startup' : ADDON.getSetting('cache.data.on.xbmc.startup')
}

SOURCE = sourceRef(SETTINGS)

n = notification.Notification(SOURCE, ADDON.getAddonInfo('path'), xbmc.translatePath(ADDON.getAddonInfo('profile')))

xbmc.log("[script.tvguide] Using source: " + str(sourceRef))

if __name__ == '__main__':
    w = gui.TVGuide(source = SOURCE, notification = n)
    w.doModal()
    del w
