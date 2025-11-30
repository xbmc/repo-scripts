import xbmc
import xbmcaddon
from datetime import datetime

class Logger:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_name = self.addon.getAddonInfo('name')

    def log(self, message, level=xbmc.LOGINFO):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'[{self.addon_name}] [{timestamp}] {message}'
        xbmc.log(log_message, level)

    def update_result(self, message):
        """Log an update result with a special prefix"""
        self.log(f'[UPDATE_RESULT] {message}', xbmc.LOGINFO)

    def error(self, message):
        self.log(message, xbmc.LOGERROR)

    def info(self, message):
        self.log(message, xbmc.LOGINFO)

    def debug(self, message):
        self.log(message, xbmc.LOGDEBUG)

    def warning(self, message):
        self.log(message, xbmc.LOGWARNING) 