import xbmc
from bossanova808.logger import Logger
# noinspection PyPackages
from .store import Store


class KodiEventMonitor(xbmc.Monitor):

    def __init__(self):
        super().__init__()
        Logger.debug('KodiEventMonitor __init__')

    def onSettingsChanged(self):
        Logger.info('onSettingsChanged - reload them.')
        Store.load_config_from_settings()
