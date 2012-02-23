# Wake-On-LAN

import xbmcaddon, sys

settings = xbmcaddon.Addon( id="script.advanced.wol" )

# Read Settings
settings = xbmcaddon.Addon( id="script.advanced.wol" )
autostart = settings.getSetting("autostart")

if (autostart == "true"):
  import default
  default.main()