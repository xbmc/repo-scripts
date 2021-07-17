import xbmc
from .common import *
from .store import Store


class KodiEventMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        log('KodiEventMonitor __init__')

    def onSettingsChanged(self):
        log('onSettingsChanged - reload them.')
        Store.load_config_from_settings()

    def onAbortRequested(self):
        log('onAbortRequested')
        log("Abort Requested")
