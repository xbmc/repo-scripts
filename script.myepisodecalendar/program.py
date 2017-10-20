import xbmcaddon

try:
    startparam = sys.argv[1]
except:
	xbmcaddon.Addon().openSettings()
else:
	import main