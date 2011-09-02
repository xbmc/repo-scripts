import sys

def moviequiz_excepthook(type, value, traceback):
    import xbmcgui
    print 'Unhandled error:', type, value, traceback
    xbmcgui.Dialog().ok('Unhandled exception', str(type), str(value), 'Exiting addon...')
#    sys.exit(1)


#sys.excepthook = moviequiz_excepthook

from quizlib.gui import MenuGui
w = MenuGui()
w.doModal()
del w

