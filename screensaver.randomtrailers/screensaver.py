#dummy screensaver will set screen to black and go fullscreen if windowed

import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()
do_fullscreen = addon.getSetting('do_fullscreen')
exit_requested = False
class MyMonitor(xbmc.Monitor): 
	def __init__( self):
		pass
		
	def onScreensaverDeactivated(self):
		global exit_requested
		exit_requested = True
		
if __name__ == '__main__':
	if do_fullscreen == 'true':
		if not xbmc.getCondVisibility("System.IsFullscreen"):
			xbmc.executebuiltin('xbmc.Action(togglefullscreen)')
	while (not xbmc.abortRequested) and (not exit_requested): 
		xbmc.sleep(1000)
