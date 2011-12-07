import os
import xbmc
import xbmcaddon

def moviequiz_excepthook(type, value, traceback):
    import xbmcgui
    print 'Unhandled error:', type, value, traceback
    xbmcgui.Dialog().ok('Unhandled exception', str(type), str(value), 'Exiting addon...')
#    sys.exit(1)


#sys.excepthook = moviequiz_excepthook

# Make sure data dir exists
ADDON = xbmcaddon.Addon()
if not os.path.exists(xbmc.translatePath(ADDON.getAddonInfo('profile'))):
    os.makedirs(xbmc.translatePath(ADDON.getAddonInfo('profile')))

from quizlib.gui import MenuGui
w = MenuGui()
w.doModal()
del w

