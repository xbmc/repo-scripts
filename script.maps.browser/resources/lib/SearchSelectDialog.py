import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()


class SearchSelectDialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.items = kwargs.get('listing')
        self.lon = ''
        self.lat = ''

    def onInit(self):
        self.list = self.getControl(6)
        self.list.controlLeft(self.list)
        self.list.controlRight(self.list)
        self.getControl(3).setVisible(False)
        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(ADDON.getLocalizedString(32015))
        self.list.addItems(self.items)
        self.setFocus(self.list)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        if controlID in [3, 6]:
            self.lat = self.list.getSelectedItem().getProperty("lat")
            self.lon = self.list.getSelectedItem().getProperty("lon")
            self.close()

    def onFocus(self, controlID):
        pass
