from bossanova808.constants import ADDON
from bossanova808.logger import Logger
from resources.lib.clean import clean_log


class Store:
    """
    Helper class to read in and store the addon settings, and to provide a centralised store

    from resources.lib.store import Store
    log(f'{Store.whatever}')
    """

    # Static class variables, referred to elsewhere by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods
    destination_path: str = ''
    crashlog_max_days: int = 3

    def __init__(self):
        """
        Load in the addon settings and do basic initialisation stuff
        """
        Store.load_config_from_settings()

    @staticmethod
    def load_config_from_settings():
        """
        Load the addon's configuration from persistent settings.

        Reads the 'log_path' setting and assigns it to Store.destination_path, then logs the resolved path (sanitized with clean_log because these paths may be URLs with embedded user/password details). This is called at startup and when settings are reloaded; it has no return value.
        """
        Logger.info("Loading configuration from settings")
        Store.destination_path = ADDON.getSetting('log_path') or ''
        if Store.destination_path:
            Logger.info(f'Logs will be tossed to: {clean_log(Store.destination_path)}')
        else:
            Logger.warning('No path set to toss logs to.')
        Store.crashlog_max_days = int(ADDON.getSetting('crashlog_max_days')) or 3
        Logger.info(f'Crashlog max days: {Store.crashlog_max_days}')
