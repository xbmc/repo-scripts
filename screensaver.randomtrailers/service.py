# monitors onScreensaverActivated event and checks guisettings.xml for screensaver.randomtrailers.
# if found it will launch the screensaver.randomtrailers script which will show trailers.
# this gets around XBMC killing a screensaver 5 seconds after onScreensaverDeactivate

import xbmc
import os

def isTrailerScreensaver():
	pguisettings = xbmc.translatePath( os.path.join( 'special://userdata' , 'guisettings.xml' ) ).decode('utf-8')
	xbmc.log(pguisettings)
	name = 'screensaver.randomtrailers'
	if name in file( pguisettings, "r" ).read():
		xbmc.log('found screensaver.randomtrailers in guisettings.html')
		return True
	else:
		xbmc.log('did not screensaver.randomtrailers in guisettings.html')
		return False

	
class MyMonitor(xbmc.Monitor): 
	def __init__( self):
		pass
		
	def onScreensaverActivated(self):
		if isTrailerScreensaver():
			xbmc.executebuiltin('xbmc.RunScript("screensaver.randomtrailers","no_genre")')
		
m = MyMonitor()
while (not xbmc.abortRequested):
	xbmc.sleep(1000)
xbmc.Player().stop
del m
