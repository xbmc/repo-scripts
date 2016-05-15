"""
This file is entry point for automatic start via XBMC
"""

import resources.lib.utils as utils
from service import WatchedList
import xbmc

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
        utils.showNotification('WatchedList Error', 'remote debug could not be imported.')
        sys.exit(1)
    except:
        utils.showNotification('WatchedList Error', 'remote debug in pydev is activated, but remote server not responding.')
        sys.exit(1)

# Run the program
xbmc.sleep(1500) # wait 1.5 seconds to prevent import-errors
utils.log("WatchedList Database Service starting...")
WatchedList().runProgram()
