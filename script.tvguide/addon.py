import xbmc
import xbmcaddon

import source
import gui

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
    'youseetv.category' : ADDON.getSetting('youseetv.category')
}

SOURCE = sourceRef(SETTINGS)

xbmc.log("Loading TVGuide [script.tvguide] source: " + str(sourceRef))

if __name__ == '__main__':
    w = gui.TVGuide(source = SOURCE)
    w.doModal()
    del w
