# Wake-On-LAN

import xbmc, xbmcgui, xbmcaddon

settings = xbmcaddon.Addon( id="script.advanced.wol" )

# Read Settings
settings = xbmcaddon.Addon( id="script.advanced.wol" )
autostart = settings.getSetting("autostart")

performWakeup = False

if (autostart == "true"):
  import default