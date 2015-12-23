import xbmc

def logoff():
	xbmc.executebuiltin("System.Logoff()")

if not xbmc.Player().isPlayingAudio():
	logoff()