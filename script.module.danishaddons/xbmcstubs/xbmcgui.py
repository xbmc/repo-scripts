__author__ = 'twi'

class DialogProgress():
    def __init__(self):
        pass

    def create(self, title):
        return DialogProgress()

    def update(handle, progress, line1 = None, line2 = None, line3 = None):
        pass

    def close(self):
        pass

    def iscanceled(self):
        return False


class ListItem():
    def __init__(self, title = None, iconImage = None, thumbnailImage = None, path = None):
        self.title = title
        self.iconImage = iconImage
        self.url = path

    def setInfo(self, type, infoLabels):
        pass

    def setLabel2(self, label2):
        self.label2 = label2

    def setProperty(self, property, value):
        pass