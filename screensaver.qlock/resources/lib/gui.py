import sys
import xbmc
import xbmcgui


__addon__ = sys.modules["__main__"].__addon__
__addonid__ = sys.modules["__main__"].__addonid__
__cwd__ = sys.modules["__main__"].__cwd__


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)


class Screensaver(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.stop = False
        self.Monitor = MyMonitor(action=self.exit)

    def onInit(self):
        while (not xbmc.abortRequested) and (not self.stop):
            xbmc.sleep(1000)

    def exit(self):
        self.stop = True
        self.close()


class MyMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()
