import os, sys
import xbmc, xbmcaddon

__addon__    = xbmcaddon.Addon()
__addonid__  = __addon__.getAddonInfo('id')
__cwd__      = __addon__.getAddonInfo('path').decode("utf-8")
__language__ = __addon__.getLocalizedString
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utils import *

def _parse_argv():
    try:
        params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        params = {}
    cache = params.get( "cache", "" )
    return cache

if __name__ == '__main__':
    opts = _parse_argv()
    if opts:
        xbmc.executebuiltin('Notification(%s,%s,%i)' % (__addonid__, __language__(30019), 5000))
        path = __addon__.getSetting('path')
        images = walk(path)
        if not xbmcvfs.exists(CACHEFOLDER):
            xbmcvfs.mkdir(CACHEFOLDER)
        try:
            cache = xbmcvfs.File(CACHEFILE, "w")
            cache.write(str(images))
            cache.close()
        except:
            log('failed to save cachefile')
        xbmc.executebuiltin('Notification(%s,%s,%i)' % (__addonid__, __language__(30020), 5000))
    else:
        import gui
        screensaver_gui = gui.Screensaver('script-python-slideshow.xml', __cwd__, 'default')
        screensaver_gui.doModal()
        del screensaver_gui
        sys.modules.clear()
