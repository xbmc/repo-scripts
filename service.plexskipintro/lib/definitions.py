import xbmc, xbmcaddon, xbmcvfs
OK_BUTTON = 201
NEW_BUTTON = 202
DISABLE_BUTTON = 210
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
addonInfo = xbmcaddon.Addon().getAddonInfo
settings = xbmcaddon.Addon().getSetting
addonPath = xbmcvfs.translatePath(addonInfo('path'))
introFound = True
introStartTime = 0
introEndTime = 0
chosen = False
Dialog = None
running = False
Ran = False
default_timeout = xbmcaddon.Addon().getSettingInt("default_timeout")