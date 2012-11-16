import sys
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__cwd__   = __addon__.getAddonInfo('path').decode("utf-8")

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

if __name__ == '__main__':
    import gui
    screensaver_gui = gui.Screensaver('script-python-slideshow.xml', __cwd__, 'default')
    screensaver_gui.doModal()
    del screensaver_gui
    sys.modules.clear()
