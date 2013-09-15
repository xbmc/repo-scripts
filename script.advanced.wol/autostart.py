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
		elapsedTime = time.time()-previousTime
		if ( elapsedTime > 5):
			if (wolDelayAfterStandby > 0):
				xbmc.sleep(wolDelayAfterStandby*1000)
			print "script.advanced.wol: Start WOL script after return from standby (Standby took "+str(time.time()-previousTime)+" sec.)"
			default.main(True)
			print "script.advanced.wol: Waiting for resume from standby"
			previousTime = time.time()
			xbmc.sleep(1000)
		else:
			previousTime = time.time()
			xbmc.sleep(1000)