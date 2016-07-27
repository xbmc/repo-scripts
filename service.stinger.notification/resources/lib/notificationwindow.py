import xbmcgui

class NotificationWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.stingertype = None
        self.message = None
        super(NotificationWindow, self).__init__()

    def onInit(self):
        try:
            type_control = self.getControl(100)
            type_control.setLabel(self.stingertype)
        except RuntimeError:
            pass
        try:
            message_control = self.getControl(101)
            message_control.setLabel(self.message)
        except RuntimeError:
            pass

    def onAction(self, action):
        # just get out of the way
        self.close()
