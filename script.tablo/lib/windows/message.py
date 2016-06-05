import xbmcgui
import kodigui

from lib import util

WM = None


class MessageWindow(kodigui.BaseWindow):
    name = 'MESSAGE'
    xmlFile = 'script-tablo-message.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.title = kwargs.get('title') or ''
        self.message = kwargs.get('message')

    def onFirstInit(self):
        self.setProperty('title', self.title)
        self.setProperty('message', self.message)

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_MOVE_LEFT):
                WM.showMenu()
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)
