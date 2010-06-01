import sys
import os
import xbmc
import string
import xbmcaddon
__scriptname__ = "XBMC Subtitles"
__scriptid__ = "script.xbmc.subtitles"
__author__ = "Amet"
__version__ = "1.6.8"
__XBMC_Revision__ = "29565"

if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id='script.xbmc.subtitles')

__language__ = __settings__.getLocalizedString
#############-----------------Is script runing from OSD? -------------------------------###############

if not xbmc.getCondVisibility('videoplayer.isfullscreen') :
    __settings__.openSettings()
    if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
else:
    skin = "main"
    xbmc.output("XBMC Subtitles version [ %s ]\nXBMC Subtitles skin XML: [ %s ]" % (__version__,skin,),level=xbmc.LOGDEBUG) 
    if ( __name__ == "__main__" ):          
        import gui
        ui = gui.GUI( "script-XBMC-Subtitles-%s.xml" % skin , os.getcwd(), "Default")
        ui.doModal()
        if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
        del ui
        sys.modules.clear()


  
