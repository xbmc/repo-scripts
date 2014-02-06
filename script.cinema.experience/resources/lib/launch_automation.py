import xbmc, xbmcaddon, xbmcvfs
import sys, os, traceback

__scriptID__             = sys.modules[ "__main__" ].__scriptID__
ha_settings              = sys.modules[ "__main__" ].ha_settings
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
home_automation_folder   = sys.modules[ "__main__" ].home_automation_folder
home_automation_module   = sys.modules[ "__main__" ].home_automation_module
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils

if not xbmcvfs.exists( home_automation_module ):
    source = os.path.join( BASE_RESOURCE_PATH, "ha_scripts", "home_automation.py" )
    xbmcvfs.mkdir( home_automation_folder )
    success = xbmcvfs.copy( source, home_automation_module )
    if success:
        utils.log( "home_automation.py copied", xbmc.LOGNOTICE )
    else:
        utils.log( "home_automation.py not copied", xbmc.LOGNOTICE )

try:
    sys.path.append( home_automation_folder )
    from home_automation import Automate
    # Import HA module set ha_imported to True if successful
    ha_imported = True
except ImportError:
    # or ha_imported to False if unsuccessful
    utils.log( "Failed to import Automate", xbmc.LOGNOTICE )
    ha_imported = False
except:
    traceback.print_exc()
    ha_imported = False
    
class Launch_automation():
    def __init__(self, *args, **kwargs):
        pass

    def launch_automation( self, trigger = None, prev_trigger = None, mode="normal" ):
        if ha_settings[ "ha_enable" ] and ha_imported:
            prev_trigger = Automate().activate_ha( trigger, prev_trigger, mode )
        return prev_trigger

