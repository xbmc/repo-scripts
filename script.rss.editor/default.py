import sys, os
import xbmc, xbmcaddon

# Script constants
__addon__      = xbmcaddon.Addon()
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__cwd__        = __addon__.getAddonInfo('path')

def log(txt):
    xbmc.log(msg=txt, level=xbmc.LOGDEBUG)

log("[SCRIPT] '%s: version %s' initialized!" % (__addon__, __version__, ))

if (__name__ == "__main__"):
    import resources.lib.rssEditor as rssEditor
    ui = rssEditor.GUI("script-RSS_Editor-rssEditor.xml", __cwd__, "default", setNum = 'set1')
    del ui

sys.modules.clear()
