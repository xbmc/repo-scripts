import xbmcgui

import kodigui
from lib import util


class BackgroundWindow(kodigui.BaseWindow):
    xmlFile = 'script-tablo-background.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.exit = True

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                # Close is handled in the window manager. We prevent it here because this stays open until all threads are finished
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)
