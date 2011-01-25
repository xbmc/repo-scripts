import os

import xbmc
import xbmcaddon

# constants are initialized in init() method
ADDON_ID = None
ADDON = None
ADDON_DATA_PATH = None
ADDON_PATH = None
ADDON_HANDLE = None
ADDON_PARAMS = None

def init(sysArgs):
    """Initializes the ADDON_* constants

    Keyword arguments:
    sysArgs -- Usually the value of sys.argv as passed by XBMC
    """
    global ADDON_ID, ADDON, ADDON_DATA_PATH, ADDON_PATH, ADDON_HANDLE, ADDON_PARAMS

    # Initialize convenience constants
    ADDON_ID = os.path.basename(os.getcwd())
    ADDON = xbmcaddon.Addon(id = ADDON_ID)
    ADDON_DATA_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
    if(len(sysArgs) > 1):
        ADDON_PATH = sysArgs[0]
        ADDON_HANDLE = int(sysArgs[1])
        ADDON_PARAMS = parseParams(sysArgs[2][1:])

    # Create addon data path
    if(not os.path.isdir(os.path.dirname(ADDON_DATA_PATH))):
        os.makedirs(os.path.dirname(ADDON_DATA_PATH))

def msg(id):
    return ADDON.getLocalizedString(id)

def parseParams(input):
    params = {}
    for pair in input.split('&'):
        if(pair.find('=') >= 0):
            keyvalue = pair.split('=', 1)
            params[keyvalue[0]] = keyvalue[1]
        else:
            params[pair] = None

    return params
