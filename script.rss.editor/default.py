import sys
import xbmc
import xbmcaddon

ADDONID = xbmcaddon.Addon().getAddonInfo('id')
CWD = xbmcaddon.Addon().getAddonInfo('path')

def log(txt):
    xbmc.log(msg=txt, level=xbmc.LOGDEBUG)

log("%s: started" % ADDONID)

if (__name__ == "__main__"):
    import lib.rssEditor as rssEditor
    ui = rssEditor.GUI("script-RSS_Editor.xml", CWD, "default", setNum = 'set1')
    del ui

sys.modules.clear()
