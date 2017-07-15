import xbmc

from utils import log


class Monitor(xbmc.Monitor):
    def __init__(self, api, *args, **kwargs):
        xbmc.Monitor.__init__(self)

        self._api = api

    def onNotification(self, sender, method, data):
        log('onNotification')
        log('sender {0}'.format(bool(sender == 'script.simkl')))
        if sender == "script.simkl":
            if method == 'Other.login':
                self._api.login()

    def onSettingsChanged(self):
        log("CHANGED")
