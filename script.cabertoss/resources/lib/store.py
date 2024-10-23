from bossanova808.constants import *
from bossanova808.logger import Logger
from resources.lib.clean import *


class Store:
    """
    Helper class to read in and store the addon settings, and to provide a centralised store

    from resources.lib.store import Store
    log(f'{Store.whatever}')
    """

    # Static class variables, referred to elsewhere by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods
    destination_path = None

    def __init__(self):
        """
        Load in the addon settings and do basic initialisation stuff
        """
        Store.load_config_from_settings()

    @staticmethod
    def load_config_from_settings():
        """
        Load in the addon settings, at start or reload them if they have been changed
        Log each setting as it is loaded
        """
        Logger.info("Loading configuration from settings")
        Store.destination_path = ADDON.getSetting('log_path')

        Logger.info(f'Logs will be tossed to: {clean_log(Store.destination_path)}')





