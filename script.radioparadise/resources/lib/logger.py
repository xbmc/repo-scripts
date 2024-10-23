import traceback

import xbmc


DEVELOPMENT = False


class Logger():
    def __init__(self, name):
        self.name = name

    def log(self, message, level=None):
        """Log the message."""
        if level is not None:
            xbmc.log(f'{self.name}: {message}', level)
        elif DEVELOPMENT:
            xbmc.log(f'{self.name}: {message}', xbmc.LOGINFO)
        else:
            xbmc.log(f'{self.name}: {message}', xbmc.LOGDEBUG)

    def exception(self, exc):
        """Log the exception."""
        if DEVELOPMENT:
            self.log(traceback.format_exc(), xbmc.LOGERROR)
        else:
            self.log(repr(exc), xbmc.LOGERROR)
