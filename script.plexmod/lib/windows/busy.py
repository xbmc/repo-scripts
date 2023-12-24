from __future__ import absolute_import
from . import kodigui
from lib import util
from kodi_six import xbmcgui
import threading


class BusyWindow(kodigui.BaseDialog):
    xmlFile = 'script-plex-busy.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080


class BusyClosableWindow(BusyWindow):
    ctx = None

    def onAction(self, action):
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP):
            self.ctx.shouldClose = True


class BusyClosableMsgWindow(BusyClosableWindow):
    xmlFile = 'script-plex-busy_msg.xml'

    def setMessage(self, msg):
        self.setProperty("message", msg)


def dialog(msg='LOADING', condition=None, delay=True):
    def methodWrap(func):
        def inner(*args, **kwargs):
            timer = None
            w = BusyWindow.create(show=not delay)

            if delay:
                timer = threading.Timer(0.5, w.show)
                timer.start()

            try:
                return func(*args, **kwargs)
            finally:
                if timer and timer.is_alive():
                    timer.cancel()
                    timer.join()
                del timer
                w.doClose()
                try:
                    del w
                except:
                    pass
                util.garbageCollect()

        if condition is not None:
            return condition() and inner or func
        return inner

    return methodWrap


def widthDialog(method, msg, *args, **kwargs):
    return dialog(msg or 'LOADING')(method)(*args, **kwargs)


class BusyContext(object):
    w = None
    timer = None
    shouldClose = False
    window_cls = BusyWindow
    delay = False

    def __enter__(self):
        self.w = self.window_cls.create(show=not self.delay)
        if self.delay:
            self.timer = threading.Timer(0.5, lambda: self.w.show())
        self.w.ctx = self
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            util.ERROR()

        if self.timer and self.timer.is_alive():
            self.timer.cancel()
            self.timer.join()

        self.w.doClose()
        del self.w
        self.w = None
        util.garbageCollect()
        return True


class BusyMsgContext(BusyContext):
    window_cls = BusyClosableMsgWindow

    def setMessage(self, msg):
        self.w.setMessage(msg)


class BusySignalContext(BusyMsgContext):
    """
    Duplicates functionality of plex.CallbackEvent to a certain degree
    """
    window_cls = BusyWindow
    delay = True

    def __init__(self, context, signal, wait_max=10, delay=True):
        self.wfSignal = signal
        self.signalEmitter = context
        self.waitMax = wait_max
        self.ignoreSignal = False
        self.signalReceived = False
        self.delay = delay

        super(BusySignalContext, self).__init__()

        context.on(signal, self.onSignal)

    def onSignal(self, *args, **kwargs):
        self.signalReceived = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            util.ERROR()

        try:
            if not self.ignoreSignal:
                waited = 0
                while not self.signalReceived and waited < self.waitMax:
                    util.MONITOR.waitForAbort(0.1)
                    waited += 0.1
        finally:
            self.signalEmitter.off(self.wfSignal, self.onSignal)

        return super(BusySignalContext, self).__exit__(exc_type, exc_val, exc_tb)


class BusyClosableMsgContext(BusyMsgContext):
    pass
