"""
This file is entry point for automatic start via Kodi
"""

import sys

import xbmc

import lib.watchedlist.utils as utils
from lib.watchedlist.watchedlist import WatchedList

__remotedebug__ = False
# Append pydev remote debugger
if __remotedebug__:
    utils.log("Initialize remote debugging.")
    # Make pydev debugger works for auto reload.
    try:
        import pydevd
        pydevd.settrace('localhost', port=60678, stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
                         "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        utils.showNotification('WatchedList Error', 'remote debug could not be imported.', xbmc.LOGERROR)
        sys.exit(1)
    except BaseException:
        utils.showNotification('WatchedList Error', 'remote debug in pydev is activated, but remote server not responding.', xbmc.LOGERROR)
        sys.exit(1)

# Run the program
if xbmc.Monitor().waitForAbort(1.5):  # wait 1.5 seconds to prevent import-errors. TODO: Is this workaround still necessary?
    sys.exit(0)  # Abort was requested while waiting.
utils.log("WatchedList Database Service starting...")
WatchedList().runProgram()
