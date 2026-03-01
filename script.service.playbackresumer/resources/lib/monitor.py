import xbmc
from bossanova808.logger import Logger
# noinspection PyPackages
from .store import Store


class KodiEventMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        Logger.debug('KodiEventMonitor __init__')

    def onSettingsChanged(self):
        """
        Handle Kodi settings changes by reloading the add-on configuration from settings.
        
        Invoked when Kodi reports settings have changed; calls the Store to reload configuration so runtime state reflects updated settings.
        """
        Logger.info('onSettingsChanged - reload them.')
        Store.load_config_from_settings()


