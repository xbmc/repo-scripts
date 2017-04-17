"""
This file is entry point for manual start via the programs menu
"""

import xbmcgui
import resources.lib.utils as utils
from service import WatchedList

__remotedebug__ = False
# append pydev remote debugger
if __remotedebug__:
    utils.log("Initialize remote debugging.")
    # Make pydev debugger works for auto reload.
    try:
        import pydevd
        pydevd.settrace('localhost', port=60678, stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        utils.showNotification('WatchedList Error', 'remote debug could not be imported.', xbmc.LOGFATAL)
        sys.exit(1)
    except:
        utils.showNotification('WatchedList Error', 'remote debug in pydev is activated, but remote server not responding.', xbmc.LOGERROR)
        sys.exit(1)


# Create WatchedList Class
WL = WatchedList()

if (not utils.getSetting("autostart") == 'true') or xbmcgui.Dialog().yesno( utils.getString(32101),utils.getString(32001) ):
    # Check if we should run updates (only ask if autostart is on)
    # run the program
    utils.log("Update Library Manual Run.")
    WL.runUpdate(True) # one time update
