import traceback
from typing import Union

import xbmc


_DEVELOPMENT = False


class Logger:
    def __init__(self, name: str) -> None:
        self._name = name

    def log(
            self,
            message: str,
            exc: Union[Exception, None] = None,
            level: Union[int, None] = None) -> None:
        """Log the message."""
        if level is not None:
            xbmc.log(f'{self._name}: {message}', level)
        elif _DEVELOPMENT:
            xbmc.log(f'{self._name}: {message}', xbmc.LOGINFO)
        else:
            xbmc.log(f'{self._name}: {message}', xbmc.LOGDEBUG)
        if exc is not None:
            if _DEVELOPMENT:
                xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            else:
                xbmc.log(repr(exc), xbmc.LOGERROR)

    def error(
            self,
            message: str,
            exc: Union[Exception, None] = None) -> None:
        """Log the error."""
        self.log(message, exc=exc, level=xbmc.LOGERROR)
