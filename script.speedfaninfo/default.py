from kodi_six import xbmc
import resources.lib.spid as SpeedFan

if ( __name__ == "__main__" ):
    window = SpeedFan.Main()
xbmc.log( '[SpeedFan Info] script stopped', xbmc.LOGNOTICE )