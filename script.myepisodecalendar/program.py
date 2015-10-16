import xbmcaddon

try:
    startparam = sys.argv[1]
except:
    startparam = False

if (startparam is False):
	xbmcaddon.Addon().openSettings()
else:
	import main