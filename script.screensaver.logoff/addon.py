import xbmc

class logoff(xbmc.Monitor):
        xbmc.executebuiltin("System.Logoff()")

mylogoff = logoff()
del mylogoff