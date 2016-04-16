import sys, os
import xbmc, xbmcaddon

# Script constants
ADDON      = xbmcaddon.Addon()
VERSION    = ADDON.getAddonInfo('version')
LANGUAGE   = ADDON.getLocalizedString
CWD        = ADDON.getAddonInfo('path')

def log(txt):
    xbmc.log(msg=txt, level=xbmc.LOGDEBUG)

log("[SCRIPT] '%s: version %s' initialized!" % (ADDON, VERSION, ))

if (__name__ == "__main__"):
    import resources.lib.rssEditor as rssEditor
    ui = rssEditor.GUI("script-RSS_Editor.xml", CWD, "default", setNum = 'set1')
    del ui

sys.modules.clear()
