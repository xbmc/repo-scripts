"""
Entry point for the Unpause Jumpback Kodi Add-on.

This script serves as the main entry point when the add-on is executed by Kodi.
It wraps the main functionality with exception logging to ensure any errors
are properly captured and logged for debugging purposes.
"""

from bossanova808 import exception_logger
from resources.lib import unpause_jumpback

if __name__ == "__main__":
    with exception_logger.log_exception():
        unpause_jumpback.run()