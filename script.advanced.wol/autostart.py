# Wake-On-LAN

import xbmcaddon, sys, time

# Read Settings
settings = xbmcaddon.Addon( id="script.advanced.wol" )
autostart = settings.getSetting("autostart")
wolAfterStandby = settings.getSetting("wolAfterStandby")
wolDelayOnLaunch = int(settings.getSetting("wolDelayOnLaunch"))
wolDelayAfterStandby = int(settings.getSetting("wolDelayAfterStandby"))

if (autostart == "true"):
  import default
  if (wolDelayOnLaunch > 0):
	xbmc.sleep(wolDelayOnLaunch*1000)
  default.main(True)
  if (wolAfterStandby == "true"):
	print "script.advanced.wol: Waiting for resume from standby"
	previousTime = time.time()
	while (not xbmc.abortRequested):
		if ( time.time()-previousTime > 5):
			if (wolDelayAfterStandby > 0):
				xbmc.sleep(wolDelayAfterStandby*1000)
			print "script.advanced.wol: Start WOL script after return from standby"
			default.main(True)
			previousTime = time.time()
			xbmc.sleep(1000)
		else:
			previousTime = time.time()
			xbmc.sleep(1000)